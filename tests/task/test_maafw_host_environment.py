"""MFW 专项各子进程共用的宿主环境隔离口径（与 Runtime 增补 2 C20 同一套名单）的纯逻辑回归。

运行池的 uv / pip、worker、agent 与 agent 的 pip 检测此前各自维护一份 ``os.environ.pop`` 名单，
彼此不一致；本文件只覆盖共用的过滤函数与各处环境构造的结果，不起子进程、不联网。
"""

from pathlib import Path

import app.core  # noqa: F401  # 初始化宿主配置
from app.task.MaaFW.tools.core.automas_maafw_agent_env import env as agent_env_module
from app.task.MaaFW.tools.core.automas_maafw_runner import (
    environment as runner_environment,
)
from app.task.MaaFW.tools.core.automas_maafw_runtime_pool import (
    installer as installer_module,
)
from app.task.MaaFW.tools.core.automas_maafw_runtime_pool.host_environment import (
    is_isolated_host_key,
    strip_host_python_environment,
)

_SCRUBBED = {
    "PYTHONHOME": r"C:\bogus",
    "PYTHONPATH": r"C:\bogus\lib",
    "pythonsafepath": "1",
    "PYTHONWARNINGS": "error",
    "PYTHONOPTIMIZE": "2",
    "PYTHONINSPECT": "1",
    "PYTHONDEVMODE": "1",
    "PYTHON_COLORS": "1",
    "PYTHONUSERBASE": r"C:\bogus\user",
    "VIRTUAL_ENV": r"C:\bogus\venv",
    "VIRTUAL_ENV_PROMPT": "(bogus)",
    "UV_PROJECT_ENVIRONMENT": r"C:\bogus\venv",
    "CONDA_PREFIX": r"C:\bogus\conda",
    "CONDA_DEFAULT_ENV": "base",
    "PIP_TARGET": r"C:\bogus\target",
    "PIP_PREFIX": r"C:\bogus\prefix",
    "PIP_USER": "1",
    "FORCE_COLOR": "1",
    "CLICOLOR_FORCE": "1",
    "NO_COLOR": "1",
    "RUST_LOG": "trace",
    "RUST_BACKTRACE": "full",
}

_PASSTHROUGH = {
    "PYTHONIOENCODING": "utf-8",
    "PYTHONUTF8": "1",
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "PYTHONNOUSERSITE": "1",
    "PATH": r"C:\Windows\system32",
    "HTTPS_PROXY": "http://proxy.example:8080",
    "NO_PROXY": "127.0.0.1,localhost",
    "AUTO_MAS_UV_INDEX_URL": "https://mirror.example/simple",
    "PIP_INDEX_URL": "https://mirror.example/simple",
    "SSL_CERT_FILE": r"C:\certs\ca.pem",
}


def test_is_isolated_host_key_matches_case_insensitively() -> None:
    for name in _SCRUBBED:
        assert is_isolated_host_key(name), name
        assert is_isolated_host_key(name.lower()), name
    for name in _PASSTHROUGH:
        assert not is_isolated_host_key(name), name
        assert not is_isolated_host_key(name.lower()), name


def test_strip_host_python_environment_filters_given_mapping() -> None:
    result = strip_host_python_environment({**_SCRUBBED, **_PASSTHROUGH})
    assert set(result) == set(_PASSTHROUGH)
    assert result == _PASSTHROUGH


def test_strip_host_python_environment_defaults_to_process_environment(
    monkeypatch,
) -> None:
    for name, value in {**_SCRUBBED, **_PASSTHROUGH}.items():
        monkeypatch.setenv(name, value)
    result = strip_host_python_environment()
    for name in _SCRUBBED:
        assert name.upper() not in {key.upper() for key in result}, name
    for name, value in _PASSTHROUGH.items():
        assert result[name] == value, name


def test_pool_process_environment_uses_shared_policy(monkeypatch) -> None:
    for name, value in {**_SCRUBBED, **_PASSTHROUGH}.items():
        monkeypatch.setenv(name, value)
    env = installer_module._clean_process_environment()
    for name in _SCRUBBED:
        assert name.upper() not in {key.upper() for key in env}, name
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PIP_INDEX_URL"] == "https://mirror.example/simple"


def test_runner_environment_does_not_inherit_host_python_variables(
    tmp_path, monkeypatch
) -> None:
    for name, value in {**_SCRUBBED, **_PASSTHROUGH}.items():
        monkeypatch.setenv(name, value)
    venv = tmp_path / "runner-venv"
    (venv / "Scripts").mkdir(parents=True)
    source_root = tmp_path / "src"
    source_root.mkdir()
    env = runner_environment.build_runner_environment(venv, import_paths=[source_root])
    assert env["PYTHONPATH"] == str(source_root.resolve())
    assert env["PYTHONSAFEPATH"] == "1"
    assert env["VIRTUAL_ENV"] == str(venv.resolve())
    for name in ("PYTHONHOME", "PYTHONWARNINGS", "PYTHONOPTIMIZE", "CONDA_PREFIX"):
        assert name not in env, name
    assert env["PYTHONUTF8"] == "1"


def test_agent_pip_environment_uses_shared_policy(tmp_path, monkeypatch) -> None:
    for name, value in {**_SCRUBBED, **_PASSTHROUGH}.items():
        monkeypatch.setenv(name, value)
    project = Path(tmp_path / "project")
    env = agent_env_module._build_agent_env_for_pip(project)
    assert env["PYTHONPATH"] == str(project)
    for name in ("PYTHONHOME", "PYTHONWARNINGS", "PYTHONSAFEPATH", "VIRTUAL_ENV"):
        assert name not in env, name
    assert env["PIP_INDEX_URL"] == "https://mirror.example/simple"
