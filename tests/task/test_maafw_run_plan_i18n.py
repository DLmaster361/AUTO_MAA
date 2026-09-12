"""构建运行计划时语言文件只加载一次，且走 json→json5 快路径。

以前 ``build_maafw_run_plan`` 自己、``_build_pretask_plans`` 和 ``_build_pi_env``
（内部两次）各自 ``json5.loads`` 同一份语言文件，共四遍；json5 是纯 Python 递归
下降解析器，MaaEnd 那份 108KB 的 zh_cn.json 一遍就要 392ms。现在顶层加载一次
向下传，解析改用 loader 的 ``parse_json_text``；解析失败也不再静默，而是按
文件提醒一次。
"""

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from app.task.MaaFW.tools.core.automas_maafw_interface import preview
from app.task.MaaFW.tools.core.automas_maafw_interface.models import MaaFWInterface
from app.task.MaaFW.tools.core.automas_maafw_runner import run_plan


def _project(tmp_path: Path, language_text: str) -> tuple[Path, dict[str, Any]]:
    project = tmp_path / "project"
    (project / "resource").mkdir(parents=True)
    (project / "zh_cn.json").write_text(language_text, encoding="utf-8")
    interface = {
        "interface_version": 2,
        "name": "demo",
        "controller": [{"name": "模拟器", "type": "Adb"}],
        "resource": [{"name": "官服", "path": ["{PROJECT_DIR}/resource"]}],
        "task": [
            {"name": "Main", "entry": "main", "label": "$task.main"},
            {"name": "Extra", "entry": "extra"},
        ],
        "languages": {"zh_cn": "zh_cn.json"},
    }
    return project, interface


def test_run_plan_loads_language_file_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, interface = _project(
        tmp_path, json.dumps({"task": {"main": "主线", "Extra": {"label": "额外"}}})
    )
    calls = {"count": 0}
    original = run_plan._load_i18n_mapping

    def counting(base_dir: Path, model: MaaFWInterface) -> dict[str, Any]:
        calls["count"] += 1
        return original(base_dir, model)

    monkeypatch.setattr(run_plan, "_load_i18n_mapping", counting)

    plan = run_plan.build_maafw_run_plan(project, interface, task_ids=["Main", "Extra"])

    assert calls["count"] == 1
    labels = {task.name: task.label for task in plan.tasks}
    assert labels["Main"] == "主线"
    assert labels["Extra"] == "额外"
    assert "PI_CONTROLLER" in plan.piEnv


def test_language_file_takes_strict_json_fast_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, interface = _project(tmp_path, json.dumps({"task": {"main": "主线"}}))

    def no_json5(_text: str) -> Any:
        raise AssertionError("严格 JSON 不该落到 json5")

    monkeypatch.setattr(
        "app.task.MaaFW.tools.core.automas_maafw_interface.loader.json5.loads",
        no_json5,
    )

    mapping = run_plan._load_i18n_mapping(
        project, MaaFWInterface.model_validate(interface)
    )

    assert mapping == {"task": {"main": "主线"}}


def test_broken_language_file_warns_once(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    project, interface = _project(tmp_path, "{ this is not json")
    model = MaaFWInterface.model_validate(interface)
    run_plan._WARNED_LANGUAGE_FILES.clear()
    preview._WARNED_LANGUAGE_FILES.clear()

    with caplog.at_level(logging.WARNING):
        assert run_plan._load_i18n_mapping(project, model) == {}
        assert run_plan._load_i18n_mapping(project, model) == {}
        assert preview._load_i18n_mapping(project, model) == {}
        assert preview._load_i18n_mapping(project, model) == {}

    messages = [record.getMessage() for record in caplog.records]
    assert sum("任务文案退回原始键" in m for m in messages) == 1
    assert sum("预览文案退回原始键" in m for m in messages) == 1
