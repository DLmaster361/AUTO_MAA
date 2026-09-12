"""MaaEnd：资源加载失败是确定性错误，不再重试；配置文件未变时任务列表复用解析结果。"""

import asyncio
import json
from datetime import datetime

from app.models.task import LogRecord, ScriptItem
from app.task.MaaEnd.AutoProxy import AutoProxyTask


def _bare_task() -> AutoProxyTask:
    task = AutoProxyTask.__new__(AutoProxyTask)
    task.cur_user_log = LogRecord()
    task.script_info = ScriptItem(script_id="s", name="测试 MaaEnd", status="运行")
    task.retryable = True
    task.color_match_failed_message = None
    task.account_switch_task_name = "切换账号"
    task.task_dict = None
    task.wait_event = asyncio.Event()
    task.maaend_config_file = None
    task._source_tasks_cache = None
    return task


def test_resource_load_failure_is_not_retryable():
    task = _bare_task()
    asyncio.run(task.check_log(["资源加载失败"], datetime.now()))
    assert task.cur_user_log.status == "MaaEnd 资源加载失败"
    assert task.retryable is False
    assert task.wait_event.is_set()


def test_task_start_failure_stays_retryable():
    task = _bare_task()
    asyncio.run(task.check_log(["任务启动失败"], datetime.now()))
    assert task.cur_user_log.status == "MaaEnd 任务启动失败"
    assert task.retryable is True


def _write_config(path, task_names: list[str]) -> None:
    payload = {
        "instances": [
            {
                "id": "automas",
                "name": "AUTO-MAS",
                "tasks": [{"taskName": name, "enabled": True} for name in task_names],
            }
        ]
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_source_tasks_are_cached_until_file_changes(tmp_path):
    config_file = tmp_path / "mxu-MaaEnd.json"
    _write_config(config_file, ["A"])
    task = _bare_task()
    task.maaend_config_file = config_file

    first = task._source_maaend_tasks()
    assert [t["taskName"] for t in first] == ["A"]
    assert task._source_maaend_tasks() is first

    _write_config(config_file, ["A", "B"])
    third = task._source_maaend_tasks()
    assert third is not first
    assert [t["taskName"] for t in third] == ["A", "B"]


def test_source_tasks_missing_file_returns_none(tmp_path):
    task = _bare_task()
    task.maaend_config_file = tmp_path / "missing.json"
    assert task._source_maaend_tasks() is None
