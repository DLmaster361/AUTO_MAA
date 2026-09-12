#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

#   Contact: DLmaster_361@163.com

"""BAAH 配置托管的最小回归测试。

覆盖 BAAH 专项最容易出错的两处契约：配置名的解析与校验、
运行前托管写入与运行后恢复的完整往返（含配置文件原本不存在的情况）。
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pytest

from app.task.BAAH.tools.config_manager import (
    MANAGED_SOFTWARE_VALUES,
    MANAGED_USER_VALUES,
    apply_managed_config,
    latest_log_file,
    resolve_config_name,
    resolve_user_config_path,
    restore_managed_config,
)


class TestResolveConfigName:
    """配置名解析与校验"""

    def test_strips_json_suffix_and_spaces(self) -> None:
        assert resolve_config_name("  国服2.json  ") == "国服2"
        assert resolve_config_name("国服2") == "国服2"

    @pytest.mark.parametrize("value", ["", "   ", ".json", ".", ".."])
    def test_rejects_empty_names(self, value: str) -> None:
        with pytest.raises(ValueError):
            resolve_config_name(value)

    @pytest.mark.parametrize("value", [r"..\evil", "../evil", r"a\b", "a/b"])
    def test_rejects_path_separators(self, value: str) -> None:
        with pytest.raises(ValueError):
            resolve_config_name(value)

    def test_resolve_user_config_path_appends_suffix(self, tmp_path: Path) -> None:
        path = resolve_user_config_path(tmp_path, "国服2.json")
        assert path == tmp_path / "国服2.json"


class TestManagedConfigRoundTrip:
    """托管写入与恢复"""

    def test_writes_managed_values_and_restores_original(
        self, tmp_path: Path
    ) -> None:
        user_path = tmp_path / "BAAH_CONFIGS" / "国服2.json"
        user_path.parent.mkdir(parents=True)
        original = {"SERVER_TYPE": "CN", "CLOSE_BAAH_FINISH": False, "KEEP_ME": 7}
        user_path.write_text(json.dumps(original), encoding="utf-8")

        software_path = tmp_path / "DATA" / "CONFIGS" / "software_config.json"
        software_path.parent.mkdir(parents=True)
        software_original = {"LANGUAGE": "zh_CN", "SAVE_LOG_TO_FILE": False}
        software_path.write_text(json.dumps(software_original), encoding="utf-8")

        backup = apply_managed_config(user_path, software_path)

        # 托管项已写入，且原有字段未被破坏
        managed_user = json.loads(user_path.read_text(encoding="utf-8"))
        for key, value in MANAGED_USER_VALUES.items():
            assert managed_user[key] == value
        assert managed_user["SERVER_TYPE"] == "CN"
        assert managed_user["KEEP_ME"] == 7

        managed_software = json.loads(software_path.read_text(encoding="utf-8"))
        for key, value in MANAGED_SOFTWARE_VALUES.items():
            assert managed_software[key] == value
        assert managed_software["LANGUAGE"] == "zh_CN"

        restore_managed_config(backup)

        # 恢复为运行前的原值
        assert json.loads(user_path.read_text(encoding="utf-8")) == original
        assert (
            json.loads(software_path.read_text(encoding="utf-8")) == software_original
        )

    def test_removes_config_created_during_run(self, tmp_path: Path) -> None:
        """运行前不存在的配置文件，恢复阶段应被删除而不是留下半成品"""

        user_path = tmp_path / "BAAH_CONFIGS" / "新建.json"
        backup = apply_managed_config(user_path, None)
        assert user_path.is_file()

        restore_managed_config(backup)
        assert not user_path.exists()

    def test_written_file_has_no_bom(self, tmp_path: Path) -> None:
        """BAAH 带 BOM 会静默按默认值运行，写盘必须是无 BOM 的 UTF-8"""

        user_path = tmp_path / "BAAH_CONFIGS" / "国服2.json"
        apply_managed_config(user_path, None)

        raw = user_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        json.loads(raw.decode("utf-8"))

    def test_restore_is_safe_without_apply(self, tmp_path: Path) -> None:
        from app.task.BAAH.tools.config_manager import ManagedConfigBackup

        restore_managed_config(ManagedConfigBackup(user_config_path=tmp_path / "x.json"))

    def test_restore_accepts_none_backup(self) -> None:
        """任务在托管配置写入前被中止时，收尾阶段会拿到 None，不应抛异常"""
        restore_managed_config(None)

    def test_applied_is_false_when_nothing_needed_changing(
        self, tmp_path: Path
    ) -> None:
        """配置本来就是托管值时不写文件，收尾阶段也无需恢复"""

        user_path = tmp_path / "BAAH_CONFIGS" / "已托管.json"
        user_path.parent.mkdir(parents=True)
        user_path.write_text(json.dumps(dict(MANAGED_USER_VALUES)), encoding="utf-8")

        backup = apply_managed_config(user_path, None)

        assert backup.applied is False
        assert restore_managed_config(backup) == []

    def test_rolls_back_user_config_when_software_write_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """软件配置写入失败时，已经落盘的用户配置必须回滚

        调用方只在写入成功后才会拿到备份对象；这里不回滚的话，用户配置就会
        带着托管值留下来，而收尾阶段已经无从恢复。
        """

        user_path = tmp_path / "BAAH_CONFIGS" / "国服2.json"
        user_path.parent.mkdir(parents=True)
        original = {"SERVER_TYPE": "CN", "KEEP_ME": 7}
        user_path.write_text(json.dumps(original), encoding="utf-8")

        software_path = tmp_path / "DATA" / "CONFIGS" / "software_config.json"

        import app.task.BAAH.tools.config_manager as config_manager

        real_write = config_manager.write_json

        def flaky_write(path: Path, data: dict) -> None:
            if path == software_path:
                raise OSError("模拟软件配置不可写")
            real_write(path, data)

        monkeypatch.setattr(config_manager, "write_json", flaky_write)

        with pytest.raises(OSError):
            apply_managed_config(user_path, software_path)

        assert json.loads(user_path.read_text(encoding="utf-8")) == original

    def test_reports_restore_failure_instead_of_swallowing_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """恢复失败必须回传给调用方：静默返回会让用户配置一直带着托管值"""

        user_path = tmp_path / "BAAH_CONFIGS" / "国服2.json"
        user_path.parent.mkdir(parents=True)
        user_path.write_text(json.dumps({"KEEP_ME": 7}), encoding="utf-8")

        backup = apply_managed_config(user_path, None)

        import app.task.BAAH.tools.config_manager as config_manager

        def boom(path: Path, data: dict) -> None:
            raise OSError("模拟配置文件只读")

        monkeypatch.setattr(config_manager, "write_json", boom)

        failures = restore_managed_config(backup)

        assert len(failures) == 1
        assert "国服2.json" in failures[0]


class TestLatestLogFile:
    """日志文件定位"""

    def test_picks_newest_after_start_time(self, tmp_path: Path) -> None:
        old_log = tmp_path / "log_2026-01-01-00-00-00.txt"
        old_log.write_text("old", encoding="utf-8")

        start_at = time.time()
        new_log = tmp_path / "log_2026-01-01-00-00-01.txt"
        new_log.write_text("new", encoding="utf-8")

        # 显式设定时间戳：同一秒内连续创建的两个文件在部分文件系统上
        # 无法靠写入顺序区分先后
        os.utime(old_log, (start_at - 10, start_at - 10))
        os.utime(new_log, (start_at + 1, start_at + 1))

        assert latest_log_file(tmp_path, start_at) == new_log

    def test_returns_none_when_no_recent_log(self, tmp_path: Path) -> None:
        (tmp_path / "log_old.txt").write_text("old", encoding="utf-8")
        assert latest_log_file(tmp_path, time.time() + 60) is None

    def test_returns_none_for_missing_dir(self, tmp_path: Path) -> None:
        assert latest_log_file(tmp_path / "missing", 0.0) is None


class TestLogTimestampRange:
    """日志时间戳切片

    ``BAAH_LOG_TIME_RANGE`` 是 LogMonitor 对整行做的**字符切片**，不是按分隔符
    分词后的字段下标。切片写错会让每一行的时间戳都解析失败，LogMonitor 会因此
    丢弃全部日志行：任务照常运行，但界面收不到任何日志，也永远判不出成功标记。
    """

    # 真实日志行（BAAH 2.4.13 实测输出）
    REAL_LINE = "2.4.13 - 24:19 - INFO : 执行任务EnterGame"

    def test_slices_timestamp_from_real_line(self) -> None:
        from app.task.BAAH.AutoProxy import (
            BAAH_LOG_TIME_FORMAT,
            BAAH_LOG_TIME_RANGE,
        )

        start, end = BAAH_LOG_TIME_RANGE
        raw = self.REAL_LINE[start:end]

        assert raw == "24:19"

        parsed = datetime.strptime(raw, BAAH_LOG_TIME_FORMAT)
        assert (parsed.minute, parsed.second) == (24, 19)

    def test_logmonitor_start_filter_accepts_line(self) -> None:
        """模拟 LogMonitor 的起始过滤：真实日志行必须能被判为「晚于启动时刻」"""

        from app.task.BAAH.AutoProxy import (
            BAAH_LOG_TIME_FORMAT,
            BAAH_LOG_TIME_RANGE,
        )
        from app.utils.LogMonitor import strptime as monitor_strptime

        start, end = BAAH_LOG_TIME_RANGE
        log_start_time = datetime(2026, 9, 12, 17, 24, 16)

        parsed = monitor_strptime(
            self.REAL_LINE[start:end],
            BAAH_LOG_TIME_FORMAT,
            datetime(2026, 9, 12, 17, 24, 20),
        )

        assert parsed > log_start_time
