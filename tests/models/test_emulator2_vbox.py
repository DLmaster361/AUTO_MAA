"""雷电 VBox 服务卡住的识别与自愈。探测样本逐行抄自 2026-09-12 的 ``ldconsole list2`` 实测。"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import app.core  # noqa: F401  # 初始化宿主配置
from app.models.emulator import DeviceInfo, DeviceStatus
from app.utils.emulator.ldplayer import LDPlayerDevice
from app.utils.emulator2 import ldplayer14 as ld14_module
from app.utils.emulator2.ldplayer14 import build_manager
from app.utils.emulator2.vbox import VmProbe, vm_is_missing


def _row(text: str) -> LDPlayerDevice:
    parts = text.split(",")
    return LDPlayerDevice(
        idx=int(parts[0]),
        title=parts[1],
        top_hwnd=int(parts[2]),
        bind_hwnd=int(parts[3]),
        in_android=int(parts[4]),
        pid=int(parts[5]),
        vbox_pid=int(parts[6]),
        width=int(parts[7]),
        height=int(parts[8]),
        density=int(parts[9]),
    )


#: 健康：修复后正常启动的实例 4。
HEALTHY = _row("4,auto2,14948100,20385656,1,56948,31756,1280,720,240")
#: 僵尸：VBox 服务被重启后只剩窗口的实例 3，「Android 已启动」还是 1。
ZOMBIE = _row("3,auto1,10884466,921502,1,60560,-1,1280,720,240")
#: 卡在启动：服务卡住时新拉的实例 4，三分钟一直是这行。
STUCK = _row("4,auto2,5769662,2297496,2,66908,-1,1280,720,240")
#: 关着。
OFFLINE = _row("4,auto2,0,0,0,-1,-1,1280,720,240")


class VmIsMissingTest(unittest.TestCase):
    def test_zombie_and_stuck_rows_are_missing_when_adb_cannot_see_them(self) -> None:
        for row in (ZOMBIE, STUCK):
            with self.subTest(row=row.title):
                probe = VmProbe(row.in_android, row.vbox_pid, serial_online=False)
                self.assertTrue(vm_is_missing(probe))

    def test_healthy_and_offline_rows_are_not_missing(self) -> None:
        for row in (HEALTHY, OFFLINE):
            with self.subTest(row=row.title):
                probe = VmProbe(row.in_android, row.vbox_pid, serial_online=False)
                self.assertFalse(vm_is_missing(probe))

    def test_adb_visibility_overrides_an_unreliable_vbox_column(self) -> None:
        probe = VmProbe(in_android=1, vbox_pid=-1, serial_online=True)
        self.assertFalse(vm_is_missing(probe))


class RecoveryFlowTest(unittest.TestCase):
    """只测编排：父类启动、进程探测、服务重启全部换成桩。"""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        exe = Path(self._tmp.name) / "LDPlayer14" / "ldconsole.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        self.manager = asyncio.run(build_manager(str(exe), max_wait_time=5))
        self.info = DeviceInfo(
            title="auto2", status=DeviceStatus.ONLINE, adb_address=""
        )

    def _run(self, *, rows, serials, parent, live_vms):
        """``rows`` 按父类启动的调用次数依次给出探测结果。"""
        rows = list(rows)
        manager = self.manager

        async def get_device_info(idx):
            # 样本行来自不同实例，这里统一挂到被测的 4 号名下
            row = rows[0] if len(rows) == 1 else rows.pop(0)
            return {"4": row}

        async def list_serials():
            return serials

        restart = mock.AsyncMock(return_value=True)
        quit_zombie = mock.AsyncMock()

        async def go():
            with (
                mock.patch.object(ld14_module.LDManager, "_open_locked", parent),
                mock.patch.object(manager, "get_device_info", get_device_info),
                mock.patch.object(manager, "_list_adb_serials", list_serials),
                mock.patch.object(manager, "_quit_zombie_instance", quit_zombie),
                mock.patch.object(ld14_module, "live_vm_pids", lambda: live_vms),
                mock.patch.object(ld14_module, "restart_vbox_service", restart),
            ):
                return await manager._open_locked("4", "")

        return go, restart, quit_zombie

    def test_healthy_boot_is_passed_through_untouched(self) -> None:
        parent = mock.AsyncMock(return_value=self.info)
        go, restart, quit_zombie = self._run(
            rows=[HEALTHY], serials=["emulator-5562"], parent=parent, live_vms=[]
        )
        self.assertIs(asyncio.run(go()), self.info)
        self.assertEqual(parent.await_count, 1)
        restart.assert_not_awaited()
        quit_zombie.assert_not_awaited()

    def test_android_flag_without_vm_triggers_service_restart_and_relaunch(
        self,
    ) -> None:
        parent = mock.AsyncMock(return_value=self.info)
        go, restart, quit_zombie = self._run(
            rows=[ZOMBIE, HEALTHY], serials=[], parent=parent, live_vms=[]
        )

        # 第二次探测要能看到 adb，否则会被判成「重启后仍起不来」
        async def list_serials_after():
            return ["emulator-5562"] if restart.await_count else []

        with mock.patch.object(self.manager, "_list_adb_serials", list_serials_after):
            self.assertIs(asyncio.run(go()), self.info)
        self.assertEqual(parent.await_count, 2)
        restart.assert_awaited_once()
        quit_zombie.assert_awaited_once()

    def test_stuck_boot_timeout_is_recovered_the_same_way(self) -> None:
        parent = mock.AsyncMock(
            side_effect=[
                RuntimeError("模拟器 4 启动超时, 当前状态码: STARTING"),
                self.info,
            ]
        )
        go, restart, quit_zombie = self._run(
            rows=[STUCK, HEALTHY], serials=[], parent=parent, live_vms=[]
        )
        self.assertIs(asyncio.run(go()), self.info)
        self.assertEqual(parent.await_count, 2)
        restart.assert_awaited_once()

    def test_other_live_vms_block_the_restart(self) -> None:
        parent = mock.AsyncMock(return_value=self.info)
        go, restart, quit_zombie = self._run(
            rows=[ZOMBIE], serials=[], parent=parent, live_vms=[25632]
        )
        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(go())
        self.assertIn("还有 1 台实例的虚拟机在运行", str(ctx.exception))
        restart.assert_not_awaited()
        quit_zombie.assert_not_awaited()
        self.assertEqual(parent.await_count, 1)

    def test_unrelated_parent_error_is_not_swallowed(self) -> None:
        parent = mock.AsyncMock(side_effect=RuntimeError("命令执行失败: boom"))
        go, restart, _ = self._run(
            rows=[OFFLINE], serials=[], parent=parent, live_vms=[]
        )
        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(go())
        self.assertEqual(str(ctx.exception), "命令执行失败: boom")
        restart.assert_not_awaited()

    def test_still_missing_after_restart_points_to_repair_tool(self) -> None:
        parent = mock.AsyncMock(return_value=self.info)
        go, restart, _ = self._run(
            rows=[ZOMBIE], serials=[], parent=parent, live_vms=[]
        )
        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(go())
        self.assertIn("dnrepairer.exe", str(ctx.exception))
        restart.assert_awaited_once()
        self.assertEqual(parent.await_count, 2)

    def test_permission_denied_is_translated(self) -> None:
        parent = mock.AsyncMock(return_value=self.info)
        go, restart, _ = self._run(
            rows=[ZOMBIE], serials=[], parent=parent, live_vms=[]
        )
        restart.side_effect = PermissionError("没有权限结束 Ld9BoxSVC.exe（pid 1）")
        with self.assertRaises(RuntimeError) as ctx:
            asyncio.run(go())
        self.assertIn("管理员", str(ctx.exception))
        self.assertEqual(parent.await_count, 1)


if __name__ == "__main__":
    unittest.main()
