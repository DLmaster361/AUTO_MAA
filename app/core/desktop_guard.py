"""无人值守时保证桌面上有真实的显示输出。

所有真实输出都断开时，Windows 不会让桌面消失，而是保留一块占位的**幻影屏**。它照旧
上报一个分辨率（实测甚至会继承上一块屏的模式），`EnumDisplayMonitors` 看起来一切正常，
但那块屏背后没有任何输出：游戏能否正常渲染、截图链路是否可靠都没有保证，DXGI 桌面复制
在这种屏上尤其容易出问题。

冷启动时更糟——没有输出的情况下 Windows 会以一个很小的安全分辨率起来，被托管的 PC 端
游戏窗口跟着被压小，脚本侧的分辨率闸门把整轮任务打掉；游戏还会把这个坏尺寸记进自己的
配置，而自动运行每轮只活几十秒，游戏来不及纠正自己，于是坏值一直留着，之后每天都在
同一处失败。

所以判据不是「桌面够不够大」而是「有没有真实输出」：前者要挑阈值，而且幻影屏报的尺寸
本来就不可信；后者是个二值事实。

设计取舍：

- **整轮开一次、结束拆一次**，不是每个脚本或每个用户一次：每次插拔都是一次桌面拓扑
  变更，本身就是风险源（会移动窗口）。
- **进程被强杀会留下孤儿屏，必须主动清理。** 上游文档称停止心跳约 1 秒后虚拟屏会自动
  拔掉，实测不成立（杀掉进程 6 秒后屏仍在）。因此挂屏时把 index 记进状态文件，下次进入
  时若记录还在、而记录里的进程已经死了，就先把那块孤儿拆掉。只拆自己记过的 index——
  同一个驱动可能同时被 Parsec 本体或别的程序使用。
- **只在没有任何真实输出时才插**，显示器正常时绝不凭空多挂一块。实测无头时挂上虚拟屏，
  幻影屏是**被替换**而不是并存，所以桌面上仍然只有一块屏，没有多屏歧义。
- **插完立刻重验**，不满足就拆掉——驱动可能因为被显卡驱动更新搞坏、或与其它虚拟显示
  驱动冲突而「插上了但没生效」。
- 任何一步失败都只记日志、照常往下跑：这一层是尽力而为的改善项，不该反过来把本来
  能跑的任务打掉。
"""

import asyncio
import json
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from app.core import Config
from app.utils import get_logger
from app.utils.platform import IS_WINDOWS

logger = get_logger("桌面保障")

# 目标客户区。取脚本侧常见的最低要求：够放下一个 1280x720 的窗口就算够用。
DESKTOP_MIN_CLIENT = (1280, 720)
# 记账文件。落在受保护的 data/ 下，和 MaaFW job 文件同级。
STATE_FILE = Path("data") / "virtual_display.json"


def _write_state(index: int) -> None:
    """记下「本进程挂了哪块屏」。进程被强杀时靠它清理孤儿。"""

    with suppress(Exception):
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(
            json.dumps({"index": index, "pid": os.getpid()}, ensure_ascii=False),
            encoding="utf-8",
        )


def _clear_state() -> None:
    with suppress(Exception):
        STATE_FILE.unlink(missing_ok=True)


def _pid_alive(pid: int) -> bool:
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        # 判断不了就当它还活着：宁可留下孤儿，也不要误拆别人的屏。
        return True


def cleanup_orphan_display() -> None:
    """清理上一次进程留下的虚拟屏。

    只拆自己记过的 index，且只在记录里的进程确实已经死了的时候拆——同一个驱动可能同时
    被 Parsec 本体或别的程序使用，按 index 乱拆会拆掉别人的屏。
    """

    try:
        raw = STATE_FILE.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except Exception as exc:
        logger.warning(f"读取虚拟显示器记账文件失败: {exc}")
        return

    try:
        state = json.loads(raw)
        index = int(state["index"])
        pid = int(state["pid"])
    except Exception:
        logger.warning("虚拟显示器记账文件无法解析，已丢弃")
        _clear_state()
        return

    if pid == os.getpid() or _pid_alive(pid):
        # 还活着说明不是孤儿——可能是同一台机器上另一个 MAS 实例正在用。
        return

    from app.utils.platform.vdd import remove_display_index

    if remove_display_index(index):
        logger.info(f"已清理上次遗留的虚拟显示器（index={index}, pid={pid}）")
    _clear_state()


def _has_real_output() -> bool:
    """桌面上有没有真实输出。查不到信息时按「有」处理，宁可不插屏也不乱动拓扑。"""

    from app.utils.platform.display import has_real_display

    try:
        return has_real_display()
    except Exception as exc:
        logger.warning(f"查询显示输出失败，按有真实输出处理: {exc}")
        return True


def _desktop_has_room() -> bool:
    """插屏之后用：新挂的屏放不放得下目标窗口。"""

    from app.utils.platform.display import find_host_monitor

    try:
        return find_host_monitor(*DESKTOP_MIN_CLIENT) is not None
    except Exception as exc:
        logger.warning(f"查询显示器失败，按可用处理: {exc}")
        return True


def _describe() -> str:
    from app.utils.platform.display import describe_monitors

    try:
        return describe_monitors()
    except Exception as exc:
        return f"（读取失败: {exc}）"


def parse_mode(text: str) -> tuple[int, int, int]:
    """把配置里的 `1920x1080@60` 解析成 (宽, 高, 刷新率)。

    解析失败时回落到默认模式而不是抛错：这一层不该因为一个配置字符串把任务打掉。
    """

    from app.utils.platform.vdd import DEFAULT_VDD_MODE

    try:
        size, _, refresh = text.partition("@")
        width, _, height = size.partition("x")
        return int(width), int(height), int(refresh)
    except (AttributeError, ValueError):
        logger.warning(f"虚拟显示器模式配置无法解析，按默认处理: {text!r}")
        return DEFAULT_VDD_MODE


@asynccontextmanager
async def ensure_desktop_available():
    """需要时挂一块虚拟显示器，退出时拆掉。不需要时是彻底的 no-op。"""

    if not IS_WINDOWS:
        yield None
        return

    # 清理孤儿放在开关判断**之前**：用户在崩溃之后把开关关掉，那块没人认领的屏同样
    # 得能被清掉。清理只动自己记账过、且记录进程已死的 index，开关关着做这件事是安全的。
    await asyncio.to_thread(cleanup_orphan_display)

    if not Config.get("Display", "IfEnableVirtualDisplay"):
        yield None
        return

    # 孤儿清掉之后再判断——否则孤儿本身就是「真实输出」，判据会一路放行。
    if await asyncio.to_thread(_has_real_output):
        yield None
        return

    from app.utils.platform.vdd import VddStatus, VirtualDisplay, probe

    detail = await asyncio.to_thread(_describe)
    logger.warning(f"桌面上没有任何真实显示输出，当前只有系统占位的幻影屏: {detail}")

    result = await asyncio.to_thread(probe)
    if result.status is not VddStatus.OK:
        logger.warning(
            f"无法挂载虚拟显示器（{_probe_hint(result)}）。"
            "没有真实显示输出时 Windows 只保留一块占位的幻影屏，游戏渲染与截图都可能不可靠；"
            "请接回显示器、使用显示器假负载，或安装 Parsec 虚拟显示驱动"
        )
        yield None
        return

    mode = parse_mode(Config.get("Display", "VirtualDisplayMode"))
    display = VirtualDisplay(mode=mode)
    try:
        await asyncio.to_thread(display.__enter__)
    except Exception as exc:
        logger.warning(f"挂载虚拟显示器失败，按原样继续: {exc}")
        yield None
        return

    if display.index is not None:
        # 记账必须在挂上之后立刻写：进程随时可能被强杀，写晚了这块屏就成了没人认领的孤儿。
        await asyncio.to_thread(_write_state, display.index)

    try:
        effective = await asyncio.to_thread(
            _has_real_output
        ) and await asyncio.to_thread(_desktop_has_room)
        if not effective:
            # 调得动不等于有效果：这一步才是「检测通过」的真正判据。
            logger.warning(
                f"虚拟显示器已挂载但桌面仍不满足要求，已拆除: {await asyncio.to_thread(_describe)}"
            )
            await asyncio.to_thread(display.close)
            _clear_state()
            yield None
            return
        if display.applied_mode != mode:
            # 分辨率没切成不致命（默认模式本来就是 1920x1080@60），但必须说出来，
            # 否则用户选了 30Hz 却静默跑在 60Hz 上。
            logger.warning(
                f"虚拟显示器未能切换到 {mode[0]}x{mode[1]}@{mode[2]}，"
                f"实际为 {display.applied_mode}"
            )
        logger.info(f"已挂载虚拟显示器: {await asyncio.to_thread(_describe)}")
        yield display
    finally:
        if display.active:
            await asyncio.to_thread(display.close)
            logger.info("已拆除虚拟显示器")
        _clear_state()


def _probe_hint(result) -> str:
    from app.utils.platform.vdd import VddStatus

    if result.status is VddStatus.NOT_INSTALLED:
        return "未安装 Parsec 虚拟显示驱动"
    if result.status is VddStatus.ACCESS_DENIED:
        # 与「未安装」是两种完全不同的故障，提示必须分开。
        return "驱动已安装但当前权限打不开设备"
    return f"驱动异常: {result.detail}"


async def probe_virtual_display_driver():
    """只跑前两段（装没装 / 能不能调），不改变桌面拓扑。

    供设置页在打开时自动调用，用来决定开关能不能打开。实测一次 0.2ms，所以**不缓存也
    不持久化**：存下来的状态只会变陈旧（驱动可能被卸载、被显卡驱动更新搞坏、或者配置
    被同步到另一台机器），而实时问一次永远是对的。
    """

    from app.models.schema import (
        VirtualDisplayCheckOut,
        VirtualDisplayCheckResultItem,
    )

    def item(stage: str, passed: bool, message: str):
        return VirtualDisplayCheckResultItem(
            stage=stage, passed=passed, message=message
        )

    if not IS_WINDOWS:
        return VirtualDisplayCheckOut(
            message="虚拟显示器仅支持 Windows",
            results=[item("installed", False, "当前系统不支持")],
        )

    from app.utils.platform.vdd import VddStatus, probe

    result = await asyncio.to_thread(probe)
    if result.status is VddStatus.NOT_INSTALLED:
        return VirtualDisplayCheckOut(
            message="未安装 Parsec 虚拟显示驱动",
            results=[item("installed", False, "未找到驱动，请先安装")],
        )
    if result.status is not VddStatus.OK:
        return VirtualDisplayCheckOut(
            message=_probe_hint(result),
            results=[
                item("installed", True, "驱动已安装"),
                item("openable", False, _probe_hint(result)),
            ],
        )
    return VirtualDisplayCheckOut(
        message="驱动可用",
        driverVersion=result.version,
        results=[
            item("installed", True, "驱动已安装"),
            item("openable", True, f"握手成功，驱动版本 0.{result.version}"),
        ],
    )


async def check_virtual_display_driver():
    """设置页「检测」按钮的三段式检查。

    第三段会真的插一块屏再拆掉，改变桌面拓扑，所以只在用户手动触发时跑。
    检测结果**不做持久化**：驱动可能被卸载、或被显卡驱动更新搞坏，一个永久的
    「检测通过」标记就是下一个假信号来源。运行时每次重新探测前两段，第三段由
    实际挂载后的重验代替。
    """

    from app.models.schema import (
        VirtualDisplayCheckOut,
        VirtualDisplayCheckResultItem,
    )

    def item(stage: str, passed: bool, message: str):
        return VirtualDisplayCheckResultItem(
            stage=stage, passed=passed, message=message
        )

    if not IS_WINDOWS:
        return VirtualDisplayCheckOut(
            message="虚拟显示器仅支持 Windows",
            results=[item("installed", False, "当前系统不支持")],
        )

    from app.utils.platform.vdd import VddStatus, VirtualDisplay, probe

    result = await asyncio.to_thread(probe)
    monitors = await asyncio.to_thread(_describe)

    if result.status is VddStatus.NOT_INSTALLED:
        return VirtualDisplayCheckOut(
            message="未安装 Parsec 虚拟显示驱动",
            monitors=monitors,
            results=[item("installed", False, "未找到驱动，请先安装后再检测")],
        )
    if result.status is not VddStatus.OK:
        return VirtualDisplayCheckOut(
            message=_probe_hint(result),
            monitors=monitors,
            results=[
                item("installed", True, "驱动已安装"),
                item("openable", False, _probe_hint(result)),
            ],
        )

    results = [
        item("installed", True, "驱动已安装"),
        item("openable", True, f"握手成功，驱动版本 0.{result.version}"),
    ]

    mode = parse_mode(Config.get("Display", "VirtualDisplayMode"))
    display = VirtualDisplay(mode=mode)
    try:
        await asyncio.to_thread(display.__enter__)
    except Exception as exc:
        results.append(item("effective", False, f"挂载失败: {exc}"))
        return VirtualDisplayCheckOut(
            message="驱动可调用，但挂载虚拟显示器失败",
            driverVersion=result.version,
            monitors=monitors,
            results=results,
        )

    try:
        applied = display.applied_mode
        monitors = await asyncio.to_thread(_describe)
        if applied == mode:
            results.append(
                item(
                    "effective",
                    True,
                    f"已挂载 {applied[0]}x{applied[1]}@{applied[2]} 并成功拆除",
                )
            )
            message = "检测通过"
        else:
            results.append(
                item(
                    "effective",
                    False,
                    f"挂载成功但模式为 {applied}，与所选的 "
                    f"{mode[0]}x{mode[1]}@{mode[2]} 不一致",
                )
            )
            message = "驱动不支持所选的分辨率或刷新率，请换一档"
    finally:
        await asyncio.to_thread(display.close)

    return VirtualDisplayCheckOut(
        message=message,
        driverVersion=result.version,
        monitors=monitors,
        results=results,
    )
