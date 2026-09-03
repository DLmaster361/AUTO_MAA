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

"""任务级配置元数据与读写。

zzz-od 每个应用（任务）的配置存于 ``config/{idx:02d}/one_dragon/{app_id}.yml``
（一条龙 group_id=one_dragon），原生 GUI 以 FLYOUT 弹出设置卡片编辑
（选项硬编码在其 GUI 组件中）。MAS 侧用数据驱动的元数据表复刻**选项静态
已知**的常用任务（卡片 ⚙ 弹出下拉）；其余任务给灰色 ⚙ 引导用户进
「在一条龙内配置」。加任务 = 在 :data:`TASK_APP_FIELDS` 加一个表项。

任务卡片配置与 MAS 字段一样是**持久写绑定槽**：注入（game_account +
_group）不碰 per-app yml，恢复备份时随槽内容一起回到该时点。
"""

from pathlib import Path
from typing import Any

from app.utils.io import read_file, write_file

# 应用配置存储子目录（一条龙默认组，与 _group.yml 同目录）
_APP_GROUP_ID = "one_dragon"

# 任务配置元数据表：app_id → 字段定义（数据驱动，加任务即加表项）。
# 选项与 zzz-od 原生 GUI 组件保持一致（如 daily_signin_setting_flyout.py）。
TASK_APP_FIELDS: dict[str, list[dict[str, Any]]] = {
    "daily_signin": [
        {
            "field": "selected_sign",
            "title": "选择签到商店",
            "options": [
                {"label": "吼吼饼铺", "value": "hou_hou_bakery"},
                {"label": "卦象集录", "value": "trigrams_collection"},
                {"label": "刮刮卡", "value": "scratch_card"},
            ],
        },
    ],
}


def get_task_app_fields(app_id: str) -> list[dict[str, Any]] | None:
    """返回任务的可配置字段定义；无元数据（复杂任务）返回 None。"""

    return TASK_APP_FIELDS.get(app_id)


def app_config_path(root: Path, slot_idx: int, app_id: str) -> Path:
    """应用配置文件路径：``config/{idx:02d}/one_dragon/{app_id}.yml``。"""

    return root / "config" / f"{int(slot_idx):02d}" / _APP_GROUP_ID / f"{app_id}.yml"


def read_app_config(root: Path, slot_idx: int, app_id: str) -> dict:
    """读取应用配置（文件不存在返回空 dict，由调用方回退默认值）。"""

    return dict(read_file(app_config_path(root, slot_idx, app_id)) or {})


def write_app_config(
    root: Path, slot_idx: int, app_id: str, values: dict[str, Any]
) -> dict:
    """按 patch 更新应用配置（读-改-写，保留未知字段），返回完整配置。"""

    path = app_config_path(root, slot_idx, app_id)
    data = read_file(path) or {}
    data.update(values)
    write_file(path, data)
    return data
