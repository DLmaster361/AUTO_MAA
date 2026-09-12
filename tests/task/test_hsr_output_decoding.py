"""M7A 输出还原与失败摘要：夹具照抄 2026-09-12 生产历史日志，不臆造字段。"""

import asyncio
from types import SimpleNamespace

from app.task.HSR.tools.log_detect import (
    find_m7a_self_game_stop,
    select_failure_summary_lines,
    unescape_backslash_u,
)
from app.task.HSR.tools.m7a_runtime import M7ARunner
from app.task.HSR.tools.run_model import external_result_failure_summary

# 非中文 ANSI 代码页机器上 M7A stderr 的原样（backslashreplace）。
ESCAPED_ERROR_LINE = (
    "2026-09-12 02:14:35,242 | ERROR | "
    "\\u65e0\\u6cd5\\u8bc6\\u522b\\u5f53\\u524d\\u6e38\\u620f\\u754c\\u9762"
)
ESCAPED_TIMEOUT_LINE = (
    "2026-09-12 02:20:56,152 | ERROR | "
    "\\u83b7\\u53d6\\u5f53\\u524d\\u754c\\u9762\\u8d85\\u65f6"
)

# 中文机器上同一段失败尾巴的样子。
M7A_FAILURE_TAIL = [
    "2026-09-12 02:14:23,178 | WARNING | 未识别出任何界面，请确保游戏画面干净，按ESC后重试",
    "2026-09-12 02:14:27,942 | WARNING | 未识别出任何界面，请确保游戏画面干净，按ESC后重试",
    "2026-09-12 02:14:32,754 | WARNING | 未识别出任何界面，请确保游戏画面干净，按ESC后重试",
    "2026-09-12 02:14:35,242 | ERROR | 当前界面：未知",
    "2026-09-12 02:14:35,242 | ERROR | 无法识别当前游戏界面",
    "2026-09-12 02:14:35,242 | ERROR | 请关闭帧率监控HUD、微星小飞机、游戏加加、HDR或N卡游戏滤镜等等任何可能影响游戏画面的软件",
    "2026-09-12 02:14:35,242 | ERROR | 你可以通过 工具箱-游戏截图 判断当前游戏画面是否被正确获取",
    "2026-09-12 02:14:35,246 | ERROR | 发生错误 无法识别当前游戏界面",
    "2026-09-12 02:14:35,487 | INFO | 错误截图已保存: logs\\screenshots\\error_2026-09-12_02-14-35.png",
    "2026-09-12 02:14:35,488 | INFO | 反馈问题时请附上此截图以协助诊断",
]


def test_unescape_restores_backslashreplace_chinese() -> None:
    assert (
        unescape_backslash_u(ESCAPED_ERROR_LINE)
        == "2026-09-12 02:14:35,242 | ERROR | 无法识别当前游戏界面"
    )


def test_unescape_merges_surrogate_pairs_and_drops_lone_halves() -> None:
    assert unescape_backslash_u("\\ud83d\\ude00 ok") == "😀 ok"
    assert unescape_backslash_u("\\ud83d alone") == "\ufffd alone"


def test_unescape_leaves_plain_text_and_paths_alone() -> None:
    plain = "游戏路径：C:\\users\\me\\StarRail.exe \\update \\u12"
    assert unescape_backslash_u(plain) == plain
    assert unescape_backslash_u("无反斜杠") == "无反斜杠"


def test_failure_summary_leads_with_error_lines_not_warning_spam() -> None:
    picked = select_failure_summary_lines(M7A_FAILURE_TAIL)

    assert picked[0] == "ERROR | 当前界面：未知"
    assert "ERROR | 发生错误 无法识别当前游戏界面" in picked
    assert any(line.startswith("INFO | 错误截图已保存:") for line in picked)
    assert not any("WARNING" in line for line in picked)
    assert not any("反馈问题时请附上此截图" in line for line in picked)


def test_failure_summary_falls_back_to_tail_without_error_lines() -> None:
    lines = [f"line {i}" for i in range(12)]
    assert select_failure_summary_lines(lines) == lines[-8:]
    assert select_failure_summary_lines(lines, limit=3) == lines[-3:]


def test_external_result_failure_summary_uses_error_lines() -> None:
    result = SimpleNamespace(error="\n".join(M7A_FAILURE_TAIL), output="", returncode=1)

    summary = external_result_failure_summary(result)

    assert summary.splitlines()[0] == "ERROR | 当前界面：未知"
    assert "WARNING" not in summary


def test_self_game_stop_marker_detection() -> None:
    lines = [
        "2026-09-12 02:20:55,151 | ERROR | 当前界面：未知",
        "2026-09-12 02:20:56,152 | ERROR | 获取当前界面超时",
    ]
    assert find_m7a_self_game_stop(lines) == lines[-1]
    assert find_m7a_self_game_stop(M7A_FAILURE_TAIL) is None
    assert find_m7a_self_game_stop([]) is None


class _Stream:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def readline(self) -> bytes:
        if not self._chunks:
            return b""
        return self._chunks.pop(0)


def test_runner_unescapes_live_lines_and_keeps_recent_output(tmp_path) -> None:
    seen: list[str] = []
    runner = M7ARunner(tmp_path, log_callback=seen.append)
    stream = _Stream(
        [
            (ESCAPED_TIMEOUT_LINE + "\r\n").encode("utf-8"),
            "2026-09-12 02:20:56,300 | INFO | 游戏终止：StarRail.exe\n".encode("utf-8"),
        ]
    )
    lines: list[str] = []

    asyncio.run(runner._read_stream_live(stream, "M7A stderr", lines))

    assert lines == [
        "2026-09-12 02:20:56,152 | ERROR | 获取当前界面超时",
        "2026-09-12 02:20:56,300 | INFO | 游戏终止：StarRail.exe",
    ]
    assert seen == [f"M7A stderr: {line}" for line in lines]
    assert runner.recent_output_lines == lines
    assert find_m7a_self_game_stop(runner.recent_output_lines) is not None
