"""MaaFW 项目指纹只在真有候选更新时才算。

``project_fingerprint`` 对整个项目 rglob + sha256（M9A 660MB 约 1s），而默认
``AutoUpdateMode=BeforeRun`` 让每次 MaaFW 运行都先走一遍更新检查。以前它在
「interface 没声明版本」和远端发现之前就无条件执行，绝大多数运行（无更新）
白付这一次；现在推迟到 ``apply_maafw_project_update`` 里、下载前算一次并绑定
到 plan 上，apply 事务锁内再算一次核对，之后只在提交后算「应用后」指纹。
"""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.task.MaaFW.tools.core.automas_maafw_project_update import updater
from app.task.MaaFW.tools.core.automas_maafw_project_update.updater import (
    MaaFWProjectUpdateCandidate,
    MaaFWProjectUpdateDiscovery,
    update_maafw_project_if_needed,
)


class _FingerprintSpy:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, project_path: Path) -> str:
        self.calls += 1
        return "f" * 64


@pytest.fixture
def fingerprint_spy(monkeypatch: pytest.MonkeyPatch) -> _FingerprintSpy:
    spy = _FingerprintSpy()
    monkeypatch.setattr(updater, "project_fingerprint", spy)
    return spy


def _discover(result: tuple[Any, Any, Any]):
    async def fake(*_args: Any, **_kwargs: Any) -> tuple[Any, Any, Any]:
        return result

    return fake


@pytest.mark.asyncio
async def test_version_missing_skips_without_fingerprint(
    tmp_path: Path, fingerprint_spy: _FingerprintSpy
) -> None:
    result = await update_maafw_project_if_needed(tmp_path, SimpleNamespace(version=""))

    assert result.checked is False
    assert fingerprint_spy.calls == 0


@pytest.mark.asyncio
async def test_no_update_found_skips_fingerprint(
    tmp_path: Path, fingerprint_spy: _FingerprintSpy, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        updater,
        "_discover_project_update_detailed",
        _discover((None, None, "未配置更新源")),
    )

    result = await update_maafw_project_if_needed(
        tmp_path, SimpleNamespace(version="v1.0.0")
    )

    assert result.updated is False
    assert fingerprint_spy.calls == 0


@pytest.mark.asyncio
async def test_candidate_found_leaves_fingerprint_to_apply(
    tmp_path: Path, fingerprint_spy: _FingerprintSpy, monkeypatch: pytest.MonkeyPatch
) -> None:
    """有候选时指纹由 apply 负责：update_if_needed 自己一次也不算。"""

    candidate = MaaFWProjectUpdateCandidate(
        source="github", version="v1.1.0", download_url="https://example.com/p.zip"
    )
    discovery = MaaFWProjectUpdateDiscovery(
        source="mirrorchyan", version="v1.1.0", candidate=candidate
    )
    monkeypatch.setattr(
        updater,
        "_discover_project_update_detailed",
        _discover((discovery, None, None)),
    )
    seen: dict[str, Any] = {}

    async def fake_apply(project_path: Path, cand: Any, **_kwargs: Any) -> dict:
        seen["fingerprint_calls_before_apply"] = fingerprint_spy.calls
        seen["candidate_fingerprint"] = cand.project_fingerprint
        return {"operationId": "op", "planId": cand.plan_id}

    monkeypatch.setattr(updater, "apply_maafw_project_update", fake_apply)

    result = await update_maafw_project_if_needed(
        tmp_path, SimpleNamespace(version="v1.0.0")
    )

    assert result.updated is True
    assert seen["fingerprint_calls_before_apply"] == 0
    assert seen["candidate_fingerprint"] is None
    assert candidate.plan_id, "plan_id 仍由 update_if_needed 分配"
