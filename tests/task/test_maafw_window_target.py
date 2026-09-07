"""MaaFW Win32 游戏窗口「目标尺寸 + 目标显示器」解析的纯逻辑回归

`Game.WindowSize` 决定 MAS 要不要动游戏窗口、动成多大、放到哪块屏。默认 Off：MAS 无从
知道某个 MaaFW 项目要的是什么比例，只在用户明确指定时才整形。

选屏与判据必须是同一次决策——早先的版本容量检查按「任意显示器」放行、整形却按「窗口当前
所在显示器」执行，多屏尺寸不同时两者会对不上。这里用假的 find_host_monitor 覆盖真实显示器，
测的是那次决策本身。
"""

from types import SimpleNamespace

import pytest

from app.utils.platform import IS_WINDOWS

pytestmark = pytest.mark.skipif(not IS_WINDOWS, reason="窗口整形仅 Windows 实现")


def _monitor(
    width: int, height: int, dpi: int = 96, device: str = "TEST", handle: int = 1
):
    from app.utils.platform.display import MonitorInfo

    return MonitorInfo(
        device=device,
        handle=handle,
        bounds=(0, 0, width, height),
        work=(0, 0, width, height),
        dpi=dpi,
        primary=True,
    )


def _task(window_size: str, monitors, monkeypatch):
    """构造一个只带 Game.WindowSize 的任务，并把可用显示器换成 monitors。"""

    from app.task.MaaFW.tools.embedded import runner_task
    from app.utils.platform.display import can_host_client

    def fake_find_host_monitor(width: int, height: int):
        for monitor in monitors:
            if can_host_client(monitor, width, height):
                return monitor
        return None

    monkeypatch.setattr(runner_task, "find_host_monitor", fake_find_host_monitor)

    task = object.__new__(runner_task.MaaFWPluginAutoProxyTask)
    task.script_config = SimpleNamespace(
        get=lambda section, key: (
            window_size if (section, key) == ("Game", "WindowSize") else None
        )
    )
    return task


def test_off_never_touches_the_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """默认不整形——用户没要求就不该替他决定窗口多大。"""

    task = _task("Off", [_monitor(3840, 2160)], monkeypatch)
    assert task._win32_window_plan() is None


def test_explicit_preset_returns_the_monitor_that_can_host_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """显式尺寸同样要求真有屏放得下，并把那块屏一起返回。"""

    big = _monitor(3840, 2160, device="BIG", handle=2)
    task = _task("1920x1080", [big], monkeypatch)
    assert task._win32_window_plan() == ((1920, 1080), big)


def test_explicit_preset_gives_up_when_no_monitor_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """放不下就返回 None，交由 check() 的闸门给出可读的失败原因。

    早先显式尺寸分支不做容量判断，会把窗口设成超出工作区的尺寸再被夹到屏幕外，
    ScreenDC 截图随即抓到垃圾像素。
    """

    task = _task("1920x1080", [_monitor(1024, 768)], monkeypatch)
    assert task._win32_window_plan() is None


def test_fit_picks_the_largest_that_actually_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fit 从大到小挑第一个放得下的，而不是无脑取最大。"""

    def plan_for(width: int, height: int):
        task = _task("Fit", [_monitor(width, height)], monkeypatch)
        return task._win32_window_plan()[0]

    assert plan_for(3840, 2160) == (1920, 1080)
    assert plan_for(1920, 1080) == (1600, 900)
    assert plan_for(1600, 900) == (1280, 720)


def test_fit_gives_up_when_nothing_fits(monkeypatch: pytest.MonkeyPatch) -> None:
    """兜底分辨率下一档都放不下。"""

    assert _task("Fit", [_monitor(1024, 768)], monkeypatch)._win32_window_plan() is None
    assert _task("Fit", [], monkeypatch)._win32_window_plan() is None


def test_larger_secondary_monitor_is_chosen_over_the_small_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """多屏尺寸不同时，选的是放得下的那块，不是第一块。

    这正是选屏与判据分家时会错的场景：窗口在小屏上，检查却按大屏放行。
    """

    small = _monitor(1024, 768, device="SMALL", handle=1)
    big = _monitor(2560, 1440, device="BIG", handle=2)
    size, host = _task("Fit", [small, big], monkeypatch)._win32_window_plan()
    assert size == (1920, 1080)
    assert host.device == "BIG"


def test_fit_accounts_for_dpi_scaling(monkeypatch: pytest.MonkeyPatch) -> None:
    """同样的屏幕像素，高 DPI 下非客户区更厚，可能就掉一档。

    临界屏幕由换算函数自己算出来，不写死——写死的数字既容易和实际的边框宽度对不上，
    也无法说明「差别真的来自 DPI」。
    """

    from app.utils.platform.display import frame_size_for_client

    width_96, height_96 = frame_size_for_client(1920, 1080, 96)
    width_192, height_192 = frame_size_for_client(1920, 1080, 192)
    assert height_192 > height_96, "高 DPI 的非客户区必须更厚，否则这条测不到东西"

    # 宽度对两档都够，高度只够 96 那一档。
    screen = max(width_96, width_192), height_96

    plan_96 = _task(
        "Fit", [_monitor(*screen, dpi=96)], monkeypatch
    )._win32_window_plan()
    plan_192 = _task(
        "Fit", [_monitor(*screen, dpi=192)], monkeypatch
    )._win32_window_plan()
    assert plan_96[0] == (1920, 1080)
    assert plan_192 is None or plan_192[0] != (1920, 1080)


def test_capacity_gate_is_silent_when_reshaping_is_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """没开整形就不该拦——用户自己管窗口时 MAS 无从判断多大算够。"""

    task = _task("Off", [_monitor(1024, 768)], monkeypatch)
    assert task._check_desktop_capacity() is None


def test_capacity_gate_passes_when_some_monitor_fits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _task("1280x720", [_monitor(1920, 1080)], monkeypatch)
    assert task._check_desktop_capacity() is None


def test_capacity_gate_reports_target_and_actual_monitors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """拦下来时必须说清楚要多大、现在有什么，否则用户无从下手。"""

    from app.task.MaaFW.tools.embedded import runner_task

    monkeypatch.setattr(
        runner_task, "describe_monitors", lambda: "DISPLAY1 1024x768(可用 1024x728)"
    )
    task = _task("1920x1080", [_monitor(1024, 768)], monkeypatch)
    message = task._check_desktop_capacity()

    assert message is not None
    assert "1920x1080" in message, "要说清楚需要多大"
    assert "1024x768" in message, "要说清楚现在有什么"


def test_capacity_gate_uses_min_client_for_fit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fit 模式按最低档 1280x720 判定，不按最大档——否则小屏会被误拦。"""

    task = _task("Fit", [_monitor(1600, 900)], monkeypatch)
    assert task._check_desktop_capacity() is None

    task = _task("Fit", [_monitor(1024, 768)], monkeypatch)
    assert task._check_desktop_capacity() is not None
