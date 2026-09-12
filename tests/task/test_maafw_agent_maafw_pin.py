"""MaaFW agent 隔离 venv 的 maafw 版本必须钉在项目自带的原生库上。

MaaFW 的 AgentServer（agent 侧）与 AgentClient（runner 侧）之间有协议版本号，
跨版本会被直接拒绝握手，在我们这边只表现为「AgentClient 连接超时」。runner 加载
的是项目自带的那份原生库，所以 agent venv 里的 binding 必须跟它同版本。

照抄 ``requirements.txt`` 做不到：很多项目写的是无版本约束的 ``MaaFw``，pip 会拉
到当时的最新版。maafw 5.13.0（2026-09-07）把协议号从 7 抬到 8，于是这些项目的
agent venv 一旦在那之后重建就必然连不上。

顺带钉住第二件事：**解析结果要进 manifest**。agent venv 的复用判据是
``requirementsHash``，钉版本若不进这个哈希，已经装错的 venv 会因为「依赖清单未
变化」被永远复用，修了也送不出去。
"""

import hashlib
import json
from pathlib import Path

from app.task.MaaFW.tools.core.automas_maafw_agent_env.env import (
    _load_project_agent_requirements as load_requirements_via_agent_env,
)
from app.task.MaaFW.tools.core.automas_maafw_agent_env.env import (
    build_agent_env_manifest,
)
from app.task.MaaFW.tools.core.automas_maafw_runner.environment import (
    pin_agent_maafw_requirement,
)
from app.task.MaaFW.tools.core.automas_maafw_runner.runner import (
    _load_project_agent_requirements as load_requirements_via_runner,
)

# 照抄真实原生库里的排布：版本号是一条 NUL 结尾的 C 字符串，前后都是别的字符串。
# 取自 Maa_bbb v1.12.10 自带的 MaaFramework.dll。
_DLL_TEMPLATE = (
    b"\x00\x00\x00\x00latest_id\x00\x00\x00\x00%s\x00DoNothing\x00\x00\x00MaaAdbC"
)


def _make_project(
    tmp_path: Path,
    *,
    requirements: list[str] | None = None,
    bundled_version: str | None = "v5.12.3",
) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    if requirements is not None:
        (project / "requirements.txt").write_text(
            "\n".join(requirements) + "\n", encoding="utf-8"
        )
    if bundled_version is not None:
        runtime_dir = project / "maafw"
        runtime_dir.mkdir()
        (runtime_dir / "MaaFramework.dll").write_bytes(
            _DLL_TEMPLATE % bundled_version.encode("ascii")
        )
    return project


def test_unpinned_declaration_is_pinned_to_bundled_runtime(tmp_path: Path) -> None:
    project = _make_project(tmp_path, requirements=["json-with-comments", "MaaFw"])

    assert pin_agent_maafw_requirement(project, ["json-with-comments", "MaaFw"]) == [
        "json-with-comments",
        "maafw==5.12.3",
    ]


def test_stale_declaration_loses_to_bundled_runtime(tmp_path: Path) -> None:
    """声明与自带库对不上时以自带库为准——我们加载的是自带的那份。"""

    project = _make_project(tmp_path, requirements=["maafw==5.13.0"])

    assert pin_agent_maafw_requirement(project, ["maafw==5.13.0"]) == ["maafw==5.12.3"]


def test_declaration_without_maafw_gets_nothing_added(tmp_path: Path) -> None:
    """没声明 maafw 的项目不凭空追加：它的 agent 多半不是 Python 的。"""

    project = _make_project(tmp_path, requirements=["requests"])

    assert pin_agent_maafw_requirement(project, ["requests"]) == ["requests"]


def test_project_without_bundled_runtime_or_declaration_is_untouched(
    tmp_path: Path,
) -> None:
    project = _make_project(tmp_path, requirements=["MaaFw"], bundled_version=None)

    assert pin_agent_maafw_requirement(project, ["MaaFw"]) == ["MaaFw"]


def test_duplicate_declarations_collapse_to_one(tmp_path: Path) -> None:
    """pip 拿到两条互斥的 maafw 约束会直接失败，只能留一条。"""

    project = _make_project(tmp_path, requirements=["MaaFw", "maafw==5.13.0"])

    assert pin_agent_maafw_requirement(project, ["MaaFw", "maafw==5.13.0"]) == [
        "maafw==5.12.3"
    ]


def test_both_requirement_loaders_apply_the_pin(tmp_path: Path) -> None:
    """runner 与 agent_env 各有一份 loader，两条路径都得钉上。"""

    project = _make_project(tmp_path, requirements=["json-with-comments", "MaaFw"])

    for load in (load_requirements_via_runner, load_requirements_via_agent_env):
        packages = load(project)
        assert "maafw==5.12.3" in packages, load.__module__
        assert "MaaFw" not in packages, load.__module__


def test_manifest_carries_the_pin_so_stale_venvs_rebuild(tmp_path: Path) -> None:
    project = _make_project(tmp_path, requirements=["json-with-comments", "MaaFw"])

    manifest = build_agent_env_manifest(project)

    assert "maafw==5.12.3" in manifest["requirements"]
    # 复用判据是 requirementsHash：装错版本时写下的那份哈希算的是未钉版本的清单，
    # 与现在必然不同，已经装错的 venv 因此会被重建。
    stale_payload = json.dumps(
        ["json-with-comments", "MaaFw"], ensure_ascii=False, separators=(",", ":")
    )
    stale_hash = hashlib.sha256(stale_payload.encode("utf-8")).hexdigest()
    assert manifest["requirementsHash"] != stale_hash
