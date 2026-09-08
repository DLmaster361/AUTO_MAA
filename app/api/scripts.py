#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2024-2025 DLmaster361
#   Copyright © 2025 MoeSnowyFox
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

#   Contact: DLmaster_361@163.com


import asyncio
import shutil
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse

from app.core import Config
from app.models.config import BetterGIConfig as RuntimeBetterGIConfig
from app.models.config import HSRConfig as RuntimeHSRConfig
from app.models.config import MaaFWConfig as RuntimeMaaFWConfig
from app.models.config import MaaFWManagedConfig as RuntimeMaaFWManagedConfig
from app.models.config import OkNteConfig as RuntimeOkNteConfig
from app.models.ConfigBase import FolderValidator
from app.models.schema import *
from app.task.MaaFW.tools.core.automas_maafw_interface.loader import (
    MaaFWInterfaceLoadError,
    load_interface_model_cached,
)
from app.task.MaaFW.tools.core.automas_maafw_interface.preview import (
    build_interface_preview_data,
)
from app.task.MaaFW.tools.core.automas_maafw_project_update import (
    MaaFWProjectUpdateError,
    discover_maafw_project_update,
    update_maafw_project_if_needed,
)
from app.task.MaaFW.tools.core.automas_maafw_project_update.updater import (
    detect_maafw_project_shell_hint,
    _public_package_source,
)
from app.task.MaaFW.tools.embedded.update_credentials import (
    describe_cdk,
    resolve_update_credentials,
)
from app.utils import get_logger
from app.utils.security import sanitize_log_message

router = APIRouter(prefix="/api/scripts", tags=["脚本管理"])


def _hsr_script_config(script_id: str):
    """Resolve an HSR script and reject cross-type IDs before domain access."""

    script_config = Config.ScriptConfig[uuid.UUID(script_id)]
    if not isinstance(script_config, RuntimeHSRConfig):
        raise TypeError("脚本配置类型错误, 不是 HSR 类型")
    return script_config


def _bettergi_script_config(script_id: str):
    """Resolve a BetterGI script and reject cross-type IDs before domain access."""

    script_config = Config.ScriptConfig[uuid.UUID(script_id)]
    if not isinstance(script_config, RuntimeBetterGIConfig):
        raise TypeError("脚本配置类型错误, 不是 BetterGI 类型")
    return script_config


def _hsr_user_config(script_config: RuntimeHSRConfig, user_id: str):
    user_config = script_config.UserData[uuid.UUID(user_id)]
    return user_config


def _oknte_script_config(script_id: str) -> tuple[uuid.UUID, RuntimeOkNteConfig]:
    script_uid = uuid.UUID(script_id)
    script_config = Config.ScriptConfig[script_uid]
    if not isinstance(script_config, RuntimeOkNteConfig):
        raise ValueError("脚本配置类型错误, 不是 OK-NTE 类型")
    return script_uid, script_config


def _oknte_legacy_mas_config_dir(script_id: str) -> Path:
    script_uid, _ = _oknte_script_config(script_id)
    return Path.cwd() / "data" / str(script_uid) / "Default" / "ConfigFile"


def _oknte_mas_config_dir(script_id: str, user_id: str) -> Path:
    script_uid, _ = _oknte_script_config(script_id)
    user_uid = uuid.UUID(user_id)
    return Path.cwd() / "data" / str(script_uid) / str(user_uid) / "ConfigFile"


def _oknte_config_file_path(config_dir: Path, filename: str) -> Path:
    file_path = Path(filename)
    if file_path.name != filename or file_path.is_absolute() or ".." in file_path.parts:
        raise ValueError("配置文件名非法")
    return config_dir / filename


def _maafw_script_config(script_id: str) -> RuntimeMaaFWConfig:
    """Resolve a MaaFW script and reject cross-type IDs before domain access."""

    script_config = Config.ScriptConfig[uuid.UUID(script_id)]
    if not isinstance(script_config, RuntimeMaaFWConfig):
        raise TypeError("脚本配置类型错误, 不是 MFW 类型")
    return script_config


# 这两种 CDK 状态不需要额外提示：ok 是正常，absent 在选 GitHub 源时本就无关。
_MAAFW_CDK_QUIET_STATUSES = frozenset({"ok", "absent"})
_maafw_update_logger = get_logger("MaaFW 项目更新")


def _maafw_update_send_log(line: str) -> None:
    """更新实现的逐行日志回调；写日志前先打码，避免 CDK 等敏感值落盘。"""

    _maafw_update_logger.info(sanitize_log_message(str(line)))


def _maafw_update_extra_fields(result: Any) -> dict[str, Any]:
    """按核心包约定的属性名读取 CDK / 版本附加字段，缺字段一律 None。

    核心包返回对象（discovery 或 result）带 ``version_name`` / ``source`` /
    ``cdk_status`` / ``cdk_message`` / ``cdk_expired_time`` / ``skipped_reason``；
    此处用 ``getattr(..., None)`` 读取，核心包尚未补齐时也能返回。
    """

    def _text(name: str) -> str | None:
        value = getattr(result, name, None)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    expired_raw = getattr(result, "cdk_expired_time", None)
    expired_time: int | None
    if isinstance(expired_raw, bool) or expired_raw is None:
        expired_time = None
    else:
        try:
            expired_time = int(expired_raw)
        except (TypeError, ValueError):
            expired_time = None

    return {
        "versionName": _text("version_name"),
        "cdkStatus": _text("cdk_status"),
        "cdkMessage": _text("cdk_message"),
        "cdkExpiredTime": expired_time,
        "skippedReason": _text("skipped_reason"),
    }


def _maafw_update_message_with_cdk(message: str, extra: dict[str, Any]) -> str:
    """CDK 状态异常时把提示原文附到摘要里。

    仍按成功返回（HTTP 200）：CDK 有问题只是这次装不了，脚本本身照常能跑，
    用户看到原因后可以去续期或改用 GitHub 源。
    """

    status = extra.get("cdkStatus")
    cdk_message = extra.get("cdkMessage")
    if status and status not in _MAAFW_CDK_QUIET_STATUSES and cdk_message:
        return f"{message}（{cdk_message}）"
    return message


def _config_text(config: Any, group: str, name: str) -> str:
    """读取一个可能不存在的配置项并归一为去空白字符串。"""

    try:
        return str(config.get(group, name) or "").strip()
    except AttributeError:
        return ""


def _maafw_update_source_config(script_config: RuntimeMaaFWConfig) -> dict[str, str]:
    """组装 MaaFW 项目更新实现所需的 source_config。

    只包含用户可配置的三项：``package_source``（脚本级 ``Update.Source``，
    Mirror 酱 / GitHub）、``mirror_cdk``、``channel``。三项**都只看脚本级、
    不做全局兜底**，与 ``tools/embedded/update_credentials.py`` 用的是同一个
    解析函数，保证手动更新与运行时自动更新的行为一致。

    仓库、tag、资产文件名等 GitHub 参数不再由用户填写，由核心包从
    ``interface.json`` 与目录名自行推断。

    额外注入 ``project_shell_hint``：GitHub 发行版常按 UI 外壳分包
    （如 M9A 同版本同时发 ``*-MFAA.zip`` 与 ``*-MXU.zip``），选包实现
    在项目名/平台收窄后需要外壳家族才能消歧。本 API 直连
    ``discover_maafw_project_update``，而该函数**自身不做兜底识别**
    （兜底在 ``update_maafw_project_if_needed`` 里），故必须在此补上。
    """

    # 三项都只看脚本级，不做全局兜底（与 embedded 侧的 resolve_update_credentials
    # 一致）：全局那两项服务的是 MAS 自身的更新，语义不同。
    credentials = resolve_update_credentials(script_config)
    config = {
        "mirror_cdk": credentials.cdk,
        "channel": credentials.channel,
        "package_source": credentials.package_source,
    }
    project_path = _config_text(script_config, "Info", "Path")
    if project_path:
        shell_hint = detect_maafw_project_shell_hint(Path(project_path))
        if shell_hint:
            config["project_shell_hint"] = shell_hint
    return config


SCRIPT_BOOK = {
    "MaaConfig": MaaConfig,
    "SrcConfig": SrcConfig,
    "MaaEndConfig": MaaEndConfig,
    "M9AConfig": M9AConfig,
    "MaaFWConfig": MaaFWConfig,
    "MaaFWManagedConfig": MaaFWConfig,
    "GeneralConfig": GeneralConfig,
    "OkwwConfig": OkwwConfig,
    "OkNteConfig": OkNteConfig,
    "HSRConfig": HSRConfig,
    "BetterGIConfig": BetterGIConfig,
    "ZzzOdConfig": ZzzOdConfig,
}
USER_BOOK = {
    "MaaConfig": MaaUserConfig,
    "SrcConfig": SrcUserConfig,
    "MaaEndConfig": MaaEndUserConfig,
    "M9AConfig": M9AUserConfig,
    "MaaFWConfig": MaaFWUserConfig,
    "MaaFWManagedConfig": MaaFWUserConfig,
    "GeneralConfig": GeneralUserConfig,
    "OkwwConfig": OkwwUserConfig,
    "OkNteConfig": OkNteUserConfig,
    "HSRConfig": HSRUserConfig,
    "BetterGIConfig": BetterGIUserConfig,
    "ZzzOdConfig": ZzzOdUserConfig,
}


@router.post(
    "/add",
    tags=["Add"],
    summary="添加脚本",
    response_model=ScriptCreateOut,
    status_code=200,
)
async def add_script(script: ScriptCreateIn = Body(...)) -> ScriptCreateOut:

    try:
        uid, config = await Config.add_script(script.type, script.scriptId)
        data = SCRIPT_BOOK[type(config).__name__](**(await config.toDict()))
    except Exception as e:
        return ScriptCreateOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            scriptId="",
            data=GeneralConfig(**{}),
        )
    return ScriptCreateOut(scriptId=str(uid), data=data)


@router.post(
    "/get",
    tags=["Get"],
    summary="查询脚本配置信息",
    response_model=ScriptGetOut,
    status_code=200,
)
async def get_script(script: ScriptGetIn = Body(...)) -> ScriptGetOut:

    try:
        index, data = await Config.get_script(script.scriptId)
        index = [ScriptIndexItem(**_) for _ in index]
        data = {
            uid: SCRIPT_BOOK[next((_.type for _ in index if _.uid == uid), "General")](
                **cfg
            )
            for uid, cfg in data.items()
        }
    except Exception as e:
        return ScriptGetOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            index=[],
            data={},
        )
    return ScriptGetOut(index=index, data=data)


@router.post(
    "/update",
    tags=["Update"],
    summary="更新脚本配置信息",
    response_model=OutBase,
    status_code=200,
)
async def update_script(script: ScriptUpdateIn = Body(...)) -> OutBase:

    try:
        await Config.update_script(
            script.scriptId, script.data.model_dump(exclude_unset=True)
        )
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/delete",
    tags=["Delete"],
    summary="删除脚本",
    response_model=OutBase,
    status_code=200,
)
async def delete_script(script: ScriptDeleteIn = Body(...)) -> OutBase:

    try:
        await Config.del_script(script.scriptId)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/order",
    tags=["Update"],
    summary="重新排序脚本",
    response_model=OutBase,
    status_code=200,
)
async def reorder_script(script: ScriptReorderIn = Body(...)) -> OutBase:

    try:
        await Config.reorder_script(script.indexList)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/import/file",
    tags=["Update"],
    summary="从文件加载脚本配置",
    response_model=OutBase,
    status_code=200,
)
async def import_script_from_file(script: ScriptFileIn = Body(...)) -> OutBase:

    try:
        await Config.import_script_from_file(script.scriptId, script.jsonFile)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/export/file",
    tags=["Action"],
    summary="导出脚本配置到文件",
    response_model=OutBase,
    status_code=200,
)
async def export_script_to_file(script: ScriptFileIn = Body(...)) -> OutBase:

    try:
        await Config.export_script_to_file(script.scriptId, script.jsonFile)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/import/web",
    tags=["Update"],
    summary="从网络加载脚本配置",
    response_model=OutBase,
    status_code=200,
)
async def import_script_from_web(script: ScriptUrlIn = Body(...)) -> OutBase:

    try:
        await Config.import_script_from_web(script.scriptId, script.url)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/Upload/web",
    tags=["Action"],
    summary="上传脚本配置到网络",
    response_model=OutBase,
    status_code=200,
)
async def upload_script_to_web(script: ScriptUploadIn = Body(...)) -> OutBase:

    try:
        await Config.upload_script_to_web(
            script.scriptId, script.config_name, script.author, script.description
        )
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/config/import",
    tags=["Action"],
    summary="从脚本目录导入配置文件",
    response_model=OutBase,
    status_code=200,
)
async def import_script_config_file(
    config: ScriptConfigImportIn = Body(...),
) -> OutBase:

    try:
        await Config.import_script_config_file(config.scriptId, config.userId)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase(message="脚本配置文件已导入")


@router.post(
    "/maaend/options",
    tags=["Get"],
    summary="获取 MaaEnd 动态选项",
    response_model=MaaEndOptionsOut,
    status_code=200,
)
async def get_maaend_options(options: ScriptDeleteIn = Body(...)) -> MaaEndOptionsOut:
    try:
        data = await Config.get_maaend_options(options.scriptId)
        return MaaEndOptionsOut(
            controllers=[ComboBoxItem(**item) for item in data["controllers"]],
            controllerTypes=data["controllerTypes"],
            essenceLocations=[
                ComboBoxItem(**item) for item in data["essenceLocations"]
            ],
        )
    except Exception as e:
        return MaaEndOptionsOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            controllers=[],
            controllerTypes={},
            essenceLocations=[],
        )


@router.post(
    "/user/get",
    tags=["Get"],
    summary="查询用户",
    response_model=UserGetOut,
    status_code=200,
)
async def get_user(user: UserGetIn = Body(...)) -> UserGetOut:

    try:
        index, data = await Config.get_user(user.scriptId, user.userId)
        index = [UserIndexItem(**_) for _ in index]
        data = {
            uid: USER_BOOK[
                type(Config.ScriptConfig[uuid.UUID(user.scriptId)]).__name__
            ](**cfg)
            for uid, cfg in data.items()
        }
    except Exception as e:
        return UserGetOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            index=[],
            data={},
        )
    return UserGetOut(index=index, data=data)


@router.post(
    "/user/add",
    tags=["Add"],
    summary="添加用户",
    response_model=UserCreateOut,
    status_code=200,
)
async def add_user(user: UserInBase = Body(...)) -> UserCreateOut:

    try:
        uid, config = await Config.add_user(user.scriptId)
        data = USER_BOOK[type(Config.ScriptConfig[uuid.UUID(user.scriptId)]).__name__](
            **(await config.toDict())
        )
    except FileNotFoundError as e:
        return UserCreateOut(
            code=409,
            status="error",
            message=str(e),
            userId="",
            data=GeneralUserConfig(**{}),
        )
    except Exception as e:
        return UserCreateOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            userId="",
            data=GeneralUserConfig(**{}),
        )
    return UserCreateOut(userId=str(uid), data=data)


@router.post(
    "/user/update",
    tags=["Update"],
    summary="更新用户配置信息",
    response_model=OutBase,
    status_code=200,
)
async def update_user(user: UserUpdateIn = Body(...)) -> OutBase:

    try:
        await Config.update_user(
            user.scriptId, user.userId, user.data.model_dump(exclude_unset=True)
        )
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/user/delete",
    tags=["Delete"],
    summary="删除用户",
    response_model=OutBase,
    status_code=200,
)
async def delete_user(user: UserDeleteIn = Body(...)) -> OutBase:

    try:
        await Config.del_user(user.scriptId, user.userId)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/user/order",
    tags=["Update"],
    summary="重新排序用户",
    response_model=OutBase,
    status_code=200,
)
async def reorder_user(user: UserReorderIn = Body(...)) -> OutBase:

    try:
        await Config.reorder_user(user.scriptId, user.indexList)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/user/infrastructure",
    tags=["Update"],
    summary="导入基建配置文件",
    response_model=OutBase,
    status_code=200,
)
async def import_infrastructure(user: UserSetIn = Body(...)) -> OutBase:

    try:
        await Config.set_infrastructure(user.scriptId, user.userId, user.jsonFile)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/user/combox/infrastructure",
    tags=["Get"],
    summary="用户自定义基建排班可选项",
    response_model=ComboBoxOut,
    status_code=200,
)
async def get_user_combox_infrastructure(user: UserDeleteIn = Body(...)) -> ComboBoxOut:

    try:
        raw_data = await Config.get_user_combox_infrastructure(
            user.scriptId, user.userId
        )
        data = [ComboBoxItem(**item) for item in raw_data] if raw_data else []
    except Exception as e:
        return ComboBoxOut(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}", data=[]
        )
    return ComboBoxOut(data=data)


@router.post(
    "/maa/depot/items",
    tags=["Get"],
    summary="MAA 库存保持物品可选项",
    response_model=ComboBoxOut,
    status_code=200,
)
async def get_maa_depot_items(script: ScriptDeleteIn = Body(...)) -> ComboBoxOut:

    try:
        raw_data = await Config.get_maa_depot_items(script.scriptId)
        data = [ComboBoxItem(**item) for item in raw_data]
    except Exception as e:
        return ComboBoxOut(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}", data=[]
        )
    return ComboBoxOut(data=data)


@router.post(
    "/webhook/get",
    tags=["Get"],
    summary="查询 webhook 配置",
    response_model=WebhookGetOut,
    status_code=200,
)
async def get_webhook(webhook: WebhookGetIn = Body(...)) -> WebhookGetOut:

    try:
        index, data = await Config.get_webhook(
            webhook.scriptId, webhook.userId, webhook.webhookId
        )
        index = [WebhookIndexItem(**_) for _ in index]
        data = {uid: Webhook(**cfg) for uid, cfg in data.items()}
    except Exception as e:
        return WebhookGetOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            index=[],
            data={},
        )
    return WebhookGetOut(index=index, data=data)


@router.post(
    "/webhook/add",
    tags=["Add"],
    summary="添加webhook项",
    response_model=WebhookCreateOut,
    status_code=200,
)
async def add_webhook(webhook: WebhookInBase = Body(...)) -> WebhookCreateOut:

    try:
        uid, config = await Config.add_webhook(webhook.scriptId, webhook.userId)
        data = Webhook(**(await config.toDict()))
    except Exception as e:
        return WebhookCreateOut(
            code=500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            webhookId="",
            data=Webhook(**{}),
        )
    return WebhookCreateOut(webhookId=str(uid), data=data)


@router.post(
    "/webhook/update",
    tags=["Update"],
    summary="更新webhook项",
    response_model=OutBase,
    status_code=200,
)
async def update_webhook(webhook: WebhookUpdateIn = Body(...)) -> OutBase:

    try:
        await Config.update_webhook(
            webhook.scriptId,
            webhook.userId,
            webhook.webhookId,
            webhook.data.model_dump(exclude_unset=True),
        )
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/webhook/delete",
    tags=["Delete"],
    summary="删除webhook项",
    response_model=OutBase,
    status_code=200,
)
async def delete_webhook(webhook: WebhookDeleteIn = Body(...)) -> OutBase:

    try:
        await Config.del_webhook(webhook.scriptId, webhook.userId, webhook.webhookId)
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


@router.post(
    "/webhook/order",
    tags=["Update"],
    summary="重新排序webhook项",
    response_model=OutBase,
    status_code=200,
)
async def reorder_webhook(webhook: WebhookReorderIn = Body(...)) -> OutBase:

    try:
        await Config.reorder_webhook(
            webhook.scriptId, webhook.userId, webhook.indexList
        )
    except Exception as e:
        return OutBase(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    return OutBase()


def _managed_store():
    """Project Store 服务。

    与 `MaaFWEmbeddedManager._resolve_managed_gateway` 同样的处境：插件形态下由
    `adapter.py` 查服务契约注入，树内没有注册表，直接实例化。Store 根按 cwd 解析，
    多次实例化指向同一根是允许的（内部有身份校验）。
    """

    from app.task.MaaFW.tools.core.automas_maafw_project_store import (
        MaaFWProjectStoreService,
    )

    return MaaFWProjectStoreService()


def _managed_projection(manifest: dict) -> MaaFWManagedProjection:
    """把 Store manifest 里现成的脱壳统计整理成界面用的形状，不另算。"""

    projection = manifest.get("projection") or {}
    shells = manifest.get("shells") or {}
    reasons = projection.get("excludedReasons") or {}
    return MaaFWManagedProjection(
        sourceSizeBytes=int(projection.get("sourceSizeBytes") or 0),
        payloadSizeBytes=int(projection.get("payloadSizeBytes") or 0),
        savedBytes=int(projection.get("savedBytes") or 0),
        savedPercent=float(projection.get("savedPercent") or 0.0),
        excludedCount=len(projection.get("excluded") or []),
        shellFamilies=list(shells.get("families") or []),
        excludedReasons={str(k): str(v) for k, v in list(reasons.items())[:128]},
    )


def _managed_gateway():
    """带 project_update 的托管服务网关；与运行时那条用的是同一个构造。"""

    from app.task.MaaFW.embedded_manager import MaaFWEmbeddedManager

    return MaaFWEmbeddedManager._resolve_managed_gateway()


async def _run_managed_project_update(
    payload: "MaaFWProjectUpdateIn",
    script_config: RuntimeMaaFWManagedConfig,
) -> "MaaFWProjectUpdateOut":
    """托管脚本的检查/更新。

    托管脚本的 ``Info.Path`` 指向 Store 产出的 checkout，**绝不能走原地更新**：
    那会把不可变版本的工作副本就地改写，Store 记的指纹与盘上内容当场分叉。
    这里改成「下整包 → 导入为新版本 → 切过去」，旧版本仍留在 Store 里可回退。
    """

    from app.task.MaaFW.tools.embedded.managed import managed_project_identity
    from app.task.MaaFW.tools.embedded.managed_update import (
        build_managed_source_config,
        managed_download_root,
        update_managed_project,
    )

    manifest = script_config.get("Managed", "ProjectManifest")
    if not isinstance(manifest, dict):
        manifest = {}
    project_id, current_version = managed_project_identity(
        {
            "ProjectId": script_config.get("Managed", "ProjectId"),
            "Version": script_config.get("Managed", "Version"),
            "ProjectManifest": manifest,
        }
    )
    if not project_id:
        return MaaFWProjectUpdateOut(
            code=400,
            status="error",
            message="该托管脚本尚未导入项目，请先在项目配置里导入",
        )

    credentials = resolve_update_credentials(script_config)
    _maafw_update_logger.info(
        f"托管项目更新({payload.action}): script={payload.scriptId} "
        f"project={project_id} channel={credentials.channel} "
        f"cdk={describe_cdk(credentials)}"
    )

    try:
        outcome = await update_managed_project(
            _managed_gateway(),
            script_id=payload.scriptId,
            project_id=project_id,
            current_version=current_version,
            source_config=build_managed_source_config(
                package_source=credentials.package_source,
                mirror_cdk=credentials.cdk,
                channel=credentials.channel,
                manifest=manifest,
            ),
            download_root=managed_download_root(),
            proxy=Config.proxy,
            check_only=payload.action == "check",
            send_log=_maafw_update_send_log,
        )
    except Exception as exc:
        return MaaFWProjectUpdateOut(
            code=400, status="error", message=f"托管项目更新失败: {exc}"
        )

    if outcome.updated:
        # 版本已经切了，脚本配置里的绑定必须跟着换，否则下次准备环境仍按旧
        # manifest 校验，会以「绑定与 Store 不一致」失败。
        try:
            store = _managed_store()
            resolved = await asyncio.to_thread(
                store.resolve_project, project_id, outcome.latest_version
            )
            await Config.update_script(
                payload.scriptId,
                {
                    "Managed": {
                        "Version": outcome.latest_version,
                        "StoreId": resolved["storeId"],
                        "ProjectManifest": resolved.get("manifest") or {},
                    }
                },
            )
        except Exception as exc:
            return MaaFWProjectUpdateOut(
                code=500,
                status="error",
                message=f"已更新到 {outcome.latest_version} 但更新脚本绑定失败: {exc}",
            )

    return MaaFWProjectUpdateOut(
        message=outcome.reason,
        data=MaaFWProjectUpdateData(**outcome.as_dict()),
    )


@router.post(
    "/maafw/managed/import",
    tags=["MaaFW"],
    summary="导入 MFW 项目到托管 Store",
    response_model=MaaFWManagedImportOut,
    status_code=200,
)
async def import_managed_maafw_project(
    payload: MaaFWManagedImportIn = Body(...),
) -> MaaFWManagedImportOut:
    """把本地目录或 ZIP 发行包导入不可变 Store，并可选地绑定到一个托管脚本。

    绑定不是可有可无的一步：只写 projectId/version 而不带 Store 身份，运行时会被
    「脚本缺少可验证的 Project Store 身份」直接拒掉。
    """

    store = _managed_store()
    try:
        record = await asyncio.to_thread(
            store.import_project,
            payload.sourcePath,
            activate=payload.activate,
        )
    except Exception as exc:
        # 闸门的拒绝理由（依赖不合规、ABI 未知、路径越界等）对用户是首要信息，
        # 原样带出来，不要吞成一句「导入失败」。
        return MaaFWManagedImportOut(
            code=400,
            status="error",
            message=f"导入 MFW 项目失败: {exc}",
            data=None,
        )

    manifest = record.get("manifest") or {}
    bound = False
    if payload.scriptId:
        try:
            await Config.update_script(
                payload.scriptId,
                {
                    "Managed": {
                        "Enabled": True,
                        "ProjectId": record["projectId"],
                        "Version": record["version"],
                        "StoreId": record["storeId"],
                        "ProjectManifest": manifest,
                    }
                },
            )
            bound = True
        except Exception as exc:
            return MaaFWManagedImportOut(
                code=500,
                status="error",
                message=f"项目已入库但绑定脚本失败: {exc}",
                data=None,
            )

    data = MaaFWManagedImportData(
        projectId=record["projectId"],
        version=record["version"],
        storeId=record["storeId"],
        dataPath=str(record.get("dataPath") or ""),
        bound=bound,
        projection=_managed_projection(manifest),
    )
    return MaaFWManagedImportOut(
        message=(
            f"已导入 {data.projectId}@{data.version}，"
            f"脱壳省下 {data.projection.savedPercent:.2f}%"
        ),
        data=data,
    )


@router.post(
    "/maafw/managed/migrate",
    tags=["MaaFW"],
    summary="把自选目录的 MFW 脚本转为托管",
    response_model=MaaFWManagedMigrateOut,
    status_code=200,
)
async def migrate_maafw_script_to_managed(
    payload: MaaFWManagedMigrateIn = Body(...),
) -> MaaFWManagedMigrateOut:
    """导入现有项目目录、原地把脚本换成托管类型，可选地删掉原目录。

    转换是**原地**的：脚本 ID 不变，队列成员、计划表、通知绑定和 ``data/<uid>/``
    下的用户数据全都留着。新建一个托管脚本再删旧的会把这些一并丢掉。

    删原目录是不可撤销的，只在 ``deleteSource`` 为真时做，并且一定排在导入与
    转换都成功之后；删除失败不回滚迁移——项目已经在 Store 里了，把它撤回去反而
    更糟，如实报告让用户自己删。
    """

    try:
        script_config = _maafw_script_config(payload.scriptId)
    except (KeyError, ValueError, TypeError) as exc:
        return MaaFWManagedMigrateOut(
            code=400, status="error", message=f"MFW 脚本无效: {exc}"
        )

    if isinstance(script_config, RuntimeMaaFWManagedConfig):
        return MaaFWManagedMigrateOut(
            code=400, status="error", message="该脚本已经是托管形态，无需迁移"
        )

    source_value = str(script_config.get("Info", "Path") or "").strip()
    if not source_value:
        return MaaFWManagedMigrateOut(
            code=400, status="error", message="该脚本还没有设置 MFW 项目路径"
        )
    source_path = Path(source_value).resolve()
    if not source_path.is_dir():
        return MaaFWManagedMigrateOut(
            code=400,
            status="error",
            message="MFW 项目路径不是有效目录，请先修好 Info.Path 再迁移",
        )

    store = _managed_store()
    try:
        record = await asyncio.to_thread(
            store.import_project, str(source_path), activate=True
        )
    except Exception as exc:
        # 闸门的拒绝理由就是用户要看的东西：迁移不成往往是项目本身不合规。
        return MaaFWManagedMigrateOut(
            code=400, status="error", message=f"导入现有项目失败: {exc}"
        )

    manifest = record.get("manifest") or {}
    try:
        await Config.convert_script(payload.scriptId, "MaaFWManaged")
        await Config.update_script(
            payload.scriptId,
            {
                # 清掉页面上的旧项目路径：迁移后项目不在那儿了，留着会把一个
                # 可能刚被删掉的目录当成项目路径显示。真正的 checkout 由准备
                # 链路在首次运行时写回。
                "Info": {"Path": ""},
                "Managed": {
                    "Enabled": True,
                    "ProjectId": record["projectId"],
                    "Version": record["version"],
                    "StoreId": record["storeId"],
                    "ProjectManifest": manifest,
                }
            },
        )
    except Exception as exc:
        return MaaFWManagedMigrateOut(
            code=500,
            status="error",
            message=f"项目已入库但脚本转换失败: {exc}",
        )

    source_deleted = False
    source_delete_error: str | None = None
    if payload.deleteSource:
        # Info.Path 本来就过了 FolderValidator，这里再验一次是防手改配置：
        # 它拦掉驱动器根、系统目录和 AUTO-MAS 自己的工作目录。
        if not FolderValidator().validate(str(source_path)):
            source_delete_error = "原目录不在允许删除的范围内，请手动确认后自行删除"
        else:
            try:
                await asyncio.to_thread(shutil.rmtree, source_path)
                source_deleted = True
            except Exception as exc:
                source_delete_error = f"{type(exc).__name__}: {exc}"

    data = MaaFWManagedMigrateData(
        projectId=record["projectId"],
        version=record["version"],
        storeId=record["storeId"],
        dataPath=str(record.get("dataPath") or ""),
        sourcePath=str(source_path),
        sourceDeleted=source_deleted,
        sourceDeleteError=source_delete_error,
        projection=_managed_projection(manifest),
    )
    message = (
        f"已转为托管：{data.projectId}@{data.version}，"
        f"脱壳省下 {data.projection.savedPercent:.2f}%"
    )
    if source_delete_error:
        message = f"{message}；原目录未删除：{source_delete_error}"
    elif source_deleted:
        message = f"{message}，原目录已删除"
    return MaaFWManagedMigrateOut(message=message, data=data)


@router.post(
    "/maafw/managed/versions",
    tags=["MaaFW"],
    summary="列出托管项目的版本",
    response_model=MaaFWManagedVersionsOut,
    status_code=200,
)
async def list_managed_maafw_versions(
    payload: MaaFWManagedVersionsIn = Body(...),
) -> MaaFWManagedVersionsOut:
    store = _managed_store()
    try:
        records = await asyncio.to_thread(store.list_versions, payload.projectId)
    except Exception as exc:
        return MaaFWManagedVersionsOut(
            code=400, status="error", message=f"读取版本列表失败: {exc}", data=None
        )

    versions = [
        MaaFWManagedVersionItem(
            version=str(item.get("version") or ""),
            createdAt=(item.get("manifest") or {}).get("createdAt"),
            lastUsedAt=item.get("lastUsedAt"),
            current=bool(item.get("current")),
            pinned=bool(item.get("pinned")),
            references=list(item.get("references") or []),
            sizeBytes=int(((item.get("summary") or {}).get("payloadSizeBytes")) or 0),
        )
        for item in records
    ]
    current = next((v.version for v in versions if v.current), None)
    return MaaFWManagedVersionsOut(
        message=f"共 {len(versions)} 个版本",
        data=MaaFWManagedVersionsData(
            projectId=payload.projectId, current=current, versions=versions
        ),
    )


@router.post(
    "/maafw/managed/switch",
    tags=["MaaFW"],
    summary="切换托管项目的当前版本",
    response_model=OutBase,
    status_code=200,
)
async def switch_managed_maafw_version(
    payload: MaaFWManagedSwitchIn = Body(...),
) -> OutBase:
    store = _managed_store()
    try:
        await asyncio.to_thread(
            store.switch_version, payload.projectId, payload.version
        )
    except Exception as exc:
        return OutBase(code=400, status="error", message=f"切换版本失败: {exc}")

    if payload.scriptId:
        try:
            resolved = await asyncio.to_thread(
                store.resolve_project, payload.projectId, payload.version
            )
            await Config.update_script(
                payload.scriptId,
                {
                    "Managed": {
                        "Version": payload.version,
                        "StoreId": resolved["storeId"],
                        "ProjectManifest": resolved.get("manifest") or {},
                    }
                },
            )
        except Exception as exc:
            return OutBase(
                code=500,
                status="error",
                message=f"版本已切换但更新脚本绑定失败: {exc}",
            )

    return OutBase(message=f"已切换到 {payload.projectId}@{payload.version}")


@router.post(
    "/maafw/managed/version/delete",
    tags=["MaaFW"],
    summary="删除托管项目的一个版本",
    response_model=OutBase,
    status_code=200,
)
async def delete_managed_maafw_version(
    payload: MaaFWManagedVersionDeleteIn = Body(...),
) -> OutBase:
    """删除受 current / pinned / references / lease 阻断——阻断理由原样返回。"""

    store = _managed_store()
    try:
        await asyncio.to_thread(
            store.delete_version, payload.projectId, payload.version
        )
    except Exception as exc:
        return OutBase(code=400, status="error", message=f"删除版本失败: {exc}")
    return OutBase(message=f"已删除 {payload.projectId}@{payload.version}")


@router.post(
    "/maafw/managed/inventory",
    tags=["MaaFW"],
    summary="查看托管 Store 的占用",
    response_model=MaaFWManagedInventoryOut,
    status_code=200,
)
async def get_managed_maafw_inventory() -> MaaFWManagedInventoryOut:
    store = _managed_store()
    try:
        info = await asyncio.to_thread(store.storage_info)
        projects = await asyncio.to_thread(store.list_projects)
    except Exception as exc:
        return MaaFWManagedInventoryOut(
            code=500, status="error", message=f"读取 Store 库存失败: {exc}", data=None
        )

    items: list[MaaFWManagedProjectItem] = []
    total = 0
    for project in projects:
        size = int(project.get("sizeBytes") or 0)
        total += size
        items.append(
            MaaFWManagedProjectItem(
                projectId=str(project.get("projectId") or ""),
                current=project.get("current"),
                versionCount=int(project.get("versionCount") or 0),
                sizeBytes=size,
            )
        )
    return MaaFWManagedInventoryOut(
        message=f"共 {len(items)} 个托管项目",
        data=MaaFWManagedInventoryData(
            storeId=str(info.get("storeId") or ""),
            root=str(info.get("root") or ""),
            runRoot=str(info.get("runRoot") or ""),
            totalBytes=total,
            projects=items,
        ),
    )


@router.post(
    "/maafw/managed/gc",
    tags=["MaaFW"],
    summary="回收托管 Store 中无人引用的版本",
    response_model=MaaFWManagedGcOut,
    status_code=200,
)
async def collect_managed_maafw_garbage(
    payload: MaaFWManagedGcIn = Body(...),
) -> MaaFWManagedGcOut:
    store = _managed_store()
    try:
        result = await asyncio.to_thread(store.collect_garbage, dry_run=payload.dryRun)
    except Exception as exc:
        return MaaFWManagedGcOut(
            code=500, status="error", message=f"回收失败: {exc}", data=None
        )
    removed = result.get("removed") or result.get("deleted") or []
    verb = "预览完成" if payload.dryRun else "回收完成"
    return MaaFWManagedGcOut(message=f"{verb}，涉及 {len(removed)} 项", data=result)


@router.post(
    "/maafw/preview",
    tags=["MaaFW"],
    summary="预览 MFW interface",
    response_model=MaaFWInterfacePreviewOut,
    status_code=200,
)
async def preview_maafw_interface(
    payload: MaaFWInterfacePreviewIn = Body(...),
) -> MaaFWInterfacePreviewOut:
    """读取 MaaFW 项目 interface，并返回 controller/resource/task 摘要。"""

    try:
        root_path = Path(payload.path).resolve()
        interface = await asyncio.to_thread(load_interface_model_cached, root_path)
        preview = await asyncio.to_thread(
            build_interface_preview_data,
            root_path,
            interface,
        )
        data = MaaFWInterfacePreviewData.model_validate(preview.model_dump(mode="json"))
    except MaaFWInterfaceLoadError as exc:
        return MaaFWInterfacePreviewOut(
            code=400,
            status="error",
            message=str(exc),
            data=None,
        )
    except Exception as exc:
        return MaaFWInterfacePreviewOut(
            code=500,
            status="error",
            message=f"MFW interface 预览失败: {exc}",
            data=None,
        )

    return MaaFWInterfacePreviewOut(
        message=f"已读取 MFW 项目 {data.project.name}，共 {len(data.tasks)} 个任务",
        data=data,
    )


@router.post(
    "/maafw/update",
    tags=["MaaFW"],
    summary="检查或执行 MFW 项目更新",
    response_model=MaaFWProjectUpdateOut,
    status_code=200,
)
async def update_maafw_project(
    payload: MaaFWProjectUpdateIn = Body(...),
) -> MaaFWProjectUpdateOut:
    """按脚本 ``Update.*`` 配置检查或应用 MaaFW 项目目录更新。

    ``action=check`` 只读取 interface 版本与更新源元数据，返回是否有新版本；
    ``action=apply`` 触发下载并原地应用更新包。失败时返回明确 ``message``。
    """

    try:
        script_config = _maafw_script_config(payload.scriptId)
    except (KeyError, ValueError, TypeError) as exc:
        return MaaFWProjectUpdateOut(
            code=400, status="error", message=f"MFW 脚本无效: {exc}"
        )

    # 托管脚本是 MaaFWConfig 的子类，上面那个 isinstance 拦不住它；不在这里
    # 分流，下面就会拿 checkout 路径去做原地更新。
    if isinstance(script_config, RuntimeMaaFWManagedConfig):
        return await _run_managed_project_update(payload, script_config)

    project_value = str(script_config.get("Info", "Path") or "").strip()
    if not project_value:
        return MaaFWProjectUpdateOut(
            code=400, status="error", message="请先设置 MFW 项目路径"
        )
    root_path = Path(project_value).resolve()
    if not root_path.is_dir():
        return MaaFWProjectUpdateOut(
            code=400,
            status="error",
            message="MFW 项目路径不是有效目录，请检查 Info.Path",
        )

    try:
        interface = await asyncio.to_thread(load_interface_model_cached, root_path)
    except MaaFWInterfaceLoadError as exc:
        return MaaFWProjectUpdateOut(
            code=400, status="error", message=f"MFW interface 读取失败: {exc}"
        )
    except Exception as exc:
        return MaaFWProjectUpdateOut(
            code=500, status="error", message=f"MFW interface 读取失败: {exc}"
        )

    current_version = str(interface.version or "")
    source_config = _maafw_update_source_config(script_config)
    proxy = Config.proxy
    # CDK 值绝不进日志：只记录「有没有」。
    _maafw_update_logger.info(
        f"MFW 项目更新({payload.action}): script={payload.scriptId} "
        f"channel={source_config['channel']} "
        f"cdk={'已配置' if source_config['mirror_cdk'] else '未配置'}"
    )

    if payload.action == "check":
        try:
            discovery = await discover_maafw_project_update(
                interface,
                current_version=current_version,
                source_config=source_config,
                proxy=proxy,
                send_log=_maafw_update_send_log,
                # 只问有没有新版本：带 CDK 去换下载地址会扣一次今日额度，
                # 而用户可能只是随手点了下「检查更新」。真更新时再取。
                version_only=True,
            )
        except MaaFWProjectUpdateError as exc:
            return MaaFWProjectUpdateOut(
                code=400, status="error", message=f"MFW 更新检查失败: {exc}"
            )
        except Exception as exc:
            return MaaFWProjectUpdateOut(
                code=500, status="error", message=f"MFW 更新检查失败: {exc}"
            )

        if discovery is None:
            return MaaFWProjectUpdateOut(
                message=f"MFW 项目已是最新版本: {current_version or '未知'}",
                data=MaaFWProjectUpdateData(
                    checked=True, currentVersion=current_version
                ),
            )

        extra = _maafw_update_extra_fields(discovery)
        candidate = getattr(discovery, "candidate", None)
        # discovery.source 是版本元数据来源（恒为 Mirror 酱）；响应里的 source
        # 要回答「会从哪里下载」：优先候选包来源，其次核心包的 package_source。
        # 一律用对外名（mirrorchyan / github）：candidate.source 是核心包的内部
        # 名（github_release），直接回给前端会让「下载来源」显示成 github_release。
        candidate_source = _public_package_source(
            (getattr(candidate, "source", None) if candidate is not None else None)
            or getattr(discovery, "package_source", None)
            or getattr(discovery, "source", None)
        )
        installable = bool(getattr(discovery, "installable", False))
        latest_version = getattr(discovery, "version", None) or extra["versionName"]
        extra["versionName"] = extra["versionName"] or latest_version
        message = (
            f"发现 MFW 项目新版本: {current_version or '未知'} -> {latest_version}"
        )
        unavailable_reason = getattr(discovery, "unavailable_reason", "")
        if not installable and unavailable_reason:
            message = f"{message}（暂无可安装更新包: {unavailable_reason}）"
        return MaaFWProjectUpdateOut(
            message=_maafw_update_message_with_cdk(message, extra),
            data=MaaFWProjectUpdateData(
                checked=True,
                updateAvailable=True,
                installable=installable,
                currentVersion=current_version,
                latestVersion=latest_version,
                source=candidate_source,
                **extra,
            ),
        )

    try:
        # 仓库、tag、资产名等 GitHub 参数不再传入：核心包从 interface.json 与
        # 目录名自行推断。**source_config 必须传**：它带着用户选定的下载源，
        # 漏了就会退回缺省的 GitHub——check 说走 Mirror 酱、apply 却从 GitHub
        # 下载，正是本次设计要禁掉的静默换源。
        result = await update_maafw_project_if_needed(
            root_path,
            interface,
            mirror_cdk=source_config["mirror_cdk"],
            channel=source_config["channel"],
            source_config=source_config,
            proxy=proxy,
            send_log=_maafw_update_send_log,
        )
    except MaaFWProjectUpdateError as exc:
        return MaaFWProjectUpdateOut(
            code=400, status="error", message=f"MFW 项目更新失败: {exc}"
        )
    except Exception as exc:
        return MaaFWProjectUpdateOut(
            code=500, status="error", message=f"MFW 项目更新失败: {exc}"
        )

    extra = _maafw_update_extra_fields(result)
    message = str(getattr(result, "message", "") or "") or "MFW 项目更新完成"
    return MaaFWProjectUpdateOut(
        message=_maafw_update_message_with_cdk(message, extra),
        data=MaaFWProjectUpdateData(
            checked=bool(getattr(result, "checked", True)),
            updated=bool(getattr(result, "updated", False)),
            updateAvailable=bool(getattr(result, "update_available", False)),
            installable=bool(getattr(result, "installable", False)),
            currentVersion=(
                getattr(result, "current_version", None)
                or getattr(result, "previous_version", None)
                or current_version
            ),
            latestVersion=getattr(result, "latest_version", None)
            or extra["versionName"],
            source=getattr(result, "source", None),
            **extra,
        ),
    )


def _maafw_agent_env_prepare_data(
    root_path: Path,
    result: Mapping[str, Any],
    logs: list[str],
    *,
    cached: bool,
) -> MaaFWAgentEnvPrepareData:
    """把 ``prepare_project_environment()`` 的结果摊平成响应体。

    缓存命中与实际准备两条路共用，免得两边的字段各写一份、慢慢长歪。
    """

    runtime = result.get("runtime")
    runtime = runtime if isinstance(runtime, Mapping) else {}
    agent_payload = result.get("agents")
    agent_payload = agent_payload if isinstance(agent_payload, Mapping) else {}
    raw_plans = agent_payload.get("plans")
    raw_plans = raw_plans if isinstance(raw_plans, list) else []

    agents = [
        MaaFWAgentEnvInfo(
            childExec=str(plan.get("childExec") or ""),
            executable=str(plan.get("executable") or ""),
            runtimeKind=plan.get("runtimeKind"),
            isolatedVenvPath=plan.get("isolatedVenvPath"),
            fallbackReason=plan.get("fallbackReason"),
        )
        for plan in raw_plans
        if isinstance(plan, Mapping)
    ]

    return MaaFWAgentEnvPrepareData(
        path=str(root_path),
        agentCount=len(agents),
        agents=agents,
        logs=logs,
        runtimeId=runtime.get("runtimeId"),
        poolId=runtime.get("poolId"),
        pythonExecutable=runtime.get("pythonExecutable"),
        venvPath=runtime.get("venvPath"),
        maafwVersion=runtime.get("maafwVersion"),
        cached=cached,
        preparedAt=result.get("preparedAt"),
    )


@router.post(
    "/maafw/agent-env/prepare",
    tags=["MaaFW"],
    summary="预备 MFW 运行环境",
    response_model=MaaFWAgentEnvPrepareOut,
    status_code=200,
)
async def prepare_maafw_agent_env(
    payload: MaaFWAgentEnvPrepareIn = Body(...),
) -> MaaFWAgentEnvPrepareOut:
    """按项目 interface 预备 Runner 运行时与各 agent 的 Python 环境。

    在项目引导里读到 interface 之后调用，把首次运行才会付出的下载与建环境
    成本提前到配置阶段。与 ``/maafw/update`` 一样是同步端点：整个准备过程
    在请求内完成，首次冷启动可能耗时数分钟。

    编辑页每打开一次就会调一次，所以先比一遍项目输入指纹：项目没更新过、上次
    准备的环境也还在盘上，就直接还回上次的结果，不再取锁起进程。用户手动重试
    时前端带 ``force``，跳过这层缓存。
    """

    # 这些模块会拉起 runtime_pool 与 agent_env，放在函数内延迟导入，
    # 避免所有 API 请求都为它们付出导入成本。
    from app.core.ws import protocol as ws_protocol
    from app.core.ws.publisher import Publisher
    from app.task.MaaFW.tools.core.automas_maafw_runner.service import (
        MaaFWRunnerService,
        project_environment_fingerprint,
    )
    from app.task.MaaFW.tools.core.automas_maafw_runtime_pool import (
        MaaFWRuntimePoolService,
    )
    from app.task.MaaFW.tools.embedded.env_cache import (
        load_prepared_environment,
        store_prepared_environment,
    )
    from app.task.MaaFW.tools.embedded.project_path import (
        release_project_path,
        try_reserve_project_path,
    )
    from app.task.MaaFW.tools.embedded.runtime_route import (
        runtime_pool_route_from_service,
    )

    logs: list[str] = []
    # 准备过程可能持续数分钟（首次要下载 MaaFramework），全程把阶段、百分比
    # 与新增日志行推给前端。progress_id 留空时只落日志、不推送。
    progress_id = str(payload.scriptId or "").strip()
    loop = asyncio.get_running_loop()

    def publish_progress(event: dict) -> None:
        if not progress_id:
            return
        data = WSMaaFWEnvPrepareProgressData(
            stage=str(event.get("stage") or ""),
            status=str(event.get("status") or "running"),
            message=str(event.get("message") or ""),
            percent=event.get("percent"),
            log=event.get("log"),
        )
        # 准备跑在工作线程里，回调要跨回事件循环才能发 WS
        asyncio.run_coroutine_threadsafe(
            Publisher.send(
                id=progress_id,
                type=ws_protocol.MAAFW_ENV_PREPARE_PROGRESS,
                data=data,
            ),
            loop,
        )

    def append_log(line: str) -> None:
        logs.append(line)
        publish_progress(
            {
                "stage": "log",
                "status": "running",
                "message": line,
                "log": line,
            }
        )

    project_value = str(payload.path or "").strip()
    if not project_value:
        return MaaFWAgentEnvPrepareOut(
            code=400, status="error", message="请先设置 MFW 项目路径"
        )
    root_path = Path(project_value).resolve()
    if not root_path.is_dir():
        return MaaFWAgentEnvPrepareOut(
            code=400,
            status="error",
            message="MFW 项目路径不是有效目录，请检查项目目录",
        )

    # 与运行、更新共用同一把项目锁：同一目录同时准备/运行会互相踩。
    reservation_key = await try_reserve_project_path(root_path)
    if reservation_key is None:
        return MaaFWAgentEnvPrepareOut(
            code=409,
            status="error",
            message="该 MFW 项目正在运行、更新或准备环境，请稍后重试",
            data=MaaFWAgentEnvPrepareData(path=str(root_path), logs=logs),
        )

    try:
        # 指纹哈希的是 interface / requirements / uv.lock 这些「脚本更新了没」
        # 的输入，所以项目一更新缓存自然失效。放在拿到项目锁之后：此刻没人在
        # 更新这个目录，算出来的指纹不会是半个更新中间态。
        fingerprint = await asyncio.to_thread(
            project_environment_fingerprint, root_path
        )
        if not payload.force:
            cached_result = await asyncio.to_thread(
                load_prepared_environment, root_path, fingerprint
            )
            if cached_result is not None:
                prepared_at = str(cached_result.get("preparedAt") or "")
                append_log(
                    "项目文件自上次准备以来没有变化，沿用已就绪的运行环境"
                    + (f"（上次准备于 {prepared_at}）" if prepared_at else "")
                )
                # 命中时不推 ready 进度：没有进度可言，而那条 WS 与本次响应
                # 抢着写同一行提示，谁后到谁说了算——推了反而会把响应里带
                # MaaFramework 版本号的那句盖成一句干巴巴的「已就绪」。
                return MaaFWAgentEnvPrepareOut(
                    message="MFW 运行环境已就绪",
                    data=_maafw_agent_env_prepare_data(
                        root_path, cached_result, logs, cached=True
                    ),
                )

        try:
            interface = await asyncio.to_thread(load_interface_model_cached, root_path)
        except MaaFWInterfaceLoadError as exc:
            return MaaFWAgentEnvPrepareOut(
                code=400,
                status="error",
                message=f"MFW interface 读取失败: {exc}",
                data=MaaFWAgentEnvPrepareData(path=str(root_path), logs=logs),
            )

        route = await asyncio.to_thread(
            lambda: runtime_pool_route_from_service(MaaFWRuntimePoolService())
        )
        try:
            result = await asyncio.to_thread(
                MaaFWRunnerService().prepare_project_environment,
                root_path,
                interface,
                runtime_pool_root=route.root,
                runtime_pool_id=route.pool_id,
                # worker 子进程跑在隔离 venv 里，代码要靠 PYTHONPATH 找到本仓
                import_paths=[Path.cwd()],
                send_log=append_log,
                progress=publish_progress,
            )
        except Exception as exc:
            publish_progress(
                {
                    "stage": "failed",
                    "status": "failed",
                    "message": f"MFW 运行环境准备失败: {exc}",
                }
            )
            return MaaFWAgentEnvPrepareOut(
                code=500,
                status="error",
                message=f"MFW 运行环境准备失败: {exc}",
                data=MaaFWAgentEnvPrepareData(path=str(root_path), logs=logs),
            )
        # 用准备流程自己回报的指纹：它在准备前后各算了一次，确认这期间项目文件
        # 没被动过；本地这份只在它没回报时兜底。
        # 写在项目锁内：写完才放行下一个准备/更新请求，免得它读到半份缓存。
        await asyncio.to_thread(
            store_prepared_environment,
            root_path,
            str(result.get("projectFingerprint") or "") or fingerprint,
            result,
        )
    finally:
        await release_project_path(reservation_key)

    publish_progress(
        {
            "stage": "ready",
            "status": "success",
            "message": "MFW 运行环境已就绪",
            "percent": 100.0,
        }
    )
    return MaaFWAgentEnvPrepareOut(
        message="MFW 运行环境已就绪",
        data=_maafw_agent_env_prepare_data(root_path, result, logs, cached=False),
    )


@router.post(
    "/m9a/tasks/available",
    tags=["M9A"],
    summary="获取 M9A 可用任务列表（排除 standalone 任务）",
    status_code=200,
)
async def get_m9a_available_tasks(script_id: str):
    """
    获取 M9A 可用任务列表（排除 standalone 任务）

    前端调用此接口获取可选择的任务列表，
    用于展示在用户编辑界面的任务选择区域。

    Args:
        script_id: M9A 脚本 ID

    Returns:
        dict: 包含任务列表的响应
    """
    from pathlib import Path

    from app.task.M9A.task_loader import M9ATaskLoader

    try:
        script_config = Config.ScriptConfig[uuid.UUID(script_id)]
        m9a_path = Path(script_config.get("Info", "Path"))
        loader = await asyncio.to_thread(M9ATaskLoader.get_cached, m9a_path)

        # 获取可用任务，并添加完整定义（包括 option 和 _option_definitions）
        available_tasks = loader.get_available_tasks()
        result_tasks = []

        for task in available_tasks:
            full_def = loader.get_full_definition(task["name"])
            if full_def:
                result_tasks.append(full_def)

        return {
            "code": 200,
            "status": "success",
            "message": f"共 {len(result_tasks)} 个可用任务",
            "data": result_tasks,
        }
    except Exception as e:
        return {
            "code": 500,
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
            "data": [],
        }


@router.get(
    "/hsr/stage-options",
    tags=["HSR"],
    summary="获取 HSR 体力副本动态选项",
    response_model=HSRStageOptionsOut,
    status_code=200,
)
async def get_hsr_stage_options_api(
    scriptId: str | None = None,
    engine: Literal["M7A", "SRA"] = "M7A",
    userId: str | None = None,
    slot: Literal["main", "eow"] = "main",
) -> HSRStageOptionsOut:
    """返回 M7A/SRA 原生副本字段。

    ``userId`` 仅用于校验用户归属；``slot`` 是兼容参数，动态选项当前
    按引擎统一返回，不按 slot 生成不同结果。
    """

    try:
        if not scriptId:
            return HSRStageOptionsOut(
                code=400,
                status="error",
                message="缺少 scriptId",
            )

        script_config = _hsr_script_config(scriptId)
        if userId:
            _hsr_user_config(script_config, userId)
        from app.task.HSR.tools.api import build_stage_options

        data = HSRStageOptionsData(**build_stage_options(script_config, engine))
        option_count = sum(len(category.options) for category in data.categories)
        return HSRStageOptionsOut(
            message=f"共 {option_count} 个 HSR 体力副本选项",
            data=data,
        )
    except Exception as e:
        return HSRStageOptionsOut(
            code=400
            if isinstance(e, (ValueError, KeyError, TypeError, RuntimeError))
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
        )


@router.get(
    "/bettergi/strategies",
    tags=["BetterGI"],
    summary="获取 BetterGI 自动战斗策略选项",
    response_model=ComboBoxOut,
    status_code=200,
)
async def get_bettergi_strategies_api(scriptId: str) -> ComboBoxOut:
    """返回 BetterGI 可用自动战斗策略：内置「根据队伍自动选择」+ ``{RootPath}/User/AutoFight/*.txt`` 文件名。"""

    try:
        script_config = _bettergi_script_config(scriptId)
        root = Path(script_config.get("Info", "RootPath")).expanduser()
        from app.task.BetterGI.tools import one_dragon

        names = one_dragon.list_auto_boss_strategies(root)
        data = [ComboBoxItem(label=n, value=n) for n in names]
        return ComboBoxOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 个自动战斗策略选项",
            data=data,
        )
    except Exception as e:
        return ComboBoxOut(
            code=400
            if isinstance(e, (ValueError, KeyError, TypeError, RuntimeError))
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/bettergi/one-dragon/custom-groups",
    tags=["BetterGI"],
    summary="获取 BetterGI 一条龙自定义配置组",
    response_model=BetterGICustomGroupsOut,
    status_code=200,
)
async def get_bettergi_custom_groups_api(
    scriptId: str, configName: str = "", useMasConfig: bool = False
) -> BetterGICustomGroupsOut:
    """返回指定一条龙配置里的自定义配置组（非内置 8 组）及其启用状态，供前端表格自动加载。

    ``useMasConfig=True``（用户独立配置）时改读 MAS 运行时槽位「MAS独立配置」：独立模式的
    per-user 配置物化在槽位而非 {configName} 实配，读槽位才能列到用户刚在 BGI GUI 里往
    独立配置添加的自定义组。
    """

    try:
        script_config = _bettergi_script_config(scriptId)
        root = Path(script_config.get("Info", "RootPath")).expanduser()
        from app.task.BetterGI.tools import one_dragon

        read_name = (
            one_dragon.launch_slot_name()
            if useMasConfig
            else one_dragon.resolve_config_name(configName)
        )
        items = one_dragon.list_custom_groups(root, read_name)
        data = [BetterGICustomGroupOut(**item) for item in items]
        return BetterGICustomGroupsOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 个自定义配置组",
            data=data,
        )
    except Exception as e:
        return BetterGICustomGroupsOut(
            code=400
            if isinstance(e, (ValueError, KeyError, TypeError, RuntimeError))
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/bettergi/one-dragon/configs",
    tags=["BetterGI"],
    summary="获取 BetterGI 一条龙配置名列表",
    response_model=ComboBoxOut,
    status_code=200,
)
async def get_bettergi_one_dragon_configs_api(scriptId: str) -> ComboBoxOut:
    """返回 BetterGI 可选一条龙配置名：{RootPath}/User/OneDragon/*.json 文件名（默认配置置顶）。"""

    try:
        script_config = _bettergi_script_config(scriptId)
        root = Path(script_config.get("Info", "RootPath")).expanduser()
        from app.task.BetterGI.tools import one_dragon

        names = one_dragon.list_one_dragon_configs(root)
        data = [ComboBoxItem(label=n, value=n) for n in names]
        return ComboBoxOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 个一条龙配置",
            data=data,
        )
    except Exception as e:
        return ComboBoxOut(
            code=400
            if isinstance(e, (ValueError, KeyError, TypeError, RuntimeError))
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/zzzod/instances",
    tags=["ZZZ-OD"],
    summary="获取 zzz-od 实例（账号）列表",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def get_zzzod_instances_api(scriptId: str) -> ZzzOdInstancesOut:
    """返回 zzz-od 实例列表（供「快速导入」选择来源实例）。"""

    try:
        data = [
            ZzzOdInstanceOut(**item) for item in Config.get_zzzod_instances(scriptId)
        ]
        return ZzzOdInstancesOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 个实例",
            data=data,
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


def _zzzod_instances_response(instances: list[dict]) -> ZzzOdInstancesOut:
    """把服务层实例列表包装为统一响应（供直控实例管理各操作复用）。"""

    data = [ZzzOdInstanceOut(**item) for item in instances]
    return ZzzOdInstancesOut(
        code=200,
        status="success",
        message=f"共 {len(data)} 个实例",
        data=data,
    )


@router.post(
    "/zzzod/instances/add",
    tags=["ZZZ-OD"],
    summary="新建一条龙实例（直控实例管理）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def add_zzzod_instance_api(
    body: ZzzOdInstanceAddIn = Body(...),
) -> ZzzOdInstancesOut:
    """创建实例（最小空闲槽，避开原生与跨脚本 MAS 绑定槽），返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.add_zzzod_instance(body.scriptId, body.name)
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.post(
    "/zzzod/instances/rename",
    tags=["ZZZ-OD"],
    summary="重命名一条龙实例（直控实例管理）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def rename_zzzod_instance_api(
    body: ZzzOdInstanceRenameIn = Body(...),
) -> ZzzOdInstancesOut:
    """只改注册表 name（实例目录不变），返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.rename_zzzod_instance(
                body.scriptId, body.instanceIdx, body.name
            )
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.post(
    "/zzzod/instances/active-in-od",
    tags=["ZZZ-OD"],
    summary="切换实例是否参与「全部实例」运行（直控实例管理）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def set_zzzod_instance_active_in_od_api(
    body: ZzzOdInstanceFlagIn = Body(...),
) -> ZzzOdInstancesOut:
    """切换 active_in_od 标志位，返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.set_zzzod_instance_active_in_od(
                body.scriptId, body.instanceIdx, body.activeInOd
            )
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.post(
    "/zzzod/instances/set-active",
    tags=["ZZZ-OD"],
    summary="把所选实例设为当前活跃（直控「选择即运行」）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def set_zzzod_active_instance_api(
    body: ZzzOdInstanceActiveIn = Body(...),
) -> ZzzOdInstancesOut:
    """把目标实例设为注册表 active（其余清 False），返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.set_zzzod_instance_active(body.scriptId, body.instanceIdx)
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.post(
    "/zzzod/instances/force-login",
    tags=["ZZZ-OD"],
    summary="切换实例「运行前切换账号」（直控实例管理；一条龙原生能力）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def set_zzzod_instance_force_login_api(
    body: ZzzOdInstanceForceLoginIn = Body(...),
) -> ZzzOdInstancesOut:
    """切换实例条目的 force_login_before_run（一条龙自己消费），返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.set_zzzod_instance_force_login(
                body.scriptId, body.instanceIdx, body.forceLogin
            )
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.post(
    "/zzzod/instances/run-mode",
    tags=["ZZZ-OD"],
    summary="设置运行实例（直控；one_dragon.yml 全局 instance_run）",
    response_model=OutBase,
    status_code=200,
)
async def set_zzzod_instance_run_mode_api(
    body: ZzzOdInstanceRunModeIn = Body(...),
) -> OutBase:
    """白名单校验后写回全局 instance_run（与直控页当前编辑哪个实例无关）。"""

    try:
        Config.set_zzzod_instance_run_mode(body.scriptId, body.instanceRun)
        return OutBase()
    except Exception as e:
        return OutBase(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
        )


@router.post(
    "/zzzod/instances/delete",
    tags=["ZZZ-OD"],
    summary="删除一条龙实例（直控实例管理；受 MAS 绑定槽保护）",
    response_model=ZzzOdInstancesOut,
    status_code=200,
)
async def delete_zzzod_instance_api(
    body: ZzzOdInstanceDeleteIn = Body(...),
) -> ZzzOdInstancesOut:
    """删除注册表条目与实例目录，返回更新后的实例列表。"""

    try:
        return _zzzod_instances_response(
            Config.delete_zzzod_instance(body.scriptId, body.instanceIdx)
        )
    except Exception as e:
        return ZzzOdInstancesOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/zzzod/teams",
    tags=["ZZZ-OD"],
    summary="获取预备编队列表（名称 + 绑定配队方案）",
    response_model=ZzzOdTeamsOut,
    status_code=200,
)
async def get_zzzod_teams_api(
    scriptId: str,
    userId: str,
    instanceIdx: int | None = None,
) -> ZzzOdTeamsOut:
    """读绑定槽（直控传 instanceIdx 读原生实例）的 team.yml（固定 20 个编队）。"""

    try:
        data = await Config.get_zzzod_teams(scriptId, userId, instance_idx=instanceIdx)
        return ZzzOdTeamsOut(
            code=200,
            status="success",
            message="操作成功",
            teams=[ZzzOdTeamItemOut(**t) for t in data["teams"]],
            autoBattle=data["autoBattle"],
            agentOptions=data["agentOptions"],
        )
    except Exception as e:
        return ZzzOdTeamsOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            teams=[],
            autoBattle=[],
        )


@router.post(
    "/zzzod/teams/save",
    tags=["ZZZ-OD"],
    summary="整表保存预备编队（名称 + 绑定配队方案；成员按行保留）",
    response_model=ZzzOdTeamsSaveOut,
    status_code=200,
)
async def save_zzzod_teams_api(script: ZzzOdTeamsSaveIn = Body(...)) -> ZzzOdTeamsSaveOut:
    """直控传 instanceIdx 直接写原生实例，缺省写用户绑定槽。"""

    try:
        saved = await Config.save_zzzod_teams(
            script.scriptId,
            script.userId,
            script.teams,
            instance_idx=script.instanceIdx,
        )
        return ZzzOdTeamsSaveOut(
            code=200,
            status="success",
            message="编队已保存",
            teams=[
                ZzzOdTeamItemOut(
                    idx=i,
                    name=str(item.get("name") or ""),
                    autoBattle=str(item.get("auto_battle") or ""),
                    agents=[str(a) for a in item.get("agent_id_list") or []],
                )
                for i, item in enumerate(saved)
            ],
        )
    except Exception as e:
        return ZzzOdTeamsSaveOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            teams=[],
        )


@router.get(
    "/zzzod/catalog",
    tags=["ZZZ-OD"],
    summary="获取一条龙任务目录",
    response_model=ZzzOdCatalogOut,
    status_code=200,
)
async def get_zzzod_catalog_api(scriptId: str) -> ZzzOdCatalogOut:
    """静态解析安装目录下的应用注册信息，供用户配置渲染任务卡片中文名。"""

    try:
        # 统一走 _zzzod_root 哨兵校验（空串在此解析成 cwd 的边界被封住）
        root = Config.get_zzzod_root(scriptId)
        from app.task.ZzzOd.tools import (
            get_task_app_fields,
            get_task_app_jump,
            list_app_catalog,
        )

        data = [
            ZzzOdCatalogItemOut(
                **item,
                configurable=get_task_app_fields(str(item["app_id"])) is not None,
                jump=get_task_app_jump(str(item["app_id"])),
            )
            for item in list_app_catalog(root)
        ]
        return ZzzOdCatalogOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 个任务",
            data=data,
        )
    except Exception as e:
        return ZzzOdCatalogOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/zzzod/app-config",
    tags=["ZZZ-OD"],
    summary="获取任务级配置（字段元数据 + 当前值）",
    response_model=ZzzOdAppConfigOut,
    status_code=200,
)
async def get_zzzod_app_config_api(
    scriptId: str,
    userId: str,
    appId: str,
    instanceIdx: int | None = None,
) -> ZzzOdAppConfigOut:
    """返回任务可配置字段、选项与当前值（直控传 instanceIdx 读原生实例，否则读绑定槽）。"""

    try:
        data = await Config.get_zzzod_app_config(
            scriptId, userId, appId, instance_idx=instanceIdx
        )
        return ZzzOdAppConfigOut(
            code=200,
            status="success",
            message="操作成功",
            appId=data["appId"],
            fields=[ZzzOdAppConfigFieldOut(**f) for f in data["fields"]],
        )
    except Exception as e:
        return ZzzOdAppConfigOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            appId=appId,
            fields=[],
        )


@router.get(
    "/zzzod/options",
    tags=["ZZZ-OD"],
    summary="获取任务计划的动态选项（副本级联树/配队方案/挑战配置）",
    response_model=ZzzOdTaskOptionsOut,
    status_code=200,
)
async def get_zzzod_task_options_api(scriptId: str, appId: str) -> ZzzOdTaskOptionsOut:
    """静态读取安装目录（compendium 数据 + 配置目录扫描），与一条龙原生 GUI 选项同源。"""

    try:
        data = await Config.get_zzzod_task_options(scriptId, appId)
        return ZzzOdTaskOptionsOut(
            code=200,
            status="success",
            message="操作成功",
            appId=data["appId"],
            trainCategories=data["trainCategories"],
            lostVoidMissions=data["lostVoidMissions"],
            autoBattle=data["autoBattle"],
            challenge=data["challenge"],
        )
    except Exception as e:
        return ZzzOdTaskOptionsOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            appId=appId,
        )


@router.post(
    "/zzzod/app-config/save",
    tags=["ZZZ-OD"],
    summary="保存任务级配置（绑定槽；直控传 instanceIdx 直接写原生实例）",
    response_model=ZzzOdAppConfigOut,
    status_code=200,
)
async def save_zzzod_app_config_api(
    script: ZzzOdAppConfigSaveIn = Body(...),
) -> ZzzOdAppConfigOut:
    """字段白名单校验后写入 per-app YAML（缺省写用户绑定槽，直控写指定原生实例）。"""

    try:
        data = await Config.save_zzzod_app_config(
            script.scriptId,
            script.userId,
            script.appId,
            script.values,
            instance_idx=script.instanceIdx,
        )
        return ZzzOdAppConfigOut(
            code=200,
            status="success",
            message="配置已保存",
            appId=script.appId,
            fields=[
                ZzzOdAppConfigFieldOut(
                    field=str(k), title=str(k), value=str(v), options=[]
                )
                for k, v in data.items()
            ],
        )
    except Exception as e:
        return ZzzOdAppConfigOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            appId=script.appId,
            fields=[],
        )


@router.get(
    "/zzzod/native-config",
    tags=["ZZZ-OD"],
    summary="获取实例原生配置（直控页面表单数据）",
    response_model=ZzzOdNativeConfigOut,
    status_code=200,
)
async def get_zzzod_native_config_api(
    scriptId: str, instanceIdx: int
) -> ZzzOdNativeConfigOut:
    """读取所选实例 game_account.yml 与 _group.yml（含默认值合并与任务目录并入）。"""

    try:
        data = await Config.get_zzzod_native_config(scriptId, instanceIdx)
        return ZzzOdNativeConfigOut(
            code=200,
            status="success",
            message="操作成功",
            instanceIdx=data["instanceIdx"],
            instanceName=data["instanceName"],
            account=[ZzzOdNativeAccountField(**f) for f in data["account"]],
            tasks=[ZzzOdNativeTaskOut(**t) for t in data["tasks"]],
            instanceRun=data["instanceRun"],
        )
    except Exception as e:
        return ZzzOdNativeConfigOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            instanceIdx=instanceIdx,
            instanceName="",
            account=[],
            tasks=[],
            instanceRun="仅运行当前",
        )


@router.post(
    "/zzzod/native-config/save",
    tags=["ZZZ-OD"],
    summary="保存实例原生配置（直控模式直接写回一条龙原始 YAML）",
    response_model=ZzzOdNativeConfigOut,
    status_code=200,
)
async def save_zzzod_native_config_api(
    script: ZzzOdNativeConfigIn = Body(...),
) -> ZzzOdNativeConfigOut:
    """白名单过滤后写回所选实例 game_account.yml、_group.yml 与 instance_run，随后回读最新数据。"""

    try:
        await Config.save_zzzod_native_config(
            script.scriptId,
            script.instanceIdx,
            script.account,
            [t.model_dump() for t in script.tasks]
            if script.tasks is not None
            else None,
            script.instanceRun,
        )
        data = await Config.get_zzzod_native_config(
            script.scriptId, script.instanceIdx
        )
        return ZzzOdNativeConfigOut(
            code=200,
            status="success",
            message="配置已保存到一条龙原生配置",
            instanceIdx=data["instanceIdx"],
            instanceName=data["instanceName"],
            account=[ZzzOdNativeAccountField(**f) for f in data["account"]],
            tasks=[ZzzOdNativeTaskOut(**t) for t in data["tasks"]],
            instanceRun=data["instanceRun"],
        )
    except Exception as e:
        return ZzzOdNativeConfigOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            instanceIdx=script.instanceIdx,
            instanceName="",
            account=[],
            tasks=[],
            instanceRun="仅运行当前",
        )


@router.get(
    "/zzzod/backups",
    tags=["ZZZ-OD"],
    summary="列出配置备份（onedragon=一条龙原生配置 / mas=MAS 用户槽）",
    response_model=ZzzOdBackupListOut,
    status_code=200,
)
async def list_zzzod_backups_api(
    scriptId: str, userId: str, target: str = "onedragon"
) -> ZzzOdBackupListOut:
    """按时间倒序返回历史备份（运行/会话前自动归档，内容无变化跳过）。"""

    try:
        data = await Config.list_zzzod_backups(scriptId, userId, target)
        return ZzzOdBackupListOut(
            code=200,
            status="success",
            message=f"共 {len(data)} 份备份",
            data=[ZzzOdBackupItemOut(**item) for item in data],
        )
    except Exception as e:
        return ZzzOdBackupListOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            data=[],
        )


@router.get(
    "/zzzod/launchers",
    tags=["ZZZ-OD"],
    summary="获取一条龙两种启动器的安装情况与默认项",
    response_model=ZzzOdLauncherOut,
    status_code=200,
)
async def get_zzzod_launchers_api(scriptId: str) -> ZzzOdLauncherOut:
    """渲染「启动器」下拉用（直控/用户两态通用）：未安装的启动器选项禁用变灰。"""

    try:
        data = Config.get_zzzod_launchers(scriptId)
        return ZzzOdLauncherOut(code=200, status="success", message="", **data)
    except Exception as e:
        return ZzzOdLauncherOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            original_available=False,
            integrated_available=False,
        )


@router.post(
    "/zzzod/backup/restore",
    tags=["ZZZ-OD"],
    summary="把指定备份恢复到目标位置（onedragon=一条龙原生配置 / mas=MAS 用户配置）",
    response_model=ZzzOdBackupRestoreOut,
    status_code=200,
)
async def restore_zzzod_backup_api(
    script: ZzzOdBackupRestoreIn = Body(...),
) -> ZzzOdBackupRestoreOut:
    """onedragon：恢复一条龙原生配置（MAS 槽不触碰）；mas：恢复槽并全量回填本页字段。"""

    try:
        slot = await Config.restore_zzzod_backup(
            script.scriptId, script.userId, script.time, target=script.target
        )
        return ZzzOdBackupRestoreOut(
            code=200,
            status="success",
            message=f"已恢复备份 {script.time}",
            slot=slot,
            target=script.target,
        )
    except Exception as e:
        return ZzzOdBackupRestoreOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            slot=-1,
            target=script.target,
        )


@router.post(
    "/zzzod/backup/ensure",
    tags=["ZZZ-OD"],
    summary="按需归档目标池当前配置（指纹去重，无变化跳过；编辑界面三时机调用）",
    response_model=ZzzOdBackupEnsureOut,
    status_code=200,
)
async def ensure_zzzod_backup_api(
    script: ZzzOdBackupEnsureIn = Body(...),
) -> ZzzOdBackupEnsureOut:
    """onedragon：一条龙原生配置当前状态（进入编辑界面时捕捉 MAS 操作前原始态）；
    mas：MAS 用户绑定槽当前状态（退出编辑界面时的用户侧终态）。"""

    try:
        data = await Config.ensure_zzzod_backup(
            script.scriptId, script.userId, target=script.target
        )
        return ZzzOdBackupEnsureOut(
            code=200,
            status="success",
            message="",
            **data,
        )
    except Exception as e:
        return ZzzOdBackupEnsureOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            created=False,
            time="",
        )


@router.post(
    "/zzzod/import",
    tags=["ZZZ-OD"],
    summary="基于一条龙已有实例快速生成当前用户配置（覆盖前自动归档当前配置）",
    response_model=ZzzOdImportOut,
    status_code=200,
)
async def import_zzzod_config_api(
    script: ZzzOdImportIn = Body(...),
) -> ZzzOdImportOut:
    """把来源实例的账号信息与已启用任务编排写入本用户；覆盖前强制归档当前 MAS 槽配置，
    导入前状态可在「配置恢复」中找回。"""

    try:
        data = await Config.import_zzzod_config(
            script.scriptId, script.userId, script.instanceIdx
        )
        return ZzzOdImportOut(
            code=200,
            status="success",
            message="已基于所选实例生成用户配置",
            **data,
        )
    except Exception as e:
        return ZzzOdImportOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            instanceIdx=-1,
            instanceName="",
            importedAccountCount=0,
            importedTaskCount=0,
            slot=-1,
        )


@router.get(
    "/zzzod/backup/preview",
    tags=["ZZZ-OD"],
    summary="读取指定备份的配置摘要（纯读不恢复，供「预览配置」快速展示）",
    response_model=ZzzOdBackupPreviewOut,
    status_code=200,
)
async def get_zzzod_backup_preview_api(
    scriptId: str, userId: str, time: str, target: str = "onedragon"
) -> ZzzOdBackupPreviewOut:
    """mas：账号字段与已启用任务编排（即 MAS 本页展示的配置）；onedragon：实例列表。"""

    # target 是 Literal 响应字段：非法值进 try 后成功/异常两条分支都会因
    # 响应模型校验失败抛 ValidationError → 裸 500；在入口用 400 拦截
    if target not in ("onedragon", "mas"):
        raise HTTPException(status_code=400, detail=f"不支持的备份类别: {target}")

    try:
        data = Config.get_zzzod_backup_preview(
            scriptId, userId, time, target=target
        )
        return ZzzOdBackupPreviewOut(
            code=200,
            status="success",
            message="",
            **data,
        )
    except Exception as e:
        # 响应模型 info/account/tasks/instances 全部 required（...）；除填
        # account/tasks/instances 外还要填 info，否则 Pydantic 校验失败抛
        # ValidationError → 裸 500。错误信息塞进 info 的首项展示给用户。
        return ZzzOdBackupPreviewOut(
            code=400 if isinstance(e, (ValueError, KeyError, TypeError)) else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
            time=time,
            target=target,  # type: ignore[arg-type]
            info=[ZzzOdPreviewField(key="error", value=str(e))],
            account=[],
            tasks=[],
            instances=[],
        )


@router.get(
    "/hsr/capabilities",
    tags=["HSR"],
    summary="获取内置 HSR 能力快照",
    response_model=HSRCapabilitiesOut,
    status_code=200,
)
async def get_hsr_capabilities_api(scriptId: str | None = None) -> HSRCapabilitiesOut:
    """返回内置 HSR 的能力快照，不暴露原生编辑器会话。"""

    try:
        if not scriptId:
            return HSRCapabilitiesOut(code=400, status="error", message="缺少 scriptId")
        script_config = _hsr_script_config(scriptId)
        from app.task.HSR.tools.api import build_capabilities

        data = HSRCapabilitiesData(**build_capabilities(script_config))
        return HSRCapabilitiesOut(data=data)
    except Exception as e:
        return HSRCapabilitiesOut(
            code=400
            if isinstance(
                e, (FileNotFoundError, OSError, RuntimeError, ValueError, KeyError)
            )
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
        )


@router.get(
    "/hsr/managed-config",
    tags=["HSR"],
    summary="获取 HSR 托管配置字段",
    response_model=HSRManagedConfigOut,
    status_code=200,
)
async def get_hsr_managed_config_api(
    scriptId: str | None = None, userId: str | None = None
) -> HSRManagedConfigOut:
    """返回原生动态托管字段；用户 ID 只负责归属校验。"""

    try:
        if not scriptId:
            return HSRManagedConfigOut(
                code=400, status="error", message="缺少 scriptId"
            )
        script_config = _hsr_script_config(scriptId)
        user_config = None
        if userId:
            user_config = _hsr_user_config(script_config, userId)
        from app.task.HSR.tools.api import build_managed_config

        data = HSRManagedConfigData(**build_managed_config(script_config, user_config))
        return HSRManagedConfigOut(data=data)
    except Exception as e:
        return HSRManagedConfigOut(
            code=400
            if isinstance(
                e, (FileNotFoundError, OSError, RuntimeError, ValueError, KeyError)
            )
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
        )


@router.get(
    "/hsr/sra-profiles",
    tags=["HSR"],
    summary="获取 HSR 可选的 SRA 配置档案",
    response_model=HSRSRAProfilesOut,
    status_code=200,
)
async def get_hsr_sra_profiles_api(scriptId: str | None = None) -> HSRSRAProfilesOut:
    """列出 ``%APPDATA%/SRA/configs`` 下的配置档案，并标出脚本当前生效的那份。"""

    try:
        if not scriptId:
            return HSRSRAProfilesOut(code=400, status="error", message="缺少 scriptId")
        script_config = _hsr_script_config(scriptId)
        from app.task.HSR.tools.api import build_sra_profiles

        data = HSRSRAProfilesData(**build_sra_profiles(script_config))
        return HSRSRAProfilesOut(
            message=f"共 {len(data.profiles)} 份 SRA 配置档案",
            data=data,
        )
    except Exception as e:
        return HSRSRAProfilesOut(
            code=400
            if isinstance(e, (ValueError, KeyError, TypeError, RuntimeError))
            else 500,
            status="error",
            message=f"{type(e).__name__}: {str(e)}",
        )


@router.post(
    "/hsr/direct-config/import",
    tags=["HSR"],
    summary="导入 HSR 原生配置快照",
    response_model=HSRDirectConfigImportOut,
    status_code=200,
)
async def import_hsr_direct_config_api(
    request: HSRDirectConfigImportIn = Body(...),
) -> HSRDirectConfigImportOut:
    from app.task.HSR.tools.api import import_direct_config
    from app.task.HSR.tools.external_locks import HSRExternalPathBusyError

    try:
        script_config = _hsr_script_config(request.scriptId)
        # 先校验用户归属，再让 provider 读取原生文件，避免无效请求触碰用户配置。
        _hsr_user_config(script_config, request.userId)

        result = await import_direct_config(
            script_config,
            request.engine,
            script_id=request.scriptId,
            user_id=request.userId,
            update_user=Config.update_user,
        )
        return HSRDirectConfigImportOut(
            message=f"{request.engine} 原生配置已导入",
            data=HSRDirectConfigImportData(**result),
        )
    except HSRExternalPathBusyError as e:
        return HSRDirectConfigImportOut(
            code=409, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, RuntimeError) as e:
        return HSRDirectConfigImportOut(
            code=400, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    except OSError as e:
        return HSRDirectConfigImportOut(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )


@router.post(
    "/hsr/direct-config/clear",
    tags=["HSR"],
    summary="清除 HSR 用户的直控配置快照",
    response_model=HSRDirectConfigImportOut,
    status_code=200,
)
async def clear_hsr_direct_config_api(
    request: HSRDirectConfigImportIn = Body(...),
) -> HSRDirectConfigImportOut:
    """清掉该用户导入的快照，直控回到直接使用脚本当前原生配置。"""

    from app.task.HSR.tools.api import clear_direct_config

    try:
        script_config = _hsr_script_config(request.scriptId)
        _hsr_user_config(script_config, request.userId)

        result = await clear_direct_config(
            script_config,
            request.engine,
            script_id=request.scriptId,
            user_id=request.userId,
            update_user=Config.update_user,
        )
        return HSRDirectConfigImportOut(
            message=f"{request.engine} 已改回使用脚本当前配置",
            data=HSRDirectConfigImportData(**result),
        )
    except (KeyError, TypeError, ValueError) as e:
        return HSRDirectConfigImportOut(
            code=400, status="error", message=f"{type(e).__name__}: {str(e)}"
        )
    except OSError as e:
        return HSRDirectConfigImportOut(
            code=500, status="error", message=f"{type(e).__name__}: {str(e)}"
        )


@router.post(
    "/oknte/configs/list",
    tags=["OKNTE"],
    summary="获取 OK-NTE 配置文件列表及 schema",
    status_code=200,
)
async def get_oknte_configs_list(script_id: str, user_id: str):
    """
    获取 OK-NTE 配置文件列表及 schema 定义。
    读写用户配置目录（data/{script_id}/{user_id}/ConfigFile/），
    若为空则自动从 ok-nte configs 目录初始化默认配置。

    Args:
        script_id: OK-NTE 脚本 ID
        user_id: 用户 ID

    Returns:
        dict: 包含配置文件列表和 schema 的响应
    """
    try:
        import json
        import shutil

        from app.task.OkNte.config_schema import (
            build_fields_for_config,
            ensure_oknte_daily_routine_configs,
            get_all_config_info,
            load_oknte_option_labels,
        )

        _, script_config = _oknte_script_config(script_id)

        # 从 ok-nte 安装目录加载翻译 → option_labels
        root_path = script_config.get("Info", "RootPath")
        option_labels = load_oknte_option_labels(root_path) if root_path else {}

        # 用户配置目录；旧版 Default 目录仅作为升级后的初始化来源。
        mas_config_dir = _oknte_mas_config_dir(script_id, user_id)

        # ok-nte 源配置目录（用于自动初始化）
        legacy_config_dir = _oknte_legacy_mas_config_dir(script_id)
        oknte_configs_dir = (
            legacy_config_dir
            if legacy_config_dir.is_dir() and any(legacy_config_dir.iterdir())
            else None
        )
        if oknte_configs_dir is None:
            raw_config_path = script_config.get("Script", "ConfigPath")
            oknte_configs_dir = Path(raw_config_path) if raw_config_path else None
        if not oknte_configs_dir or not oknte_configs_dir.exists():
            if root_path:
                root = Path(root_path)
                packaged_dir = root / "data" / "apps" / "ok-nte" / "working" / "configs"
                source_dir = root / "configs"
                oknte_configs_dir = (
                    packaged_dir if packaged_dir.is_dir() else source_dir
                )

        # 自动初始化：用户目录为空时从旧版共享目录或 ok-nte configs 复制默认配置
        need_init = not mas_config_dir.exists() or not any(mas_config_dir.iterdir())
        if need_init and oknte_configs_dir and oknte_configs_dir.is_dir():
            mas_config_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(oknte_configs_dir, mas_config_dir, dirs_exist_ok=True)
        mas_config_dir.mkdir(parents=True, exist_ok=True)
        ensure_oknte_daily_routine_configs(mas_config_dir)

        configs_info = get_all_config_info()

        # 读取 per-user JSON 配置，通过 build_fields_for_config 构建字段列表
        result = []
        for info in configs_info:
            filename = info["filename"]
            filepath = _oknte_config_file_path(mas_config_dir, filename)
            current_data: dict[str, Any] = {}
            if filepath.exists():
                try:
                    current_data = json.loads(filepath.read_text(encoding="utf-8"))
                except Exception:
                    pass

            fields = build_fields_for_config(filename, current_data, option_labels)

            result.append(
                {
                    **info,
                    "fields": fields,
                    "currentData": current_data,
                }
            )

        return {
            "code": 200,
            "status": "success",
            "message": f"共 {len(result)} 个配置文件",
            "data": result,
            "optionLabels": option_labels,
            "configPath": str(mas_config_dir) if mas_config_dir else None,
        }
    except Exception as e:
        return {
            "code": 500,
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
            "data": [],
        }


@router.post(
    "/oknte/configs/update",
    tags=["OKNTE"],
    summary="更新 OK-NTE 配置文件",
    status_code=200,
)
async def update_oknte_config(
    script_id: str = Body(...),
    user_id: str = Body(...),
    filename: str = Body(...),
    data: dict = Body(...),
):
    """
    更新 OK-NTE 配置文件

    Args:
        script_id: OK-NTE 脚本 ID
        user_id: 用户 ID
        filename: 配置文件名（如 DailyTask.json）
        data: 要更新的配置数据

    Returns:
        dict: 操作结果
    """
    try:
        from app.task.OkNte.config_schema import update_oknte_config_data

        # 写入用户配置目录
        mas_config_dir = _oknte_mas_config_dir(script_id, user_id)
        mas_config_dir.mkdir(parents=True, exist_ok=True)

        filepath = _oknte_config_file_path(mas_config_dir, filename)

        existing_data = update_oknte_config_data(filepath, data)

        return {
            "code": 200,
            "status": "success",
            "message": f"配置文件 {filename} 已更新",
            "data": existing_data,
        }
    except Exception as e:
        return {
            "code": 500,
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


@router.post(
    "/oknte/configs/batch-update",
    tags=["OKNTE"],
    summary="批量更新 OK-NTE 配置文件",
    status_code=200,
)
async def batch_update_oknte_configs(
    script_id: str = Body(...),
    user_id: str = Body(...),
    configs: dict = Body(...),
):
    """
    批量更新 OK-NTE 配置文件

    Args:
        script_id: OK-NTE 脚本 ID
        user_id: 用户 ID
        configs: { filename: data } 格式的配置数据

    Returns:
        dict: 操作结果
    """
    try:
        from app.task.OkNte.config_schema import update_oknte_config_data

        # 写入用户配置目录
        mas_config_dir = _oknte_mas_config_dir(script_id, user_id)
        mas_config_dir.mkdir(parents=True, exist_ok=True)

        updated_files = []
        for filename, data in configs.items():
            filepath = _oknte_config_file_path(mas_config_dir, filename)
            update_oknte_config_data(filepath, data)
            updated_files.append(filename)

        return {
            "code": 200,
            "status": "success",
            "message": f"已更新 {len(updated_files)} 个配置文件",
            "data": updated_files,
        }
    except Exception as e:
        return {
            "code": 500,
            "status": "error",
            "message": f"{type(e).__name__}: {str(e)}",
        }


_MAAFW_IMAGE_SUFFIXES = {
    ".avif",
    ".bmp",
    ".gif",
    ".ico",
    ".jpeg",
    ".jpg",
    ".png",
    ".svg",
    ".webp",
}
"""允许外发的图片后缀。

白名单而非黑名单：``/maafw/asset`` 的 root 由请求方给定，等于把「读任意目录下的
文件」的能力暴露出去了，只能靠「必须在 root 内」+「必须是图片」两道闸门把它收窄
成「读项目内的图片」。放开成任意后缀就变成了任意文件读取。
"""


def _maafw_asset_file_path(root: str, asset_path: str) -> Path:
    """把 (项目根, 项目内相对路径) 解析成一个可安全外发的图片绝对路径。"""

    root_path = Path(root).resolve()
    if not root_path.is_dir():
        raise ValueError("MFW 项目目录不存在")

    normalized_asset_path = asset_path.replace("\\", "/").strip()
    relative_path = Path(normalized_asset_path)
    if (
        not normalized_asset_path
        or relative_path.is_absolute()
        or ".." in relative_path.parts
    ):
        raise ValueError("MFW 资源路径非法")

    file_path = (root_path / relative_path).resolve()
    # 逐段比对而不是比字符串前缀：符号链接与 ..（上面已挡）之外，
    # 大小写与短路径名的差异也会让前缀比较判错。
    if root_path not in file_path.parents:
        raise ValueError("MFW 资源路径越界")
    if file_path.suffix.casefold() not in _MAAFW_IMAGE_SUFFIXES:
        raise ValueError("仅支持 MFW 图片资源")
    if not file_path.is_file():
        raise FileNotFoundError("MFW 图片资源不存在")
    return file_path


@router.get(
    "/maafw/asset",
    tags=["MaaFW"],
    summary="读取 MFW 项目内的图片资源",
    response_class=FileResponse,
)
async def get_maafw_asset(
    root: str = Query(..., description="MFW 项目根目录"),
    path: str = Query(..., description="项目根目录内的相对图片路径"),
) -> FileResponse:
    """把 MFW 项目目录内的图片按需读给前端。

    任务说明（interface 的 ``doc`` / ``description``）是 markdown，里面的图片写的是
    **项目内相对路径**，浏览器没法直接读本地文件，必须由后端转一手。

    前端侧对应 ``buildMaaFWAssetUrl``：它已经拦掉了绝对路径、UNC、上跳与远程 URL，
    但那只是省一次往返，安全边界在这里 —— 请求可以绕过前端直接打过来。
    """

    try:
        file_path = _maafw_asset_file_path(root, path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(file_path)
