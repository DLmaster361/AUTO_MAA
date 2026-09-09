"""MaaFW 项目指纹对运行期产物的排除回归

指纹只回答「项目是否还是我们装下去的那份」，用于差量更新的基线校验。项目跑起来时
MaaFramework 会往项目目录写 debug/ 日志、runner 会重写 config/maa_option.json，受管项目
还会被铺一层 maafw/ 原生运行时覆盖层。这些算进哈希的话，项目跑过一次后基线就永远对不上，
而那条路径没有回退全量包的分支——Mirror 酱源于是再也装不上更新。

反过来，发行包自带的 maafw/（没有覆盖层标记）必须照常算进指纹，否则真正的包内改动会溜过去。
"""

from pathlib import Path

from app.task.MaaFW.tools.core.automas_maafw_project_update.contracts import (
    NATIVE_RUNTIME_OVERLAY_MARKER,
    project_fingerprint,
)


def _make_project(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "interface.json").write_text('{"name": "demo"}', encoding="utf-8")


def test_runtime_artifacts_do_not_change_fingerprint(tmp_path: Path) -> None:
    """写入 debug/、config/maa_option.json、__pycache__ 后指纹必须不变。"""

    root = tmp_path / "project"
    _make_project(root)
    before = project_fingerprint(root)

    (root / "debug").mkdir()
    (root / "debug" / "maafw.log").write_text("noise", encoding="utf-8")
    (root / "config").mkdir()
    (root / "config" / "maa_option.json").write_text("{}", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "x.pyc").write_bytes(b"\x00")

    assert project_fingerprint(root) == before


def test_marked_native_runtime_overlay_is_ignored(tmp_path: Path) -> None:
    """带覆盖层标记的 maafw/ 是运行期产物，不算进指纹。"""

    root = tmp_path / "project"
    _make_project(root)
    before = project_fingerprint(root)

    overlay = root / "maafw"
    overlay.mkdir()
    (overlay / NATIVE_RUNTIME_OVERLAY_MARKER).write_text("{}", encoding="utf-8")
    (overlay / "MaaFramework.dll").write_bytes(b"binary")

    assert project_fingerprint(root) == before


def test_bundled_maafw_dir_still_counts(tmp_path: Path) -> None:
    """发行包自带的 maafw/（无标记）必须照常算进指纹，否则包内改动会溜过去。"""

    root = tmp_path / "project"
    _make_project(root)
    bundled = root / "maafw"
    bundled.mkdir()
    (bundled / "MaaFramework.dll").write_bytes(b"v1")
    before = project_fingerprint(root)

    (bundled / "MaaFramework.dll").write_bytes(b"v2")

    assert project_fingerprint(root) != before


def test_config_dir_other_than_maa_option_still_counts(tmp_path: Path) -> None:
    """只排 config/maa_option.json 这一个文件，config/ 下别的内容仍要算进去。"""

    root = tmp_path / "project"
    _make_project(root)
    (root / "config").mkdir()
    (root / "config" / "maa_option.json").write_text("{}", encoding="utf-8")
    before = project_fingerprint(root)

    (root / "config" / "project.json").write_text('{"a": 1}', encoding="utf-8")

    assert project_fingerprint(root) != before
