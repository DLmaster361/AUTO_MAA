from datetime import datetime, timedelta, timezone

from app.task.MAA.AutoProxy import _is_marked_today

UTC4 = timezone(timedelta(hours=4))


def test_marked_date_not_today_counts_as_pending() -> None:
    assert not _is_marked_today("2000-01-01", datetime(2026, 9, 7, 12, 0, tzinfo=UTC4))


def test_marked_today_suppresses_rerun() -> None:
    assert _is_marked_today("2026-09-07", datetime(2026, 9, 7, 12, 0, tzinfo=UTC4))


def test_marked_date_anchor_is_utc4() -> None:
    # 东八区 2026-09-08 03:00 仍处于东四区 9 月 7 日，当日标记应继续生效
    beijing_early_morning = datetime(
        2026, 9, 8, 3, 0, tzinfo=timezone(timedelta(hours=8))
    )

    assert _is_marked_today("2026-09-07", beijing_early_morning.astimezone(UTC4))
    assert not _is_marked_today("2026-09-06", beijing_early_morning.astimezone(UTC4))


def test_non_utc4_datetime_is_normalized_internally() -> None:
    # UTC 时间 2026-09-07 20:00 即东四区的 2026-09-08 00:00：跨入新游戏日的临界时刻
    utc_boundary = datetime(2026, 9, 7, 20, 0, tzinfo=timezone.utc)

    assert _is_marked_today("2026-09-08", utc_boundary)
    assert not _is_marked_today("2026-09-07", utc_boundary)
