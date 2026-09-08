"""托管 Project Store 六条路由的回归。

端点直接调用、Store 用 mock：这些路由自己不含业务，价值全在「把 Store 的结果和
拒绝理由如实翻译给界面」，所以测的正是翻译本身。
"""

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import app.api.scripts as scripts_api
from app.models.schema import (
    MaaFWManagedGcIn,
    MaaFWManagedImportIn,
    MaaFWManagedSwitchIn,
    MaaFWManagedVersionDeleteIn,
    MaaFWManagedVersionsIn,
)

MANIFEST = {
    "projection": {
        "sourceSizeBytes": 684_302_336,
        "payloadSizeBytes": 74_711_040,
        "savedBytes": 609_591_296,
        "savedPercent": 89.09,
        "excluded": ["libs", "python", "runtimes"],
        "excludedReasons": {"libs": "ui-shell", "python": "embedded-python"},
    },
    "shells": {"families": ["MFAAvalonia", "MaaPiCli"]},
}
RECORD = {
    "projectId": "m9a",
    "version": "v4.6.0",
    "storeId": "store-1",
    "dataPath": r"D:\store\projects\m9a\versions\v4.6.0\data",
    "manifest": MANIFEST,
}


class ProjectionSummaryTest(unittest.TestCase):
    """脱壳报告的数值一律取自 manifest，不在这里重算。"""

    def test_reads_numbers_from_manifest(self) -> None:
        p = scripts_api._managed_projection(MANIFEST)
        self.assertEqual(p.savedBytes, 609_591_296)
        self.assertAlmostEqual(p.savedPercent, 89.09)
        self.assertEqual(p.excludedCount, 3)
        self.assertEqual(p.shellFamilies, ["MFAAvalonia", "MaaPiCli"])
        self.assertEqual(p.excludedReasons["libs"], "ui-shell")

    def test_empty_manifest_degrades_to_zeros(self) -> None:
        p = scripts_api._managed_projection({})
        self.assertEqual((p.savedBytes, p.excludedCount, p.shellFamilies), (0, 0, []))


class ImportRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_import_without_script_does_not_bind(self) -> None:
        store = MagicMock()
        store.import_project.return_value = RECORD
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.import_managed_maafw_project(
                MaaFWManagedImportIn(sourcePath=r"D:\pkg")
            )
        self.assertEqual(out.code, 200)
        self.assertFalse(out.data.bound)
        self.assertEqual(out.data.projectId, "m9a")
        self.assertIn("89.09", out.message)

    async def test_import_binds_store_identity_not_just_version(self) -> None:
        """只写 projectId/version 会在运行时被拒，绑定必须带上 StoreId 与 manifest。"""

        store = MagicMock()
        store.import_project.return_value = RECORD
        update = AsyncMock()
        with (
            patch.object(scripts_api, "_managed_store", return_value=store),
            patch.object(scripts_api.Config, "update_script", update),
        ):
            out = await scripts_api.import_managed_maafw_project(
                MaaFWManagedImportIn(sourcePath=r"D:\pkg", scriptId="s1")
            )
        self.assertTrue(out.data.bound)
        managed = update.await_args.args[1]["Managed"]
        self.assertEqual(managed["StoreId"], "store-1")
        self.assertIs(managed["ProjectManifest"], MANIFEST)
        self.assertTrue(managed["Enabled"])

    async def test_gate_rejection_reason_is_passed_through(self) -> None:
        store = MagicMock()
        store.import_project.side_effect = RuntimeError(
            "Python Agent runtime ABI is unknown for indexes 0"
        )
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.import_managed_maafw_project(
                MaaFWManagedImportIn(sourcePath=r"D:\src-repo")
            )
        self.assertEqual(out.code, 400)
        self.assertIn("ABI is unknown", out.message)
        self.assertIsNone(out.data)


class VersionRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_versions_are_flattened_for_the_ui(self) -> None:
        store = MagicMock()
        store.list_versions.return_value = [
            {
                "version": "v4.6.0",
                "current": True,
                "pinned": False,
                "references": ["maafw-project:m9a@v4.6.0"],
                "lastUsedAt": "2026-09-08T00:00:00Z",
                "manifest": {"createdAt": "2026-09-07T00:00:00Z"},
                "summary": {"payloadSizeBytes": 74_711_040},
            },
            {"version": "v4.5.0", "current": False, "pinned": True},
        ]
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.list_managed_maafw_versions(
                MaaFWManagedVersionsIn(projectId="m9a")
            )
        self.assertEqual(out.data.current, "v4.6.0")
        self.assertEqual(len(out.data.versions), 2)
        self.assertEqual(out.data.versions[0].sizeBytes, 74_711_040)
        self.assertTrue(out.data.versions[1].pinned)

    async def test_switch_updates_script_binding_when_given(self) -> None:
        store = MagicMock()
        store.resolve_project.return_value = RECORD
        update = AsyncMock()
        with (
            patch.object(scripts_api, "_managed_store", return_value=store),
            patch.object(scripts_api.Config, "update_script", update),
        ):
            out = await scripts_api.switch_managed_maafw_version(
                MaaFWManagedSwitchIn(projectId="m9a", version="v4.6.0", scriptId="s1")
            )
        self.assertEqual(out.code, 200)
        store.switch_version.assert_called_once_with("m9a", "v4.6.0")
        self.assertEqual(update.await_args.args[1]["Managed"]["Version"], "v4.6.0")

    async def test_delete_block_reason_is_passed_through(self) -> None:
        """current / pinned / references / lease 的阻断理由要原样给用户。"""

        store = MagicMock()
        store.delete_version.side_effect = RuntimeError("version is pinned")
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.delete_managed_maafw_version(
                MaaFWManagedVersionDeleteIn(projectId="m9a", version="v4.6.0")
            )
        self.assertEqual(out.code, 400)
        self.assertIn("pinned", out.message)


class InventoryAndGcRouteTest(unittest.IsolatedAsyncioTestCase):
    async def test_inventory_sums_project_sizes(self) -> None:
        store = MagicMock()
        store.storage_info.return_value = {
            "storeId": "store-1",
            "root": r"D:\store",
            "runRoot": r"D:\runs",
        }
        store.list_projects.return_value = [
            {"projectId": "m9a", "current": "v4.6.0", "versionCount": 2, "sizeBytes": 100},
            {"projectId": "kes", "current": "v1.1.11", "versionCount": 1, "sizeBytes": 52},
        ]
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.get_managed_maafw_inventory()
        self.assertEqual(out.data.totalBytes, 152)
        self.assertEqual(out.data.storeId, "store-1")
        self.assertEqual(len(out.data.projects), 2)

    async def test_gc_defaults_to_dry_run(self) -> None:
        store = MagicMock()
        store.collect_garbage.return_value = {"removed": ["m9a@v4.5.0"]}
        with patch.object(scripts_api, "_managed_store", return_value=store):
            out = await scripts_api.collect_managed_maafw_garbage(MaaFWManagedGcIn())
        store.collect_garbage.assert_called_once_with(dry_run=True)
        self.assertIn("预览完成", out.message)
        self.assertIn("1 项", out.message)


if __name__ == "__main__":
    unittest.main()
