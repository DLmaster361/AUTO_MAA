"""HSR 队列项遇到非重试异常时的行为：记失败、后续模块照常继续、不进补跑。"""

from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

import app.core  # noqa: F401  # 初始化宿主配置
from app.task.HSR.AutoProxy import HSRAutoProxyTask
from app.task.HSR.tools.run_model import HSRRetryableTaskError, HSRRunItem


class _Config:
    """最小脚本配置桩：关闭 MAS 游戏管理，避免 _run_item_with_game_guard 轮询进程。"""

    def get(self, group: str, key: str):
        if (group, key) == ("Game", "Enabled"):
            return False
        return None


def _make_task() -> tuple[HSRAutoProxyTask, list[str], list[dict]]:
    task = object.__new__(HSRAutoProxyTask)
    task.script_config = _Config()
    logs: list[str] = []
    results: list[dict] = []
    task._append_log = lambda message, **_: logs.append(message)
    task._record_module_result = lambda **kwargs: results.append(kwargs)
    return task, logs, results


def _item(
    name: str, run, *, phase: str = "daily", module_key: str | None = None
) -> HSRRunItem:
    return HSRRunItem(
        user_name="u",
        user_id="uid",
        phase=phase,
        module_key=module_key or name,
        module_name=name,
        script="M7A",
        description=name,
        run=run,
    )


class NonRetryableQueueItemTest(unittest.TestCase):
    def test_non_retryable_error_keeps_running_and_is_not_retryable(self) -> None:
        task, _logs, results = _make_task()
        executed: list[str] = []

        async def boom():
            executed.append("A")
            raise ValueError("config broken")

        async def ok(name: str):
            executed.append(name)
            return SimpleNamespace(success=True)

        items = [
            _item("A", boom),
            _item("B", lambda: ok("B")),
            _item("C", lambda: ok("C")),
        ]
        failures = asyncio.run(task._run_queue_items(items))

        self.assertEqual(executed, ["A", "B", "C"])
        self.assertEqual([item.module_name for item in failures], ["A"])
        self.assertFalse(failures[0].retryable)
        self.assertEqual(failures[0].last_error, "config broken")
        self.assertEqual([r["module_key"] for r in results], ["B", "C"])

    def test_retryable_error_stays_retryable(self) -> None:
        task, _logs, _results = _make_task()

        async def retryable():
            raise HSRRetryableTaskError("script failed")

        failures = asyncio.run(task._run_queue_items([_item("A", retryable)]))

        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0].retryable)

    def test_non_retryable_start_game_aborts_rest_without_retry(self) -> None:
        task, _logs, _results = _make_task()
        executed: list[str] = []

        async def boom():
            raise OSError("launcher missing")

        async def ok():
            executed.append("B")
            return SimpleNamespace(success=True)

        items = [_item("StartGame", boom), _item("B", ok)]
        failures = asyncio.run(task._run_queue_items(items))

        self.assertEqual(executed, [])
        self.assertEqual([item.module_key for item in failures], ["StartGame", "B"])
        self.assertTrue(all(not item.retryable for item in failures))


if __name__ == "__main__":
    unittest.main()
