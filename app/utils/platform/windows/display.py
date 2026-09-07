"""显示器几何查询。

Win32 桌面游戏任务需要知道「桌面上有没有一块屏放得下目标窗口」：物理显示器断开
时 Windows 会回落到很小的兜底分辨率，游戏窗口跟着被压小，脚本侧的分辨率闸门随后
把整轮任务全部打掉。

本模块只查询，不改动任何显示设置。DPI 感知用 `SetThreadDpiAwarenessContext` 按调用
临时切换，不去动进程级的 DPI 感知——那会影响到同进程里其它按逻辑像素工作的代码。
"""

import ctypes
from contextlib import contextmanager, suppress
from ctypes import wintypes
from dataclasses import dataclass

DEFAULT_DPI = 96
MONITORINFOF_PRIMARY = 0x00000001
MONITOR_DEFAULTTONEAREST = 0x00000002
MDT_EFFECTIVE_DPI = 0
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4
# 普通可调整大小的窗口。用它换算「客户区 -> 窗口外框」的非客户区开销。
WS_OVERLAPPEDWINDOW = 0x00CF0000


class _RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class _MONITORINFOEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", _RECT),
        ("rcWork", _RECT),
        ("dwFlags", wintypes.DWORD),
        ("szDevice", ctypes.c_wchar * 32),
    ]


_MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wintypes.BOOL,
    wintypes.HMONITOR,
    wintypes.HDC,
    ctypes.POINTER(_RECT),
    wintypes.LPARAM,
)


@dataclass(frozen=True)
class MonitorInfo:
    """一块显示器的几何信息，坐标均为物理像素。"""

    device: str
    handle: int
    bounds: tuple[int, int, int, int]
    work: tuple[int, int, int, int]
    dpi: int
    primary: bool

    @property
    def size(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return right - left, bottom - top

    @property
    def work_size(self) -> tuple[int, int]:
        """去掉任务栏之后的可用区域。窗口能不能放下要看它，不是看整块屏。"""

        left, top, right, bottom = self.work
        return right - left, bottom - top

    @property
    def scaling(self) -> float:
        return self.dpi / DEFAULT_DPI

    def describe(self) -> str:
        width, height = self.size
        work_width, work_height = self.work_size
        return (
            f"{self.device} {width}x{height}"
            f"(可用 {work_width}x{work_height})"
            f" DPI={self.dpi}({self.scaling:.2f}x)"
            f"{' 主显示器' if self.primary else ''}"
        )


# 用私有的 WinDLL 实例，不是 `_user32`：后者是进程级共享缓存，在它上面
# 声明 restype 会波及仓库里其它同样用它的模块（如 OkNte 的 launcher_start）。
_user32 = ctypes.WinDLL("user32", use_last_error=True)
_shcore = ctypes.WinDLL("shcore", use_last_error=True)


def _declare_prototypes() -> None:
    """显式声明返回类型。

    ctypes 默认 restype=c_int，会把返回句柄的函数截成 32 位。截断后的失败往往不像
    失败——比如设备枚举会表现成「一个都没有」，和「真的没有」无法区分。
    老系统上缺失的函数用 AttributeError 跳过即可。
    """

    for dll, name, restype, argtypes in (
        (_user32, "SetThreadDpiAwarenessContext", ctypes.c_void_p, [ctypes.c_void_p]),
        (
            _user32,
            "MonitorFromWindow",
            wintypes.HMONITOR,
            [wintypes.HWND, wintypes.DWORD],
        ),
        (_user32, "GetMonitorInfoW", wintypes.BOOL, None),
        (_user32, "EnumDisplayMonitors", wintypes.BOOL, None),
        (_user32, "AdjustWindowRectExForDpi", wintypes.BOOL, None),
        (_user32, "AdjustWindowRectEx", wintypes.BOOL, None),
        (_shcore, "GetDpiForMonitor", ctypes.c_long, None),
    ):
        with suppress(AttributeError, OSError):
            func = getattr(dll, name)
            func.restype = restype
            if argtypes is not None:
                func.argtypes = argtypes


_declare_prototypes()


@contextmanager
def per_monitor_dpi():
    """临时切到 per-monitor DPI 感知，保证拿到的是物理像素。

    不用进程级的 `SetProcessDpiAwareness`：那是一次性且不可逆的全局副作用，
    会影响同进程里其它按逻辑像素工作的代码。
    """

    user32 = _user32
    previous = None
    with suppress(AttributeError, OSError):
        # Windows 10 1703 以下没有这个函数，拿不到就按当前感知级别继续。
        previous = user32.SetThreadDpiAwarenessContext(
            ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
    try:
        yield
    finally:
        if previous:
            with suppress(OSError):
                user32.SetThreadDpiAwarenessContext(previous)


def _monitor_dpi(handle: int) -> int:
    dpi_x = wintypes.UINT()
    dpi_y = wintypes.UINT()
    try:
        result = _shcore.GetDpiForMonitor(
            wintypes.HMONITOR(handle),
            MDT_EFFECTIVE_DPI,
            ctypes.byref(dpi_x),
            ctypes.byref(dpi_y),
        )
    except (AttributeError, OSError):
        return DEFAULT_DPI
    if result != 0 or not dpi_x.value:
        return DEFAULT_DPI
    return int(dpi_x.value)


def _read_monitor(handle: int) -> MonitorInfo | None:
    info = _MONITORINFOEXW()
    info.cbSize = ctypes.sizeof(_MONITORINFOEXW)
    if not _user32.GetMonitorInfoW(wintypes.HMONITOR(handle), ctypes.byref(info)):
        return None
    return MonitorInfo(
        device=info.szDevice,
        handle=int(handle),
        bounds=(
            info.rcMonitor.left,
            info.rcMonitor.top,
            info.rcMonitor.right,
            info.rcMonitor.bottom,
        ),
        work=(
            info.rcWork.left,
            info.rcWork.top,
            info.rcWork.right,
            info.rcWork.bottom,
        ),
        dpi=_monitor_dpi(handle),
        primary=bool(info.dwFlags & MONITORINFOF_PRIMARY),
    )


def list_monitors() -> list[MonitorInfo]:
    """枚举当前所有显示器。失败返回空列表，由调用方决定要不要当成致命。"""

    monitors: list[MonitorInfo] = []

    def callback(handle, _hdc, _rect, _param) -> bool:
        monitor = _read_monitor(handle)
        if monitor is not None:
            monitors.append(monitor)
        return True

    with per_monitor_dpi():
        try:
            _user32.EnumDisplayMonitors(None, None, _MONITORENUMPROC(callback), 0)
        except OSError:
            return []
    return monitors


def frame_size_for_client(
    client_width: int,
    client_height: int,
    dpi: int = DEFAULT_DPI,
    style: int = WS_OVERLAPPEDWINDOW,
    ex_style: int = 0,
) -> tuple[int, int]:
    """把目标客户区换算成所需的窗口外框尺寸。

    非客户区（标题栏、边框）的高度随 DPI 变——150% 下标题栏约 48px、100% 下约
    31px，写死余量在高 DPI 显示器上必然误判，所以走系统的换算函数。
    """

    rect = _RECT(0, 0, int(client_width), int(client_height))
    user32 = _user32
    adjusted = False
    with suppress(AttributeError, OSError):
        # Windows 10 1607+ 才有带 DPI 的版本。
        adjusted = bool(
            user32.AdjustWindowRectExForDpi(
                ctypes.byref(rect),
                wintypes.DWORD(style),
                wintypes.BOOL(False),
                wintypes.DWORD(ex_style),
                wintypes.UINT(int(dpi)),
            )
        )
    if not adjusted:
        with suppress(AttributeError, OSError):
            user32.AdjustWindowRectEx(
                ctypes.byref(rect),
                wintypes.DWORD(style),
                wintypes.BOOL(False),
                wintypes.DWORD(ex_style),
            )
    return rect.right - rect.left, rect.bottom - rect.top


def can_host_client(
    monitor: MonitorInfo, client_width: int, client_height: int
) -> bool:
    """这块屏的可用区域放不放得下目标客户区（含标题栏与边框）。"""

    frame_width, frame_height = frame_size_for_client(
        client_width, client_height, monitor.dpi
    )
    work_width, work_height = monitor.work_size
    return work_width >= frame_width and work_height >= frame_height


def find_host_monitor(client_width: int, client_height: int) -> MonitorInfo | None:
    """挑一块放得下目标客户区的屏；主显示器优先，其次可用面积最大的。"""

    candidates = [
        monitor
        for monitor in list_monitors()
        if can_host_client(monitor, client_width, client_height)
    ]
    if not candidates:
        return None
    for monitor in candidates:
        if monitor.primary:
            return monitor
    return max(candidates, key=lambda item: item.work_size[0] * item.work_size[1])


def describe_monitors() -> str:
    """一行式的显示器概况，供诊断日志使用。"""

    monitors = list_monitors()
    if not monitors:
        return "未能枚举到显示器"
    return "; ".join(monitor.describe() for monitor in monitors)


# 显式声明公开面：`platform/display.py` 用星号导入本模块，不声明的话 ctypes、wintypes
# 这些实现细节会一起泄漏进 `app.utils.platform.display` 命名空间。
__all__ = [
    "MonitorInfo",
    "per_monitor_dpi",
    "list_monitors",
    "frame_size_for_client",
    "can_host_client",
    "find_host_monitor",
    "describe_monitors",
]
