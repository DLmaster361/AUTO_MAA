"""Emulator 2.0「屏蔽广告」挂接：纯逻辑与钩子顺序。

真机（2026-09-11，一次性 MuMu 实例）已经用产品的 ``open()`` 走通：开关开着时五个组件
``pm disable``、桌面重启后四类广告全消、游戏中心保留；开关关着时 ``pm enable`` 全部恢复，
Windows 侧占位文件也撤掉。这里只锁不用真机就能锁的：命令怎么拼、输出怎么判、占位怎么落、
两个钩子在 ``open()`` 里的顺序与容错、两家后端把什么参数交给了子进程。
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from app.models.emulator import DeviceBase, DeviceInfo, DeviceStatus
from app.utils.emulator2 import adblock, ldplayer14, mumu6
from app.utils.emulator2.adblock import (
    MUMU_AD_COMPONENTS,
    MUMU_SH_TIMEOUT,
    apply_splash_placeholders,
    ldplayer_clean_mode_args,
    mumu_component_applied,
    mumu_component_shell,
    mumu_splash_placeholder_paths,
)
from app.utils.emulator2.applaunch import AppLaunchMixin, AppLaunchResult

#: 真机上 ``MuMuManager sh -v 1 -c "pm disable --user 0 …"`` 五条合成一条后的合并输出（CRLF）。
_PM_DISABLE_OUTPUT = "".join(
    f"Component {{com.mumu.store/{component}}} new state: disabled\r\n"
    for component in MUMU_AD_COMPONENTS
)
_PM_ENABLE_OUTPUT = _PM_DISABLE_OUTPUT.replace("disabled", "enabled")


class CleanModeArgsTest(unittest.TestCase):
    """雷电只认 ``globalsetting --cleanmode 1|0``，开关两个方向都要写，和旧配置口径一致。"""

    def test_on_and_off(self) -> None:
        self.assertEqual(
            ldplayer_clean_mode_args(True), ("globalsetting", "--cleanmode", "1")
        )
        self.assertEqual(
            ldplayer_clean_mode_args(False), ("globalsetting", "--cleanmode", "0")
        )


class ComponentShellTest(unittest.TestCase):
    def test_disable_is_one_line_with_five_components(self) -> None:
        """五条合成一条：``NemuShell.exe`` 只起一次，少四次卡住的机会。"""
        shell = mumu_component_shell(True)
        parts = shell.split("; ")
        self.assertEqual(len(parts), 5)
        for part in parts:
            # 组件必须用 ``pm disable``；``disable-user`` 对组件会静默返回 default
            self.assertTrue(part.startswith("pm disable --user 0 com.mumu.store/"))
        self.assertIn("com.mumu.login_handler.LoginServerReceiver", shell)

    def test_enable_mirrors_disable(self) -> None:
        shell = mumu_component_shell(False)
        self.assertEqual(shell.count("pm enable com.mumu.store/"), 5)
        self.assertNotIn("disable", shell)


class ComponentAppliedTest(unittest.TestCase):
    def test_real_output_counts_as_applied(self) -> None:
        self.assertTrue(mumu_component_applied(_PM_DISABLE_OUTPUT, True))
        self.assertTrue(mumu_component_applied(_PM_ENABLE_OUTPUT, False))

    def test_one_missing_line_is_not_applied(self) -> None:
        four = _PM_DISABLE_OUTPUT.rsplit("Component", 1)[0]
        self.assertFalse(mumu_component_applied(four, True))

    def test_wrong_direction_is_not_applied(self) -> None:
        self.assertFalse(mumu_component_applied(_PM_ENABLE_OUTPUT, True))
        self.assertFalse(mumu_component_applied("", False))


class SplashPlaceholderTest(unittest.TestCase):
    """与旧配置 ``EMULATOR_SPLASH_ADS_PATH_BOOK`` 的手法一致：删目录、放同名空文件。"""

    def test_paths_live_under_mumu_appdata(self) -> None:
        paths = mumu_splash_placeholder_paths(Path("R:/AppData"))
        self.assertEqual(
            paths,
            [
                Path("R:/AppData/Netease/MuMuPlayer/data/startupImage"),
                Path("R:/AppData/Netease/MuMuPlayer/data/ProgramAds"),
            ],
        )

    def test_block_replaces_dir_with_empty_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "startupImage"
            (target / "sub").mkdir(parents=True)
            (target / "sub" / "ad.png").write_bytes(b"x")
            apply_splash_placeholders([target], True)
            self.assertTrue(target.is_file())
            self.assertEqual(target.stat().st_size, 0)

    def test_block_creates_missing_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "data" / "ProgramAds"
            apply_splash_placeholders([target], True)
            self.assertTrue(target.is_file())

    def test_unblock_removes_only_our_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            placeholder = Path(tmp) / "startupImage"
            placeholder.touch()
            real_dir = Path(tmp) / "ProgramAds"
            real_dir.mkdir()
            apply_splash_placeholders([placeholder, real_dir], False)
            self.assertFalse(placeholder.exists())
            self.assertTrue(real_dir.is_dir())


class _FakeNative(DeviceBase):
    """假的原生管理器：只记录 ``open`` 被调到，其余抽象方法占位。"""

    def __init__(self) -> None:  # noqa: D107 - 测试桩
        self.events: list[str] = []

    async def open(self, idx: str, package_name: str = "") -> DeviceInfo:
        self.events.append("native-open")
        return DeviceInfo(title="t", status=DeviceStatus.ONLINE, adb_address="")

    async def close(self, idx):  # pragma: no cover - 抽象方法占位
        raise NotImplementedError

    async def getInfo(self, idx):  # pragma: no cover - 抽象方法占位
        raise NotImplementedError

    async def getStatus(self, idx):  # pragma: no cover - 抽象方法占位
        raise NotImplementedError

    async def list_devices(self):  # pragma: no cover - 抽象方法占位
        raise NotImplementedError

    async def setVisible(self, idx, is_visible):  # pragma: no cover - 抽象方法占位
        raise NotImplementedError


class _Hooked(AppLaunchMixin, _FakeNative):
    def __init__(  # noqa: D107 - 测试桩
        self, *, fail_prepare: bool = False, fail_after: bool = False
    ) -> None:
        super().__init__()
        self.fail_prepare = fail_prepare
        self.fail_after = fail_after

    async def prepare_launch(self, idx: str) -> None:
        self.events.append("prepare")
        if self.fail_prepare:
            raise RuntimeError("prepare boom")

    async def after_boot(self, idx: str, info: DeviceInfo) -> None:
        self.events.append("after")
        if self.fail_after:
            raise RuntimeError("after boom")

    async def launch_app(  # type: ignore[override] - 测试桩只记录
        self, idx, package_name, info=None, *, launch_timeout=None
    ) -> AppLaunchResult:
        self.events.append(f"launch:{package_name}")
        return AppLaunchResult(True, "launched")


class HookOrderTest(unittest.IsolatedAsyncioTestCase):
    async def test_hooks_wrap_native_open_and_precede_app_launch(self) -> None:
        m = _Hooked()
        await m.open("1", "com.example")
        self.assertEqual(
            m.events, ["prepare", "native-open", "after", "launch:com.example"]
        )

    async def test_hooks_are_empty_by_default(self) -> None:
        """不覆盖钩子的后端，行为和以前完全一样。"""

        class _Plain(AppLaunchMixin, _FakeNative):
            pass

        m = _Plain()
        await m.open("1")
        self.assertEqual(m.events, ["native-open"])

    async def test_failing_hooks_never_block_the_launch(self) -> None:
        m = _Hooked(fail_prepare=True, fail_after=True)
        info = await m.open("1", "com.example")
        self.assertEqual(info.status, DeviceStatus.ONLINE)
        self.assertEqual(
            m.events, ["prepare", "native-open", "after", "launch:com.example"]
        )


class _FakeConfig:
    def get(self, group: str, key: str) -> int:
        assert (group, key) == ("Info", "MaxWaitTime")
        return 120


def _bare(cls):
    """绕过父类构造函数（它要求 exe 真实存在），只放上钩子用到的两个属性。"""
    m = object.__new__(cls)
    m.config = _FakeConfig()
    m.emulator_path = Path("R:/emu/console.exe")
    return m


class _Result:
    def __init__(self, stdout: str = "", returncode: int = 0) -> None:  # noqa: D107 - 测试桩
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


class LDPlayerHookTest(unittest.IsolatedAsyncioTestCase):
    """雷电启动前把开关写进全局纯净模式，开关两个方向都写。"""

    async def _run(self, block: bool) -> list[tuple]:
        calls: list[tuple] = []

        async def fake_run(program, *args, **kwargs):
            calls.append((program, args, kwargs))
            return _Result()

        with (
            mock.patch.object(ldplayer14, "is_block_ad_enabled", return_value=block),
            mock.patch.object(ldplayer14.ProcessRunner, "run_process", fake_run),
        ):
            await _bare(ldplayer14.LDPlayer14Manager).prepare_launch("3")
        return calls

    async def test_writes_clean_mode_both_ways(self) -> None:
        for block, flag in ((True, "1"), (False, "0")):
            with self.subTest(block=block):
                calls = await self._run(block)
                self.assertEqual(len(calls), 1)
                program, args, kwargs = calls[0]
                self.assertEqual(program, Path("R:/emu/console.exe"))
                self.assertEqual(args, ("globalsetting", "--cleanmode", flag))
                self.assertEqual(kwargs["timeout"], 120)
                self.assertTrue(kwargs["breakaway"])

    async def test_console_failure_does_not_raise(self) -> None:
        async def boom(*_args, **_kwargs):
            raise OSError("no console")

        with (
            mock.patch.object(ldplayer14, "is_block_ad_enabled", return_value=True),
            mock.patch.object(ldplayer14.ProcessRunner, "run_process", boom),
        ):
            await _bare(ldplayer14.LDPlayer14Manager).prepare_launch("3")


class MuMuHookTest(unittest.IsolatedAsyncioTestCase):
    """MuMu 在线之后走 root shell 禁 / 启组件；只有禁用成功才重启桌面。"""

    def setUp(self) -> None:
        self.m = _bare(mumu6.MuMu6Manager)
        self.shell_calls: list[str] = []
        self.restarts = 0
        self.shell_output: str | None = _PM_DISABLE_OUTPUT
        self.info = DeviceInfo(title="t", status=DeviceStatus.ONLINE, adb_address="")

        async def fake_shell(idx: str, command: str) -> str | None:
            self.shell_calls.append(command)
            return self.shell_output

        async def fake_restart(idx: str) -> None:
            self.restarts += 1

        self.m._root_shell = fake_shell
        self.m._restart_launcher = fake_restart

    async def test_block_disables_then_restarts_launcher(self) -> None:
        with mock.patch.object(mumu6, "is_block_ad_enabled", return_value=True):
            await self.m.after_boot("1", self.info)
        self.assertEqual(self.shell_calls, [mumu_component_shell(True)])
        self.assertEqual(self.restarts, 1)

    async def test_unblock_enables_without_touching_launcher(self) -> None:
        self.shell_output = _PM_ENABLE_OUTPUT
        with mock.patch.object(mumu6, "is_block_ad_enabled", return_value=False):
            await self.m.after_boot("1", self.info)
        self.assertEqual(self.shell_calls, [mumu_component_shell(False)])
        self.assertEqual(self.restarts, 0)

    async def test_partial_or_failed_shell_skips_restart(self) -> None:
        for output in (None, _PM_DISABLE_OUTPUT.rsplit("Component", 1)[0]):
            with self.subTest(output=output):
                self.restarts = 0
                self.shell_output = output
                with mock.patch.object(mumu6, "is_block_ad_enabled", return_value=True):
                    await self.m.after_boot("1", self.info)
                self.assertEqual(self.restarts, 0)


class MuMuRootShellTest(unittest.IsolatedAsyncioTestCase):
    """``MuMuManager sh`` 的底层 ``NemuShell.exe`` 会无限重试：超时必须清孤儿，而且不能抛。"""

    async def test_passes_short_timeout_and_returns_output(self) -> None:
        calls: list[tuple] = []

        async def fake_run(program, *args, **kwargs):
            calls.append((program, args, kwargs))
            return _Result("uid=0(root)\r\n")

        with mock.patch.object(mumu6.ProcessRunner, "run_process", fake_run):
            out = await _bare(mumu6.MuMu6Manager)._root_shell("1", "id")
        self.assertEqual(out, "uid=0(root)\r\n")
        program, args, kwargs = calls[0]
        self.assertEqual(args, ("sh", "-v", "1", "-c", "id"))
        self.assertEqual(kwargs["timeout"], MUMU_SH_TIMEOUT)
        self.assertLess(MUMU_SH_TIMEOUT, 60)

    async def test_timeout_kills_helper_and_returns_none(self) -> None:
        calls: list[tuple] = []

        async def fake_run(program, *args, **kwargs):
            calls.append((program, args))
            if args and args[0] == "sh":
                raise asyncio.TimeoutError
            return _Result()

        with mock.patch.object(mumu6.ProcessRunner, "run_process", fake_run):
            out = await _bare(mumu6.MuMu6Manager)._root_shell("1", "id")
        self.assertIsNone(out)
        self.assertEqual(
            calls[1], ("taskkill", ("/F", "/IM", adblock.MUMU_SH_HELPER_IMAGE))
        )

    async def test_nonzero_return_is_none(self) -> None:
        """实例没在跑时 MuMuManager 立刻报错返回，不会卡住（真机实测 0.1 秒）。"""

        async def fake_run(program, *args, **kwargs):
            return _Result('{"errcode": -201, "errmsg": "vm not running"}', 1)

        with mock.patch.object(mumu6.ProcessRunner, "run_process", fake_run):
            self.assertIsNone(await _bare(mumu6.MuMu6Manager)._root_shell("1", "id"))


if __name__ == "__main__":
    unittest.main()
