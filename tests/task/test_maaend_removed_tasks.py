from app.task.MaaEnd.AutoProxy import _disable_removed_tasks


def test_removed_task_disabled_and_reported() -> None:
    tasks = [
        {"id": "a", "taskName": "GiftOperator", "enabled": True},
        {"id": "b", "taskName": "AutoUseSpMedication", "enabled": True},
        {"id": "c", "taskName": "__MXU_helper", "enabled": True},
    ]
    removed = _disable_removed_tasks(
        tasks, {"GiftOperator": "赠送干员礼物", "AccountSwitch": "切换账号"}
    )
    assert removed == {"AutoUseSpMedication"}
    assert [task["enabled"] for task in tasks] == [True, False, True]


def test_unknown_and_mxu_tasks_kept_untouched() -> None:
    tasks = [
        {"id": "a", "taskName": "__MXU_helper", "enabled": True},
        {"id": "b", "taskName": "DailyRewards", "enabled": False},
    ]
    assert _disable_removed_tasks(tasks, {"DailyRewards": "日常奖励领取"}) == set()
    assert [task["enabled"] for task in tasks] == [True, False]
