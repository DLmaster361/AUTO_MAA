import unittest
from unittest.mock import patch

from app.models.emulator import DeviceInfo, DeviceStatus
from app.utils.emulator2 import service
from app.utils.emulator2.slots import PathRecord, SlotTable

LD = r"D:\leidian\LDPlayer14"


class FakeBackend:
    async def getInfo(self, idx):
        return {
            "0": DeviceInfo(title="0", status=DeviceStatus.OFFLINE, adb_address=""),
        }

    async def read_instance_settings(self, idx):
        from app.utils.emulator2.settings import build_settings

        return build_settings({"basicSettings.fps": 60}, None)

    async def read_stable_mode(self, idx):
        return True, []


class FakeManager:
    """只提供 list_devices 用到的那几样。"""

    def __init__(self, native_indexes) -> None:
        self.path = PathRecord.create(LD, "雷电", "ldplayer", "14.0.25.1")
        self.paths = [self.path]
        self.slots = SlotTable()
        # 表里有两台（0 和 1），但这次枚举只报出 native_indexes 里的
        self.slots.sync_path(self.path.path_id, ["0", "1"])
        self._native_indexes = native_indexes

    async def enumerate_native(self, path):
        return self._native_indexes

    async def manager_for(self, path):
        return FakeBackend()


async def run_list(native_indexes):
    manager = FakeManager(native_indexes)
    with (
        patch.object(service, "build_manager", return_value=manager),
        patch.object(service, "_save", return_value=None),
    ):
        return await service.list_devices("fake-id")


class MissingDevicesAreHiddenTest(unittest.IsolatedAsyncioTestCase):
    """查证不存在的实例不该在设备表里占一行。

    用户的原话：「你都 not found 了还显示它干嘛」。列一台并不存在的模拟器，
    对用户来说就是一台幽灵设备。
    """

    async def test_absent_instance_gets_no_row(self) -> None:
        """枚举成功、但表里那台不在结果中 = 已确认它没了。"""
        result = await run_list(["0"])

        self.assertEqual([d["slot"] for d in result["devices"]], ["0"])

    async def test_present_instances_still_show(self) -> None:
        result = await run_list(["0", "1"])

        self.assertEqual([d["slot"] for d in result["devices"]], ["0", "1"])

    async def test_unreachable_install_keeps_all_its_rows(self) -> None:
        """枚举失败是「没问到」，不是「确认没有」——这时候藏起来才是错的。

        整条安装不可达（路径在断开的盘上等）时实例多半都还在，
        把它们全部从表里抹掉会让用户以为模拟器没了。
        """
        result = await run_list(None)

        self.assertEqual([d["slot"] for d in result["devices"]], ["0", "1"])
        self.assertEqual(
            {d["availability"] for d in result["devices"]}, {"unavailable"}
        )

    async def test_hidden_row_keeps_its_slot_record(self) -> None:
        """行不显示，但设备号仍占着：同一个原生索引再出现还是这个号。"""
        manager = FakeManager(["0"])
        with (
            patch.object(service, "build_manager", return_value=manager),
            patch.object(service, "_save", return_value=None),
        ):
            await service.list_devices("fake-id")

        record = manager.slots.resolve("1")
        assert record is not None
        self.assertEqual(record.state, "active")


if __name__ == "__main__":
    unittest.main()
