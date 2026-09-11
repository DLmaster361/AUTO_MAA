"""HSR 外部脚本更新的事务与版本比较。

覆盖两件在真机上不好复现、但错了会毁掉用户安装目录的事：崩在改名中途时能
否逐字节回滚，以及包外文件（用户自定义策略）会不会被误删。
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from app.task.HSR.tools.update.apply import (
    HSRUpdateApplyError,
    apply_package,
    has_pending_journal,
    journal_path,
    rollback,
)
from app.task.HSR.tools.update.discover import HSRUpdateError, is_newer
from app.task.HSR.tools.update.engines import get_spec, select_asset_name


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot(root: Path) -> dict[str, str]:
    return {
        item.relative_to(root).as_posix(): _digest(item)
        for item in sorted(root.rglob("*"))
        if item.is_file() and ".automas_update" not in item.parts
    }


def _make_install(root: Path) -> None:
    """造一个像 SRA 的安装目录：上游文件 + 用户自定义内容。"""

    root.mkdir(parents=True, exist_ok=True)
    (root / "SRA-cli.exe").write_bytes(b"old-binary")
    (root / "resources").mkdir()
    (root / "resources" / "img.png").write_bytes(b"old-image")
    strategies = root / "tasks" / "currency_wars" / "strategies"
    strategies.mkdir(parents=True)
    (strategies / "template.json").write_text("upstream-v1", encoding="utf-8")
    # 用户自己另存的策略：包里没有，任何时候都不许动它
    (strategies / "my-custom.json").write_text("user-owned", encoding="utf-8")
    # 用户状态目录：包外，同样不许动
    (root / "logs").mkdir()
    (root / "logs" / "run.log").write_text("keep me", encoding="utf-8")


def _make_zip(path: Path, entries: dict[str, bytes], *, root_folder: str = "") -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in entries.items():
            archive.writestr(f"{root_folder}{name}" if root_folder else name, payload)
    return path


@pytest.fixture
def install(tmp_path: Path) -> Path:
    root = tmp_path / "install"
    _make_install(root)
    return root


@pytest.fixture
def package(tmp_path: Path) -> Path:
    return _make_zip(
        tmp_path / "update.zip",
        {
            "SRA-cli.exe": b"new-binary",
            "resources/img.png": b"old-image",  # 内容相同，应被跳过
            "resources/added.png": b"brand-new",
            "tasks/currency_wars/strategies/template.json": b"upstream-v2",
        },
    )


def test_apply_updates_changed_and_keeps_user_files(
    install: Path, package: Path
) -> None:
    before = _snapshot(install)

    result = apply_package(
        package,
        install,
        engine="SRA",
        from_version="v2.19.0",
        to_version="v2.21.0",
        seven_zip=None,
    )

    # 内容相同的文件不该计入改动
    assert result.changed_files == 3
    assert (install / "SRA-cli.exe").read_bytes() == b"new-binary"
    assert (install / "resources" / "added.png").read_bytes() == b"brand-new"

    # 包内同名的上游模板会被覆盖——与 M7A/SRA 自己的更新器行为一致
    strategies = install / "tasks" / "currency_wars" / "strategies"
    assert (
        strategies.joinpath("template.json").read_text(encoding="utf-8")
        == "upstream-v2"
    )

    # 包外的一律不动
    assert (
        strategies.joinpath("my-custom.json").read_text(encoding="utf-8")
        == "user-owned"
    )
    assert (install / "logs" / "run.log").read_text(encoding="utf-8") == "keep me"
    assert before["resources/img.png"] == _snapshot(install)["resources/img.png"]

    # 成功后不留工作目录
    assert not has_pending_journal(install)
    assert not (install / ".automas_update").exists()


def test_rollback_restores_byte_for_byte(
    install: Path, package: Path, monkeypatch
) -> None:
    before = _snapshot(install)

    real_replace = __import__("os").replace
    calls = {"n": 0}

    def flaky_replace(src, dst):
        calls["n"] += 1
        if calls["n"] == 4:  # 改到一半炸
            raise OSError("simulated failure mid-commit")
        return real_replace(src, dst)

    monkeypatch.setattr("app.task.HSR.tools.update.apply.os.replace", flaky_replace)

    with pytest.raises(HSRUpdateApplyError) as excinfo:
        apply_package(
            package,
            install,
            engine="SRA",
            from_version="v2.19.0",
            to_version="v2.21.0",
            seven_zip=None,
        )

    assert excinfo.value.rolled_back is True
    assert _snapshot(install) == before
    assert not has_pending_journal(install)


def test_rollback_from_leftover_journal(install: Path, package: Path) -> None:
    """模拟进程被杀：journal 和 backup 都在，下次启动应能收拾干净。"""

    before = _snapshot(install)
    work = install / ".automas_update"
    backup = work / "backup"
    backup.mkdir(parents=True)

    # 手工制造「已把旧文件挪走、新文件已就位」的中间态
    (backup / "SRA-cli.exe").write_bytes(b"old-binary")
    (install / "SRA-cli.exe").write_bytes(b"new-binary")
    (install / "resources" / "added.png").write_bytes(b"brand-new")
    journal_path(install).write_text(
        json.dumps(
            {
                "schema": 1,
                "engine": "SRA",
                "from_version": "v2.19.0",
                "to_version": "v2.21.0",
                "entries": [
                    {"rel": "SRA-cli.exe", "action": "replace"},
                    {"rel": "resources/added.png", "action": "create"},
                ],
            }
        ),
        encoding="utf-8",
    )

    assert has_pending_journal(install) is True
    assert rollback(install) is True
    assert _snapshot(install) == before
    assert not work.exists()


def test_rollback_without_journal_is_noop(install: Path) -> None:
    assert rollback(install) is False


def test_pending_journal_is_rolled_back_before_a_new_apply(
    install: Path, tmp_path: Path
) -> None:
    """崩溃后紧接着再来一次更新，不能把上一轮的备份冲掉。

    ``apply_package`` 开头会重置 backup 目录，而崩溃留下的 backup 里存着唯一
    一份旧文件。手动更新入口（``POST /hsr/update``）不像任务流程那样先经过
    ``prepare()`` 的回滚，所以回滚必须是 ``apply_package`` 自己的前置动作。
    """

    before = _snapshot(install)

    # 造出「旧文件已挪进 backup、新文件尚未就位」的崩溃中间态
    work = install / ".automas_update"
    backup = work / "backup"
    backup.mkdir(parents=True)
    (backup / "SRA-cli.exe").write_bytes(b"old-binary")
    (install / "SRA-cli.exe").unlink()
    journal_path(install).write_text(
        json.dumps(
            {
                "schema": 1,
                "engine": "SRA",
                "from_version": "v2.19.0",
                "to_version": "v2.21.0",
                "entries": [{"rel": "SRA-cli.exe", "action": "replace"}],
            }
        ),
        encoding="utf-8",
    )
    assert not (install / "SRA-cli.exe").exists()

    # 紧接着来一个解不开的包：即便这次更新失败，旧文件也必须已经被救回来
    broken = tmp_path / "broken.zip"
    broken.write_bytes(b"this is not a zip at all")

    with pytest.raises(Exception):
        apply_package(
            broken,
            install,
            engine="SRA",
            from_version="v2.19.0",
            to_version="v2.21.0",
            seven_zip=None,
        )

    assert (install / "SRA-cli.exe").read_bytes() == b"old-binary"
    assert _snapshot(install) == before


@pytest.mark.parametrize(
    "bad_journal",
    [
        b"{ this is not json",
        json.dumps({"schema": 999, "entries": []}).encode(),
    ],
    ids=["corrupt-json", "unknown-schema"],
)
def test_unreadable_journal_blocks_apply_instead_of_wiping_backup(
    install: Path, tmp_path: Path, bad_journal: bytes
) -> None:
    """rollback() 对读不懂的 journal 是返回 False 而不是抛。

    apply_package 若不查这个返回值，紧接着的 _reset_dir(backup) 就会把上一轮
    崩溃留下的唯一备份清掉。这里备份里的文件必须原样留着、journal 也留着，
    等人来看。
    """

    work = install / ".automas_update"
    backup = work / "backup"
    backup.mkdir(parents=True)
    (backup / "SRA-cli.exe").write_bytes(b"old-binary")
    journal_path(install).write_bytes(bad_journal)

    with pytest.raises(HSRUpdateError, match="无法识别的未完成更新记录"):
        apply_package(
            tmp_path / "irrelevant.zip",
            install,
            engine="SRA",
            from_version="v2.19.0",
            to_version="v2.21.0",
            seven_zip=None,
        )

    assert (backup / "SRA-cli.exe").read_bytes() == b"old-binary"
    assert has_pending_journal(install)


def test_single_root_folder_is_stripped(tmp_path: Path, install: Path) -> None:
    """M7A 的包是单根 update/ 或 March7thAssistant_full/，必须脱壳。"""

    package = _make_zip(
        tmp_path / "wrapped.zip",
        {"SRA-cli.exe": b"new-binary"},
        root_folder="March7thAssistant_full/",
    )

    apply_package(
        package,
        install,
        engine="M7A",
        from_version="v2026.8.28",
        to_version="v2026.9.7",
        seven_zip=None,
    )

    assert (install / "SRA-cli.exe").read_bytes() == b"new-binary"
    assert not (install / "March7thAssistant_full").exists()


def test_zip_slip_is_rejected(tmp_path: Path, install: Path) -> None:
    package = tmp_path / "evil.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("../escaped.txt", b"nope")

    with pytest.raises(Exception, match="越界"):
        apply_package(
            package,
            install,
            engine="SRA",
            from_version=None,
            to_version="v9.9.9",
            seven_zip=None,
        )

    assert not (install.parent / "escaped.txt").exists()


def test_flat_package_with_one_directory_is_not_stripped(
    install: Path, tmp_path: Path
) -> None:
    """扁平包恰好只含一个目录时，不能把它当成外壳脱掉。

    判据是可执行文件在不在顶层——只数「顶层是否只有一个目录」会误脱。
    """

    package = _make_zip(
        tmp_path / "flat.zip",
        {"SRA-cli.exe": b"new-binary", "resources/img.png": b"changed"},
    )

    apply_package(
        package,
        install,
        engine="SRA",
        from_version="v2.19.0",
        to_version="v2.21.0",
        seven_zip=None,
    )

    assert (install / "SRA-cli.exe").read_bytes() == b"new-binary"
    assert (install / "resources" / "img.png").read_bytes() == b"changed"


def test_noop_when_package_matches_install(install: Path, tmp_path: Path) -> None:
    package = _make_zip(
        tmp_path / "same.zip",
        {"SRA-cli.exe": b"old-binary", "resources/img.png": b"old-image"},
    )
    before = _snapshot(install)

    result = apply_package(
        package,
        install,
        engine="SRA",
        from_version="v2.21.0",
        to_version="v2.21.0",
        seven_zip=None,
    )

    assert result.changed_files == 0
    assert _snapshot(install) == before
    assert not (install / ".automas_update").exists()


@pytest.mark.parametrize(
    ("remote", "current", "expected"),
    [
        # M7A 的日历版本
        ("v2026.9.7", "v2026.8.28", True),
        ("v2026.5.10", "v2026.5.6", True),
        ("v2026.9.7", "v2026.9.7", False),
        # SRA 的语义版本，含 prerelease 排序
        ("v2.21.0", "v2.16.1", True),
        ("v2.22.0-beta.3", "v2.21.0", True),
        ("v2.22.0", "v2.22.0-beta.3", True),
        ("v2.22.0-beta.3", "v2.22.0-beta.2", True),
        ("v2.21.0", "v2.22.0-beta.1", False),
        # 读不到本地版本时视为需要更新
        ("v2.21.0", None, True),
        # 解析不了就保守地不升级
        ("not-a-version", "v2.21.0", False),
    ],
)
def test_version_comparison(remote: str, current: str | None, expected: bool) -> None:
    assert is_newer(remote, current) is expected


@pytest.mark.parametrize(
    ("engine", "can_7z", "expected"),
    [
        ("M7A", True, ("7z", "update.7z")),
        ("M7A", False, ("zip", "March7thAssistant_full.zip")),
        ("SRA", True, ("zip", "StarRailAssistant_v2.21.0.zip")),
        ("SRA", False, ("zip", "StarRailAssistant_v2.21.0.zip")),
    ],
)
def test_asset_selection(engine: str, can_7z: bool, expected: tuple[str, str]) -> None:
    assert (
        select_asset_name(get_spec(engine), "v2.21.0", can_extract_7z=can_7z)
        == expected
    )


def test_station_url_only_for_sra() -> None:
    assert get_spec("M7A").station_url("v2026.9.7") is None
    assert get_spec("SRA").station_url("v2.21.0") == (
        "https://download.auto-mas.top/d/StarRailAssistant/StarRailAssistant-v2.21.0.zip"
    )
