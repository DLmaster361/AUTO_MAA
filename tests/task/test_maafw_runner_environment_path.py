"""MaaFW worker 子进程的源码解析路径回归

受 AUTO-MAS-Runtime 监督时后端的工作目录是 `<app-root>`，源码在 `<app-root>/repo/`，
而 `<app-root>` 下还躺着安装包自带的那棵源码树（只随整包安装更新）。worker 以
`python -m app.task...worker` 启动，`python -m` 会把 cwd 插到 `sys.path[0]` 并排在
`PYTHONPATH` 之前，于是 worker 会导入安装包那份旧 `app/` 包、跑上一个版本的引擎代码，
而且不报错——引擎侧的修复因此永远等不到热更新生效。

`build_runner_environment` 必须同时做到两件事：把调用方给的源码根写进 `PYTHONPATH`，
以及禁掉 cwd 前置，让 `PYTHONPATH` 说了算。
"""

import os
from pathlib import Path

from app.task.MaaFW.tools.core.automas_maafw_runner.environment import (
    build_runner_environment,
)


def test_import_paths_land_in_pythonpath(tmp_path: Path) -> None:
    """调用方给的代码路径要原样进 PYTHONPATH。"""

    venv = tmp_path / "venv"
    source_root = tmp_path / "repo"
    source_root.mkdir()

    env = build_runner_environment(venv, import_paths=[source_root])

    assert env["PYTHONPATH"].split(os.pathsep)[0] == str(source_root.resolve())


def test_cwd_is_not_prepended_to_sys_path(tmp_path: Path) -> None:
    """必须设 PYTHONSAFEPATH，否则 cwd 下的旧 app/ 会盖掉 PYTHONPATH 里的源码根。"""

    env = build_runner_environment(tmp_path / "venv", import_paths=[tmp_path])

    assert env["PYTHONSAFEPATH"] == "1"


def test_missing_import_path_is_dropped(tmp_path: Path) -> None:
    """不存在的路径不写进 PYTHONPATH，避免把空目录当成源码根。"""

    env = build_runner_environment(tmp_path / "venv", import_paths=[tmp_path / "nope"])

    assert "PYTHONPATH" not in env
