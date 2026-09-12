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

"""雷电 VBox 服务卡住的识别与自愈。

**故障形态**（2026-09-12 生产实测）。雷电 9 / 14 共用 ``C:\\Program Files\\ldplayer9box\\``
里的 VirtualBox 运行时，其中 ``Ld9BoxSVC.exe`` 是整机唯一的 COM 服务，每台实例的虚拟机
``Ld9BoxHeadless.exe`` 都由它拉起。它卡住之后，**已经在跑的实例不受影响，新实例却一台都
起不来**：``ldconsole launch`` 正常返回，播放器窗口也开了，``list2`` 里却一直是
``VBox pid = -1``、adb 永远看不到 ``emulator-NNNN``。更坏的一种是「Android 已启动」标志
照样置 1，MAS 以为它在线，MAA 一连就报 ADB 异常，三轮重试三轮都是同一个结果。

雷电自己的修复工具最终做的也只是重启这个服务（修复前后安装目录没有任何文件变化），
但它是纯图形程序、没有命令行开关，MAS 调不动，只能自己做同样的事。

**必须守住的一条**：``Ld9BoxSVC.exe`` 一死，它名下所有虚拟机一起死。当天的修复就把另一
台正在跑的实例打成了僵尸窗口。所以只有整机没有任何 ``Ld9BoxHeadless.exe`` 在跑时才允许
重启服务，否则宁可报错让用户自己决定。
"""

import asyncio
from dataclasses import dataclass

import psutil

from app.utils import get_logger

logger = get_logger("Emulator2 雷电 VBox 自愈")

#: 整机共用的 VBox COM 服务；杀它等于关掉所有雷电虚拟机。
VBOX_SERVICE_PROCESS = "Ld9BoxSVC.exe"
#: 每台实例一个的虚拟机进程。
VBOX_VM_PROCESS = "Ld9BoxHeadless.exe"

#: 等服务进程退出的上限。它退得很快，等不到多半是没权限杀。
_SERVICE_EXIT_TIMEOUT = 10.0


@dataclass(frozen=True)
class VmProbe:
    """一次「虚拟机到底在不在」的探测输入，全部来自 ``list2`` 和 ``adb devices``。"""

    in_android: int
    vbox_pid: int
    serial_online: bool


def vm_is_missing(probe: VmProbe) -> bool:
    """播放器窗口在、VBox 进程不在、adb 也看不到——虚拟机没起来或已经死了。

    三个条件缺一不可：

    - ``in_android == 0`` 是根本没开，不是这里要管的
    - ``vbox_pid > 0`` 说明虚拟机进程在，哪怕 adb 暂时没核上也只是还没就绪
    - adb 能核上说明虚拟机活着；``list2`` 那列在个别版本上可能不可靠，靠 adb 兜底
    """
    if probe.in_android == 0:
        return False
    if probe.vbox_pid > 0:
        return False
    return not probe.serial_online


def _processes_named(name: str) -> list[psutil.Process]:
    wanted = name.casefold()
    found = []
    for proc in psutil.process_iter(["name"]):
        try:
            if (proc.info["name"] or "").casefold() == wanted:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return found


def live_vm_pids() -> list[int]:
    """整机上还在跑的雷电虚拟机进程。不为空就绝不能重启服务。"""
    return [proc.pid for proc in _processes_named(VBOX_VM_PROCESS)]


async def restart_vbox_service() -> bool:
    """杀掉 ``Ld9BoxSVC.exe`` 并等它退出；下一次 ``launch`` 会由雷电自己重新拉起服务。

    返回是否真的杀了一个。没找到进程返回 ``False``（服务本来就没在跑，不算失败）；
    没权限杀直接抛 ``PermissionError``——调用方要把它翻译成给用户看的话。
    """
    targets = _processes_named(VBOX_SERVICE_PROCESS)
    if not targets:
        logger.info(f"{VBOX_SERVICE_PROCESS} 没有在运行，无需重启")
        return False

    for proc in targets:
        try:
            proc.kill()
        except psutil.NoSuchProcess:
            continue
        except psutil.AccessDenied as e:
            raise PermissionError(
                f"没有权限结束 {VBOX_SERVICE_PROCESS}（pid {proc.pid}）"
            ) from e

    def _wait() -> None:
        psutil.wait_procs(targets, timeout=_SERVICE_EXIT_TIMEOUT)

    await asyncio.to_thread(_wait)
    survivors = [proc.pid for proc in targets if proc.is_running()]
    if survivors:
        raise RuntimeError(f"{VBOX_SERVICE_PROCESS} 结束后仍未退出: {survivors}")
    logger.warning(
        f"已重启 {VBOX_SERVICE_PROCESS}（结束 pid {[p.pid for p in targets]}）"
    )
    return True
