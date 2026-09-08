#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2024-2025 DLmaster361
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


"""历史游戏签到通知兼容入口。"""

from app.core.notify import (
    DispatchResult,
    dispatch_task_report,
)
from app.core.ws import Publisher
from app.utils.logger import get_logger

from .community_notify import (
    append_task_community_summary,
    detect_community_notification_format,
    dispatch_community_notification,
    format_community_notification,
    format_community_task_summary,
    get_task_community_summary,
    mark_task_community_summary_consumed,
)

logger = get_logger("游戏社区通知兼容入口")

format_game_sign_notification = format_community_notification
format_game_sign_task_summary = format_community_task_summary
get_task_game_sign_summary = get_task_community_summary
mark_task_game_sign_summary_consumed = mark_task_community_summary_consumed
append_task_game_sign_summary = append_task_community_summary
push_game_sign_notification = dispatch_community_notification


def finalize_task_game_sign_notification(
    task_info: object,
    has_summary: bool,
    result: DispatchResult,
) -> None:
    """记录部分失败，并在汇总送达全部渠道后消费签到汇总。"""

    if result.failed:
        logger.warning(f"推送代理结果部分失败: {'、'.join(result.failed)}")
    if not has_summary:
        return
    # 渠道级投递状态由 dispatch_task_report 写入:
    # 零实际渠道时 delivered 为空, 不会误标为已送达。
    if getattr(task_info, "game_sign_summary_delivered", ()) and not getattr(
        task_info, "game_sign_summary_pending", ()
    ):
        mark_task_game_sign_summary_consumed(task_info)


__all__ = [
    "Publisher",
    "append_task_game_sign_summary",
    "detect_community_notification_format",
    "dispatch_task_report",
    "finalize_task_game_sign_notification",
    "format_game_sign_notification",
    "format_game_sign_task_summary",
    "get_task_game_sign_summary",
    "mark_task_game_sign_summary_consumed",
    "push_game_sign_notification",
]
