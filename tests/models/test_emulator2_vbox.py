"""雷电 VBox 服务卡住的识别判据。探测样本逐行抄自 2026-09-12 的 ``ldconsole list2`` 实测。"""

import unittest

from app.utils.emulator.ldplayer import LDPlayerDevice
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


if __name__ == "__main__":
    unittest.main()
