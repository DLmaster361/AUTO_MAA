"""通用目录删除原语 `force_rmtree` 的纯逻辑回归测试

脚本配置目录里可能带脚本自己的版本库，git 在 Windows 上会把 `.git/objects/pack/*`
标记为只读；`shutil.rmtree(..., ignore_errors=True)` 删不掉这类文件且静默跳过，
残留文件随后会让 `copytree(..., dirs_exist_ok=True)` 覆盖时抛 `PermissionError`，
配置既没复原、任务也被记成异常。
"""

import os
import stat
from pathlib import Path

from app.utils.io import force_rmtree


def _write_readonly(path: Path) -> None:
    """按 git 的做法把文件标成只读（Windows 上即 FILE_ATTRIBUTE_READONLY）。"""

    path.write_bytes(b"PACK")
    os.chmod(path, stat.S_IREAD)


def test_removes_tree_containing_readonly_files(tmp_path: Path) -> None:
    """目录树里有只读文件时也能整体删掉，不留下残留。"""

    pack_dir = tmp_path / "configs" / ".git" / "objects" / "pack"
    pack_dir.mkdir(parents=True)
    for suffix in ("idx", "pack", "rev"):
        _write_readonly(pack_dir / f"pack-aabb.{suffix}")
    (tmp_path / "configs" / "Basic Options.json").write_text("{}", encoding="utf-8")

    force_rmtree(tmp_path / "configs")

    assert not (tmp_path / "configs").exists()


def test_missing_path_is_a_noop(tmp_path: Path) -> None:
    """路径不存在时不抛异常，重复调用幂等。"""

    force_rmtree(tmp_path / "not-exists")
    force_rmtree(tmp_path / "not-exists")

    assert not (tmp_path / "not-exists").exists()
