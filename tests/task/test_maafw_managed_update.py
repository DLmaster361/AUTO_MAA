"""托管形态远程更新编排的纯逻辑回归。

这条链路（发现 → 下载 → 导入为新版本 → 切换）原本在未移植的插件宿主里，接线
时是重写的，所以每一个「写错了不报错、只是结果不对」的点都要钉住：

- 差量包会导出一个跑不起来的版本 → ``prefer_full_package`` 必须为真
- 托管载荷已脱壳，外壳提示只能从 manifest 回填，否则同项目多外壳发行会选错包
- ``upgrade_project`` 固定 inactive 导入，不切版本就等于没更新
- 临时下载包必须释放，且释放失败不能盖掉真正的失败原因

全部用假网关，不联网、不落盘。
"""

import unittest
from typing import Any

from app.task.MaaFW.tools.embedded.managed_update import (
    ManagedUpdateError,
    build_managed_source_config,
    managed_shell_hint,
    update_managed_project,
)


class FakeGateway:
    """记录调用的假网关。每个动作的返回值都可以按用例改写。"""

    def __init__(self, **overrides: Any) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.project = overrides.get(
            "project", {"projectId": "M9A", "version": "v4.6.0", "dataPath": "/store/p"}
        )
        self.interface = overrides.get("interface", {"name": "M9A"})
        self.discovery = overrides.get("discovery")
        self.package = overrides.get("package", {"path": "/tmp/pkg.zip", "sha256": "a"})
        self.upgraded = overrides.get("upgraded", {"latestVersion": "v4.7.0"})
        self.released = overrides.get("released", {"retained": False})
        self.upgrade_error: Exception | None = overrides.get("upgrade_error")
        self.release_error: Exception | None = overrides.get("release_error")

    def _record(self, name: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        self.calls.append((name, args, kwargs))

    @property
    def call_names(self) -> list[str]:
        return [name for name, _, _ in self.calls]

    def kwargs_of(self, name: str) -> dict[str, Any]:
        return next(kwargs for called, _, kwargs in self.calls if called == name)

    def args_of(self, name: str) -> tuple[Any, ...]:
        return next(args for called, args, _ in self.calls if called == name)

    async def resolve_project(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("resolve_project", args, kwargs)
        return self.project

    async def load_interface(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("load_interface", args, kwargs)
        return self.interface

    async def discover_remote_update(self, *args: Any, **kwargs: Any) -> Any:
        self._record("discover_remote_update", args, kwargs)
        return self.discovery

    async def download_remote_package(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("download_remote_package", args, kwargs)
        return self.package

    async def upgrade_project(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("upgrade_project", args, kwargs)
        if self.upgrade_error is not None:
            raise self.upgrade_error
        return self.upgraded

    async def switch_version(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("switch_version", args, kwargs)
        return {"switched": True}

    async def release_remote_package(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self._record("release_remote_package", args, kwargs)
        if self.release_error is not None:
            raise self.release_error
        return self.released


def installable_discovery(version: str = "v4.7.0") -> dict[str, Any]:
    return {
        "version": version,
        "candidate": {
            "source": "mirrorchyan",
            "version": version,
            "download_url": "https://example.invalid/pkg.zip",
            "sha256": "b",
        },
    }


async def run_update(gateway: FakeGateway, **overrides: Any) -> Any:
    payload: dict[str, Any] = {
        "script_id": "s1",
        "project_id": "M9A",
        "current_version": "v4.6.0",
        "source_config": {"package_source": "github_release"},
        "download_root": "/tmp/dl",
    }
    payload.update(overrides)
    return await update_managed_project(gateway, **payload)


class ShellHintTest(unittest.TestCase):
    """脱壳把根目录标志文件全删了，提示只能从 manifest 回填。"""

    def test_reads_family_recorded_by_the_store(self) -> None:
        self.assertEqual(
            managed_shell_hint({"shells": {"families": ["MXU"]}}),
            "MXU",
        )

    def test_picks_the_primary_shell_when_several_were_stripped(self) -> None:
        # MXU 包里常常还留着 MaaPiCli；选资产要看主外壳。
        self.assertEqual(
            managed_shell_hint({"shells": {"families": ["MaaPiCli", "MXU"]}}),
            "MXU",
        )

    def test_unknown_or_malformed_manifest_yields_no_hint(self) -> None:
        for manifest in (
            None,
            {},
            {"shells": None},
            {"shells": {"families": None}},
            {"shells": {"families": []}},
            {"shells": {"families": ["Unheard"]}},
        ):
            with self.subTest(manifest=manifest):
                self.assertEqual(managed_shell_hint(manifest), "")

    def test_source_config_carries_the_hint_only_when_known(self) -> None:
        with_hint = build_managed_source_config(
            package_source="github_release",
            mirror_cdk="",
            channel="stable",
            manifest={"shells": {"families": ["MFAAvalonia"]}},
        )
        self.assertEqual(with_hint["project_shell_hint"], "MFAAvalonia")
        # 认不出来时不能塞空串：核心包只在非空时才当它有效，塞了反而多一层猜。
        without_hint = build_managed_source_config(
            package_source="github_release",
            mirror_cdk="",
            channel="stable",
            manifest={},
        )
        self.assertNotIn("project_shell_hint", without_hint)


class ManagedUpdateFlowTest(unittest.IsolatedAsyncioTestCase):
    async def test_no_discovery_reports_up_to_date_without_downloading(self) -> None:
        gateway = FakeGateway(discovery=None)
        outcome = await run_update(gateway)

        self.assertFalse(outcome.updated)
        self.assertEqual(outcome.level, "info")
        self.assertIn("已是最新", outcome.reason)
        self.assertNotIn("download_remote_package", gateway.call_names)

    async def test_always_asks_for_a_full_package(self) -> None:
        # 差量包解开只是一堆补丁文件，作为不可变版本导进去就是个坏版本。
        gateway = FakeGateway(discovery=None)
        await run_update(gateway)

        self.assertIs(
            gateway.kwargs_of("discover_remote_update")["prefer_full_package"],
            True,
        )

    async def test_proxy_reaches_both_discovery_and_download(self) -> None:
        # 少传一处就会出现「自选目录形态能更、托管形态不能更」。
        gateway = FakeGateway(discovery=installable_discovery())
        await run_update(gateway, proxy="proxy-object")

        self.assertEqual(
            gateway.kwargs_of("discover_remote_update")["proxy"], "proxy-object"
        )
        self.assertEqual(
            gateway.kwargs_of("download_remote_package")["proxy"], "proxy-object"
        )

    async def test_interface_is_read_from_the_immutable_payload(self) -> None:
        # 更新跑在准备环境之前，这时脚本还没有 checkout 可读。
        gateway = FakeGateway(discovery=None)
        await run_update(gateway)

        self.assertEqual(gateway.args_of("load_interface"), ("/store/p",))

    async def test_new_version_without_download_url_is_reported_not_installed(
        self,
    ) -> None:
        gateway = FakeGateway(
            discovery={
                "version": "v4.7.0",
                "candidate": {"source": "mirrorchyan", "version": "v4.7.0"},
                "unavailable_reason": "CDK 已过期",
            }
        )
        outcome = await run_update(gateway)

        self.assertFalse(outcome.updated)
        self.assertEqual(outcome.level, "warning")
        self.assertIn("CDK 已过期", outcome.reason)
        self.assertNotIn("download_remote_package", gateway.call_names)

    async def test_missing_candidate_still_surfaces_a_reason(self) -> None:
        gateway = FakeGateway(
            discovery={"version": "v4.7.0", "message": "GitHub 未发布匹配资产"}
        )
        outcome = await run_update(gateway)

        self.assertFalse(outcome.updated)
        self.assertIn("GitHub 未发布匹配资产", outcome.reason)

    async def test_happy_path_imports_then_switches_then_releases(self) -> None:
        gateway = FakeGateway(discovery=installable_discovery())
        outcome = await run_update(gateway)

        self.assertTrue(outcome.updated)
        self.assertEqual(outcome.latest_version, "v4.7.0")
        self.assertEqual(
            gateway.call_names,
            [
                "resolve_project",
                "load_interface",
                "discover_remote_update",
                "download_remote_package",
                "upgrade_project",
                "switch_version",
                "release_remote_package",
            ],
        )

    async def test_switch_uses_the_version_the_store_actually_imported(self) -> None:
        # Store 可能归一化版本号；跟着发现结果切会切到一个不存在的版本。
        gateway = FakeGateway(
            discovery=installable_discovery("v4.7.0"),
            upgraded={"latestVersion": "4.7.0"},
        )
        outcome = await run_update(gateway)

        self.assertEqual(gateway.args_of("switch_version")[0]["version"], "4.7.0")
        self.assertEqual(outcome.latest_version, "4.7.0")

    async def test_import_reference_uses_the_reconciler_prefix(self) -> None:
        # reconcile_project_references 只认 maafw-upgrade:<scriptId>: 前缀，
        # 换个写法这条过渡引用永远不会被对账清掉。
        gateway = FakeGateway(discovery=installable_discovery())
        await run_update(gateway, script_id="script-7")

        reference = gateway.args_of("upgrade_project")[0]["projectReference"]
        self.assertTrue(reference.startswith("maafw-upgrade:script-7:"))

    async def test_temporary_package_is_released_even_when_import_fails(self) -> None:
        gateway = FakeGateway(
            discovery=installable_discovery(),
            upgrade_error=RuntimeError("Store 拒绝导入"),
        )
        with self.assertRaises(RuntimeError):
            await run_update(gateway)

        self.assertIn("release_remote_package", gateway.call_names)

    async def test_release_failure_does_not_mask_the_real_failure(self) -> None:
        gateway = FakeGateway(
            discovery=installable_discovery(),
            upgrade_error=RuntimeError("Store 拒绝导入"),
            release_error=OSError("文件占用"),
        )
        with self.assertRaises(RuntimeError) as caught:
            await run_update(gateway)

        self.assertIn("Store 拒绝导入", str(caught.exception))

    async def test_release_failure_alone_is_only_logged(self) -> None:
        # 临时包没删掉不该让一次成功的更新报成失败。
        logs: list[str] = []
        gateway = FakeGateway(
            discovery=installable_discovery(),
            release_error=OSError("文件占用"),
        )
        outcome = await run_update(gateway, send_log=logs.append)

        self.assertTrue(outcome.updated)
        self.assertTrue(any("未能释放" in line for line in logs))

    async def test_import_without_a_version_refuses_to_switch(self) -> None:
        gateway = FakeGateway(
            discovery={
                "candidate": {
                    "source": "github_release",
                    "version": "",
                    "download_url": "https://example.invalid/pkg.zip",
                }
            },
            upgraded={},
        )
        with self.assertRaises(ManagedUpdateError):
            await run_update(gateway)

        self.assertNotIn("switch_version", gateway.call_names)

    async def test_requires_a_bound_project(self) -> None:
        gateway = FakeGateway()
        with self.assertRaises(ManagedUpdateError):
            await run_update(gateway, project_id="  ")

    async def test_payload_without_a_path_is_rejected_before_any_network_call(
        self,
    ) -> None:
        gateway = FakeGateway(project={"projectId": "M9A", "version": "v4.6.0"})
        with self.assertRaises(ManagedUpdateError):
            await run_update(gateway)

        self.assertNotIn("discover_remote_update", gateway.call_names)


class CheckOnlyTest(unittest.IsolatedAsyncioTestCase):
    """只查版本不能扣 Mirror 酱额度，也不能顺手把版本换了。"""

    async def test_check_does_not_download_import_or_switch(self) -> None:
        gateway = FakeGateway(discovery=installable_discovery())
        outcome = await run_update(gateway, check_only=True)

        self.assertFalse(outcome.updated)
        self.assertTrue(outcome.update_available)
        self.assertTrue(outcome.installable)
        self.assertEqual(
            gateway.call_names,
            ["resolve_project", "load_interface", "discover_remote_update"],
        )

    async def test_check_asks_the_service_for_version_only(self) -> None:
        # 不传 version_only，带 CDK 换地址会扣一次当日额度，而用户只是点了下检查。
        gateway = FakeGateway(discovery=None)
        await run_update(gateway, check_only=True)

        self.assertIs(
            gateway.kwargs_of("discover_remote_update")["version_only"], True
        )

    async def test_real_update_never_asks_for_version_only(self) -> None:
        gateway = FakeGateway(discovery=installable_discovery())
        await run_update(gateway)

        self.assertIs(
            gateway.kwargs_of("discover_remote_update")["version_only"], False
        )

    async def test_deferred_url_counts_as_installable_when_only_checking(self) -> None:
        # url_deferred 是「确认有新版本、故意还没换地址」，不是「装不了」。
        gateway = FakeGateway(
            discovery={
                "version": "v4.7.0",
                "candidate": {
                    "source": "mirrorchyan",
                    "version": "v4.7.0",
                    "url_deferred": True,
                },
            }
        )
        outcome = await run_update(gateway, check_only=True)

        self.assertTrue(outcome.installable)
        self.assertEqual(outcome.level, "info")

    async def test_deferred_url_is_not_enough_for_a_real_update(self) -> None:
        gateway = FakeGateway(
            discovery={
                "version": "v4.7.0",
                "candidate": {
                    "source": "mirrorchyan",
                    "version": "v4.7.0",
                    "url_deferred": True,
                },
                "unavailable_reason": "尚未换取下载地址",
            }
        )
        outcome = await run_update(gateway)

        self.assertFalse(outcome.updated)
        self.assertFalse(outcome.installable)
        self.assertNotIn("download_remote_package", gateway.call_names)

    async def test_cdk_fields_reach_the_outcome(self) -> None:
        # 更新面板靠这几项告诉用户「CDK 过期了」，丢了就只剩一句失败。
        gateway = FakeGateway(
            discovery={
                "version": "v4.7.0",
                "candidate": {"source": "mirrorchyan", "version": "v4.7.0"},
                "cdk_status": "expired",
                "cdk_message": "CDK 已过期",
                "cdk_expired_time": 1234567890,
                "package_source": "mirrorchyan",
            }
        )
        outcome = await run_update(gateway, check_only=True)
        payload = outcome.as_dict()

        self.assertEqual(payload["cdkStatus"], "expired")
        self.assertEqual(payload["cdkMessage"], "CDK 已过期")
        self.assertEqual(payload["cdkExpiredTime"], 1234567890)
        self.assertEqual(payload["source"], "mirrorchyan")


if __name__ == "__main__":
    unittest.main()
