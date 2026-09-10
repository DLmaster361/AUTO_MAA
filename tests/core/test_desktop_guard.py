"""虚拟显示器守卫的判据回归

判据是「有没有真实显示输出」，不是「桌面够不够大」。所有真实输出都断开时 Windows 会
保留一块占位的幻影屏，它照旧上报一个看着正常的分辨率（实测甚至会继承上一块屏的模式），
按尺寸判会直接放行、什么都不做。

守卫改成常驻之后，最容易出错的地方从「什么时候不该插」多出了一条「挂着的时候拿什么当
判据」：自己挂的那块屏本身就算真实输出，继续拿 `has_real_output` 判会永远认为显示器已经
回来，于是插一块拆一块地空转。所以 `decide()` 被拆成纯函数，下面第一组测试就打在它上面。
"""

import asyncio
import json
import os
import time

import pytest

import app.core  # noqa: F401  # 初始化宿主配置
from app.core import desktop_guard
from app.core.desktop_guard import ATTACH, DETACH, IDLE, LOST, RELEASE, decide
from app.utils.platform import IS_WINDOWS

pytestmark = pytest.mark.skipif(
    not IS_WINDOWS, reason="虚拟显示器与显示输出判据仅 Windows 实现"
)


@pytest.fixture
def guard(monkeypatch: pytest.MonkeyPatch):
    """一只干净的守卫。单例带跨用例状态（静默期、防抖计数），不能直接用。"""

    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", True)
    return desktop_guard._DesktopGuard()


def _config(monkeypatch: pytest.MonkeyPatch, **values) -> None:
    defaults = {"IfEnableVirtualDisplay": True, "VirtualDisplayMode": "1920x1080@60"}
    defaults.update(values)
    monkeypatch.setattr(
        desktop_guard.Config,
        "get",
        lambda group, name: defaults[name],
        raising=False,
    )


_OUR_DEVICE = r"\\.\DISPLAY9"
_OTHER_DEVICE = r"\\.\DISPLAY1"


class _FakeDisplay:
    """替身。`VirtualDisplay` 的最小契约：`__enter__` / `close` / index / device。"""

    instances: list["_FakeDisplay"] = []
    device_name = _OUR_DEVICE

    def __init__(self, mode):
        self.mode = mode
        self.index = 7
        self.device = type(self).device_name
        self.applied_mode = mode
        self.closed = 0
        type(self).instances.append(self)

    @property
    def active(self):
        return self.index is not None

    def __enter__(self):
        return self

    def close(self):
        self.closed += 1


# --------------------------------------------------------------------------- #
# 判据本身
# --------------------------------------------------------------------------- #


def test_no_real_output_means_attach() -> None:
    assert decide(
        enabled=True, holding=None, has_real_output=False, real_devices=set()
    ) == (ATTACH, "桌面上没有任何真实显示输出")


def test_real_output_is_left_alone() -> None:
    """有真实输出时不挂虚拟屏——多挂一块会移动用户已经打开的窗口。"""

    action, _ = decide(
        enabled=True, holding=None, has_real_output=True, real_devices={r"\\.\DISPLAY1"}
    )
    assert action == IDLE


def test_switch_off_never_attaches() -> None:
    action, _ = decide(
        enabled=False, holding=None, has_real_output=False, real_devices=set()
    )
    assert action == IDLE


def test_our_own_display_does_not_count_as_the_monitor_coming_back() -> None:
    """挂着的时候只有「除自己以外」的真实输出才算显示器回来了。

    这是常驻化引入的新坑：自己挂的那块屏本身就算真实输出，继续拿 `has_real_output`
    当判据会立刻判定「显示器已恢复」，于是每一轮巡检都插一块又拆一块。
    """

    ours = r"\\.\DISPLAY9"
    action, _ = decide(
        enabled=True, holding=ours, has_real_output=True, real_devices={ours}
    )
    assert action == IDLE


def test_real_monitor_coming_back_detaches() -> None:
    ours = r"\\.\DISPLAY9"
    action, reason = decide(
        enabled=True,
        holding=ours,
        has_real_output=True,
        real_devices={ours, r"\\.\DISPLAY1"},
    )
    assert action == DETACH
    assert reason


def test_monitor_coming_back_mid_task_is_deferred() -> None:
    """任务跑到一半接回显示器，不能当场把它脚下的屏抽掉。

    拆屏是一次桌面拓扑变更：窗口会被 Windows 挪到刚接回来的那块屏上、尺寸也可能跟着变，
    而脚本正按坐标点——这一下足以打掉整轮。推迟到任务结束再拆。
    """

    ours = _OUR_DEVICE
    action, _ = decide(
        enabled=True,
        holding=ours,
        has_real_output=True,
        real_devices={ours, _OTHER_DEVICE},
        task_running=True,
    )
    assert action == IDLE


def test_deferred_detach_happens_once_the_task_ends() -> None:
    """推迟不是取消：巡检一直在跑，最后一个任务收尾之后自然会拆。"""

    ours = _OUR_DEVICE
    action, _ = decide(
        enabled=True,
        holding=ours,
        has_real_output=True,
        real_devices={ours, _OTHER_DEVICE},
        task_running=False,
    )
    assert action == DETACH


def test_switch_off_still_wins_over_a_running_task() -> None:
    """关开关是用户明示的意图，任务在不在跑都照办——否则开关看着像坏了。"""

    action, _ = decide(
        enabled=False,
        holding=_OUR_DEVICE,
        has_real_output=True,
        real_devices={_OUR_DEVICE},
        task_running=True,
    )
    assert action == RELEASE


def test_attach_is_not_deferred_by_a_running_task() -> None:
    """任务中途被拔掉显示器时照样补一块——推迟的只有「拆」。"""

    action, _ = decide(
        enabled=True,
        holding=None,
        has_real_output=False,
        real_devices=set(),
        task_running=True,
    )
    assert action == ATTACH


def test_switch_turned_off_while_holding_releases() -> None:
    ours = r"\\.\DISPLAY9"
    action, _ = decide(
        enabled=False, holding=ours, has_real_output=True, real_devices={ours}
    )
    assert action == RELEASE


def test_our_display_vanishing_is_reported_as_lost() -> None:
    """驱动重载、睡眠恢复之后自己那块屏可能已经不在了，得就地认账。

    不认账的话 `holding` 永远指着一块不存在的屏，守卫再也不会去挂新的。
    """

    action, _ = decide(
        enabled=True,
        holding=r"\\.\DISPLAY9",
        has_real_output=True,
        real_devices=set(),
    )
    assert action == LOST


def test_lost_is_not_deferred_by_a_running_task() -> None:
    """屏都已经不在了，任务在跑也得认账。

    推迟成 IDLE 的话 `holding` 会永远指着一块不存在的屏，守卫再也不会去挂新的——
    正在跑的那轮任务反而彻底失去保障。
    """

    action, _ = decide(
        enabled=True,
        holding=_OUR_DEVICE,
        has_real_output=True,
        real_devices=set(),
        task_running=True,
    )
    assert action == LOST


# --------------------------------------------------------------------------- #
# 巡检
# --------------------------------------------------------------------------- #


def test_disabled_switch_never_touches_the_driver(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """开关关着时，连显示查询都不该发生——用户没同意就别碰驱动。"""

    _config(monkeypatch, IfEnableVirtualDisplay=False)

    def _boom():
        raise AssertionError("开关关着不该查显示输出")

    monkeypatch.setattr(desktop_guard, "_has_real_output", _boom)
    monkeypatch.setattr(desktop_guard, "_real_devices", _boom)

    asyncio.run(guard.ensure_now())
    assert guard.device is None


def test_non_windows_is_a_noop(guard, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(desktop_guard, "IS_WINDOWS", False)

    def _boom(*_args, **_kwargs):
        raise AssertionError("非 Windows 不该走到判据")

    monkeypatch.setattr(desktop_guard, "_has_real_output", _boom)
    asyncio.run(guard.ensure_now())
    asyncio.run(guard.start())
    assert guard.device is None


def test_missing_driver_does_not_break_the_run(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """没装驱动只记日志，任务照常跑——这一层是改善项，不是前置条件。"""

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)
    )

    asyncio.run(guard.ensure_now())
    assert guard.device is None


def test_phantom_display_with_normal_resolution_still_triggers(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """分辨率看着正常、但没有真实输出时，必须插屏。

    这是旧判据（按尺寸判）会漏掉的那一档：物理显示器关闭后 Windows 保留的幻影屏照旧
    上报 1920x1080，`find_host_monitor` 一路放行，保障层什么都不做——而那块屏背后没有
    任何输出。判据换成「有没有真实输出」之后这条才被覆盖。
    """

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    # 尺寸判据说「够用」，真实输出判据说「没有」。
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏 1920x1080")

    probed: list[bool] = []

    def _probe():
        probed.append(True)
        return vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)

    monkeypatch.setattr(vdd, "probe", _probe)

    asyncio.run(guard.ensure_now())
    assert probed, "尺寸够用但没有真实输出时，必须走到探测驱动这一步"


def test_attached_but_ineffective_display_is_removed(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """插上了但仍没有真实输出，就得拆掉——调得动不等于有效果。"""

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "STATE_FILE", tmp_path / "virtual_display.json")
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仍是幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )
    monkeypatch.setattr(_FakeDisplay, "instances", [])
    monkeypatch.setattr(vdd, "VirtualDisplay", _FakeDisplay)

    asyncio.run(guard.ensure_now())

    assert _FakeDisplay.instances, "应当真的尝试挂一块"
    assert _FakeDisplay.instances[0].closed == 1, "重验不过必须拆掉"
    assert guard.device is None


def test_failed_attach_closes_the_half_inserted_display(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`__enter__` 抛错时也要收尾。

    `VirtualDisplay.__enter__` 会在屏**已经插上**之后才可能失败（认不出对应的显示设备）。
    这时记账还没写，那块屏既没人认领、也不会被下次启动的孤儿清理捡走——只能由这里拆掉。
    """

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )

    class _FailsToIdentify(_FakeDisplay):
        def __enter__(self):
            raise vdd.VddError("虚拟显示器已挂载，但未能在桌面上认出对应的显示设备")

    monkeypatch.setattr(_FakeDisplay, "instances", [])
    monkeypatch.setattr(vdd, "VirtualDisplay", _FailsToIdentify)

    asyncio.run(guard.ensure_now())

    assert _FakeDisplay.instances[0].closed == 1, "插上之后才失败的那块屏必须就地拆掉"
    assert guard.device is None


def test_repeated_failures_back_off(guard, monkeypatch: pytest.MonkeyPatch) -> None:
    """探测失败后进入静默期：没装驱动的用户不该每几秒被探测一次。"""

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")

    probes: list[bool] = []

    def _probe():
        probes.append(True)
        return vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)

    monkeypatch.setattr(vdd, "probe", _probe)

    async def main():
        for _ in range(5):
            await guard.ensure_now()

    asyncio.run(main())
    assert len(probes) == 1, f"静默期内不该重复探测驱动: {len(probes)} 次"


def test_topology_actions_need_two_consecutive_ticks(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """拓扑判据要连续成立才动手。

    切模式、驱动重载、KVM 切换、睡眠恢复都会让判据在中间态里短暂成立，单次采样就插拔
    会来回抖，而每次插拔都会移动用户已经打开的窗口。
    """

    import app.utils.platform.vdd as vdd

    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: False)
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")

    probes: list[bool] = []

    def _probe():
        probes.append(True)
        return vdd.VddProbeResult(vdd.VddStatus.NOT_INSTALLED)

    monkeypatch.setattr(vdd, "probe", _probe)

    async def main():
        await guard._tick(confirm=True)
        assert not probes, "第一次成立不该动手"
        await guard._tick(confirm=True)

    asyncio.run(main())
    assert probes, f"连续 {desktop_guard.CONFIRM_TICKS} 次成立之后必须动手"


def test_forced_tick_never_detaches_without_confirmation(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """任务开跑前的强制巡检只对「挂上」免防抖。

    拆除同样免防抖的话，一次误判（枚举拿到中间态）就会把任务脚下的屏抽掉，而任务恰好
    就在那一刻起来。
    """

    monkeypatch.setattr(desktop_guard, "STATE_FILE", tmp_path / "virtual_display.json")
    _config(monkeypatch)
    ours = _FakeDisplay.device_name
    monkeypatch.setattr(desktop_guard, "_real_devices", lambda: {ours, _OTHER_DEVICE})

    display = _FakeDisplay((1920, 1080, 60))
    guard._display = display

    asyncio.run(guard.ensure_now())
    assert display.closed == 0, "单次强制巡检不该拆屏"

    asyncio.run(guard.ensure_now())
    assert display.closed == 1, "判据连续成立之后才拆"


def test_tick_asks_whether_a_task_is_running(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """巡检必须真的把「有没有任务在跑」喂给判据。

    `decide()` 的单测只证明纯函数会推迟，不证明 `_tick` 传了这个参数——漏传的话推迟
    在生产路径上就是死代码。
    """

    monkeypatch.setattr(desktop_guard, "STATE_FILE", tmp_path / "virtual_display.json")
    _config(monkeypatch)
    monkeypatch.setattr(
        desktop_guard, "_real_devices", lambda: {_OUR_DEVICE, _OTHER_DEVICE}
    )

    display = _FakeDisplay((1920, 1080, 60))
    guard._display = display

    monkeypatch.setattr(desktop_guard, "_task_running", lambda: True)

    async def while_running():
        for _ in range(desktop_guard.CONFIRM_TICKS + 1):
            await guard._tick(confirm=True)

    asyncio.run(while_running())
    assert display.closed == 0, "任务还在跑，不该拆掉它脚下的屏"

    monkeypatch.setattr(desktop_guard, "_task_running", lambda: False)

    async def after_it_ends():
        for _ in range(desktop_guard.CONFIRM_TICKS):
            await guard._tick(confirm=True)

    asyncio.run(after_it_ends())
    assert display.closed == 1, "任务结束之后要补上这次拆除"


def test_config_session_does_not_count_as_a_running_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """脚本自己的配置界面不算「任务在跑」。

    `ScriptConfig` 是 MAS 替用户打开脚本原生的设置窗口——人就坐在机器前，窗口可以开着
    不关。把它算进来就等于「忘了关设置窗口，虚拟屏永远不拆」。
    """

    from types import SimpleNamespace

    from app.core import TaskManager

    # mode 的取值来自 app/models/task.py 的 TaskInfo：AutoProxy / ScriptConfig / Update。
    monkeypatch.setattr(
        TaskManager,
        "task_info",
        {"a": SimpleNamespace(mode="ScriptConfig")},
        raising=False,
    )
    assert desktop_guard._task_running() is False

    monkeypatch.setattr(
        TaskManager,
        "task_info",
        {
            "a": SimpleNamespace(mode="ScriptConfig"),
            "b": SimpleNamespace(mode="AutoProxy"),
        },
        raising=False,
    )
    assert desktop_guard._task_running() is True


def test_cancelled_attach_is_not_abandoned(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """挂屏进行中被取消，也不能把屏丢在桌面上。

    `asyncio.to_thread` 被取消**不会**打断已经跑起来的线程：`VirtualDisplay.__enter__`
    照常把屏插上（光是等拓扑落定就要 1.5 秒）。用户在任务刚开跑时点「停止」正好走这条路
    ——`TaskManager.stop_task` 直接 cancel 掉那条任务，而任务开跑前 await 的正是守卫的
    强制巡检。若挂屏跟着半途而废，桌面上就留下一块守卫不认、记账也没写的屏，连下次启动的
    孤儿清理都捡不到它；更糟的是它本身算「真实输出」，此后每轮巡检都会一路放行。
    """

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    _config(monkeypatch)
    # 第一次问（触发判据）说没有真实输出，之后（插屏后重验）说有。
    answers = iter([False, True])
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: next(answers, True))
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )

    class _SlowDisplay(_FakeDisplay):
        def __enter__(self):
            time.sleep(0.3)
            return self

    monkeypatch.setattr(_FakeDisplay, "instances", [])
    monkeypatch.setattr(vdd, "VirtualDisplay", _SlowDisplay)

    async def main():
        pending = asyncio.create_task(guard.ensure_now())
        await asyncio.sleep(0.05)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        # 取消只影响「等不等它」，不影响「谁来收尾」：守卫仍要认下这块屏。
        await guard.stop()

    asyncio.run(main())

    assert _FakeDisplay.instances, "线程照样把屏插上了"
    assert _FakeDisplay.instances[0].closed == 1, (
        "被取消的挂屏必须由守卫认下并收尾，不能留在桌面上"
    )
    assert not state.exists(), "拆完要清掉记账"


def test_turning_the_switch_off_detaches_immediately(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """关开关是用户明示的意图，不该再等防抖，也不该被一次显示查询挡下来。"""

    monkeypatch.setattr(desktop_guard, "STATE_FILE", tmp_path / "virtual_display.json")
    _config(monkeypatch, IfEnableVirtualDisplay=False)

    def _boom():
        raise AssertionError("开关关着就该直接拆，不必先查显示设备")

    monkeypatch.setattr(desktop_guard, "_real_devices", _boom)
    monkeypatch.setattr(desktop_guard, "_has_real_output", _boom)

    display = _FakeDisplay((1920, 1080, 60))
    guard._display = display

    asyncio.run(guard._tick(confirm=True))

    assert display.closed == 1, "开关一关就该拆，不等第二次巡检"
    assert guard.device is None


def test_attaching_records_state_for_crash_recovery(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """挂上虚拟屏之后必须立刻写记账，否则孤儿清理永远拿不到数据。

    这条是补上来的：`_write_state` 曾经只有定义没有调用，读端的三条测试全绿，
    但整个孤儿清理在生产路径上是死代码——进程被强杀后那块屏永远留在桌面上。
    """

    import app.utils.platform.vdd as vdd

    state = tmp_path / "virtual_display.json"
    monkeypatch.setattr(desktop_guard, "STATE_FILE", state)
    _config(monkeypatch)
    monkeypatch.setattr(desktop_guard, "_describe", lambda: "仅有幻影屏")
    monkeypatch.setattr(
        vdd, "probe", lambda: vdd.VddProbeResult(vdd.VddStatus.OK, version=45)
    )
    # 第一次问（触发判据）说没有真实输出，之后（插屏后重验）说有。
    answers = iter([False, True])
    monkeypatch.setattr(desktop_guard, "_has_real_output", lambda: next(answers, True))
    monkeypatch.setattr(desktop_guard, "_desktop_has_room", lambda: True)
    monkeypatch.setattr(_FakeDisplay, "instances", [])
    monkeypatch.setattr(vdd, "VirtualDisplay", _FakeDisplay)

    asyncio.run(guard.ensure_now())

    assert state.exists(), "挂上屏之后必须已经写好记账"
    recorded = json.loads(state.read_text(encoding="utf-8"))
    assert recorded["index"] == 7, f"记账里应当是挂上那块屏的 index: {recorded}"
    assert recorded["pid"] == os.getpid()
    assert guard.device == r"\\.\DISPLAY9"

    # 拆掉之后记账要清干净，否则下次启动会去拆一块早就不存在的屏。
    asyncio.run(guard.stop())
    assert not state.exists()
    assert _FakeDisplay.instances[0].closed == 1


def test_shutdown_removes_the_display(
    guard, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """后端退出后没人会再来收尾这块屏。"""

    monkeypatch.setattr(desktop_guard, "STATE_FILE", tmp_path / "virtual_display.json")
    display = _FakeDisplay((1920, 1080, 60))
    guard._display = display

    asyncio.run(guard.stop())
    assert display.closed == 1


# --------------------------------------------------------------------------- #
# 孤儿清理
# --------------------------------------------------------------------------- #


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


def test_orphan_cleanup_runs_even_when_switch_is_off(
    guard, monkeypatch: pytest.MonkeyPatch
) -> None:
    """开关关掉之后，上次遗留的孤儿仍要能被清掉。

    用户崩溃之后很可能顺手把开关关了；清理若排在开关判断之后，那块没人认领的屏
    就永远留在桌面上。清理还必须排在第一次巡检之前——孤儿本身就算真实输出，
    不先清掉的话巡检判据会一路放行。
    """

    _config(monkeypatch, IfEnableVirtualDisplay=False)

    called: list[bool] = []
    monkeypatch.setattr(
        desktop_guard, "cleanup_orphan_display", lambda: called.append(True)
    )

    async def main():
        await guard.start()
        await guard.stop()

    asyncio.run(main())
    assert called, "开关关着也必须尝试清理孤儿"


# --------------------------------------------------------------------------- #
# 配置解析
# --------------------------------------------------------------------------- #


def test_parse_mode_reads_the_configured_string() -> None:
    assert desktop_guard.parse_mode("1920x1080@60") == (1920, 1080, 60)
    assert desktop_guard.parse_mode("3840x2160@60") == (3840, 2160, 60)


def test_parse_mode_falls_back_instead_of_raising() -> None:
    """配置串坏掉时回落到默认模式，不能把整轮任务打掉。"""

    from app.utils.platform.vdd import DEFAULT_VDD_MODE

    for bad in ("", "1920x1080", "abc@60", None):
        assert desktop_guard.parse_mode(bad) == DEFAULT_VDD_MODE
