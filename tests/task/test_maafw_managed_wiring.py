"""第三层（MAS 托管）接线后的回归。

前身是 `tests/task/test_maafw_managed_gate.py`（`137adfed` 落库、#509 删除），
它当年把「落库不接线」钉死；解 gate 的前提是第二层稳定，而第二层已合入 dev 并
经真机修复，因此这里把每一条断言**反过来写**：接线点必须在位。

只覆盖不触碰文件系统、不联网、不装解释器的部分。
"""

import unittest
from pathlib import Path

import app.core  # noqa: F401  # 初始化宿主配置
from app.core.config import _as_json_mapping
from app.models.config import CLASS_BOOK, MaaFWConfig, MaaFWManagedConfig
from app.models.ConfigBase import (
    ConfigItem,
    FolderValidator,
    JSONValidator,
    ManagedFolderValidator,
)
from app.utils.constants import TYPE_BOOK

REPO_ROOT = Path(__file__).resolve().parents[2]


class ManagedScriptTypeRegisteredTest(unittest.TestCase):
    """托管脚本类型必须在每一张按类名/键索引的表里，漏一张就静默出错。"""

    def test_subclasses_maafw_so_existing_dispatch_still_hits(self) -> None:
        # task_manager 用 isinstance 分发到 MaaFWEmbeddedManager；子类化正是
        # 为了让托管形态复用同一个 manager 而不必新写一个。
        self.assertTrue(issubclass(MaaFWManagedConfig, MaaFWConfig))

    def test_registered_in_class_book_with_contract_key(self) -> None:
        # 键必须正好是 "MaaFWManaged"：environment_service 硬编码了它。
        self.assertIs(CLASS_BOOK.get("MaaFWManaged"), MaaFWManagedConfig)

    def test_registered_in_type_book(self) -> None:
        # 缺了会在按类名取显示名处 KeyError。
        self.assertIn("MaaFWManagedConfig", TYPE_BOOK)

    def test_registered_in_script_config_list(self) -> None:
        # MultipleConfig 按类名索引；漏注册会在加载时静默丢弃整条脚本配置。
        source = (REPO_ROOT / "app" / "models" / "config.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("MaaFWManagedConfig,", source)

    def test_only_the_subclass_carries_the_three_managed_keys(self) -> None:
        managed = MaaFWManagedConfig()
        for name in ("ImportProjectId", "RunRootId", "Status"):
            self.assertEqual(managed.get("Managed", name), "")
        self.assertFalse(hasattr(MaaFWConfig(), "Managed_Status"))


class ManagedProjectPathValidatorTest(unittest.TestCase):
    """托管的 `Info.Path` 指向 MAS 自己产出的 checkout，就在工作目录之下。"""

    def test_parent_still_forbids_the_working_directory(self) -> None:
        inside = str(Path.cwd() / "data" / "maafw_project_runs")
        self.assertFalse(FolderValidator().validate(inside))

    def test_managed_validator_allows_the_working_directory(self) -> None:
        self.assertNotIn(Path.cwd().resolve(), ManagedFolderValidator()._forbidden_paths())

    def test_managed_validator_still_forbids_drive_root(self) -> None:
        self.assertFalse(ManagedFolderValidator().validate(str(Path.cwd().anchor)))

    def test_each_config_uses_its_own_validator(self) -> None:
        self.assertIsInstance(MaaFWConfig().Info_Path.validator, FolderValidator)
        self.assertIsInstance(
            MaaFWManagedConfig().Info_Path.validator, ManagedFolderValidator
        )


class JSONValidatorAcceptsStructuredInputTest(unittest.TestCase):
    """托管环境服务写的是 dict；只认字符串会把值静默丢成空。"""

    def test_dict_is_serialised_instead_of_discarded(self) -> None:
        corrected = JSONValidator(dict).correct({"runtimeId": "r1"})
        self.assertEqual(corrected, '{"runtimeId": "r1"}')

    def test_list_is_serialised(self) -> None:
        self.assertEqual(JSONValidator(list).correct([1, 2]), "[1, 2]")

    def test_string_input_is_unchanged(self) -> None:
        self.assertEqual(JSONValidator(dict).correct('{"a":1}'), '{"a":1}')

    def test_invalid_text_still_falls_back(self) -> None:
        self.assertEqual(JSONValidator(dict).correct("nope"), "{ }")
        self.assertEqual(JSONValidator(list).correct("nope"), "[ ]")

    def test_config_item_stores_json_text(self) -> None:
        item = ConfigItem("Managed", "ProjectManifest", "{ }", JSONValidator(dict))
        item.setValue({"runtime": {"binding": {"runtimeId": "r1"}}})
        self.assertIsInstance(item.value, str)
        self.assertIn("runtimeId", item.value)


class ScriptRecordJSONFieldTest(unittest.TestCase):
    """`get_script_records` 要把 JSON 字段解析成 Mapping 再交给托管环境服务。"""

    def test_parses_text(self) -> None:
        self.assertEqual(_as_json_mapping('{"a": 1}'), {"a": 1})

    def test_passes_through_mapping(self) -> None:
        self.assertEqual(_as_json_mapping({"a": 1}), {"a": 1})

    def test_degrades_broken_values_to_empty(self) -> None:
        for raw in ("", "   ", "nope", "[1,2]", None, 5):
            self.assertEqual(_as_json_mapping(raw), {})


class ManagedLayerIsWiredTest(unittest.TestCase):
    """当年门禁测试断言「没接线」的四处，现在必须反过来成立。"""

    def test_embedded_manager_references_the_managed_layer(self) -> None:
        source = (
            REPO_ROOT / "app" / "task" / "MaaFW" / "embedded_manager.py"
        ).read_text(encoding="utf-8")
        self.assertIn("MaaFWManagedConfig", source)
        self.assertIn("prepare_script_environment", source)
        self.assertIn("managed_execution_route", source)

    def test_host_contracts_exist(self) -> None:
        from app.core.config import AppConfig

        self.assertTrue(hasattr(AppConfig, "get_script_records"))
        self.assertTrue(hasattr(AppConfig, "script_config_transaction"))


class ManagedRemoteUpdateIsWiredTest(unittest.TestCase):
    """远程更新那条链路只有全接上才有效，缺一环都是静默降级。"""

    def test_gateway_carries_the_project_update_service(self) -> None:
        # 这一位曾经固定传 None（本地导入用不到）。仍是 None 的话，托管脚本
        # 的自动更新会在「缺少服务」上失败，而失败是被吞掉只记日志的。
        from app.task.MaaFW.embedded_manager import MaaFWEmbeddedManager

        gateway = MaaFWEmbeddedManager._resolve_managed_gateway()
        self.assertIsNotNone(gateway.project_update)
        self.assertTrue(hasattr(gateway.project_update, "discover_update"))
        self.assertTrue(hasattr(gateway.project_update, "download_package"))
        self.assertTrue(hasattr(gateway.project_update, "release_download_package"))

    def test_update_runs_before_the_environment_is_prepared(self) -> None:
        """顺序反了不会报错，只是这一轮仍然跑旧版本。

        准备环境会解析 Store 的当前版本并建 checkout；更新排在它后面，切过去的
        新版本要等下一次运行才生效，日志却已经说「已更新」。
        """

        import inspect

        from app.task.MaaFW.embedded_manager import MaaFWEmbeddedManager

        source = inspect.getsource(MaaFWEmbeddedManager.main_task)
        update_at = source.find("_run_managed_project_update")
        prepare_at = source.find("_prepare_managed_environment")
        self.assertGreater(update_at, -1)
        self.assertGreater(prepare_at, -1)
        self.assertLess(update_at, prepare_at)

    def test_managed_scripts_skip_the_in_place_updater(self) -> None:
        # 就地更新会把 Store 产出的 checkout 当用户目录改写。
        import inspect

        from app.task.MaaFW.embedded_manager import MaaFWEmbeddedManager

        source = inspect.getsource(MaaFWEmbeddedManager.main_task)
        self.assertIn("not self._is_managed", source)


if __name__ == "__main__":
    unittest.main()
