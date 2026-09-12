"""MFW 专项各子进程共用的宿主环境隔离口径。

运行池的 uv / pip、worker、项目 agent 与 agent 的 pip 检测都从 ``os.environ`` 复制一份再改，
此前每处各维护一份 ``pop`` 名单且互不一致：``PYTHONHOME`` / ``PYTHONUSERBASE`` 都剔了，
``PYTHONWARNINGS=error``（第一条 DeprecationWarning 就崩）、``PYTHONOPTIMIZE``（断言被删）、
``PYTHONINSPECT``（进程退不出）、``PYTHONDEVMODE`` 却原样穿过去。受 Runtime 监督时这些已在
Runtime 边界按增补 2 C20 剔除，但旧启动链路（``AUTO_MAS_RUNTIME_MODE=off``）与开发态直接继承
宿主环境，后端必须自己守住同一条线。

口径与 Runtime 一致：所有 ``PYTHON`` 开头的宿主变量默认不放行（新版本解释器新增的也不放行），
只保留不改变「加载什么代码、以什么模式运行」的编码 / 缓冲 / 字节码落盘 / 用户站点开关；
激活中的虚拟环境标记、pip 的安装位置覆盖、颜色强制与 Rust 调试变量一并剔除。
``PIP_INDEX_URL`` / ``AUTO_MAS_*`` 等用户显式给 MFW 专项的开关不在名单内，仍按各处既有约定生效。
"""

from __future__ import annotations

import os
from collections.abc import Mapping

#: 宿主 ``PYTHON*`` 变量里仅有的放行项。
PASSTHROUGH_PYTHON_KEYS: frozenset[str] = frozenset(
    {
        "PYTHONIOENCODING",
        "PYTHONUTF8",
        "PYTHONUNBUFFERED",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONNOUSERSITE",
    }
)

#: ``PYTHON*`` 之外同样不从宿主继承的变量。
ISOLATED_HOST_KEYS: frozenset[str] = frozenset(
    {
        # 启动链路（Runtime → uv run → 后端）或用户终端里激活的环境指向：交给 uv / pip 前
        # 必须剔除，否则外部 uv 会把项目环境解析到 MAS 自己的 venv 上。
        "VIRTUAL_ENV",
        "VIRTUAL_ENV_PROMPT",
        "UV_PROJECT_ENVIRONMENT",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "__PYVENV_LAUNCHER__",
        # pip 的安装位置覆盖会把包装到 venv 之外。
        "PIP_TARGET",
        "PIP_PREFIX",
        "PIP_USER",
        # FORCE_COLOR / CLICOLOR_FORCE 会压过 uv 的 --color never 往日志里塞 ANSI 序列；
        # RUST_LOG 不加 -v 也会让 uv 往 stderr 倾倒 TRACE。
        "FORCE_COLOR",
        "CLICOLOR_FORCE",
        "CLICOLOR",
        "NO_COLOR",
        "RUST_LOG",
        "RUST_BACKTRACE",
        "RUST_MIN_STACK",
    }
)


def is_isolated_host_key(name: str) -> bool:
    """按 Windows 的大小写不敏感语义判断一个宿主变量是否不得下传。"""

    upper = name.upper()
    if upper.startswith("PYTHON"):
        return upper not in PASSTHROUGH_PYTHON_KEYS
    return upper in ISOLATED_HOST_KEYS


def strip_host_python_environment(
    environment: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """返回剔除了宿主 Python / uv 相关变量的环境副本；缺省从 ``os.environ`` 复制。

    调用方在返回值上再显式设置自己需要的 ``PYTHONPATH`` / ``VIRTUAL_ENV`` 等，
    这样每处只需要声明「我要什么」，不必各自记住「要剔什么」。
    """

    source = os.environ if environment is None else environment
    return {
        name: value for name, value in source.items() if not is_isolated_host_key(name)
    }
