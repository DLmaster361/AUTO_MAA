"""全量更新必须清掉资源目录里旧版布局的残留文件。

更新器平时靠自己的清单算「上一版铺了哪些文件」，只删这些，用户自己放进项目的
文件一概不碰。但项目第一次被更新时没有这份清单——用户是直接指到一棵已解压好的
目录，那棵树不是更新器铺的。此时全量包退化成纯覆盖：新版挪走或删掉的文件会原地
留下。

现场是 MaaYYs v3.10.2 → v3.15.5 把 ``resource_pack/base/pipeline/kun28.json`` 挪进
了 ``战斗/`` 子目录，旧的那份留在原地，两份都定义顶层节点 ``困28``，MaaFramework
拒收整个资源包（``key already exists``），项目从此每次运行都失败。

兜底的扫描范围**只有 interface.json 声明的资源包目录**，这里同时钉住这条边界：
包也会铺 ``preset/`` 这类混着用户内容的目录（MXU 把用户自建预设写在那儿），它们
不能被碰；有了清单之后必须走回精确口径。
"""

import json
import zipfile
from pathlib import Path

from app.task.MaaFW.tools.core.automas_maafw_project_update.apply import (
    apply_package_transaction,
)

RESOURCE_DIR = "resource_pack/base"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _interface(version: str) -> str:
    return json.dumps(
        {
            "name": "MaaYYs",
            "version": version,
            "resource": [{"name": "官服2", "path": [f"./{RESOURCE_DIR}"]}],
        },
        ensure_ascii=False,
    )


def _make_package(tmp_path: Path, name: str, files: dict[str, str]) -> Path:
    package_path = tmp_path / f"{name}.zip"
    with zipfile.ZipFile(package_path, "w") as archive:
        for relative, content in files.items():
            archive.writestr(relative, content)
    return package_path


def _apply(project: Path, package: Path, tmp_path: Path) -> dict:
    return apply_package_transaction(
        project,
        package,
        operation_root=tmp_path / "operations",
    )


def _make_project(tmp_path: Path) -> Path:
    """一棵用户自己解压好的旧版项目树：没有更新器清单。"""

    project = tmp_path / "project"
    _write(project / "interface.json", _interface("v3.10.2"))
    _write(project / f"{RESOURCE_DIR}/pipeline/kun28.json", '{"困28": {}}')
    _write(project / f"{RESOURCE_DIR}/pipeline/导航.json", '{"导航": {}}')
    # 包不含的顶层目录：运行期产物与用户数据。
    _write(project / "config/user.json", '{"服": "官服2"}')
    _write(project / "debug/maa.log", "old log")
    return project


def test_full_update_without_baseline_removes_relocated_file(tmp_path: Path) -> None:
    project = _make_project(tmp_path)
    package = _make_package(
        tmp_path,
        "v3.15.5",
        {
            "interface.json": _interface("v3.15.5"),
            f"{RESOURCE_DIR}/pipeline/战斗/kun28.json": '{"困28": {}}',
            f"{RESOURCE_DIR}/pipeline/导航.json": '{"导航": {}}',
        },
    )

    result = _apply(project, package, tmp_path)

    assert result["status"] == "committed"
    assert result["packageType"] == "full"
    assert (project / f"{RESOURCE_DIR}/pipeline/战斗/kun28.json").is_file()
    assert not (project / f"{RESOURCE_DIR}/pipeline/kun28.json").exists(), (
        "旧版遗留的同名节点文件必须清掉，否则 MaaFramework 会拒收整个资源包"
    )


def test_full_update_without_baseline_keeps_shipped_user_content_dirs(
    tmp_path: Path,
) -> None:
    """包也会铺 preset/ 这类混着用户内容的目录，扫描范围不能扩到那里。

    这条是在测试床上用真包试出来的：MaaYYs v3.15.5 自带两个预设放在 preset/，
    而 MXU 把**用户自建的预设**写在同一个目录。
    """

    project = _make_project(tmp_path)
    _write(project / "preset/我的预设.json", '{"mine": true}')
    _write(project / "tasks/我的任务.json", '{"mine": true}')
    package = _make_package(
        tmp_path,
        "v3.15.5",
        {
            "interface.json": _interface("v3.15.5"),
            "preset/一键日常.json": '{"builtin": true}',
            "tasks/999.json": '{"builtin": true}',
            f"{RESOURCE_DIR}/pipeline/导航.json": '{"导航": {}}',
        },
    )

    _apply(project, package, tmp_path)

    assert (project / "preset/我的预设.json").is_file(), "用户自建预设不能被当成残留"
    assert (project / "tasks/我的任务.json").is_file()


def test_full_update_without_baseline_keeps_runtime_dirs(tmp_path: Path) -> None:
    """包不含的顶层目录是运行期产物与用户数据的家，一个都不能动。"""

    project = _make_project(tmp_path)
    package = _make_package(
        tmp_path,
        "v3.15.5",
        {
            "interface.json": _interface("v3.15.5"),
            f"{RESOURCE_DIR}/pipeline/导航.json": '{"导航": {}}',
        },
    )

    _apply(project, package, tmp_path)

    assert (project / "config/user.json").read_text(
        encoding="utf-8"
    ) == '{"服": "官服2"}'
    assert (project / "debug/maa.log").is_file()


def test_full_update_without_baseline_keeps_our_own_artifacts(tmp_path: Path) -> None:
    """我们自己铺进项目的文件不是旧版残留，不能按「包里没有」清掉。"""

    project = _make_project(tmp_path)
    _write(project / f"{RESOURCE_DIR}/.auto_mas_something.json", "{}")
    package = _make_package(
        tmp_path,
        "v3.15.5",
        {
            "interface.json": _interface("v3.15.5"),
            f"{RESOURCE_DIR}/pipeline/导航.json": '{"导航": {}}',
        },
    )

    _apply(project, package, tmp_path)

    assert (project / f"{RESOURCE_DIR}/.auto_mas_something.json").is_file()


def test_full_update_skips_resource_dir_the_package_does_not_fill(
    tmp_path: Path,
) -> None:
    """interface 声明了资源目录、包里却一个文件都没铺：声明与实际对不上，不能清。"""

    project = _make_project(tmp_path)
    package = _make_package(
        tmp_path,
        "v3.15.5",
        {"interface.json": _interface("v3.15.5"), "tasks/999.json": "{}"},
    )

    _apply(project, package, tmp_path)

    assert (project / f"{RESOURCE_DIR}/pipeline/kun28.json").is_file()


def test_second_update_falls_back_to_the_manifest(tmp_path: Path) -> None:
    """装过一次就有清单了，之后必须走回精确口径：用户后放的文件不再被清。"""

    project = _make_project(tmp_path)
    first = _make_package(
        tmp_path,
        "v3.15.5",
        {
            "interface.json": _interface("v3.15.5"),
            f"{RESOURCE_DIR}/pipeline/战斗/kun28.json": '{"困28": {}}',
        },
    )
    _apply(project, first, tmp_path)

    # 用户在资源目录里自己加了一份覆写。
    _write(project / f"{RESOURCE_DIR}/pipeline/我的覆写.json", '{"我的": {}}')

    second = _make_package(
        tmp_path,
        "v3.16.0",
        {
            "interface.json": _interface("v3.16.0"),
            f"{RESOURCE_DIR}/pipeline/战斗/kun28.json": '{"困28": {"v": 2}}',
        },
    )
    _apply(project, second, tmp_path)

    assert (project / f"{RESOURCE_DIR}/pipeline/我的覆写.json").is_file(), (
        "有清单之后，包外的未知文件必须保持不动"
    )
