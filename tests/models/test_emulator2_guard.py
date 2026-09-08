import unittest

from app.utils.emulator2.guard import (
    capture,
    drift,
    dump_baselines,
    load_baselines,
)
from app.utils.emulator2.settings import FieldValue, InstanceSettings


def make_settings(**fields: tuple[int | None, str]) -> InstanceSettings:
    return InstanceSettings(
        fields={
            name: FieldValue(value, state) for name, (value, state) in fields.items()
        }
    )


class CaptureTest(unittest.TestCase):
    """基准只记用户显式设过的字段。"""

    def test_only_saved_fields_are_recorded(self) -> None:
        settings = make_settings(
            width=(1280, "saved"),
            cpu=(6, "default"),
            memoryMb=(None, "unset"),
            fps=(60, "saved"),
        )

        self.assertEqual(capture(settings), {"width": 1280, "fps": 60})

    def test_default_values_are_not_recorded(self) -> None:
        """把模拟器默认值写进基准，等于替用户决定这个值以后就该是这样。

        他之后在模拟器里调了 CPU，守卫还会给他改回去——他从没表达过要锁住它。
        """
        settings = make_settings(cpu=(6, "default"))

        self.assertEqual(capture(settings), {})

    def test_unreadable_is_not_recorded(self) -> None:
        settings = make_settings(width=(None, "unreadable"))

        self.assertEqual(capture(settings), {})


class DriftTest(unittest.TestCase):
    def test_no_drift_when_everything_matches(self) -> None:
        current = make_settings(width=(1280, "saved"), fps=(60, "saved"))

        self.assertEqual(drift({"width": 1280, "fps": 60}, current), {})

    def test_changed_field_is_restored_to_the_baseline(self) -> None:
        """返回的是**基准值**，不是现状值——这是要写回去的东西。"""
        current = make_settings(width=(960, "saved"))

        self.assertEqual(drift({"width": 1280}, current), {"width": 1280})

    def test_unreadable_field_is_left_alone(self) -> None:
        """读不出来是「没问到」，不是「被改了」。

        拿一份可能过期的基准去覆盖一份根本没看清的现状，比不管更糟。
        """
        current = make_settings(width=(None, "unreadable"))

        self.assertEqual(drift({"width": 1280}, current), {})

    def test_field_missing_from_current_is_left_alone(self) -> None:
        self.assertEqual(drift({"width": 1280}, make_settings()), {})

    def test_default_state_still_counts_as_drift(self) -> None:
        """用户设过 CPU，后来模拟器把那条键弄没了、回落成默认值——这就是要还原的情况。"""
        current = make_settings(cpu=(6, "default"))

        self.assertEqual(drift({"cpu": 2}, current), {"cpu": 2})


class PersistenceTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        baselines = {"0": {"width": 1280, "fps": 60}, "3": {"cpu": 2}}

        self.assertEqual(load_baselines(dump_baselines(baselines)), baselines)

    def test_garbage_is_empty_not_an_error(self) -> None:
        for raw in (None, "", "[]", "not json", '{"0": 5}'):
            with self.subTest(raw=raw):
                self.assertEqual(load_baselines(raw), {})

    def test_unknown_fields_are_dropped(self) -> None:
        """词表之外的键写进来只会在还原时报未知设置项。"""
        loaded = load_baselines('{"0": {"width": 1280, "rootMode": 1}}')

        self.assertEqual(loaded, {"0": {"width": 1280}})

    def test_bool_is_not_accepted_as_a_value(self) -> None:
        self.assertEqual(load_baselines('{"0": {"cpu": true}}'), {})


if __name__ == "__main__":
    unittest.main()
