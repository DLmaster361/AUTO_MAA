"""scripts/changelog.py 的纯逻辑回归测试。

CHANGELOG.md 是版本号与更新日志的唯一手写来源，res/version.json 与另外四处版本号
都由该脚本生成。解析器一旦跑偏，发布 CI 与合并后补署名的机器人会一起跟着错，
所以这里锁住解析、规范化与生成三件事。
"""

import importlib.util
from types import ModuleType

import pytest

from app.utils.paths import SOURCE_ROOT


def _load_changelog_module() -> ModuleType:
    """scripts/ 不是包，按路径加载。"""

    script_path = SOURCE_ROOT / "scripts" / "changelog.py"
    spec = importlib.util.spec_from_file_location("changelog_script", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


changelog = _load_changelog_module()


def test_changelog_round_trips_to_itself() -> None:
    """仓库里的 CHANGELOG.md 已是规范形式：解析再渲染应逐字不变。"""

    original = changelog.read_text(changelog.CHANGELOG_PATH)
    _, sections = changelog.parse_changelog(original)

    assert changelog.render_changelog(sections) == original


def test_version_json_matches_changelog() -> None:
    """已提交的 res/version.json 必须是当前 CHANGELOG.md 的生成结果。"""

    current_version, sections = changelog.parse_changelog(
        changelog.read_text(changelog.CHANGELOG_PATH)
    )

    assert changelog.render_version_json(
        current_version, sections
    ) == changelog.read_text(changelog.VERSION_JSON_PATH)


def test_current_version_is_the_first_section() -> None:
    """当前版本号取文件里第一个版本段，而不是最大的那个。"""

    current_version, sections = changelog.parse_changelog(
        "## v9.9.9-beta.1\n\n### 修复BUG\n\n- 甲\n\n## v9.9.8\n\n### 修复BUG\n\n- 乙\n"
    )

    assert current_version == "v9.9.9-beta.1"
    assert list(sections) == ["v9.9.9-beta.1", "v9.9.8"]


def test_duplicate_entry_is_rejected() -> None:
    """同一分类下重复登记同一条会直接报错，避免更新日志里出现两条一样的。"""

    with pytest.raises(changelog.ChangelogError, match="条目重复"):
        changelog.parse_changelog("## v1.0.0\n\n### 修复BUG\n\n- 同一条\n- 同一条\n")


def test_free_text_line_is_rejected() -> None:
    """条目之外的散文会被拒绝，保证文件始终能无损转成 version.json。"""

    with pytest.raises(changelog.ChangelogError, match="无法识别的内容"):
        changelog.parse_changelog("## v1.0.0\n\n### 修复BUG\n\n随手写的一段说明\n")


def test_unterminated_comment_is_rejected() -> None:
    """没闭合的注释会吞掉后面所有条目，而 sync 又不保留注释——必须拦住。"""

    with pytest.raises(changelog.ChangelogError, match="未闭合"):
        changelog.parse_changelog("<!-- 忘了闭合\n\n## v1.0.0\n\n### 修复BUG\n\n- 甲\n")


def test_comment_inside_a_version_section_is_rejected() -> None:
    """版本段里的注释不会被 render 保留，写了就会被 sync 悄悄删掉。"""

    with pytest.raises(changelog.ChangelogError, match="不能写注释"):
        changelog.parse_changelog(
            "## v1.0.0\n\n### 修复BUG\n\n<!-- 顺手记一笔 -->\n\n- 甲\n"
        )


def test_indented_entry_is_rejected() -> None:
    """嵌套列表转不成 version.json，扁平化会悄悄改变原意。"""

    with pytest.raises(changelog.ChangelogError, match="不能缩进"):
        changelog.parse_changelog("## v1.0.0\n\n### 修复BUG\n\n- 甲\n  - 子项\n")


def test_bom_is_stripped_on_read(tmp_path) -> None:
    """记事本存出来的 BOM 不该让整份文件解析失败。"""

    path = tmp_path / "CHANGELOG.md"
    path.write_text(
        "## v1.0.0\n\n### 修复BUG\n\n- 甲\n", encoding="utf-8-sig", newline="\n"
    )

    current_version, _ = changelog.parse_changelog(changelog.read_text(path))

    assert current_version == "v1.0.0"


def test_invalid_version_heading_is_rejected() -> None:
    with pytest.raises(changelog.ChangelogError, match="版本标题"):
        changelog.parse_changelog("## 5.5.0\n\n### 修复BUG\n\n- 甲\n")


def test_known_categories_are_ordered_and_unknown_ones_kept() -> None:
    """置顶两类排在最前，表外的分类照常保留、排在已知分类之后。"""

    ordered = changelog.order_categories(
        {
            "修复BUG": ["丙"],
            "自定义分类": ["丁"],
            "本次亮点": ["乙"],
            "重要变更": ["甲"],
        }
    )

    assert list(ordered) == ["重要变更", "本次亮点", "修复BUG", "自定义分类"]


@pytest.mark.parametrize(
    ("tag", "expected"),
    [
        ("v5.5.0-beta.3", "5.5.0b3"),
        ("v5.5.0-alpha.1", "5.5.0a1"),
        ("v5.5.0-rc.2", "5.5.0rc2"),
        ("v5.4.0", "5.4.0"),
        ("v5.5.10-beta.10", "5.5.10b10"),
    ],
)
def test_to_pep440(tag: str, expected: str) -> None:
    assert changelog.to_pep440(tag) == expected


def test_to_pep440_rejects_unsupported_shape() -> None:
    with pytest.raises(changelog.ChangelogError, match="PEP 440"):
        changelog.to_pep440("v5.5.0-dev")
