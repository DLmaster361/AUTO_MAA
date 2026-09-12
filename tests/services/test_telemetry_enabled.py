"""遥测开关读取: 缺失/空文件按开启, 损坏文件按关闭。"""

import json
import tempfile
import unittest
from pathlib import Path

from app.services.telemetry import is_telemetry_enabled


class TelemetryEnabledTest(unittest.TestCase):
    def test_missing_or_empty_config_defaults_to_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Config.json"
            self.assertTrue(is_telemetry_enabled(path))
            path.write_text("", encoding="utf-8")
            self.assertTrue(is_telemetry_enabled(path))

    def test_corrupt_config_is_treated_as_disabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Config.json"
            path.write_text('{"Function": {', encoding="utf-8")
            self.assertFalse(is_telemetry_enabled(path))

    def test_explicit_switch_is_respected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Config.json"
            path.write_text(
                json.dumps({"Function": {"IfEnableTelemetry": False}}),
                encoding="utf-8",
            )
            self.assertFalse(is_telemetry_enabled(path))
            path.write_text(json.dumps({"Function": {}}), encoding="utf-8")
            self.assertTrue(is_telemetry_enabled(path))
