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

"""ZZZ-OD 配置备份归档：一条龙原生配置 / MAS 用户配置，两类独立快照。

备份时机：MAS 运行注入前、配置会话基线注入前——此时 zzz-od 尚未被 MAS
触碰，两个视角各自捕获「动手前」的状态：

- ``onedragon``：一条龙自己的原生配置 = ``config/one_dragon.yml``（实例
  注册表）+ 注册表内的原生实例目录（**排除 MAS-xxx 槽**）。防止 MAS 的
  注入/合成视图等机制意外破坏原生配置后可完整找回；恢复只写回这些文件，
  MAS 槽目录永不触碰。
- ``mas``：MAS 用户配置 = 绑定槽（MAS-xxx）目录整份快照——含本页注入的
  账号/任务编排与用户在原生 GUI 里维护的配队等；恢复到槽并回填本页字段。

两类各自指纹去重（内容无变化跳过归档）、各自保留最近 :data:`KEEP_COUNT`
份。
"""

import shutil
from datetime import datetime
from pathlib import Path

from app.utils import get_logger

from .zzz_od_config import (
    _one_dragon_file,
    instance_dir,
    list_instances,
    restore_instance_view,
)

logger = get_logger("ZZZ-OD 配置备份")

KEEP_COUNT = 10
"""每类保留的归档份数（超出清理最旧的）"""

_TIME_FORMAT = "%Y%m%d-%H%M%S"

MAS_SLOT_PREFIX = "MAS-"
"""MAS 用户槽在注册表中的实例名前缀"""


def backup_root(script_id: str) -> Path:
    """某脚本的备份归档根目录：``data/{script_id}/ZzzOdBackups``。"""

    return Path.cwd() / "data" / script_id / "ZzzOdBackups"


def onedragon_backup_root(script_id: str) -> Path:
    """一条龙原生配置的归档目录：``.../ZzzOdBackups/onedragon``。"""

    return backup_root(script_id) / "onedragon"


def mas_backup_root(script_id: str, slot_idx: int) -> Path:
    """MAS 用户槽的归档目录：``.../ZzzOdBackups/mas/{slot:02d}``。"""

    return backup_root(script_id) / "mas" / f"{int(slot_idx):02d}"


def _list_times(root: Path) -> list[str]:
    """归档目录下全部时间戳，按时间倒序（目录名即时间戳）。"""

    if not root.is_dir():
        return []
    return sorted((p.name for p in root.iterdir() if p.is_dir()), reverse=True)


def _hash_files(files: dict[str, Path]) -> str:
    """文件集指纹：相对键 + 内容的组合哈希（文件集合变化也算变化）。"""

    import hashlib

    digest = hashlib.sha256()
    for rel in sorted(files):
        path = files[rel]
        digest.update(f"f:{rel}:{path.stat().st_size}:".encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _onedragon_files(root: Path) -> dict[str, Path]:
    """当前一条龙原生配置的文件集：one_dragon.yml + 注册表内原生实例目录。"""

    files: dict[str, Path] = {}
    od_file = _one_dragon_file(root)
    if od_file.is_file():
        files["one_dragon.yml"] = od_file
    for item in list_instances(root):
        if str(item.get("name") or "").startswith(MAS_SLOT_PREFIX):
            continue  # MAS 用户槽不属于一条龙原生配置
        idx = int(item.get("idx", -1))
        idx_dir = instance_dir(root, idx)
        if not idx_dir.is_dir():
            continue
        for path in sorted(idx_dir.rglob("*")):
            if path.is_file():
                rel = path.relative_to(idx_dir).as_posix()
                files[f"{idx}/{rel}"] = path
    return files


def _backup_onedragon_files(backup_dir: Path) -> dict[str, Path]:
    """备份目录内的文件集（结构与当前侧对称：one_dragon.yml + {idx}/...）。"""

    files: dict[str, Path] = {}
    for path in sorted(backup_dir.rglob("*")):
        if path.is_file():
            files[path.relative_to(backup_dir).as_posix()] = path
    return files


# ══════════════════ 一条龙原生配置 ══════════════════


def archive_onedragon_backup(script_id: str, root: Path, force: bool = False) -> Path | None:
    """归档一条龙原生配置（one_dragon.yml + 原生实例目录，排除 MAS 槽）。

    内容与最近一份备份完全一致时跳过（``force=True`` 强制归档，用于恢复前
    存底——让「恢复前的配置」在列表里有明确的时间戳条目）；跳过返回
    ``None``，否则返回归档目录。
    """

    files = _onedragon_files(root)
    if not files:
        raise ValueError(f"一条龙原生配置不存在: {root}")

    dest_root = onedragon_backup_root(script_id)
    times = _list_times(dest_root)
    if not force and times:
        try:
            latest = _backup_onedragon_files(dest_root / times[0])
            if _hash_files(latest) == _hash_files(files):
                logger.info("一条龙原生配置无变化，跳过归档")
                return None
        except OSError as e:
            logger.warning(f"一条龙原生配置指纹对比失败，照常归档: {e}")

    dest = dest_root / datetime.now().strftime(_TIME_FORMAT)
    serial = 1
    while dest.exists():  # 同秒内多次备份（理论罕见）顺延序号
        serial += 1
        dest = dest_root / f"{datetime.now().strftime(_TIME_FORMAT)}-{serial}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    for rel, path in files.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)

    for old in _list_times(dest_root)[KEEP_COUNT:]:
        shutil.rmtree(dest_root / old, ignore_errors=True)

    logger.info(f"一条龙原生配置已归档: {dest.name} ({len(files)} 个文件)")
    return dest


def list_onedragon_backups(script_id: str) -> list[str]:
    """一条龙原生配置全部归档时间戳（倒序，最新在前）。"""

    return _list_times(onedragon_backup_root(script_id))


def get_onedragon_backup_dir(script_id: str, ts: str) -> Path | None:
    """取指定时间戳的一条龙归档目录；不存在返回 None。"""

    dest = onedragon_backup_root(script_id) / str(ts)
    return dest if dest.is_dir() else None


def restore_onedragon_backup(script_id: str, ts: str, root: Path) -> None:
    """把归档恢复到一条龙原生位置（恢复前自动归档当前，误恢复可找回）。

    只写回备份中存在的文件（one_dragon.yml + 对应实例目录）；MAS 槽目录
    与备份外的实例目录一律不触碰。恢复前先清残留合成视图，防止 sidecar
    自愈把刚恢复的注册表盖回旧内容。
    """

    backup_dir = get_onedragon_backup_dir(script_id, ts)
    if backup_dir is None:
        raise ValueError(f"备份不存在: {ts}")
    backup_files = _backup_onedragon_files(backup_dir)
    if not backup_files:
        raise ValueError(f"备份内容为空: {ts}")

    # 先清残留合成视图（幂等；无 sidecar 即 no-op）
    restore_instance_view(root)
    # 恢复前强制归档当前原生配置——「恢复前的配置」在列表里有明确的时间戳条目
    archive_onedragon_backup(script_id, root, force=True)

    od_file = backup_files.get("one_dragon.yml")
    if od_file is not None:
        shutil.copyfile(od_file, _one_dragon_file(root))

    # 备份中的实例目录逐个替换（MAS 槽不在备份内，天然不受影响）
    idx_dirs = sorted(
        {rel.split("/", 1)[0] for rel in backup_files if "/" in rel},
    )
    for idx_dir_name in idx_dirs:
        idx = int(idx_dir_name)
        target = instance_dir(root, idx)
        shutil.rmtree(target, ignore_errors=True)
        shutil.copytree(backup_dir / idx_dir_name, target)

    logger.info(
        f"一条龙原生配置已恢复备份 {ts} (实例目录 {len(idx_dirs)} 个)"
    )


# ══════════════════ MAS 用户配置（绑定槽） ══════════════════


def archive_mas_backup(
    script_id: str, slot_idx: int, slot_dir: Path, force: bool = False
) -> Path | None:
    """归档 MAS 用户槽目录整份（覆盖式加时间戳）。

    内容与最近一份备份完全一致时跳过（``force=True`` 强制归档，用于恢复前
    存底）；跳过返回 ``None``，否则返回归档目录。
    """

    slot_dir = Path(slot_dir)
    if not slot_dir.is_dir():
        raise ValueError(f"备份来源不存在: {slot_dir}")

    dest_root = mas_backup_root(script_id, slot_idx)
    times = _list_times(dest_root)
    if not force and times:
        try:
            if _hash_files(_dir_files(dest_root / times[0])) == _hash_files(
                _dir_files(slot_dir)
            ):
                logger.info(f"槽 {slot_idx:02d} MAS 配置无变化，跳过归档")
                return None
        except OSError as e:
            logger.warning(f"槽 {slot_idx:02d} 备份指纹对比失败，照常归档: {e}")

    dest = dest_root / datetime.now().strftime(_TIME_FORMAT)
    serial = 1
    while dest.exists():  # 同秒内多次备份（理论罕见）顺延序号
        serial += 1
        dest = dest_root / f"{datetime.now().strftime(_TIME_FORMAT)}-{serial}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(slot_dir, dest)

    for old in _list_times(dest_root)[KEEP_COUNT:]:
        shutil.rmtree(dest_root / old, ignore_errors=True)

    logger.info(f"槽 {slot_idx:02d} MAS 配置已归档: {dest.name}")
    return dest


def _dir_files(source: Path) -> dict[str, Path]:
    """目录内全部文件集（相对路径 → 绝对路径）。"""

    files: dict[str, Path] = {}
    for path in sorted(source.rglob("*")):
        if path.is_file():
            files[path.relative_to(source).as_posix()] = path
    return files


def list_mas_backups(script_id: str, slot_idx: int) -> list[str]:
    """MAS 用户槽全部归档时间戳（倒序，最新在前）。"""

    return _list_times(mas_backup_root(script_id, slot_idx))


def get_mas_backup_dir(script_id: str, slot_idx: int, ts: str) -> Path | None:
    """取指定时间戳的 MAS 归档目录；不存在返回 None。"""

    dest = mas_backup_root(script_id, slot_idx) / str(ts)
    return dest if dest.is_dir() else None


def restore_mas_backup(script_id: str, slot_idx: int, ts: str, slot_dir: Path) -> None:
    """把归档恢复到 MAS 用户槽目录（恢复前自动归档当前，误恢复可找回）。"""

    backup_dir = get_mas_backup_dir(script_id, slot_idx, ts)
    if backup_dir is None:
        raise ValueError(f"备份不存在: {ts}")
    if Path(slot_dir).is_dir():
        # 恢复前强制归档当前内容——「恢复前的配置」在列表里有明确的时间戳条目
        archive_mas_backup(script_id, slot_idx, Path(slot_dir), force=True)
    shutil.rmtree(Path(slot_dir), ignore_errors=True)
    shutil.copytree(backup_dir, Path(slot_dir))
