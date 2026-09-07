import unittest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from pydantic import ValidationError

from app.models.config import (
    MaaEndConfigModeValidator,
    MaaEndPlanConfig,
    MaaEndUserConfig,
)
from app.models.ConfigBase import OptionsValidator
from app.models.schema import MaaEndUserConfig_Task

UTC4 = timezone(timedelta(hours=4))
WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


class MaaEndUserConfigTest(unittest.IsolatedAsyncioTestCase):
    def test_mode_validator_maps_legacy_values_before_parent_correction(self) -> None:
        validator = MaaEndConfigModeValidator()

        with patch.object(
            OptionsValidator,
            "correct",
            side_effect=AssertionError("父类校验不应提前执行"),
        ):
            self.assertEqual(validator.correct("简洁"), "脚本")
            self.assertEqual(validator.correct("详细"), "用户")
            self.assertEqual(validator.correct("自定义"), "用户")

    async def test_pull_count_calculator_is_disabled_by_default(self) -> None:
        config = MaaEndUserConfig()

        self.assertFalse(config.get("Task", "IfPullCountCalculator"))

    async def test_load_migrates_legacy_protocol_space_tab(self) -> None:
        config = MaaEndUserConfig()

        await config.load(
            {
                "Task": {
                    "SanityTaskType": "ProtocolSpace",
                    "ProtocolSpaceTab": "WeaponProgression",
                }
            }
        )

        self.assertEqual(config.get("Task", "SanityTaskType"), "WeaponProgression")

    async def test_partial_task_load_keeps_existing_sanity_task_type(self) -> None:
        config = MaaEndUserConfig()
        await config.set("Task", "SanityTaskType", "CrisisDrills")

        await config.load({"Task": {"RewardsSetOption": "RewardsSetB"}})

        self.assertEqual(config.get("Task", "SanityTaskType"), "CrisisDrills")
        self.assertEqual(config.get("Task", "RewardsSetOption"), "RewardsSetB")

    def test_daily_once_tasks_schema_uses_json_string_contract(self) -> None:
        config = MaaEndUserConfig_Task(DailyOnceTasks='["IfSanity"]')

        self.assertEqual(config.DailyOnceTasks, '["IfSanity"]')
        with self.assertRaises(ValidationError):
            MaaEndUserConfig_Task(DailyOnceTasks=["IfSanity"])

    async def test_plan_load_migrates_legacy_slot_to_key(self) -> None:
        config = MaaEndPlanConfig()

        await config.load(
            {
                "ALL": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFTheHub",
                }
            }
        )

        data = await config.toDict()
        self.assertEqual(
            data["ALL"],
            {
                "Key": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFTheHub",
                }
            },
        )

    async def test_fixed_mode_returns_complete_plan_key(self) -> None:
        config = MaaEndUserConfig()

        key, mode = config.get_effective_sanity_task_key()

        self.assertEqual(mode, "Fixed")
        self.assertEqual(key["SanityTaskType"], "OperatorProgression")
        self.assertEqual(key["OperatorProgression"], "OperatorEXP")

    async def test_plan_load_migrates_legacy_weekday_slot(self) -> None:
        config = MaaEndPlanConfig()

        await config.load(
            {
                "Wednesday": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFPine",
                }
            }
        )

        data = await config.toDict()
        self.assertEqual(
            data["Wednesday"],
            {
                "Key": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFPine",
                }
            },
        )

    async def test_plan_load_migrates_legacy_protocol_space_slot(self) -> None:
        config = MaaEndPlanConfig()

        await config.load(
            {
                "ALL": {
                    "SanityTaskType": "ProtocolSpace",
                    "ProtocolSpaceTab": "WeaponProgression",
                    "WeaponProgression": "WeaponTune",
                }
            }
        )

        data = await config.toDict()
        self.assertEqual(
            data["ALL"],
            {
                "Key": {
                    "SanityTaskType": "WeaponProgression",
                    "OperatorProgression": "OperatorEXP",
                    "WeaponProgression": "WeaponTune",
                    "CrisisDrills": "AdvancedProgression1",
                    "RewardsSetOption": "RewardsSetA",
                }
            },
        )

    def _register_plan(self, plan: MaaEndPlanConfig) -> str:
        plan_uid = uuid.uuid4()
        MaaEndUserConfig.related_config["PlanConfig"] = {plan_uid: plan}
        self.addCleanup(MaaEndUserConfig.related_config.clear)
        return str(plan_uid)

    async def test_effective_sanity_task_key_plan_mode_returns_current_key(
        self,
    ) -> None:
        config = MaaEndUserConfig()
        plan = MaaEndPlanConfig()
        await plan.load(
            {
                "ALL": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFPine",
                }
            }
        )
        plan_uid = self._register_plan(plan)
        await config.set("Info", "SanityMode", plan_uid)

        key, mode = config.get_effective_sanity_task_key()

        self.assertEqual(mode, plan_uid)
        self.assertEqual(
            key,
            {"SanityTaskType": "Essence", "AutoEssenceSpecifiedLocation": "VFPine"},
        )

    async def test_effective_sanity_task_key_weekly_plan_returns_today_slot(
        self,
    ) -> None:
        config = MaaEndUserConfig()
        plan = MaaEndPlanConfig()
        await plan.load(
            {
                "Info": {"Mode": "Weekly"},
                "ALL": {
                    "SanityTaskType": "Essence",
                    "AutoEssenceSpecifiedLocation": "VFTheHub",
                },
                **{
                    day: {
                        "SanityTaskType": "Essence",
                        "AutoEssenceSpecifiedLocation": "VFPine",
                    }
                    for day in WEEKDAY_NAMES
                },
            }
        )
        plan_uid = self._register_plan(plan)
        await config.set("Info", "SanityMode", plan_uid)

        key, mode = config.get_effective_sanity_task_key()

        self.assertEqual(mode, plan_uid)
        # Weekly 模式应取东四区当日槽位，而不是 ALL 槽位
        today = datetime.now(tz=UTC4).strftime("%A")
        self.assertEqual(key, plan.config_item_dict[today].getValue())
        self.assertEqual(key["AutoEssenceSpecifiedLocation"], "VFPine")

    async def test_effective_sanity_task_key_missing_plan_raises(self) -> None:
        config = MaaEndUserConfig()
        plan = MaaEndPlanConfig()
        plan_uid = self._register_plan(plan)
        await config.set("Info", "SanityMode", plan_uid)
        del MaaEndUserConfig.related_config["PlanConfig"][uuid.UUID(plan_uid)]

        # 正常读取会被 validator 纠正回 Fixed，绕过读取模拟读取后计划表被删除的窗口
        with patch.object(MaaEndUserConfig, "get", return_value=plan_uid):
            with self.assertRaises(ValueError):
                config.get_effective_sanity_task_key()


if __name__ == "__main__":
    unittest.main()
