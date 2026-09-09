import unittest

from app.utils.emulator2.applaunch import (
    ensure_app_running,
    is_package_foreground,
    is_package_missing,
    parse_launch_component,
)

PACKAGE = "com.hypergryph.arknights"
COMPONENT = f"{PACKAGE}/com.u8.sdk.U8UnityContext"

#: 明日方舟在前台时的 `dumpsys activity activities`，逐行抄自 MuMu 6 / Android 15 实测。
#: 该镜像用的是 `topResumedActivity=` 与 `ResumedActivity:`，没有老版的 `mResumedActivity:`。
FOREGROUND = f"""  * Task{{4dfffed #32 type=standard A=10053:{PACKAGE} U=0 visible=true visibleRequested=true mode=fullscreen translucent=false sz=1}}
    topResumedActivity=ActivityRecord{{17509892 u0 {COMPONENT} t32}}
    * Hist  #0: ActivityRecord{{17509892 u0 {COMPONENT} t32}}
      packageName={PACKAGE} processName={PACKAGE}
  ResumedActivity: ActivityRecord{{17509892 u0 {COMPONENT} t32}}
  mCurrentFocus=null
"""

#: 关键的反例：游戏退到后台、桌面在前台。两段都是实测行，只是拼在同一份输出里。
#: 只按包名匹配会把这种情况判成「已经在前台」，于是永远不去拉起它；
#: `Hist` 与 `mLastPausedActivity:` 都带包名却都不含任何前台标记，正是要靠这个分开。
BACKGROUND = f"""  * Task{{c85edc9 #2 type=home I=app.lawnchair/.LawnchairLauncher U=0 rootTaskId=1 visible=true}}
    topResumedActivity=ActivityRecord{{50825199 u0 app.lawnchair/.LawnchairLauncher t2}}
  ResumedActivity: ActivityRecord{{50825199 u0 app.lawnchair/.LawnchairLauncher t2}}
  * Task{{4dfffed #32 type=standard A=10053:{PACKAGE} U=0 visible=false}}
      mLastPausedActivity: ActivityRecord{{17509892 u0 {COMPONENT} t32}}
      * Hist  #0: ActivityRecord{{17509892 u0 {COMPONENT} t32}}
        packageName={PACKAGE} processName={PACKAGE}
"""


class ForegroundTest(unittest.TestCase):
    def test_resumed_activity_counts(self) -> None:
        self.assertTrue(is_package_foreground(FOREGROUND, PACKAGE))

    def test_present_but_not_resumed_does_not_count(self) -> None:
        """在历史栈里 ≠ 在前台。判错会让「补启动」整个失效。"""
        self.assertFalse(is_package_foreground(BACKGROUND, PACKAGE))

    def test_every_marker_spelling_is_recognised(self) -> None:
        """只认一种写法会在某些镜像上永远判成没起来。"""
        for marker in (
            "topResumedActivity=",
            "ResumedActivity:",
            "mResumedActivity:",
            "mCurrentFocus=",
        ):
            with self.subTest(marker=marker):
                self.assertTrue(
                    is_package_foreground(
                        f"  {marker}ActivityRecord{{{COMPONENT}}}\n", PACKAGE
                    )
                )

    def test_garbage_does_not_raise(self) -> None:
        for raw in ("", "error: device not found"):
            with self.subTest(raw=raw):
                self.assertFalse(is_package_foreground(raw, PACKAGE))


class MissingPackageTest(unittest.TestCase):
    """`pm path` 的三种真实输出，取自 MuMu 6 / Android 15 实测。

    回归：判据必须是「输出为空」。没装和设备掉线的**返回码都是 1**，按返回码非 0
    判会把掉线误报成没装；按返回码 0 判则永远判不出没装，那条分支就成了死代码
    （实测中确实一次都没触发过，missing 的包一路走到 launch-timeout）。
    """

    def test_installed_package_prints_a_path(self) -> None:
        self.assertFalse(
            is_package_missing(
                "package:/system/system_ext/priv-app/Settings/Settings.apk"
            )
        )

    def test_missing_package_prints_nothing(self) -> None:
        self.assertTrue(is_package_missing(""))

    def test_offline_device_is_not_reported_as_missing(self) -> None:
        self.assertFalse(
            is_package_missing("adb.exe: device '127.0.0.1:9999' not found")
        )


class ResolveComponentTest(unittest.TestCase):
    def test_takes_the_component_line(self) -> None:
        output = (
            "priority=0 preferredOrder=0 match=0x108000 specificIndex=-1 isDefault=true\n"
            f"{COMPONENT}\n"
        )
        self.assertEqual(parse_launch_component(output, PACKAGE), COMPONENT)

    def test_relative_activity_survives(self) -> None:
        """`包名/.Activity` 也是 am start -n 认的写法，不能因为带点就丢掉。"""
        self.assertEqual(
            parse_launch_component(f"{PACKAGE}/.MainActivity\n", PACKAGE),
            f"{PACKAGE}/.MainActivity",
        )

    def test_no_match_returns_none(self) -> None:
        """解析不出就返回 None，绝不猜一个组件名去 am start。"""
        for raw in ("", "No activity found", "com.other.app/.Main"):
            with self.subTest(raw=raw):
                self.assertIsNone(parse_launch_component(raw, PACKAGE))


class FakeAdb:
    """按命令派发的假 adb，同时记录调用顺序。

    ``foreground_from`` 决定应用什么时候算进了前台：``start`` 一开始就在、
    ``monkey`` / ``am`` / ``vendor`` 表示只有那一路生效、``never`` 始终不在。
    分开这三种是因为真机上它们各自会瞎：雷电没有 ``monkey``，
    ``am start`` 拿不到组件名时发不出去。
    """

    def __init__(
        self,
        *,
        boot: str = "1",
        pm_path: str = f"package:/data/app/{PACKAGE}-1/base.apk",
        foreground_from: str = "never",
        resolve: str = COMPONENT,
    ) -> None:
        self.boot = boot
        self.pm_path = pm_path
        self.foreground_from = foreground_from
        self.resolve = resolve
        self.calls: list[tuple[str, ...]] = []
        self.vendor_calls = 0

    def sent(self, *needles: str) -> bool:
        return any(all(n in call for n in needles) for call in self.calls)

    async def vendor_launch(self) -> str:
        self.vendor_calls += 1
        return "ok"

    @property
    def _foreground(self) -> bool:
        if self.foreground_from == "start":
            return True
        if self.foreground_from == "monkey":
            return self.sent("monkey")
        if self.foreground_from == "am":
            return self.sent("am", "start")
        if self.foreground_from == "vendor":
            return self.vendor_calls > 0
        return False

    async def __call__(self, *args: str, timeout: float = 0) -> tuple[int, str]:
        foreground_before = self._foreground
        self.calls.append(args)

        if args[:3] == ("shell", "getprop", "sys.boot_completed"):
            return 0, self.boot
        if args[:3] == ("shell", "pm", "path"):
            # 真机上没装的包是「返回码 1 + 空输出」，装了才是 0
            return (0, self.pm_path) if self.pm_path else (1, "")
        if args[:2] == ("shell", "dumpsys"):
            return 0, FOREGROUND if foreground_before else BACKGROUND
        if "resolve-activity" in args:
            return 0, self.resolve
        if "monkey" in args:
            # 雷电镜像里没有 monkey，真机返回码就是 127
            return (0, "") if self.foreground_from != "no-monkey" else (127, "")
        return 0, ""


async def _run(adb: FakeAdb, *, with_vendor: bool = True, **kwargs):
    return await ensure_app_running(
        adb,
        PACKAGE,
        boot_timeout=0,
        launch_timeout=0,
        poll_seconds=0,
        vendor_launch=adb.vendor_launch if with_vendor else None,
        **kwargs,
    )


class EnsureAppRunningTest(unittest.IsolatedAsyncioTestCase):
    async def test_already_foreground_launches_nothing(self) -> None:
        """已经在前台还去拉一把，会把用户正在看的界面顶掉。"""
        adb = FakeAdb(foreground_from="start")

        result = await _run(adb)

        self.assertTrue(result.ok)
        self.assertEqual(result.reason, "already-running")
        self.assertFalse(adb.sent("monkey"))
        self.assertEqual(adb.vendor_calls, 0)

    async def test_fires_all_three_at_once(self) -> None:
        """三路一起发：任何一路单独失效都不该让整次启动多等一轮超时。"""
        adb = FakeAdb(foreground_from="monkey")

        result = await _run(adb)

        self.assertTrue(result.ok)
        self.assertTrue(adb.sent("monkey"))
        self.assertIn(("shell", "am", "start", "-n", COMPONENT), adb.calls)
        self.assertEqual(adb.vendor_calls, 1)

    async def test_any_single_path_is_enough(self) -> None:
        """回归：雷电没有 monkey、组件名解析不出时也只发得出部分路子。"""
        for winner in ("monkey", "am", "vendor"):
            with self.subTest(winner=winner):
                adb = FakeAdb(foreground_from=winner)

                result = await _run(adb)

                self.assertTrue(result.ok)
                self.assertEqual(result.reason, "launched")

    async def test_without_a_vendor_command_adb_paths_still_fire(self) -> None:
        adb = FakeAdb(foreground_from="am")

        result = await _run(adb, with_vendor=False)

        self.assertTrue(result.ok)
        self.assertEqual(adb.vendor_calls, 0)
        self.assertTrue(adb.sent("monkey"))

    async def test_unresolvable_component_skips_am_start_without_guessing(self) -> None:
        """解析不出组件名就少发一路，绝不猜一个去 am start。"""
        adb = FakeAdb(resolve="No activity found", foreground_from="vendor")

        result = await _run(adb)

        self.assertTrue(result.ok)
        self.assertFalse(adb.sent("am", "start"))
        self.assertTrue(adb.sent("monkey"))

    async def test_missing_package_stops_before_launching(self) -> None:
        """没装就别白发三路又等一轮，直接给出能照做的结论。"""
        adb = FakeAdb(pm_path="")

        result = await _run(adb)

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "not-installed")
        self.assertFalse(adb.sent("monkey"))
        self.assertEqual(adb.vendor_calls, 0)

    async def test_boot_timeout_stops_before_probing_the_package(self) -> None:
        """系统没起完时 adb 查什么都不准，不该拿它的输出下结论。"""
        adb = FakeAdb(boot="")

        result = await _run(adb)

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "boot-timeout")
        self.assertFalse(adb.sent("pm"))

    async def test_everything_fails_reports_launch_timeout(self) -> None:
        adb = FakeAdb(foreground_from="never")

        result = await _run(adb)

        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "launch-timeout")
        self.assertTrue(adb.sent("monkey"))
        self.assertEqual(adb.vendor_calls, 1)


if __name__ == "__main__":
    unittest.main()


class ForeignSerialMarkerTest(unittest.TestCase):
    """回归：`emulator-NNNN` 是全局别名，别家模拟器占了同一个回环端口就会顶包。

    实测 MuMu 6 除了 `127.0.0.1:16384` 还绑 `127.0.0.1:5555`，正好是雷电 0 号的端口；
    归属看两家的启动顺序，两个方向都复现过，而 resolve_serial 照样标「核对通过」。
    判据用「认出别人」而不是「认出自己」——雷电游戏中心用户可以卸掉。
    """

    def test_foreign_marker_present_means_not_ldplayer(self) -> None:
        # MuMu 上 `pm path com.mumu.store` 的真实输出形状
        self.assertFalse(
            is_package_missing("package:/system/app/MuMuStore/MuMuStore.apk")
        )

    def test_absent_marker_leaves_the_device_alone(self) -> None:
        """雷电上查 MuMu 的包是「返回码 1 + 空输出」，不能因此判成别家。"""
        self.assertTrue(is_package_missing(""))

    def test_markers_cover_both_mumu_packages(self) -> None:
        from app.utils.emulator2.ldplayer14 import _FOREIGN_MARKER_PACKAGES

        self.assertIn("com.mumu.store", _FOREIGN_MARKER_PACKAGES)
        self.assertIn("com.netease.mumu.cloner", _FOREIGN_MARKER_PACKAGES)
