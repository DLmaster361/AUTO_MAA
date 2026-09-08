"""虚拟显示器保障层的判据回归

判据是「有没有真实显示输出」，不是「桌面够不够大」。所有真实输出都断开时 Windows 会
保留一块占位的幻影屏，它照旧上报一个看着正常的分辨率（实测甚至会继承上一块屏的模式），
按尺寸判会直接放行、什么都不做。

这一层最容易出错的不是「怎么插屏」，而是「什么时候不该插」——挂一块虚拟屏会改变桌面
拓扑、移动已有窗口，有真实输出时凭空多挂一块是有害的；反过来把开关关着还去碰驱动也不对。
所以下面几条大多是「不该插」的路径。
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
        raise AssertionError("开关关着不该查显示输出")

    monkeypatch.setattr(desktop_guard, "_has_real_output", _boom)
    assert _run(desktop_guard.ensure_desktop_available()) is None


def test_real_output_is_left_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    """有真实输出时不挂虚拟屏——多挂一块会移动用户已经打开的窗口。"""

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: True)

    import app.utils.platform.vdd as vdd

    def _boom():
        raise AssertionError("有真实输出时不该探测驱动")

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
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)
    )

    assert _run(desktop_guard.ensure_desktop_available()) is None


def test_phantom_display_with_normal_resolution_still_triggers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """分辨率看着正常、但没有真实输出时，必须插屏。

    这是旧判据（按尺寸判）会漏掉的那一档：物理显示器关闭后 Windows 保留的幻影屏照旧
    上报 1920x1080，`find_host_monitor` 一路放行，保障层什么都不做——而那块屏背后没有
    任何输出。判据换成「有没有真实输出」之后这条才被覆盖。
    """

    import app.utils.platform.vdd as vdd

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    # 尺寸判据说「够用」，真实输出判据说「没有」。
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏 1920x1080")

    probed: list[bool] = []

    def _probe():
        probed.append(True)
        return vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)

    monkeypatch.setattr(vdd, "probe", _probe)

    _run(desktop_guard.ensure_desktop_available())
    assert probed, "尺寸够用但没有真实输出时，必须走到探测驱动这一步"


def test_attached_but_ineffective_display_is_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """插上了但仍没有真实输出，就得拆掉——调得动不等于有效果。"""

    import app.utils.platform.vdd as vdd

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仍是幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )

    closed: list[bool] = []

    class _FakeDisplay:
        def __init__(self, mode):
            self.applied_mode = None
            self.device = None
            self._active = False

        @property
        def active(self):
            return self._active

        def __enter__(self):
            self._active = True
            return self

        def close(self):
            self._active = False
            closed.append(True)

    monkeypatch.setattr(vdd, "VirtualDisplay", _FakeDisplay)

    assert _run(desktop_guard.ensure_desktop_available()) is None
    assert closed, "重验不过必须拆掉，不能把一块没生效的屏留在桌面上"
