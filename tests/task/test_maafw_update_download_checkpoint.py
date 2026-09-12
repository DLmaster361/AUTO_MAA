"""更新包下载循环不再每块同步读一遍操作状态文件。

以前每收 64KB 就 ``operation.read()`` 一次（同步 read_text + 整读 journal 逐行
json.loads），只为看暂停/取消标志——而那两个标志的唯一写入方（计划/暂停/
恢复 API）从未接线、已随死代码删除。现在一次下载尝试只在开头读一次状态
（取 attempt 号），每 1MB 的 fsync + 元数据原子改写也挪进了线程。
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest

from app.task.MaaFW.tools.core.automas_maafw_project_update import transport
from app.task.MaaFW.tools.core.automas_maafw_project_update.state import (
    UpdateOperationStore,
)

CHUNKS = 40  # 40 × 64KB = 2.5MB：跨过两次 1MB 检查点


class _FakeResponse:
    status_code = 200
    headers: dict[str, str] = {}
    url = "https://example.com/pkg.zip"

    async def aiter_bytes(self, chunk_size: int):
        for _ in range(CHUNKS):
            yield b"x" * transport.CHUNK_SIZE

    async def aread(self) -> bytes:
        return b""


class _FakeStream:
    async def __aenter__(self) -> _FakeResponse:
        return _FakeResponse()

    async def __aexit__(self, *_exc: Any) -> None:
        return None


class _FakeClient:
    def __init__(self, **_kwargs: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    def stream(self, _method: str, _url: str, *, headers: dict) -> _FakeStream:
        return _FakeStream()


def test_download_reads_operation_state_once_per_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(transport.httpx, "AsyncClient", _FakeClient)
    store = UpdateOperationStore.create(root=tmp_path / "ops", operation_id="a" * 32)
    reads = {"count": 0}
    original_read = store.read

    def counting_read() -> dict[str, Any]:
        reads["count"] += 1
        return original_read()

    monkeypatch.setattr(store, "read", counting_read)
    checkpoints = {"count": 0}
    original_checkpoint = transport._write_checkpoint

    def counting_checkpoint(*args: Any) -> None:
        checkpoints["count"] += 1
        original_checkpoint(*args)

    monkeypatch.setattr(transport, "_write_checkpoint", counting_checkpoint)

    outcome = asyncio.run(
        transport.download_resumable(
            source="github",
            version="v1.0.0",
            download_url="https://example.com/pkg.zip",
            cache_root=tmp_path / "cache",
            operation=store,
        )
    )

    assert outcome.size == CHUNKS * transport.CHUNK_SIZE
    assert outcome.path.is_file()
    assert reads["count"] <= 2, "状态文件只该在尝试开头读一次，不是每块一次"
    assert checkpoints["count"] == 2, "2.5MB 应落两次 1MB 检查点"
