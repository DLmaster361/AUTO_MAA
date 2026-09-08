#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
#   Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

"""托管形态的项目更新编排。

自选目录形态是「就地更新一棵树」，托管形态是「下一个整包，作为新的不可变版本
导入 Store，再切过去」。发现与下载两步共用核心更新包，落地方式完全不同，所以
不能复用 ``update_maafw_project_if_needed``——它会把 checkout 当成用户目录原地
改写，而 checkout 是 Store 的产物。

三处托管形态特有、写错了不会报错只会出坏结果的地方：

- **必须要整包**。Store 导入的是一整棵树，差量包解开只是一堆补丁文件，导进去
  就是一个跑不起来的版本。所以 ``prefer_full_package`` 恒为真。
- **外壳提示要从 manifest 取**。``detect_maafw_project_shell_hint`` 靠根目录的
  ``MFW.exe`` / ``maafw/`` 之类标志判断外壳，而托管载荷正好把这些全脱掉了；
  不回填提示，M9A 这种同时发 ``-MXU.zip`` 与 ``-MFAA.zip`` 的项目会选错资产。
- **导入后必须切版本**。``upgrade_project`` 固定以 inactive 导入，不切的话下一次
  准备环境仍然解析到旧版本，表现为「更新成功但没生效」。

不做两阶段的 ``Managed.PendingUpgrade`` 升级：那条路要配套的配置迁移计划引擎，
在未移植的插件宿主里。自选目录形态今天就是直接更新的——新 interface 里没有的
任务由 run_plan 记成 ``skippedTasks``，全没了才报错。托管沿用同一口径，且旧版本
仍留在 Store 里可以随时切回去，比原地更新更容易挽回。
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# 断点续传的缓存根。放在 Store 之外：Store 根下的目录会被它自己的盘点与回收
# 当成项目数据看待，临时下载包不该出现在那张表里。
MANAGED_DOWNLOAD_DIR = Path("data") / "maafw_project_downloads"

#: ``_build_shell_summary`` 记的家族名与 ``detect_maafw_project_shell_hint``
#: 返回的是同一套词，可以直接回填。
_SHELL_FAMILY_PRIORITY = ("MXU", "MFAAvalonia", "MFW", "CFA", "MaaPiCli")


class ManagedUpdateError(RuntimeError):
    """托管更新失败。调用方负责翻译成用户可读的一句话，不外抛到调度层。"""


@dataclass(frozen=True, slots=True)
class ManagedUpdateOutcome:
    """一次托管检查或更新的结果。``level`` 决定要不要弹通知。

    字段与 ``MaaFWProjectUpdateData`` 一一对应：托管与自选目录两种形态共用同一
    个更新面板，出参形状不一致会让前端要分两套解析。
    """

    updated: bool
    current_version: str
    latest_version: str | None = None
    reason: str = ""
    level: str = "info"
    checked: bool = True
    update_available: bool = False
    installable: bool = False
    source: str | None = None
    cdk_status: str | None = None
    cdk_message: str | None = None
    cdk_expired_time: int | None = None
    skipped_reason: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "checked": self.checked,
            "updated": self.updated,
            "updateAvailable": self.update_available,
            "installable": self.installable,
            "currentVersion": self.current_version or None,
            "latestVersion": self.latest_version,
            "source": self.source,
            "versionName": self.latest_version,
            "cdkStatus": self.cdk_status,
            "cdkMessage": self.cdk_message,
            "cdkExpiredTime": self.cdk_expired_time,
            "skippedReason": self.skipped_reason,
        }


def managed_download_root(base: str | Path | None = None) -> Path:
    """下载缓存根。相对 ``base``（默认当前工作目录，即 MAS 的数据根）。"""

    root = Path(base) if base is not None else Path.cwd()
    return (root / MANAGED_DOWNLOAD_DIR).resolve()


def managed_shell_hint(manifest: Mapping[str, Any] | None) -> str:
    """从 manifest 的脱壳记录还原外壳提示；认不出来就返回空串。

    多个家族同时命中时按 ``_SHELL_FAMILY_PRIORITY`` 取一个：真实项目里这种
    情况来自「MXU 包内还留着 MaaPiCli」这类嵌套，主外壳才是选资产的依据。
    """

    if not isinstance(manifest, Mapping):
        return ""
    shells = manifest.get("shells")
    if not isinstance(shells, Mapping):
        return ""
    families = shells.get("families")
    if not isinstance(families, (list, tuple)):
        return ""
    present = {str(item).strip() for item in families if str(item).strip()}
    for family in _SHELL_FAMILY_PRIORITY:
        if family in present:
            return family
    return ""


def build_managed_source_config(
    *,
    package_source: str,
    mirror_cdk: str,
    channel: str,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """把脚本级更新凭据翻译成核心更新包要的 ``source_config``。"""

    source_config: dict[str, Any] = {
        "package_source": package_source,
        "mirror_cdk": mirror_cdk,
        "channel": channel,
    }
    shell_hint = managed_shell_hint(manifest)
    if shell_hint:
        source_config["project_shell_hint"] = shell_hint
    return source_config


def _text(value: Any) -> str:
    return str(value or "").strip()


def _project_payload_path(project: Mapping[str, Any]) -> str:
    for key in ("dataPath", "projectPath", "path"):
        value = _text(project.get(key))
        if value:
            return value
    raise ManagedUpdateError("项目存储服务返回值缺少 dataPath/projectPath/path")


def _discovery_blocked_reason(discovery: Mapping[str, Any]) -> str:
    """发现到了新版本却装不了时，把服务给的理由拼成一句话。"""

    for key in ("unavailable_reason", "message", "skipped_reason"):
        reason = _text(discovery.get(key))
        if reason:
            return reason
    cdk_message = _text(discovery.get("cdk_message"))
    if cdk_message:
        return cdk_message
    return "远程服务未说明原因"


def _discovery_extras(discovery: Mapping[str, Any]) -> dict[str, Any]:
    """把发现结果里的 CDK 与来源字段抄进 outcome，缺字段一律 None。"""

    expired = discovery.get("cdk_expired_time")
    return {
        "source": _text(discovery.get("package_source")) or None,
        "cdk_status": _text(discovery.get("cdk_status")) or None,
        "cdk_message": _text(discovery.get("cdk_message")) or None,
        "cdk_expired_time": expired if isinstance(expired, int) else None,
        "skipped_reason": _text(discovery.get("skipped_reason")) or None,
    }


async def update_managed_project(
    gateway: Any,
    *,
    script_id: str,
    project_id: str,
    current_version: str,
    source_config: Mapping[str, Any],
    download_root: str | Path,
    proxy: Any = None,
    check_only: bool = False,
    send_log: Callable[[str], None] | None = None,
) -> ManagedUpdateOutcome:
    """发现 → 下载 → 导入为新版本 → 切换。临时包一定释放。

    ``check_only`` 只问「有没有新版本」，**不去换下载地址**：带 CDK 换地址会扣
    一次 Mirror 酱的当日额度，而用户可能只是随手点了下检查更新。自选目录形态的
    检查按钮就是这个口径，两边必须一致。

    只在真的失败时抛 :class:`ManagedUpdateError`；「已是最新」「有新版本但装
    不了」都是正常返回，由调用方决定怎么说。
    """

    log = send_log or (lambda _: None)
    normalized_script_id = _text(script_id)
    normalized_project_id = _text(project_id)
    if not normalized_script_id:
        raise ManagedUpdateError("托管更新需要 scriptId")
    if not normalized_project_id:
        raise ManagedUpdateError("托管更新需要 projectId")

    project = await gateway.resolve_project(
        normalized_project_id,
        current_version or None,
    )
    resolved_version = _text(project.get("version")) or current_version
    # 从不可变载荷读 interface，而不是从 checkout：更新跑在准备环境之前，
    # 这时脚本还没有 checkout。
    interface = await gateway.load_interface(_project_payload_path(project))

    discovery = await gateway.discover_remote_update(
        interface,
        current_version=resolved_version,
        source_config=dict(source_config),
        prefer_full_package=True,
        version_only=check_only,
        proxy=proxy,
    )
    if not discovery:
        return ManagedUpdateOutcome(
            updated=False,
            current_version=resolved_version,
            reason=f"已是最新版本：{resolved_version or '未知'}",
        )

    extras = _discovery_extras(discovery)
    latest_version = _text(discovery.get("version")) or None
    candidate = discovery.get("candidate")
    # ``url_deferred`` 是只查版本时的正常状态：确认了有新版本、来源也可用，
    # 只是故意还没去换下载地址。它算「能装」，不算「装不了」。
    deferred = isinstance(candidate, Mapping) and bool(candidate.get("url_deferred"))
    has_url = isinstance(candidate, Mapping) and bool(
        _text(candidate.get("download_url"))
    )

    if check_only:
        installable = deferred or has_url
        return ManagedUpdateOutcome(
            updated=False,
            current_version=resolved_version,
            latest_version=latest_version,
            update_available=True,
            installable=installable,
            reason=(
                f"发现新版本 {latest_version or '未知'}"
                if installable
                else (
                    f"发现新版本 {latest_version or '未知'}，但无法下载："
                    f"{_discovery_blocked_reason(discovery)}"
                )
            ),
            level="info" if installable else "warning",
            **extras,
        )

    if not has_url:
        return ManagedUpdateOutcome(
            updated=False,
            current_version=resolved_version,
            latest_version=latest_version,
            update_available=True,
            installable=False,
            reason=(
                f"发现新版本 {latest_version or '未知'}，但无法下载："
                f"{_discovery_blocked_reason(discovery)}"
            ),
            level="warning",
            **extras,
        )

    log(f"发现新版本 {latest_version or '未知'}，开始下载整包")
    package = await gateway.download_remote_package(
        download_root,
        candidate,
        proxy=proxy,
    )
    try:
        upgraded = await gateway.upgrade_project(
            {
                "sourcePath": _text(package.get("path")),
                "projectId": normalized_project_id,
                "currentVersion": resolved_version,
                "version": latest_version,
                # 与 reconcile_project_references 认的前缀一致。切换成功后
                # prepare 会补上 maafw-script:，这条过渡引用由对账清掉。
                "projectReference": (
                    f"maafw-upgrade:{normalized_script_id}:"
                    f"{latest_version or 'unknown'}"
                ),
            }
        )
        imported_version = _text(upgraded.get("latestVersion")) or latest_version
        if not imported_version:
            raise ManagedUpdateError("导入成功但未返回版本号，无法切换")
        # upgrade_project 固定 inactive 导入，不切就等于没更新。
        await gateway.switch_version(
            {"projectId": normalized_project_id, "version": imported_version}
        )
    finally:
        # 释放失败只是留下一个临时包，不该盖掉上面真正的失败原因。
        try:
            released = await gateway.release_remote_package(download_root, package)
        except Exception as exc:  # noqa: BLE001
            log(f"临时下载包未能释放，下次更新会复用：{exc}")
        else:
            if released.get("retained"):
                log("临时下载包已保留供断点续传复用")

    log(f"已切换到新版本 {imported_version}")
    return ManagedUpdateOutcome(
        updated=True,
        current_version=resolved_version,
        latest_version=imported_version,
        update_available=True,
        installable=True,
        reason=f"已更新到 {imported_version}（原 {resolved_version or '未知'}）",
        **extras,
    )


__all__ = [
    "MANAGED_DOWNLOAD_DIR",
    "ManagedUpdateError",
    "ManagedUpdateOutcome",
    "build_managed_source_config",
    "managed_download_root",
    "managed_shell_hint",
    "update_managed_project",
]
