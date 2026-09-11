"""「打开游戏中心」：从 mixin 到 service 的三段纯逻辑。

真机上三路启动都已实测（雷电 cleanmode 下 ``runapp`` 1 秒到前台、``am start`` 立刻到前台），
这里只锁三件事：mixin 按后端自己的包名转发、没有商店时不碰设备、service 把原因码翻成能照做的话。
"""

import unittest

from app.utils.emulator2 import service
from app.utils.emulator2.applaunch import (
    _STORE_LAUNCH_TIMEOUT,
    AppLaunchMixin,
    AppLaunchResult,
)
from app.utils.emulator2.ldplayer14 import LDPlayer14Manager
from app.utils.emulator2.mumu6 import MuMu6Manager


class _RecordingMixin(AppLaunchMixin):
    """只记录 ``launch_app`` 收到什么，不碰设备。

    ``DeviceBase`` 是抽象类，测试桩把那几个抽象方法补成空实现即可——
    ``open_store`` 一条也不会调到它们。
    """

    def __init__(self, store_package: str | None) -> None:  # noqa: D107 - 测试桩
        self.store_package = store_package
        self.calls: list[tuple[str, str, float | None]] = []

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

    async def launch_app(  # type: ignore[override] - 测试桩只关心参数
        self, idx, package_name, info=None, *, launch_timeout=None
    ) -> AppLaunchResult:
        self.calls.append((idx, package_name, launch_timeout))
        return AppLaunchResult(True, "launched")


class OpenStoreMixinTest(unittest.IsolatedAsyncioTestCase):
    async def test_forwards_backend_store_package_with_short_timeout(self) -> None:
        """按钮点一下等 45 秒不能接受：必须用短上限，且包名来自后端自己。"""
        mixin = _RecordingMixin("com.android.flysilkworm")
        result = await mixin.open_store("3")
        self.assertTrue(result.ok)
        self.assertEqual(
            mixin.calls, [("3", "com.android.flysilkworm", _STORE_LAUNCH_TIMEOUT)]
        )
        self.assertLess(_STORE_LAUNCH_TIMEOUT, 45)

    async def test_no_store_returns_without_touching_device(self) -> None:
        mixin = _RecordingMixin(None)
        result = await mixin.open_store("3")
        self.assertFalse(result.ok)
        self.assertEqual(result.reason, "no-store")
        self.assertEqual(mixin.calls, [])


class StorePackageTest(unittest.TestCase):
    def test_both_backends_declare_their_store(self) -> None:
        """两家的游戏中心包名，实测来源：雷电 ``/system/priv-app/ldAppStore``、MuMu ``/system/priv-app/com.mumu.store``。"""
        self.assertEqual(LDPlayer14Manager.store_package, "com.android.flysilkworm")
        self.assertEqual(MuMu6Manager.store_package, "com.mumu.store")


class StoreOpenMessageTest(unittest.TestCase):
    def test_every_reason_has_a_message(self) -> None:
        """界面直接显示 message，任何一个原因码漏了都会给用户看到裸英文码。"""
        for reason in (
            "launched",
            "already-running",
            "no-store",
            "not-installed",
            "no-adb",
            "boot-timeout",
            "launch-timeout",
        ):
            with self.subTest(reason=reason):
                self.assertIn(reason, service._STORE_OPEN_MESSAGES)
                self.assertTrue(service._STORE_OPEN_MESSAGES[reason])


if __name__ == "__main__":
    unittest.main()
