"""雷电 VBox 运行时被修复工具修残后的识别与补全。目录形状照抄 2026-09-12 实测。"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.utils.emulator2.vbox import (
    VBOX_RUNTIME_SENTINELS,
    complete_vbox_runtime,
    missing_runtime_sentinels,
)

#: 修复工具删剩下的核心文件（当天 ldplayer9box 里 162 个中的代表）。
CORE = (
    "Ld9BoxSVC.exe",
    "Ld9BoxHeadless.exe",
    "VBoxC.dll",
    "VBoxVMM.dll",
    "x86/VBoxClient-x86.dll",
)
#: 随安装自带的 vbox64：只有 GPU 那一套。
VBOX64 = (
    "libOpenglRender2.dll",
    "host_manager2.dll",
    "fastpipe2.dll",
    "GLES_V2.dll",
    "EGL.dll",
)
#: 修复工具解压出的 vbox：完整运行时，还多 x86 的 CRT。
VBOX_FULL = CORE + VBOX64 + ("x86/ucrtbase.dll", "msvcp140.dll")


def _touch(root: Path, names, payload: bytes = b"x") -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


class MissingSentinelsTest(unittest.TestCase):
    def test_complete_runtime_reports_nothing(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            _touch(runtime, CORE + VBOX_RUNTIME_SENTINELS)
            self.assertEqual(missing_runtime_sentinels(runtime), [])

    def test_repair_tool_leftover_reports_the_gpu_libraries(self) -> None:
        with TemporaryDirectory() as tmp:
            runtime = Path(tmp)
            _touch(runtime, CORE)
            self.assertEqual(
                missing_runtime_sentinels(runtime), list(VBOX_RUNTIME_SENTINELS)
            )


class CompleteRuntimeTest(unittest.TestCase):
    def test_fills_from_vbox64_when_that_is_all_the_install_has(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, install = root / "ldplayer9box", root / "LDPlayer14"
            _touch(runtime, CORE)
            _touch(install / "vbox64", VBOX64)

            copied = complete_vbox_runtime(runtime, install)

            self.assertEqual(sorted(copied), sorted(VBOX64))
            self.assertEqual(missing_runtime_sentinels(runtime), [])

    def test_prefers_the_full_vbox_extraction_and_never_overwrites(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, install = root / "ldplayer9box", root / "LDPlayer14"
            _touch(runtime, CORE, payload=b"in-use-original")
            _touch(install / "vbox", VBOX_FULL, payload=b"fresh")
            _touch(install / "vbox64", VBOX64, payload=b"shipped")

            copied = complete_vbox_runtime(runtime, install)

            # 核心文件一个没动（正被在跑的虚拟机映射着）
            for name in CORE:
                self.assertEqual((runtime / name).read_bytes(), b"in-use-original")
            # GPU 库来自完整解压，不再从 vbox64 重复拷
            self.assertEqual((runtime / "libOpenglRender2.dll").read_bytes(), b"fresh")
            expected = {str(Path(name)) for name in set(VBOX_FULL) - set(CORE)}
            self.assertEqual(set(copied), expected)
            self.assertEqual(missing_runtime_sentinels(runtime), [])

    def test_no_source_dirs_copies_nothing_and_stays_missing(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime, install = root / "ldplayer9box", root / "LDPlayer14"
            _touch(runtime, CORE)
            install.mkdir()

            self.assertEqual(complete_vbox_runtime(runtime, install), [])
            self.assertEqual(
                missing_runtime_sentinels(runtime), list(VBOX_RUNTIME_SENTINELS)
            )


if __name__ == "__main__":
    unittest.main()
