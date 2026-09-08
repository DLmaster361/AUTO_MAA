"""log_box 采集工厂

顶层入口：``from app.log_box import log_box``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Optional, Union

from .collect import LogCollect

PathLike = Union[str, Path]


class LogBox:
    """log_box 采集工厂：get_collect 创建日志采集会话"""

    def get_collect(
        self,
        paths: Optional[Union[PathLike, Iterable[PathLike]]] = None,
        *,
        sink: Optional[Callable[[str, str, float], None]] = None,
        start_from_end: bool = True,
        rotated_name: Optional[str] = None,
    ) -> LogCollect:
        """创建日志采集会话

        Args:
            paths: 日志位置（单个或多个文件）；None 时回退到环境变量
                ``MAS_SCRIPT_LOG_PATH``（MAS 配置的日志位置）。
            sink: MAS 进程宿主注入的 push_log 写入回调 sink(log_type, text, ts)；
                缺省时结果走 @@LOGBOX@@ 标记回传（脚本子进程宿主）。
            start_from_end: 是否从文件末尾起始采集（仅采集会话内新增内容）。
            rotated_name: 轮转文件名的 strftime 模板（完整文件名，相对日志所在
                目录，如 ``ok-script.%Y-%m-%d.log``、``log.txt.%Y-%m-%d``）。
                缺省按 inode 在同目录找回被重命名的旧日志（与 LogMonitor 同
                逻辑），重命名式滚动无需声明；日期式滚动命名应声明（文件系统
                不提供 inode 时这是唯一兜底），声明后只按模板探测，缺省仅回退
                ``.bak`` 约定猜测。

        Returns:
            LogCollect 实例
        """
        return LogCollect(
            paths, sink=sink, start_from_end=start_from_end, rotated_name=rotated_name
        )


log_box = LogBox()
