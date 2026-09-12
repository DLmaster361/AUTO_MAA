"""ZZZ-OD 调度器：单用户运行只装入目标用户（对齐其余调度器的 is_target_user 收窄）。"""

import asyncio
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

import app.core  # noqa: F401  # 初始化宿主配置
from app.core.task_manager import TaskInfo
from app.models.config import ZzzOdConfig, ZzzOdUserConfig
from app.models.task import ScriptItem
from app.task.ZzzOd.manager import ZzzOdManager


async def build_manager(root: Path, *, user_id: str | None, users: list[uuid.UUID]):
    script_uid = uuid.uuid4()
    script_config = ZzzOdConfig()
    await script_config.update({"Info": {"Name": "测试 ZZZ-OD", "RootPath": str(root)}})
    for name in ("甲", "乙"):
        uid, user_cfg = await script_config.UserData.add(ZzzOdUserConfig)
        await user_cfg.update(
            {"Info": {"Name": name, "Status": True, "RemainedDay": -1}}
        )
        users.append(uid)

    task_info = TaskInfo(
        mode="AutoProxy",
        task_id="task-id",
        queue_id=None,
        script_id=str(script_uid),
        user_id=user_id,
    )
    script_item = ScriptItem(
        script_id=str(script_uid), name="测试 ZZZ-OD", status="运行"
    )
    task_info.script_list = [script_item]
    return ZzzOdManager(script_item), script_uid, script_config


class ZzzOdSingleUserScopeTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "OneDragon-Launcher.exe").write_bytes(b"")

    def _run(self, *, single_user: bool):
        async def go():
            users: list[uuid.UUID] = []
            manager, script_uid, config = await build_manager(
                self.root, user_id=None, users=users
            )
            if single_user:
                manager.task_info.user_id = str(users[0])
            with mock.patch.object(
                app.core.Config, "ScriptConfig", {script_uid: config}
            ):
                check_result = await manager.check()
                check_names = [user.name for user in manager.script_info.user_list]
                await manager.prepare()
                prepare_names = [user.name for user in manager.script_info.user_list]
            await config.unlock()
            return check_result, check_names, prepare_names

        return asyncio.run(go())

    def test_single_user_run_only_loads_target_user(self) -> None:
        check_result, check_names, prepare_names = self._run(single_user=True)
        self.assertEqual(check_result, "Pass")
        self.assertEqual(check_names, ["甲"])
        self.assertEqual(prepare_names, ["甲"])

    def test_full_run_loads_every_enabled_user(self) -> None:
        check_result, check_names, prepare_names = self._run(single_user=False)
        self.assertEqual(check_result, "Pass")
        self.assertEqual(check_names, ["甲", "乙"])
        self.assertEqual(prepare_names, ["甲", "乙"])


if __name__ == "__main__":
    unittest.main()
