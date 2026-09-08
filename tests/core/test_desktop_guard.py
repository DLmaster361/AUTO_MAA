"""虚拟显示器保障层的判据回归

判据是「有没有真实显示输出」，不是「桌面够不够大」。所有真实输出都断开时 Windows 会
保留一块占位的幻影屏，它照旧上报一个看着正常的分辨率（实测甚至会继承上一块屏的模式），
按尺寸判会直接放行、什么都不做。

这一层最容易出错的不是「怎么插屏」，而是「什么时候不该插」——挂一块虚拟屏会改变桌面
拓扑、移动已有窗口，有真实输出时凭空多挂一块是有害的；反过来把开关关着还去碰驱动也不对。
所以下面几条大多是「不该插」的路径。
"""

import asyncio
import json
import os

import pytest

import app.core  # noqa: F401  # 初始化宿主配置
from app.core import desktop_guard
from app.utils.platform import IS_WINDOWS

pytestmark = pytest.mark.skipif(
    not IS_WINDOWS, reason="虚拟显示器与显示输出判据仅 Windows 实现"
)


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
            self.index = 0
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


def test_orphan_from_a_dead_process_is_cleaned_up(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """上次进程被强杀留下的虚拟屏，下次进入时要拆掉。

    上游文档称停止心跳约 1 秒后虚拟屏会自动拔掉，**实测不成立**（杀掉进程 6 秒后屏仍在）。
    所以不能把保活当成清理机制，必须靠记账主动拆。
    """

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    state.write_text('{"index": 3, "pid": 999999}', encoding="utf-8")
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    monkeypatch.setattr(desktop_guard, "_pid_alive", lambda pid: False)

    removed: list[int] = []
    monkeypatch.setattr(
        vdd, "remove_display_index", lambda index: (removed.append(index), True)[1]
    )

    desktop_guard.cleanup_orphan_display()
    assert removed == [3], "应当按记账里的 index 拆掉那块孤儿"
    assert not state.exists(), "拆完要清掉记账"


def test_display_of_a_live_process_is_not_touched(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """记录里的进程还活着就不能拆——同一台机器可能跑着另一个实例。"""

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    state.write_text('{"index": 1, "pid": 4242}', encoding="utf-8")
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    monkeypatch.setattr(desktop_guard, "_pid_alive", lambda pid: True)

    def _boom(index):
        raise AssertionError("进程还活着不该拆屏")

    monkeypatch.setattr(vdd, "remove_display_index", _boom)

    desktop_guard.cleanup_orphan_display()
    assert state.exists(), "还活着就不该清掉记账"


def test_unreadable_state_file_removes_nothing(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """记账坏了就丢弃，绝不按猜测去拆屏——驱动只认 index，拆错就是别人的屏。"""

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    state.write_text("{ 这不是 json", encoding="utf-8")
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)

    def _boom(index):
        raise AssertionError("记账坏了不该拆任何屏")

    monkeypatch.setattr(vdd, "remove_display_index", _boom)

    desktop_guard.cleanup_orphan_display()
    assert not state.exists()


def test_pid_alive_defaults_to_true_when_undecidable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """判断不了进程死活时按「活着」处理：宁可留下孤儿，也不要误拆别人的屏。"""

    import builtins

    real_import = builtins.__import__

    def _no_psutil(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("模拟 psutil 不可用")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _no_psutil)
    assert desktop_guard._pid_alive(999999) is True


def test_attaching_records_state_for_crash_recovery(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """挂上虚拟屏之后必须立刻写记账，否则孤儿清理永远拿不到数据。

    这条是补上来的：`_write_state` 曾经只有定义没有调用，读端的三条测试全绿，
    但整个孤儿清理在生产路径上是死代码——进程被强杀后那块屏永远留在桌面上。
    """

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: True, raising=False
    )
    monkeypatch.setattr(desktop_guard, "cleanup_orphan_display", lambda: None)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )

    # 第一次问（触发判据）说没有真实输出，之后（插屏后重验）说有。
    answers = iter([False, True])
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: next(answers, True))
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)

    class _FakeDisplay:
        def __init__(self, mode):
            self.index = 7
            self.device = "DISPLAYTEST"
            self.applied_mode = mode
            self._active = False

        @property
        def active(self):
            return self._active

        def __enter__(self):
            self._active = True
            return self

        def close(self):
            self._active = False

    monkeypatch.setattr(vdd, "VirtualDisplay", _FakeDisplay)

    seen: list[dict] = []

    async def main():
        async with desktop_guard.ensure_desktop_available() as display:
            assert display is not None
            assert state.exists(), "挂上屏之后必须已经写好记账"
            seen.append(json.loads(state.read_text(encoding="utf-8")))

    asyncio.run(main())

    assert seen and seen[0]["index"] == 7, f"记账里应当是挂上那块屏的 index: {seen}"
    assert seen[0]["pid"] == os.getpid()
    assert not state.exists(), "正常收尾要清掉记账"


def test_orphan_cleanup_runs_even_when_switch_is_off(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """开关关掉之后，上次遗留的孤儿仍要能被清掉。

    用户崩溃之后很可能顺手把开关关了；清理若排在开关判断之后，那块没人认领的屏
    就永远留在桌面上。
    """

    state = tmp_path / "virtual_display.json"
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    monkeypatch.setattr(
        desktop_guard.Config, "get", lambda group, name: False, raising=False
    )

    called: list[bool] = []
    monkeypatch.setattr(
        desktop_guard, "cleanup_orphan_display", lambda: called.append(True)
    )

    assert _run(desktop_guard.ensure_desktop_available()) is None
    assert called, "开关关着也必须尝试清理孤儿"
