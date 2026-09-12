#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
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

"""BAAH 配置文件读写与关键项托管。

BAAH 的用户配置是 ``BAAH_CONFIGS/<名字>.json`` 的**扁平 JSON**（没有嵌套分组），
软件配置单独放在 ``DATA/CONFIGS/software_config.json``。运行前必须把若干关键项
改成托管取值，运行结束后恢复用户原值。

写盘必须自校验：BAAH 读取配置时会吞掉所有异常并退回空配置，语法错误或带 BOM
的文件不会报错，而是静默按默认值运行。
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.utils import get_logger

logger = get_logger("BAAH 配置托管")

## 用户配置中需要托管的项
##
## 运行结束后自动退出：BAAH 默认停在 input() 等待回车，进程永不结束，会让本软件
## 误判为脚本卡死并反复重启；失败重试与通知同样收归本软件统一负责。
MANAGED_USER_VALUES: dict[str, Any] = {
    ## 运行结束后自动关闭 BAAH
    "CLOSE_BAAH_FINISH": True,
    ## 发生错误后也自动关闭 BAAH
    "CLOSE_BAAH_ERROR": True,
    ## 模拟器与游戏的启停由本软件编排，避免 BAAH 关掉仍需复用的实例
    "CLOSE_EMULATOR_FINISH": False,
    "CLOSE_EMULATOR_ERROR": False,
    "CLOSE_GAME_FINISH": False,
    "CLOSE_GAME_ERROR": False,
    ## 脚本运行报错后自动重新运行脚本的次数
    "RETRY_WHEN_ERROR": 0,
    ## 正常运行结束与错误时的通知改由本软件发送
    "NOTI_WHEN_SUCCESS": False,
    "NOTI_WHEN_ERROR": False,
}

## 软件配置中需要托管的项
##
## BAAH 默认不把日志写进文件，而任务报告的任务节点依赖日志文件采集。
MANAGED_SOFTWARE_VALUES: dict[str, Any] = {
    "SAVE_LOG_TO_FILE": True,
}

## 用户配置目录名（BAAH 程序目录下）
CONFIG_DIR_NAME = "BAAH_CONFIGS"
## 软件配置相对路径（BAAH 程序目录下）
SOFTWARE_CONFIG_RELATIVE = Path("DATA") / "CONFIGS" / "software_config.json"
## 日志目录相对路径（BAAH 程序目录下）
LOG_DIR_RELATIVE = Path("DATA") / "LOGS"


@dataclass
class ManagedConfigBackup:
    """托管前的配置快照，用于运行结束后恢复原值。"""

    ## 用户配置文件路径
    user_config_path: Path
    ## 用户配置在托管前的完整内容
    user_config: dict[str, Any] = field(default_factory=dict)
    ## 用户配置在托管前是否存在（不存在时恢复阶段应删除）
    user_config_existed: bool = False
    ## 软件配置文件路径，未托管时为 None
    software_config_path: Path | None = None
    ## 软件配置在托管前的完整内容
    software_config: dict[str, Any] = field(default_factory=dict)
    ## 软件配置在托管前是否存在
    software_config_existed: bool = False
    ## 是否真的执行过托管写入
    applied: bool = False


def read_json(path: Path) -> dict[str, Any]:
    """读取 JSON 配置。

    容忍带 BOM 的文件；文件不存在、为空或内容损坏时返回空字典，
    与 BAAH 自身"读不出来就全用默认值"的行为保持一致。

    Args:
        path: 配置文件路径。

    Returns:
        dict[str, Any]: 解析出的配置内容。
    """

    try:
        content: Any = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
        logger.warning(f"读取 BAAH 配置失败, 按空配置处理: {path} ({e})")
        return {}

    if not isinstance(content, dict):
        logger.warning(f"BAAH 配置不是键值对象, 按空配置处理: {path}")
        return {}

    return content


def write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写入 JSON 配置。

    写入使用不带 BOM 的 UTF-8，并先做一次解析自校验，再以临时文件替换目标文件。

    Args:
        path: 配置文件路径。
        data: 要写入的配置内容。
    """

    text = json.dumps(data, indent=4, ensure_ascii=False)
    ## 自校验：BAAH 不会为损坏的配置报错，落盘内容必须保证可解析
    json.loads(text)

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    os.replace(tmp_path, path)


def resolve_config_name(config_name: str) -> str:
    """校验并规范化用户填写的 BAAH 配置名。

    Args:
        config_name: 用户在界面上填写的配置名，可带 ``.json`` 后缀。

    Returns:
        str: 规范化后的配置名（不含后缀）。

    Raises:
        ValueError: 配置名为空或包含路径分隔符。
    """

    name = config_name.strip()
    if name.lower().endswith(".json"):
        name = name[: -len(".json")]
    name = name.strip()
    if not name:
        raise ValueError("未填写 BAAH 配置文件名")
    if Path(name).name != name or name in {".", ".."}:
        raise ValueError(f"BAAH 配置名不合法: {config_name}")
    return name


def resolve_user_config_path(config_dir: Path, config_name: str) -> Path:
    """把配置名解析为 BAAH 用户配置文件路径。

    Args:
        config_dir: BAAH 配置目录。
        config_name: 用户填写的配置名。

    Returns:
        Path: 配置文件路径。
    """

    return config_dir / f"{resolve_config_name(config_name)}.json"


def resolve_config_dir(root_path: Path, configured: str) -> Path:
    """解析 BAAH 配置目录，留空时回落到程序目录下的默认位置。

    Args:
        root_path: BAAH 程序目录。
        configured: 配置中填写的配置目录。

    Returns:
        Path: 配置目录路径。
    """

    if configured.strip():
        return Path(configured)
    return root_path / CONFIG_DIR_NAME


def resolve_log_dir(root_path: Path, configured: str) -> Path:
    """解析 BAAH 日志目录，留空时回落到程序目录下的默认位置。

    Args:
        root_path: BAAH 程序目录。
        configured: 配置中填写的日志目录。

    Returns:
        Path: 日志目录路径。
    """

    if configured.strip():
        return Path(configured)
    return root_path / LOG_DIR_RELATIVE


def apply_managed_config(
    user_config_path: Path,
    software_config_path: Path | None,
) -> ManagedConfigBackup:
    """写入托管项并返回恢复所需的快照。

    Args:
        user_config_path: BAAH 用户配置文件路径。
        software_config_path: BAAH 软件配置文件路径，None 表示不托管软件配置。

    Returns:
        ManagedConfigBackup: 运行结束后交回 ``restore_managed_config`` 的快照。
    """

    backup = ManagedConfigBackup(user_config_path=user_config_path)

    backup.user_config_existed = user_config_path.exists()
    user_config = read_json(user_config_path)
    backup.user_config = dict(user_config)

    changed = False
    for key, value in MANAGED_USER_VALUES.items():
        if user_config.get(key) != value:
            user_config[key] = value
            changed = True

    if changed:
        write_json(user_config_path, user_config)
        logger.info(f"已写入 BAAH 托管配置项: {user_config_path}")

    if software_config_path is not None:
        backup.software_config_path = software_config_path
        backup.software_config_existed = software_config_path.exists()
        software_config = read_json(software_config_path)
        backup.software_config = dict(software_config)

        software_changed = False
        for key, value in MANAGED_SOFTWARE_VALUES.items():
            if software_config.get(key) != value:
                software_config[key] = value
                software_changed = True

        if software_changed:
            write_json(software_config_path, software_config)
            logger.info(f"已写入 BAAH 托管软件配置项: {software_config_path}")

    backup.applied = True
    return backup


def restore_managed_config(backup: ManagedConfigBackup) -> None:
    """把托管项恢复为运行前的取值。

    每步独立容错：恢复失败只记录日志，不向调用方抛出，避免影响任务收尾。

    Args:
        backup: ``apply_managed_config`` 返回的快照。
    """

    if not backup.applied:
        return

    try:
        if backup.user_config_existed:
            write_json(backup.user_config_path, backup.user_config)
        elif backup.user_config_path.exists():
            ## 配置文件是本次运行期间新建的，恢复阶段删除
            backup.user_config_path.unlink()
    except Exception as e:
        logger.opt(exception=True).warning(f"恢复 BAAH 用户配置失败: {e}")

    software_config_path = backup.software_config_path
    if software_config_path is None:
        return

    try:
        if backup.software_config_existed:
            write_json(software_config_path, backup.software_config)
        elif software_config_path.exists():
            software_config_path.unlink()
    except Exception as e:
        logger.opt(exception=True).warning(f"恢复 BAAH 软件配置失败: {e}")


def latest_log_file(log_dir: Path, not_before: float) -> Path | None:
    """返回日志目录内不早于指定时间的最新 BAAH 日志文件。

    BAAH 每次运行都会新建 ``log_<时间戳>.txt``，因此按启动时刻过滤即可锁定本次日志。

    Args:
        log_dir: BAAH 日志目录。
        not_before: 起始时间戳（``time.time()`` 语义），早于它的日志文件会被忽略。

    Returns:
        Path | None: 本次运行的日志文件路径，未产生时为 None。
    """

    if not log_dir.is_dir():
        return None

    try:
        candidates = [
            path
            for path in log_dir.glob("log_*.txt")
            if path.stat().st_mtime >= not_before
        ]
    except OSError as e:
        logger.warning(f"扫描 BAAH 日志目录失败: {e}")
        return None

    if not candidates:
        return None

    return max(candidates, key=lambda path: path.stat().st_mtime)
