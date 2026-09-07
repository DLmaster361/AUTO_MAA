"""虚拟显示器保障层的判据回归

这一层最容易出错的不是「怎么插屏」，而是「什么时候不该插」。挂一块虚拟屏会改变桌面
拓扑、移动已有窗口，在显示器正常时凭空多挂一块是有害的；反过来把开关关着还去碰驱动
也不对。所以下面几条全是「不该插」的路径。
"""

import asyncio

import pytest

import app.core  # noqa: F401  # 初始化宿主配置
from app.core import desktop_guard


def _run(cm):
    async def main():
        async with cm as value:
            return value

    return asyncio.run(main())


def test_parse_mode_reads_the_configured_string() -> None:
    assert desktop_guard.parse_mode("1920x1080@60") == (1920, 1080, 60)
    assert desktop_guard.parse_mode("3840x2160@60") == (3840, 2160, 60)


def test_parse_mode_falls_back_instead_of_raising() -> None:
    """配置串坏掉时回落到默认模式，不能把整轮任务打掉。"""

    from app.utils.platform.vdd import DEFAULT_VDD_MODE

    for bad in ("", "1920x1080", "abc@60", None):
        assert desktop_guard.parse_mode(bad) == DEFAULT_VDD_MODE


def test_disabled_switch_never_touches_the_driver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """开关关着时，连探测都不该发生——用户没同意就别碰驱动。"""

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: False, raising=False
    )

    def _boom():
        raise AssertionError("开关关着不该查显示器")

    monkeypatch.setattr(desktop_guard, "_desktop_has_room", _boom)
    assert _run(desktop_guard.ensure_desktop_available()) is None


def test_roomy_desktop_is_left_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """显示器正常时不挂虚拟屏——多挂一块会移动用户已经打开的窗口。"""

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)

    import app.utils.platform.vdd as vdd

    def _boom():
        raise AssertionError("桌面够用时不该探测驱动")

    monkeypatch.setattr(vdd, "probe", _boom)
    assert _run(desktop_guard.ensure_desktop_available()) is None


def test_non_windows_is_a_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", False)
    assert _run(desktop_guard.ensure_desktop_available()) is None


def test_missing_driver_does_not_break_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """没装驱动只记日志，任务照常跑——这一层是改善项，不是前置条件。"""

    import app.utils.platform.vdd as vdd

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "无可用显示器")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)
    )

    assert _run(desktop_guard.ensure_desktop_available()) is None
