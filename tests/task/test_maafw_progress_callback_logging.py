"""进度回调抛错要留痕，不能再静默吞掉。

五处 ``try: callback(event) except Exception: return`` 曾把回调里的
``RuntimeError: no running event loop`` 完全藏起来，表面只剩一句「…失败」。
现在仍然不让回调拖垮主流程，但会 ``warning`` 一条带堆栈的日志。
"""

import logging
from typing import Any, Callable

import pytest

from app.task.MaaFW.tools.core.automas_maafw_agent_env import env as agent_env
from app.task.MaaFW.tools.core.automas_maafw_project_update import apply, updater
from app.task.MaaFW.tools.core.automas_maafw_runner import environment, service


def _boom(*_args: Any, **_kwargs: Any) -> None:
    raise RuntimeError("no running event loop")


CASES: list[tuple[str, Callable[[], None]]] = [
    (
        "updater._report_progress",
        lambda: updater._report_progress(_boom, "checking", message="m"),
    ),
    ("apply._emit", lambda: apply._emit(_boom, "staged", {"planId": "p"})),
    (
        "environment._report_environment_progress",
        lambda: environment._report_environment_progress(_boom, "s", "running", "m"),
    ),
    (
        "service._report_project_progress",
        lambda: service._report_project_progress(_boom, "s", "running", "m"),
    ),
    (
        "env._report_agent_progress",
        lambda: agent_env._report_agent_progress(
            _boom, status="running", message="m", percent=0.0, completed=0, total=1
        ),
    ),
]


@pytest.mark.parametrize("name, call", CASES, ids=[case[0] for case in CASES])
def test_callback_failure_is_logged_not_raised(
    name: str, call: Callable[[], None], caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="automas.maafw"):
        call()  # 不得抛出

    records = [r for r in caplog.records if r.name.startswith("automas.maafw")]
    assert len(records) == 1, name
    assert records[0].levelno == logging.WARNING
    assert records[0].exc_info is not None, "要带堆栈，否则还是查不到根因"
    assert "no running event loop" in logging.Formatter().formatException(
        records[0].exc_info
    )
