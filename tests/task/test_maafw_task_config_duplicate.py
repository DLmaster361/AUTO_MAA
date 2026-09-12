import unittest

from app.task.MaaFW.tools.core.automas_maafw_interface.models import (
    MaaFWInterface,
    MaaFWOption,
    MaaFWOptionCase,
    MaaFWTask,
    build_duplicate_task_id,
    resolve_task_instance_name,
)
from app.task.MaaFW.tools.core.automas_maafw_interface.task_config import (
    normalize_snapshot,
    normalize_task_execution_payload,
)

TASK_B_COPY = build_duplicate_task_id("TaskB", "ab12cd34")


def build_interface_model() -> MaaFWInterface:
    return MaaFWInterface(
        interface_version=2,
        name="Demo",
        version="1.0.0",
        task=[
            MaaFWTask(name="TaskB", entry="entry_b", option=["OptAlpha"]),
            MaaFWTask(name="TaskA", entry="entry_a"),
        ],
        option={
            "OptAlpha": MaaFWOption(
                type="select",
                cases=[
                    MaaFWOptionCase(name="Red"),
                    MaaFWOptionCase(name="Blue"),
                ],
            ),
        },
    )


class MaafwDuplicateTaskIdTest(unittest.TestCase):
    def test_bare_task_name_resolves_to_itself(self) -> None:
        self.assertEqual(resolve_task_instance_name("TaskB", {"TaskB"}), "TaskB")

    def test_duplicate_id_resolves_to_task_name(self) -> None:
        self.assertEqual(resolve_task_instance_name(TASK_B_COPY, {"TaskB"}), "TaskB")

    def test_task_name_containing_separator_wins_over_duplicate_reading(self) -> None:
        # 项目自己的任务名恰好含分隔符时，整串仍按任务名解析，不能被当成副本。
        weird_name = build_duplicate_task_id("TaskB", "literal")
        self.assertEqual(
            resolve_task_instance_name(weird_name, {"TaskB", weird_name}),
            weird_name,
        )

    def test_unknown_head_is_left_untouched(self) -> None:
        unknown = build_duplicate_task_id("TaskZ", "ab12cd34")
        self.assertEqual(resolve_task_instance_name(unknown, {"TaskB"}), unknown)


class MaafwDuplicateTaskSnapshotTest(unittest.TestCase):
    def test_snapshot_keeps_duplicate_instance_with_own_options(self) -> None:
        interface_model = build_interface_model()
        snapshot = normalize_snapshot(
            {
                "taskOrder": ["TaskB", TASK_B_COPY, "TaskA"],
                "taskChecked": {"TaskB": True, TASK_B_COPY: True, "TaskA": False},
                "taskOptions": {
                    "TaskB": {"OptAlpha": "Red"},
                    TASK_B_COPY: {"OptAlpha": "Blue"},
                },
            },
            interface_model,
        )

        self.assertEqual(snapshot.taskOrder, ["TaskB", TASK_B_COPY, "TaskA"])
        self.assertTrue(snapshot.taskChecked[TASK_B_COPY])
        self.assertEqual(snapshot.taskOptions["TaskB"]["OptAlpha"], "Red")
        self.assertEqual(snapshot.taskOptions[TASK_B_COPY]["OptAlpha"], "Blue")

    def test_snapshot_drops_duplicate_of_unknown_task(self) -> None:
        interface_model = build_interface_model()
        snapshot = normalize_snapshot(
            {
                "taskOrder": ["TaskB", build_duplicate_task_id("TaskZ", "ab12cd34")],
                "taskChecked": {},
                "taskOptions": {},
            },
            interface_model,
        )
        self.assertEqual(snapshot.taskOrder, ["TaskB", "TaskA"])

    def test_snapshot_still_collapses_the_same_instance_id_twice(self) -> None:
        interface_model = build_interface_model()
        snapshot = normalize_snapshot(
            {
                "taskOrder": [TASK_B_COPY, TASK_B_COPY],
                "taskChecked": {},
                "taskOptions": {},
            },
            interface_model,
        )
        self.assertEqual(snapshot.taskOrder.count(TASK_B_COPY), 1)

    def test_legacy_snapshot_without_duplicates_is_unchanged(self) -> None:
        interface_model = build_interface_model()
        snapshot = normalize_snapshot(
            {
                "taskOrder": ["TaskA", "TaskB"],
                "taskChecked": {"TaskA": True},
                "taskOptions": {"TaskB": {"OptAlpha": "Blue"}},
            },
            interface_model,
        )
        self.assertEqual(snapshot.taskOrder, ["TaskA", "TaskB"])
        self.assertTrue(snapshot.taskChecked["TaskA"])
        self.assertEqual(snapshot.taskOptions["TaskB"]["OptAlpha"], "Blue")


class MaafwDuplicateTaskExecutionPayloadTest(unittest.TestCase):
    def test_execution_payload_keeps_both_copies_with_own_options(self) -> None:
        interface_model = build_interface_model()
        task_list, task_options = normalize_task_execution_payload(
            ["TaskB", TASK_B_COPY],
            {
                "TaskB": {"OptAlpha": "Red"},
                TASK_B_COPY: {"OptAlpha": "Blue"},
            },
            interface_model,
        )

        self.assertEqual(task_list, ["TaskB", TASK_B_COPY])
        self.assertEqual(task_options["TaskB"]["OptAlpha"], "Red")
        self.assertEqual(task_options[TASK_B_COPY]["OptAlpha"], "Blue")

    def test_execution_payload_falls_back_to_defaults_for_new_copy(self) -> None:
        interface_model = build_interface_model()
        _, task_options = normalize_task_execution_payload(
            [TASK_B_COPY],
            {},
            interface_model,
        )
        self.assertEqual(task_options[TASK_B_COPY]["OptAlpha"], "Red")


if __name__ == "__main__":
    unittest.main()
