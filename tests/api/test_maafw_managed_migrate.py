"""自选目录 → 托管的迁移回归。

迁移最容易出的两种错都不会报错，只会让用户在别处发现东西没了：

- 用「新建一个托管脚本再删旧的」代替原地转换：脚本 ID 变了，队列成员、计划表、
  通知绑定和 ``data/<uid>/`` 下的用户数据全部对不上。
- 删原目录删早了或删错了：导入还没成功就把源删了，或者把驱动器根、AUTO-MAS
  自己的工作目录当成"原目录"删掉。

所以这里钉的是「uid 与用户数据不变」和「删除的时机与范围」。
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

    def _patched(self, script_config, *, import_error=None, rmtree=None):
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
            patch.object(scripts_api.shutil, "rmtree", rmtree or MagicMock()),
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
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 400)
        self.assertIn("依赖不合规", result.message)

    async def test_source_is_kept_unless_the_user_asked(self) -> None:
        rmtree = MagicMock()
        patches = self._patched(await self._plain_config(), rmtree=rmtree)
        with patches[0], patches[1], patches[2], patches[3], patches[4]:
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1")
            )

        self.assertEqual(result.code, 200)
        self.assertFalse(result.data.sourceDeleted)
        rmtree.assert_not_called()

    async def test_source_is_deleted_only_after_a_successful_conversion(self) -> None:
        rmtree = MagicMock()
        patches = self._patched(await self._plain_config(), rmtree=rmtree)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patch.object(
                scripts_api.FolderValidator, "validate", lambda _self, _v: True
            ),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1", deleteSource=True)
            )

        self.assertTrue(result.data.sourceDeleted)
        rmtree.assert_called_once()

    async def test_conversion_failure_leaves_the_source_alone(self) -> None:
        rmtree = MagicMock()
        patches = self._patched(await self._plain_config(), rmtree=rmtree)
        with (
            patches[0],
            patches[1],
            patches[4],
            patch.object(
                scripts_api.Config,
                "convert_script",
                AsyncMock(side_effect=RuntimeError("配置已锁定")),
            ),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1", deleteSource=True)
            )

        self.assertEqual(result.code, 500)
        rmtree.assert_not_called()

    async def test_forbidden_source_is_reported_not_deleted(self) -> None:
        rmtree = MagicMock()
        patches = self._patched(await self._plain_config(), rmtree=rmtree)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patch.object(
                scripts_api.FolderValidator, "validate", lambda _self, _v: False
            ),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1", deleteSource=True)
            )

        self.assertEqual(result.code, 200)
        self.assertFalse(result.data.sourceDeleted)
        self.assertIn("允许删除的范围", result.data.sourceDeleteError)
        rmtree.assert_not_called()

    async def test_delete_failure_does_not_undo_a_finished_migration(self) -> None:
        # 项目已经在 Store 里、脚本也已经转过去了，把这一步报成失败会让用户以为
        # 迁移没成，再点一次就又导入一个同内容的新版本。
        rmtree = MagicMock(side_effect=PermissionError("文件占用"))
        patches = self._patched(await self._plain_config(), rmtree=rmtree)
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[3],
            patches[4],
            patch.object(
                scripts_api.FolderValidator, "validate", lambda _self, _v: True
            ),
        ):
            result = await scripts_api.migrate_maafw_script_to_managed(
                MaaFWManagedMigrateIn(scriptId="s1", deleteSource=True)
            )

        self.assertEqual(result.code, 200)
        self.assertFalse(result.data.sourceDeleted)
        self.assertIn("文件占用", result.data.sourceDeleteError)
        self.assertIn("原目录未删除", result.message)

    async def test_stale_project_path_is_cleared(self) -> None:
        # 迁移后项目不在原处了；留着会把一个可能刚被删掉的目录当项目路径显示。
        update = AsyncMock()
        patches = self._patched(await self._plain_config())
        with (
            patches[0],
            patches[1],
            patches[2],
            patches[4],
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
