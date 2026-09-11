from app.task.MAA.AutoProxy import _has_completed_annihilation_week


def test_week_completed_requires_progress_line_at_cap() -> None:
    log = "完成任务: 剿灭作战\n剿灭模式 : 1800 / 1800"
    assert _has_completed_annihilation_week(log) is True
    assert _has_completed_annihilation_week("剿灭模式 : 1850 / 1800\n完成任务: 剿灭作战") is True


def test_week_not_completed_without_cap_progress() -> None:
    assert _has_completed_annihilation_week("完成任务: 剿灭作战\n剿灭模式 : 1480 / 1800") is False
    assert _has_completed_annihilation_week("开始任务: 剿灭作战\n完成任务: 剿灭作战") is False
    assert _has_completed_annihilation_week("剿灭模式 : 1480 / 1800") is False
