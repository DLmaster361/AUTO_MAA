"""Emulator 2.0 的 MuMu 实例启动失败时把 ``info`` 里的自带诊断带进报错。记录形状抄自 MuMu 6.6.4.0 的 ``info -v all``。"""

import unittest

from app.utils.emulator2.mumu6 import format_launch_diagnosis

#: 关机状态的真实记录：这些字段在没出错时都是 0 / false / 空，一个都不该出现在报错里。
IDLE = {
    "android_version": "15.0",
    "created_timestamp": 1782870868271143,
    "disk_size_bytes": 71489106684,
    "error_code": 0,
    "hyperv_enabled": True,
    "index": "0",
    "info_source": "local",
    "is_android_started": False,
    "is_main": False,
    "is_process_started": False,
    "name": "MuMu安卓设备",
}


class FormatLaunchDiagnosisTest(unittest.TestCase):
    def test_idle_record_adds_nothing(self) -> None:
        self.assertEqual(format_launch_diagnosis(IDLE), "")

    def test_launch_error_fields_are_surfaced_in_order(self) -> None:
        entry = {
            **IDLE,
            "launch_err_code": 1101,
            "launch_err_msg": "headless crash",
            "player_state": "start_failed",
        }
        self.assertEqual(
            format_launch_diagnosis(entry),
            "；MuMu 诊断: 启动错误码=1101, 启动错误=headless crash, 实例状态=start_failed",
        )

    def test_zero_and_empty_values_are_skipped(self) -> None:
        entry = {
            **IDLE,
            "launch_err_code": 0,
            "launch_err_msg": "",
            "player_state": None,
        }
        self.assertEqual(format_launch_diagnosis(entry), "")
        self.assertEqual(
            format_launch_diagnosis({**IDLE, "error_code": 7}),
            "；MuMu 诊断: 实例错误码=7",
        )


if __name__ == "__main__":
    unittest.main()
