"""自选目录 → 托管的迁移回归。

迁移最容易出的错不会报错，只会让用户在别处发现东西没了：用「新建一个托管脚本
再删旧的」代替原地转换，脚本 ID 变了，队列成员、计划表、通知绑定和 ``data/<uid>/``
下的用户数据全部对不上。

另一条是硬规矩：**迁移永远不碰原目录。** 投影是白名单式的，万一漏了运行时才需要
但 interface.json 没声明的文件，原目录是唯一的退路；删不删由用户在外面自己做。

所以这里钉的是「uid 与用户数据不变」和「原目录一个字节不动」。
"""

import shutil
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import app.api.scripts as scripts_api
from app.models.config import MaaFWConfig, MaaFWManagedConfig, MaaFWUserConfig
from app.models.ConfigBase import MultipleConfig
from app.models.schema import MaaFWManagedMigrateIn

RECORD = {
    "projectId": "m9a",
    "version": "v4.6.0",
    "storeId": "store-1",
    "dataPath": r"D:\store\projects\m9a\versions\v4.6.0\data",
    "manifest": {
        "projection": {
            "sourceSizeBytes": 100,
            "payloadSizeBytes": 40,
            "savedBytes": 60,
            "savedPercent": 60.0,
            "excluded": ["python"],
            "excludedReasons": {"python": "embedded-python"},
        },
        "shells": {"families": ["MXU"]},
    },
}


class ConvertKeepsIdentityTest(unittest.IsolatedAsyncioTestCase):
    """原地换类型：uid、顺序、用户数据一个都不能变。"""

    async def _seeded(self) -> tuple[MultipleConfig, uuid.UUID]:
        config = MultipleConfig([MaaFWConfig, MaaFWManagedConfig])
        uid, item = await config.add(MaaFWConfig)
        await item.set("Info", "Name", "我的 M9A", commit=False)
        return config, uid

    async def test_uid_and_order_survive_the_conversion(self) -> None:
        config, uid = await self._seeded()
        order_before = list(config.order)

        await config.convert(uid, MaaFWManagedConfig)

        self.assertEqual(config.order, order_before)
        self.assertIn(uid, config)
        self.assertIsInstance(config[uid], MaaFWManagedConfig)

    async def test_existing_values_are_carried_over(self) -> None:
        config, uid = await self._seeded()

        await config.convert(uid, MaaFWManagedConfig)

        self.assertEqual(config[uid].get("Info", "Name"), "我的 M9A")

    async def test_user_uuids_are_not_regenerated(self) -> None:
        # data/<script>/<user> 目录按用户 uuid 命名；重新生成会让用户数据全丢。
        config, uid = await self._seeded()
        user_uid, _ = await config[uid].UserData.add(MaaFWUserConfig)

        await config.convert(uid, MaaFWManagedConfig)

        self.assertIn(user_uid, config[uid].UserData)

    async def test_target_type_must_be_declared(self) -> None:
        config, uid = await self._seeded()
        with self.assertRaises(ValueError):
            await config.convert(uid, MaaFWConfig.__mro__[1])

    async def test_locked_item_is_refused(self) -> None:
        config, uid = await self._seeded()
        config[uid].is_locked = True
        with self.assertRaises(ValueError):
            await config.convert(uid, MaaFWManagedConfig)


class MigrateRouteTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # 用真目录：FolderValidator 会把不存在的路径纠成空串，假路径根本存不进去。
        self.source = Path(tempfile.mkdtemp(prefix="mas-migrate-"))
        self.addCleanup(shutil.rmtree, self.source, ignore_errors=True)

    async def _plain_config(self, path: str | None = None):
        config = MaaFWConfig()
        await config.set("Info", "Path", str(self.source) if path is None else path)
        return config

    def _patched(self, script_config, *, import_error=None):
        store = MagicMock()
        if import_error is not None:
            store.import_project.side_effect = import_error
        else:
            store.import_project.return_value = RECORD
        return (
            patch.object(
                scripts_api, "_maafw_script_config", return_value=script_config
            ),
            patch.object(scripts_api, "_managed_store", return_value=store),
            patch.object(scripts_api.Config, "convert_script", AsyncMock()),
            patch.object(scripts_api.Config, "update_script", AsyncMock()),
        )

    async def test_already_managed_script_is_refused(self) -> None:
        with patch.object(
            scripts_api, "_maafw_script_config", return_value=MaaFWManagedConfig()
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 400)
        self.assertIn("已经是托管形态", result.message)

    async def test_script_without_a_project_path_is_refused(self) -> None:
        with patch.object(
            scripts_api,
            "_maafw_script_config",
            return_value=await self._plain_config(path=""),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 400)
        self.assertIn("项目路径", result.message)

    async def test_import_rejection_reason_is_passed_through(self) -> None:
        patches = self._patched(
            await self._plain_config(), import_error=RuntimeError("依赖不合规")
        )
        with patches[0], patches[1], patches[2], patches[3]:
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 400)
        self.assertIn("依赖不合规", result.message)

    async def test_source_directory_is_never_touched(self) -> None:
        # 投影万一漏了文件，原目录是唯一退路；删不删由用户在资源管理器里自己做。
        marker = self.source / "keep-me.txt"
        marker.write_text("still here", encoding="utf-8")
        patches = self._patched(await self._plain_config())
        with patches[0], patches[1], patches[2], patches[3]:
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 200)
        self.assertTrue(marker.is_file())
        self.assertEqual(result.data.sourcePath, str(self.source))
        # 用户得知道原目录在哪、什么时候可以删。
        self.assertIn(str(self.source), result.message)
        self.assertIn("自行删除", result.message)

    async def test_stale_project_path_is_cleared(self) -> None:
        # 迁移后项目不在原处了；留着会把一个可能刚被删掉的目录当项目路径显示。
        update = AsyncMock()
        patches = self._patched(await self._plain_config())
        with (
            patches[0],
            patches[1],
            patches[2],
            patch.object(scripts_api.Config, "update_script", update),
        ):
            await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        payload = update.await_args.args[1]
        self.assertEqual(payload["Info"]["Path"], "")
        self.assertEqual(payload["Managed"]["ProjectId"], "m9a")


if __name__ == "__main__":
    unittest.main()
