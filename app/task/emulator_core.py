#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

#   Contact: DLmaster_361@163.com

"""各专项收尾环节共用的模拟器关闭动作。

MAA / M9A / BAAH / MaaEnd / SRC 的 final_task 在结束代理任务时都要关闭本次
接管的模拟器实例，原本各自内联调用，关闭失败的日志文案也各写一份。统一收敛
到本模块：只负责「关掉这次任务的模拟器」这一件事，是否要关由各专项的收尾
分支自己决定。
"""

from typing import Any

from app.utils import get_logger

logger = get_logger("模拟器管理")


async def close_emulator(owner: Any) -> None:
    """关闭 owner 接管的模拟器实例；未接管则跳过。

    Args:
        owner: 任务执行对象，需提供 emulator_manager 与 script_config。
    """

    emulator_manager = getattr(owner, "emulator_manager", None)
    if emulator_manager is None:
        return

    try:
        await emulator_manager.close(owner.script_config.get("Emulator", "Index"))
        logger.success("模拟器已关闭")
    except Exception as e:
        logger.opt(exception=True).warning(f"关闭模拟器失败: {e}")
