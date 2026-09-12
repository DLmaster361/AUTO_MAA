#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team
#
#   This file is part of AUTO-MAS.
#
#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License
#   as published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

"""通用配置恢复服务：双目标（MAS 用户配置 / 脚本原生配置）的列表、预览、恢复。

供各专项直接传参套用，避免重复实现「时间戳列表 → 预览摘要 → 恢复」这套
前端弹窗所需的统一后端能力。文件级快照/回写原语在 ``app.utils.config_archive``，
本层在其之上补齐「目标池」抽象：

- 每个目标池（:class:`ConfigRestoreTarget`）只暴露三个异步回调：``list_backups``、
  ``preview``、``restore``——专项各自闭包捕获脚本/用户等上下文实现；
- 专项调用 :class:`ConfigRestoreService` 时传入 ``script_name``（文案参数化用，
  如「一条龙」）与目标池列表（顺序即前端展示顺序，MAS 在前脚本在后）；
- 服务层不感知任何脚本结构，也不做文件读写之外的业务（守卫/信息字段回填等
  归专项回调）。

参考实现：``app.core.config`` 的 ZzzOd 恢复方法（``list_zzzod_backups`` /
``get_zzzod_backup_preview`` / ``restore_zzzod_backup``）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from app.utils import get_logger

logger = get_logger("配置恢复服务")


@dataclass
class ConfigRestoreTarget:
    """一个可恢复目标池（如「MAS 用户配置」「脚本原生配置」）。"""

    key: str
    """目标标识（如 ``mas`` / ``onedragon``），前端 segmented 与后端路由共用。"""

    list_backups: Callable[[], Awaitable[list[str]]]
    """返回该目标全部备份时间戳（倒序，最新在前）。"""

    preview: Callable[[str], Awaitable[dict]] | None = None
    """给定时间戳返回预览摘要 dict（纯读不恢复）；None 表示该目标不支持预览。"""

    restore: Callable[[str], Awaitable[object]] | None = None
    """给定时间戳执行恢复（恢复前归档当前由回调自理）；返回供前端展示的结果。"""

    snapshot: Callable[[], Awaitable[dict]] | None = None
    """归档当前配置（指纹去重，无变化跳过）；None 表示该目标不支持按需归档。

    供编辑界面的三时机归档使用：进入编辑界面（MAS 会触碰的原生配置捕捉
    「操作前原始态」）、退出编辑界面（MAS 侧配置终态）、运行前。返回
    ``{"created": bool, "time": str}``。
    """


class ConfigRestoreService:
    """双目标配置恢复服务：按 key 分发列表/预览/恢复。

    ``script_name`` 只用于文案参数化（错误提示等），前端展示文案走 i18n
    ``{script}`` 插值。
    """

    def __init__(
        self,
        script_name: str,
        targets: list[ConfigRestoreTarget],
    ) -> None:
        if not targets:
            raise ValueError("配置恢复服务至少需要一个目标池")
        self.script_name = script_name
        self._targets = {t.key: t for t in targets}

    def get_target(self, key: str) -> ConfigRestoreTarget:
        target = self._targets.get(key)
        if target is None:
            raise ValueError(f"不支持的恢复目标: {key}")
        return target

    async def list(self, key: str) -> list[str]:
        return await self.get_target(key).list_backups()

    async def preview(self, key: str, ts: str) -> dict:
        target = self.get_target(key)
        if target.preview is None:
            raise ValueError(f"目标「{key}」不支持预览")
        return await target.preview(ts)

    async def restore(self, key: str, ts: str) -> object:
        target = self.get_target(key)
        if target.restore is None:
            raise ValueError(f"目标「{key}」不支持恢复")
        return await target.restore(ts)

    async def ensure(self, key: str) -> dict:
        """归档目标池当前配置（指纹去重，无变化自动跳过）。

        编辑界面三时机的通用入口：进入时（原生配置「操作前原始态」）、
        退出时（MAS 侧配置终态）、运行前。返回 ``{"created", "time"}``。
        """

        target = self.get_target(key)
        if target.snapshot is None:
            raise ValueError(f"目标「{key}」不支持按需归档")
        return await target.snapshot()
