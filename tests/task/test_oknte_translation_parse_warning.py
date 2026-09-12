"""OK-NTE：翻译文件解析失败要留告警，不再静默返回空表。"""

from loguru import logger as loguru_logger

from app.task.OkNte.config_schema import _parse_mo_file, _parse_po_file, _parse_ts_file


def _capture_warnings():
    records: list[str] = []
    handler_id = loguru_logger.add(
        lambda message: records.append(message.record["message"]), level="WARNING"
    )
    return records, handler_id


def test_missing_po_file_returns_empty_and_warns(tmp_path):
    records, handler_id = _capture_warnings()
    try:
        assert _parse_po_file(tmp_path / "ok.po") == {}
    finally:
        loguru_logger.remove(handler_id)
    assert any("ok.po" in r and "解析 OK-NTE 翻译文件失败" in r for r in records)


def test_missing_mo_file_returns_empty_and_warns(tmp_path):
    records, handler_id = _capture_warnings()
    try:
        assert _parse_mo_file(tmp_path / "ok.mo") == {}
    finally:
        loguru_logger.remove(handler_id)
    assert any("ok.mo" in r for r in records)


def test_broken_ts_file_returns_empty_and_warns(tmp_path):
    ts_path = tmp_path / "zh_CN.ts"
    ts_path.write_text("<TS><message><source>a</source>", encoding="utf-8")
    records, handler_id = _capture_warnings()
    try:
        assert _parse_ts_file(ts_path) == {}
    finally:
        loguru_logger.remove(handler_id)
    assert any("zh_CN.ts" in r for r in records)


def test_valid_po_file_still_parses(tmp_path):
    po_path = tmp_path / "ok.po"
    po_path.write_text('msgid "Daily"\nmsgstr "日常"\n', encoding="utf-8")
    assert _parse_po_file(po_path) == {"Daily": "日常"}
