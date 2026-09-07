"""MaaFW Win32 游戏窗口目标尺寸解析的纯逻辑回归

`Game.WindowSize` 决定 MAS 要不要动游戏窗口、动成多大。默认 Off：MAS 无从知道某个
MaaFW 项目要的是什么比例，只在用户明确指定时才整形。Fit 从大到小挑第一个放得下的。
"""

from types import SimpleNamespace

import pytest

from app.utils.platform import IS_WINDOWS

pytestmark = pytest.mark.skipif(not IS_WINDOWS, reason="窗口整形仅 Windows 实现")


def _task(window_size: str):
    from app.task.MaaFW.tools.embedded.runner_task import MaaFWPluginAutoProxyTask

    task = object.__new__(MaaFWPluginAutoProxyTask)
    task.script_config = SimpleNamespace(
        get=lambda section, key: window_size
        if (section, key) == ("Game", "WindowSize")
        else None
    )
    return task


def _monitor(width: int, height: int, dpi: int = 96):
    from app.utils.platform.display import MonitorInfo

    return MonitorInfo(
        device="\\\\.\\DISPLAYTEST",
        handle=0,
        bounds=(0, 0, width, height),
        work=(0, 0, width, height),
        dpi=dpi,
        primary=True,
    )


def test_off_never_touches_the_window() -> None:
    """默认不整形——用户没要求就不该替他决定窗口多大。"""

    assert _task("Off")._win32_window_target(_monitor(3840, 2160)) is None


def test_explicit_preset_ignores_screen_size() -> None:
    """指定了具体尺寸就照做，容量检查交给 check() 的闸门。"""

    assert _task("1280x720")._win32_window_target(_monitor(1024, 768)) == (1280, 720)
    assert _task("1920x1080")._win32_window_target(_monitor(3840, 2160)) == (1920, 1080)


def test_fit_picks_the_largest_that_actually_fits() -> None:
    """Fit 从大到小挑第一个放得下的，而不是无脑取最大。"""

    task = _task("Fit")
    assert task._win32_window_target(_monitor(3840, 2160)) == (1920, 1080)
    assert task._win32_window_target(_monitor(1920, 1080)) == (1600, 900)
    assert task._win32_window_target(_monitor(1600, 900)) == (1280, 720)


def test_fit_gives_up_when_nothing_fits() -> None:
    """兜底分辨率下一档都放不下，返回 None 交由闸门给出可读的失败原因。"""

    assert _task("Fit")._win32_window_target(_monitor(1024, 768)) is None
    assert _task("Fit")._win32_window_target(None) is None


def test_fit_accounts_for_dpi_scaling() -> None:
    """同样的屏幕像素，高 DPI 下非客户区更厚，可能就掉一档。

    临界屏幕由换算函数自己算出来，不写死——写死的数字既容易和实际的边框宽度
    对不上，也无法说明「差别真的来自 DPI」。
    """

    from app.utils.platform.display import frame_size_for_client

    width_96, height_96 = frame_size_for_client(1920, 1080, 96)
    width_192, height_192 = frame_size_for_client(1920, 1080, 192)
    assert height_192 > height_96, "高 DPI 的非客户区必须更厚，否则这条测不到东西"

    # 宽度对两档都够，高度只够 96 那一档。
    screen = max(width_96, width_192), height_96

    task = _task("Fit")
    assert task._win32_window_target(_monitor(*screen, dpi=96)) == (1920, 1080)
    assert task._win32_window_target(_monitor(*screen, dpi=192)) != (1920, 1080)
