#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team
#
#   This file is part of AUTO-MAS.
#
#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

import asyncio
import shutil
from pathlib import Path

from app.utils import get_logger

logger = get_logger("OK-NTE配置替换")


async def replace_config_dir(
    src: Path,
    dst: Path,
    *,
    retries: int = 5,
    delay: float = 0.5,
) -> None:
    """用 ``src`` 的内容整体替换目录 ``dst``。

    先把内容拷进同级的 ``dst.tmp``，再尝试删掉 ``dst`` 并把 ``dst.tmp`` 改名换上，
    这样任务期新增的多余文件不会残留。

    ``dst`` 被占用而删不掉时（ok-nte 刚被结束、Windows 尚未释放句柄），退回
    「就地覆盖」：把备份内容直接盖回 ``dst``。宁可留下几个多余文件，也不让用户的
    配置目录停在半删状态。

    这样写是因为原来的
    ``shutil.rmtree(dst, ignore_errors=True)`` + ``tmp.rename(dst)``
    会把删不掉的文件留下、又不报错，接着 ``rename`` 到一个仍然存在的目录上，
    在 Windows 上必然抛 ``WinError 5``——最终配置既没删干净，备份也没还原回去。

    Args:
        src: 内容来源目录。
        dst: 待替换的目标目录。
        retries: 删除 ``dst`` 的尝试次数，用于等待句柄释放。
        delay: 两次尝试之间的等待秒数。
    """

    tmp_dst = dst.with_name(dst.name + ".tmp")
    shutil.rmtree(tmp_dst, ignore_errors=True)
    shutil.copytree(src, tmp_dst, dirs_exist_ok=True)

    last_error: OSError | None = None
    for attempt in range(retries):
        if not dst.exists():
            last_error = None
            break
        try:
            shutil.rmtree(dst)
            last_error = None
            break
        except OSError as e:
            last_error = e
            if attempt < retries - 1:
                await asyncio.sleep(delay)

    if last_error is not None:
        # 删不干净: rmtree 可能已经删掉了一部分, 就地覆盖把它们补回来
        logger.warning(f"配置目录被占用，改为就地覆盖还原: {dst} ({last_error})")
        shutil.copytree(tmp_dst, dst, dirs_exist_ok=True)
        shutil.rmtree(tmp_dst, ignore_errors=True)
        return

    tmp_dst.rename(dst)
