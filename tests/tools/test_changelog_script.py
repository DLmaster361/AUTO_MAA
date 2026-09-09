"""scripts/changelog.py 的纯逻辑回归测试。

CHANGELOG.md 遵循 Keep a Changelog 1.1.0，是版本号与更新日志的唯一手写来源，
res/version.json 与另外四处版本号都由该脚本生成。解析器一旦跑偏，发布 CI 与合并后
补署名的机器人会一起跟着错，所以这里锁住解析、规范化与生成三件事。
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

MINIMAL = f"## [v1.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n"


def test_changelog_round_trips_to_itself() -> None:
    """仓库里的 CHANGELOG.md 已是规范形式：解析再渲染应逐字不变。"""

    original = changelog.read_text(changelog.CHANGELOG_PATH)
    _, sections, dates = changelog.parse_changelog(original)

    assert changelog.render_changelog(sections, dates) == original


def test_version_json_matches_changelog() -> None:
    """已提交的 res/version.json 必须是当前 CHANGELOG.md 的生成结果。"""

    current_version, sections, _ = changelog.parse_changelog(
        changelog.read_text(changelog.CHANGELOG_PATH)
    )

    assert changelog.render_version_json(
        current_version, sections
    ) == changelog.read_text(changelog.VERSION_JSON_PATH)


def test_version_json_carries_no_dates() -> None:
    """version.json 的结构是已发布客户端的解析契约，日期只留在 CHANGELOG.md 里。"""

    current_version, sections, _ = changelog.parse_changelog(
        changelog.read_text(changelog.CHANGELOG_PATH)
    )
    payload = changelog.json.loads(
        changelog.render_version_json(current_version, sections)
    )

    assert set(payload) == {"version", "version_info"}
    for categories in payload["version_info"].values():
        assert all(isinstance(items, list) for items in categories.values())


def test_current_version_is_the_first_section() -> None:
    """当前版本号取文件里第一个版本段，而不是最大的那个。"""

    current_version, sections, dates = changelog.parse_changelog(
        f"## [v9.9.9-beta.1] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n\n"
        "## [v9.9.8] - 2026-01-01\n\n### 修复\n\n- 乙\n"
    )

    assert current_version == "v9.9.9-beta.1"
    assert list(sections) == ["v9.9.9-beta.1", "v9.9.8"]
    assert dates["v9.9.9-beta.1"] == changelog.UNRELEASED


def test_preamble_prose_and_comments_are_skipped() -> None:
    """第一个版本标题之前是文件头说明，散文和注释都不该让解析失败。"""

    current_version, _, _ = changelog.parse_changelog(
        "# 更新日志\n\n本项目所有值得注意的变更都记录在此文件中。\n\n"
        "格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。\n\n"
        "<!-- 贡献者须知 -->\n\n" + MINIMAL
    )

    assert current_version == "v1.0.0"


def test_link_definitions_are_ignored_on_parse() -> None:
    """底部的版本对比链接由 render 重新生成，解析时不能被当成条目。"""

    _, sections, _ = changelog.parse_changelog(
        MINIMAL + "\n[v1.0.0]: https://example.invalid/releases/tag/v1.0.0\n"
    )

    assert sections == {"v1.0.0": {"修复": ["甲"]}}


def test_links_compare_against_the_previous_listed_version() -> None:
    """未发布版本对到开发分支，最老的一版指向自己的 Release 页。"""

    _, sections, dates = changelog.parse_changelog(
        f"## [v2.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n\n"
        "## [v1.5.0] - 2026-01-02\n\n### 修复\n\n- 乙\n\n"
        "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 丙\n"
    )

    assert changelog.render_links(sections, dates) == [
        f"[v2.0.0]: {changelog.REPO_URL}/compare/v1.5.0...{changelog.DEVELOPMENT_BRANCH}",
        f"[v1.5.0]: {changelog.REPO_URL}/compare/v1.0.0...v1.5.0",
        f"[v1.0.0]: {changelog.REPO_URL}/releases/tag/v1.0.0",
    ]


def test_unreleased_is_only_allowed_at_the_top() -> None:
    """已发布的版本段必须带真实日期，否则发布链路取不到发布时间。"""

    with pytest.raises(changelog.ChangelogError, match="只有文件顶部"):
        changelog.parse_changelog(
            "## [v2.0.0] - 2026-01-02\n\n### 修复\n\n- 甲\n\n"
            f"## [v1.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 乙\n"
        )


def test_first_version_must_be_unreleased() -> None:
    """文件不能以已发布版本开头，否则会把旧版本继续当作当前版本。"""

    with pytest.raises(changelog.ChangelogError, match="第一个版本.*未发布"):
        changelog.parse_changelog("## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 甲\n")


def test_invalid_calendar_date_is_rejected() -> None:
    """形状像 ISO 8601 但实际不存在的日期也不能进入历史版本段。"""

    with pytest.raises(changelog.ChangelogError, match="不是有效日期"):
        changelog.parse_changelog(
            f"## [v2.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n\n"
            "## [v1.0.0] - 2026-99-88\n\n### 修复\n\n- 乙\n"
        )


def test_pr_changelog_accepts_exactly_one_current_entry() -> None:
    base = (
        f"## [v2.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n\n"
        "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 旧条目\n"
    )
    head = base.replace("- 甲", "- 甲\n- 乙", 1)

    assert changelog.validate_pr_changelog(base, head) == (
        "v2.0.0",
        "修复",
        "乙",
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda text: text, "实际新增 0 条"),
        (lambda text: text.replace("- 甲", "- 甲\n- 乙\n- 丙", 1), "实际新增 2 条"),
        (
            lambda text: text.replace("- 旧条目", "- 旧条目\n- 历史补记", 1),
            "当前未发布版本",
        ),
        (lambda text: text.replace("- 甲", "- 改写甲", 1), "不能删除或修改"),
        (lambda text: text.replace("2026-01-01", "2026-01-02", 1), "版本段或发布日期"),
    ],
)
def test_pr_changelog_rejects_non_additive_changes(mutate, message: str) -> None:
    base = (
        f"## [v2.0.0] - {changelog.UNRELEASED}\n\n### 修复\n\n- 甲\n\n"
        "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 旧条目\n"
    )

    with pytest.raises(changelog.ChangelogError, match=message):
        changelog.validate_pr_changelog(base, mutate(base))


def test_duplicate_entry_is_rejected() -> None:
    """同一分类下重复登记同一条会直接报错，避免更新日志里出现两条一样的。"""

    with pytest.raises(changelog.ChangelogError, match="条目重复"):
        changelog.parse_changelog(
            "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 同一条\n- 同一条\n"
        )


def test_free_text_line_is_rejected() -> None:
    """条目之外的散文会被拒绝，保证文件始终能无损转成 version.json。"""

    with pytest.raises(changelog.ChangelogError, match="无法识别的内容"):
        changelog.parse_changelog(
            "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n随手写的一段说明\n"
        )


def test_comment_inside_a_version_section_is_rejected() -> None:
    """版本段里的注释不会被 render 保留，写了就会被 sync 悄悄删掉。"""

    with pytest.raises(changelog.ChangelogError, match="不能写注释"):
        changelog.parse_changelog(
            "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n<!-- 顺手记一笔 -->\n\n- 甲\n"
        )


def test_indented_entry_is_rejected() -> None:
    """嵌套列表转不成 version.json，扁平化会悄悄改变原意。"""

    with pytest.raises(changelog.ChangelogError, match="不能缩进"):
        changelog.parse_changelog(
            "## [v1.0.0] - 2026-01-01\n\n### 修复\n\n- 甲\n  - 子项\n"
        )


def test_bom_is_stripped_on_read(tmp_path) -> None:
    """记事本存出来的 BOM 不该让整份文件解析失败。"""

    path = tmp_path / "CHANGELOG.md"
    path.write_text(MINIMAL, encoding="utf-8-sig", newline="\n")

    current_version, _, _ = changelog.parse_changelog(changelog.read_text(path))

    assert current_version == "v1.0.0"


@pytest.mark.parametrize(
    "heading",
    [
        "## v1.0.0",  # 少了方括号与日期
        "## [v1.0.0]",  # 少了日期
        "## [1.0.0] - 2026-01-01",  # 少了 v 前缀
        "## [v1.0.0] - 2026/01/01",  # 日期不是 ISO 8601
        "## [v1.0.0] - 明天",
    ],
)
def test_invalid_release_heading_is_rejected(heading: str) -> None:
    with pytest.raises(changelog.ChangelogError, match="版本标题|版本号"):
        changelog.parse_changelog(f"{heading}\n\n### 修复\n\n- 甲\n")


def test_known_categories_are_ordered_and_unknown_ones_kept() -> None:
    """置顶两类排在最前，Keep a Changelog 六类按规范顺序，表外分类排在最后。"""

    ordered = changelog.order_categories(
        {
            "开发流程": ["己"],
            "修复": ["丁"],
            "自定义分类": ["庚"],
            "新增": ["丙"],
            "本次亮点": ["乙"],
            "破坏性变更": ["甲"],
            "安全": ["戊"],
        }
    )

    assert list(ordered) == [
        "破坏性变更",
        "本次亮点",
        "新增",
        "修复",
        "安全",
        "开发流程",
        "自定义分类",
    ]


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
