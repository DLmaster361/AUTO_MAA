"""MFW 托管的小范围试用开关。

开关只锁「进门」——建托管脚本、导入项目、把现有脚本转成托管；不锁「房间」——
已经建好的托管脚本关掉开关后仍然能看版本、切版本、跑。两条都要钉住：

- 锁门漏了一处，就等于没有试用期；
- 锁到房间里，维护者哪天关掉开关，试用者的脚本会集体瘫掉，而这一步不会报错。

文案里故意不写怎么打开：谁能用是维护者逐个告知的事，界面不该自己泄露。
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import app.api.scripts as scripts_api
import app.core  # noqa: F401  # 初始化宿主配置
from app.core import Config
from app.models.schema import (
    MaaFWManagedImportIn,
    MaaFWManagedMigrateIn,
    MaaFWManagedVersionsIn,
    ScriptCreateIn,
)

DENIED = "尚未对本安装开放"


def _preview(enabled: bool):
    return patch.object(Config, "maafw_managed_preview_enabled", return_value=enabled)


class GateDefaultsTest(unittest.TestCase):
    def test_disabled_by_default(self) -> None:
        # 新装用户不该莫名其妙看到一个未验证的功能。
        from app.models.config import GlobalConfig

        self.assertFalse(GlobalConfig().get("Function", "MaaFWManagedPreview"))

    def test_denial_message_does_not_explain_how_to_enable(self) -> None:
        with _preview(False), self.assertRaises(PermissionError) as caught:
            Config.require_maafw_managed_preview()
        text = str(caught.exception)
        self.assertIn(DENIED, text)
        for leak in ("Config.json", "MaaFWManagedPreview", "Function"):
            self.assertNotIn(leak, text)

    def test_schema_carries_the_key_so_the_frontend_can_read_it(self) -> None:
        # 前端靠 /api/setting/get 决定藏不藏入口；保存走 exclude_unset，界面不绑它
        # 就永远不会回写，因此放进 schema 不会被设置页的保存抹掉。
        from app.models.schema import GlobalConfig_Function

        self.assertIn("MaaFWManagedPreview", GlobalConfig_Function.model_fields)


class DoorIsLockedTest(unittest.IsolatedAsyncioTestCase):
    async def test_add_script_refuses_managed_type(self) -> None:
        with _preview(False), self.assertRaises(PermissionError):
            await Config.add_script("MaaFWManaged")

    async def test_add_route_answers_403_not_500(self) -> None:
        # 策略拒绝不是故障：三个入口的状态码和文案要一致，试用者回报时才说得清。
        with _preview(False):
            result = await scripts_api.add_script(ScriptCreateIn(type="MaaFWManaged"))
        self.assertEqual(result.code, 403)
        self.assertIn(DENIED, result.message)
        self.assertNotIn("PermissionError", result.message)

    async def test_add_script_still_allows_plain_maafw(self) -> None:
        # 只锁托管这一种类型，自选目录形态的 MFW 不受影响。
        add = AsyncMock(return_value=("uid", object()))
        with _preview(False), patch.object(Config.ScriptConfig, "add", add):
            await Config.add_script("MaaFW")
        add.assert_awaited_once()

    async def test_convert_script_refuses_when_locked(self) -> None:
        with _preview(False), self.assertRaises(PermissionError):
            await Config.convert_script(
                "00000000-0000-0000-0000-000000000000", "MaaFWManaged"
            )

    async def test_import_route_refuses_before_touching_the_store(self) -> None:
        store = MagicMock()
        with (
            _preview(False),
            patch.object(scripts_api, "_managed_store", return_value=store),
        ):
            result = await scripts_api.import_managed_maafw_project(
                MaaFWManagedImportIn(sourcePath=r"D:\x")
            )
        self.assertEqual(result.code, 403)
        self.assertIn(DENIED, result.message)
        store.import_project.assert_not_called()

    async def test_migrate_route_refuses_before_reading_the_script(self) -> None:
        resolve = MagicMock()
        with (
            _preview(False),
            patch.object(scripts_api, "_maafw_script_config", resolve),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )
        self.assertEqual(result.code, 403)
        self.assertIn(DENIED, result.message)
        resolve.assert_not_called()


class RoomStaysOpenTest(unittest.IsolatedAsyncioTestCase):
    async def test_existing_project_versions_are_still_listed_when_locked(self) -> None:
        store = MagicMock()
        store.list_versions.return_value = [
            {"version": "v1", "current": True, "pinned": False, "references": []}
        ]
        with (
            _preview(False),
            patch.object(scripts_api, "_managed_store", return_value=store),
        ):
            result = await scripts_api.list_managed_maafw_versions(
                MaaFWManagedVersionsIn(projectId="m9a")
            )
        self.assertEqual(result.code, 200)
        self.assertEqual(result.data.current, "v1")

    async def test_add_script_allows_managed_type_when_enabled(self) -> None:
        add = AsyncMock(return_value=("uid", object()))
        with _preview(True), patch.object(Config.ScriptConfig, "add", add):
            await Config.add_script("MaaFWManaged")
        add.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
