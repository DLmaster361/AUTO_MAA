"""MFW 运行环境准备结果的指纹缓存。

背景：编辑页每打开一次就调一次 ``/maafw/agent-env/prepare``，而底层准备是
幂等的——项目没动过时那几秒全花在「确认」上（取项目锁、起解释器核 ABI、逐个
agent 跑 pip 健康检查）。``env_cache`` 把成功准备过的结果连同项目输入指纹落盘，
下次先比指纹，命中就直接还回上次的结果。

这里盯住两类判据：**指纹变了必须落空**（项目更新后不能拿旧环境糊弄过去），
以及**结果里记的路径不在了必须落空**（运行池被清掉、venv 被删）。缓存读写都
不许抛异常——它不是正确性的一部分，坏了最多是多准备一次。
"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from app.task.MaaFW.tools.embedded.env_cache import (
    discard_prepared_environment,
    load_prepared_environment,
    store_prepared_environment,
)


class MaaFWEnvCacheTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        # 缓存落在 ``Path.cwd()/config`` 下，把工作目录挪进临时目录再测。
        self._previous_cwd = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(lambda: os.chdir(self._previous_cwd))

        self.project = self.root / "project"
        self.project.mkdir()

        self.runtime_venv = self.root / "runtime_venv"
        self.runtime_python = self.runtime_venv / "python.exe"
        self.agent_venv = self.root / "agent_venv"
        self.agent_python = self.agent_venv / "python.exe"
        for exe in (self.runtime_python, self.agent_python):
            exe.parent.mkdir(parents=True, exist_ok=True)
            exe.write_text("", encoding="utf-8")

        self.result = {
            "status": "ready",
            "runtime": {
                "runtimeId": "rt-1",
                "poolId": "pool-1",
                "pythonExecutable": str(self.runtime_python),
                "venvPath": str(self.runtime_venv),
                "maafwVersion": "v4.5.0",
            },
            "agents": {
                "projectPath": str(self.project),
                "plans": [
                    {
                        "childExec": "agent.py",
                        "executable": str(self.agent_python),
                        "runtimeKind": "isolated_venv",
                        "isolatedVenvPath": str(self.agent_venv),
                        "fallbackReason": None,
                    }
                ],
                "preparedVenvs": [str(self.agent_venv)],
                "skipped": [],
                "messages": ["prepared"],
            },
        }

    def _cache_files(self) -> list[Path]:
        return list((self.root / "config" / "maafw_env_cache").glob("*.json"))

    def _store(self, fingerprint: str = "FP-A") -> None:
        store_prepared_environment(self.project, fingerprint, self.result)

    def test_hit_returns_runtime_and_agents(self) -> None:
        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))

        self._store()
        hit = load_prepared_environment(self.project, "FP-A")

        self.assertIsNotNone(hit)
        assert hit is not None
        self.assertEqual(hit["runtime"]["maafwVersion"], "v4.5.0")
        self.assertEqual(hit["agents"]["plans"][0]["childExec"], "agent.py")
        self.assertTrue(hit.get("preparedAt"))

    def test_fingerprint_change_misses(self) -> None:
        """项目更新过（interface / requirements 变了）就必须重新准备。"""

        self._store()
        self.assertIsNone(load_prepared_environment(self.project, "FP-B"))

    def test_missing_fingerprint_never_hits_or_stores(self) -> None:
        """读不到 interface 的项目算不出指纹，既不该命中也不该写缓存。"""

        self._store()
        self.assertIsNone(load_prepared_environment(self.project, None))

        discard_prepared_environment(self.project)
        store_prepared_environment(self.project, None, self.result)
        self.assertEqual(self._cache_files(), [])

    def test_cache_is_per_project(self) -> None:
        self._store()
        other = self.root / "other_project"
        other.mkdir()
        self.assertIsNone(load_prepared_environment(other, "FP-A"))

    def test_missing_runtime_python_misses(self) -> None:
        self._store()
        self.runtime_python.unlink()
        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))

    def test_missing_agent_venv_misses(self) -> None:
        self._store()
        self.agent_python.unlink()
        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))

        # 环境补回来之后同一份缓存应该重新可用，不需要先手动清理。
        self.agent_python.write_text("", encoding="utf-8")
        self.assertIsNotNone(load_prepared_environment(self.project, "FP-A"))

    def test_relative_agent_executable_is_not_path_checked(self) -> None:
        """external agent 的 executable 可能只是个命令名，交给 PATH 解析。"""

        self.result["agents"]["plans"] = [
            {
                "childExec": "agent",
                "executable": "node",
                "runtimeKind": "external",
                "isolatedVenvPath": None,
                "fallbackReason": None,
            }
        ]
        self._store()
        self.assertIsNotNone(load_prepared_environment(self.project, "FP-A"))

    def test_corrupt_cache_misses_without_raising(self) -> None:
        self._store()
        cache_files = self._cache_files()
        self.assertEqual(len(cache_files), 1)

        cache_files[0].write_text("{ not json", encoding="utf-8")
        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))

    def test_unknown_format_version_misses(self) -> None:
        self._store()
        cache_file = self._cache_files()[0]
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        payload["version"] = payload["version"] + 1000
        cache_file.write_text(json.dumps(payload), encoding="utf-8")

        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))

    def test_logs_are_not_cached(self) -> None:
        """命中时还回的是上一次的准备结果，那次的日志不该冒充这次的。"""

        self.result["agents"]["messages"] = ["prepared"]
        self._store()
        hit = load_prepared_environment(self.project, "FP-A")
        assert hit is not None
        self.assertNotIn("logs", hit)

    def test_discard_is_idempotent(self) -> None:
        self._store()
        discard_prepared_environment(self.project)
        self.assertIsNone(load_prepared_environment(self.project, "FP-A"))
        discard_prepared_environment(self.project)


if __name__ == "__main__":
    unittest.main()
