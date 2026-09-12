"""BetterGI：原生一条龙配置读不出来 ≠ 没有启用任务。"""

from types import SimpleNamespace

from app.task.BetterGI.AutoProxy import AutoProxyTask
from app.task.BetterGI.tools import one_dragon

_CONFIG_NAME = "MAS测试"


def _fake_task(root):
    return SimpleNamespace(
        script_root_path=root,
        launch_config_name=_CONFIG_NAME,
        cur_user_item=SimpleNamespace(name="甲"),
    )


def test_missing_config_means_no_enabled_tasks(tmp_path):
    assert AutoProxyTask._native_one_dragon_has_tasks(_fake_task(tmp_path)) is False


def test_enabled_list_decides_true_or_false(tmp_path):
    one_dragon.write_one_dragon(
        tmp_path, _CONFIG_NAME, {"TaskEnabledList": {"a": True}}
    )
    assert AutoProxyTask._native_one_dragon_has_tasks(_fake_task(tmp_path)) is True

    one_dragon.write_one_dragon(
        tmp_path, _CONFIG_NAME, {"TaskEnabledList": {"a": False}}
    )
    assert AutoProxyTask._native_one_dragon_has_tasks(_fake_task(tmp_path)) is False


def test_malformed_config_is_reported_as_read_failure(tmp_path):
    path = one_dragon.one_dragon_path(tmp_path, _CONFIG_NAME)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{", encoding="utf-8")
    assert AutoProxyTask._native_one_dragon_has_tasks(_fake_task(tmp_path)) is None


def test_unreadable_config_is_reported_as_read_failure(tmp_path):
    # 目录占住配置文件路径：exists() 为真但 read_bytes() 抛 OSError
    one_dragon.one_dragon_path(tmp_path, _CONFIG_NAME).mkdir(parents=True)
    assert AutoProxyTask._native_one_dragon_has_tasks(_fake_task(tmp_path)) is None
