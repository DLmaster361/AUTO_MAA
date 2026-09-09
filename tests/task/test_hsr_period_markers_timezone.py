"""HSR 日 / 周标记的时区口径回归

星铁在服务器时间（UTC+8）周一 04:00 重置，等价于 UTC+4 的零点。周标记按 UTC+8 算会提前
四小时翻页：周一 00:00~04:00（北京时间，对欧洲用户就是周日晚上）跑的那一轮，会把「上一周
已完成」的外部脚本结果写成新一周的完成态，等游戏真正重置后整周都不再尝试。

`_period_markers` 是纯函数（可注入 now_dt），这里直接钉住边界两侧的取值。
"""

from datetime import datetime, timedelta, timezone

from app.task.HSR.AutoProxy import HSRAutoProxyTask

CST = timezone(timedelta(hours=8))


def test_before_server_reset_still_previous_week() -> None:
    """服务器时间周一 03:59 仍属于上一周——游戏此刻还没重置。"""

    _, week = HSRAutoProxyTask._period_markers(datetime(2026, 9, 14, 3, 59, tzinfo=CST))

    assert week == "2026-W37"


def test_after_server_reset_is_new_week() -> None:
    """服务器时间周一 04:00 起才是新一周。"""

    _, week = HSRAutoProxyTask._period_markers(datetime(2026, 9, 14, 4, 0, tzinfo=CST))

    assert week == "2026-W38"


def test_day_marker_rolls_at_server_reset_too() -> None:
    """日期标记同样按 04:00 换日，与日常代理写回的 LastProxyDate 口径一致。"""

    before, _ = HSRAutoProxyTask._period_markers(
        datetime(2026, 9, 14, 3, 59, tzinfo=CST)
    )
    after, _ = HSRAutoProxyTask._period_markers(datetime(2026, 9, 14, 4, 0, tzinfo=CST))

    assert before == "2026-09-13"
    assert after == "2026-09-14"


def test_marker_is_independent_of_local_timezone() -> None:
    """同一瞬间无论用哪个时区表示，标记都必须一样——用户在哪个时区不影响游戏周。"""

    instant_cst = datetime(2026, 9, 14, 4, 0, tzinfo=CST)
    instant_utc2 = instant_cst.astimezone(timezone(timedelta(hours=2)))

    assert HSRAutoProxyTask._period_markers(
        instant_cst
    ) == HSRAutoProxyTask._period_markers(instant_utc2)
