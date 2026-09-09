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


#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""更新日志与版本号的唯一入口。

`CHANGELOG.md` 遵循 Keep a Changelog 1.1.0，是**唯一由人手写**的来源：文件里第一个
`## [vX.Y.Z] - 未发布` 标题就是当前尚未发布的版本号，它下面的条目就是这一版的更新日志。
其余五处版本号与 `res/version.json` 全部由本脚本从它生成，不要手改：

- `res/version.json`   —— 整份生成（前端编译期注入、发布 CI 生成 Release 正文都读它）
- `frontend/package.json`
- `app/core/config.py`
- `pyproject.toml`     —— PEP 440 写法，如 5.5.0b3
- `uv.lock`            —— 其中 auto-mas 包自身的版本，同样是 PEP 440 写法

用法::

    python scripts/changelog.py sync      # 从 CHANGELOG.md 同步到上述各处
    python scripts/changelog.py check     # 校验各处已同步（CI 与本地打包脚本用）
    python scripts/changelog.py check-pr BASE_REF HEAD_REF
                                          # 校验 PR 恰好新增一条当前版本记录
    python scripts/changelog.py current   # 打印当前版本号

`sync` 也会把 `CHANGELOG.md` 自身规范化：重写文件头的说明、把分类按固定顺序排列、
重新生成底部的版本对比链接。所以贡献者只要把条目写进对的分类下就行。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/AUTO-MAS-Project/AUTO-MAS"
# 未发布版本的对比链接指向开发分支
DEVELOPMENT_BRANCH = "dev"

CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
VERSION_JSON_PATH = REPO_ROOT / "res" / "version.json"
PACKAGE_JSON_PATH = REPO_ROOT / "frontend" / "package.json"
APP_CONFIG_PATH = REPO_ROOT / "app" / "core" / "config.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

UNRELEASED = "未发布"

# 分类的固定顺序。中间六类是 Keep a Changelog 的标准分类（用中文标题，因为条目本身是
# 中文、而且这些标题会直接显示在应用内的更新提示里）；首尾三类是本项目的扩展。
# 这不是白名单——表外的新分类照常保留，只是排在这些之后。
CATEGORY_ORDER = [
    "破坏性变更",  # 本项目扩展：需要用户动手确认的改动，置顶最醒目
    "本次亮点",  # 本项目扩展：这一版最值得看的三五条
    "新增",  # Added
    "变更",  # Changed
    "弃用",  # Deprecated
    "移除",  # Removed
    "修复",  # Fixed
    "安全",  # Security
    "开发流程",  # 本项目扩展：只影响贡献者、不影响用户的改动
]
LEGACY_CATEGORY_NAMES = {
    "新增功能": "新增",
    "程序优化": "变更",
    "修复BUG": "修复",
}

VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")
PRE_RELEASE_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
PRE_RELEASE_ABBR = {"alpha": "a", "beta": "b", "rc": "rc"}

RELEASE_HEADING = re.compile(
    rf"^## \[(?P<version>[^\]]+)\] - (?P<date>{UNRELEASED}|\d{{4}}-\d{{2}}-\d{{2}})$"
)
# 底部的版本对比链接，由 render_changelog 重新生成，解析时跳过
LINK_DEFINITION = re.compile(r"^\[[^\]]+\]:\s+\S+$")

CHANGELOG_PREAMBLE = """# 更新日志

本项目所有值得注意的变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/spec/v2.0.0.html)。

<!--
  本文件是更新日志与版本号的唯一手写来源，请不要手改 res/version.json 等生成物。

  - 文件顶部第一个 `## [vX.Y.Z] - 未发布` 标题即当前尚未发布的版本号，新条目写进它下面。
  - 每个 PR 都要在这里登记一条，写在最贴切的分类下；分类不存在就新建一个 `###`。
  - 条目写成一行，`- ` 开头，从用户视角描述这次改动带来了什么。
  - 不要手写 ` by [@用户](链接)` 署名，PR 合并后由机器人补。
  - 改完运行 `python scripts/changelog.py sync`，它会同步各处版本号、规范化本文件、
    并重新生成底部的版本对比链接。

  分类含义（中间六类来自 Keep a Changelog）：

  - 破坏性变更：需要用户动手确认或会改变既有行为的改动，在更新提示里最醒目地展示。
  - 本次亮点：这一版最值得一看的三五条，正文仍写在下面对应的分类里。
  - 新增：新添加的功能。
  - 变更：对现有功能的变更，含优化与调整。
  - 弃用：已经不建议使用、即将移除的功能。
  - 移除：已经移除的功能。
  - 修复：对 bug 的修复。
  - 安全：对安全性的改进。
  - 开发流程：只影响贡献者、用户看不见的改动。
-->
"""


class ChangelogError(Exception):
    """CHANGELOG.md 不符合约定的格式。"""


Sections = Dict[str, Dict[str, List[str]]]
Dates = Dict[str, str]
Entry = Tuple[str, str, str]


def read_text(path: Path) -> str:
    """用 utf-8-sig 读，顺手吃掉记事本保存出来的 BOM，免得报成「无法识别的内容」。"""

    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    """始终以 LF 写出，避免 Windows 上写成 CRLF 与 .gitattributes 冲突。"""

    path.write_text(content, encoding="utf-8", newline="\n")


def parse_changelog(text: str) -> Tuple[str, Sections, Dates]:
    """把 CHANGELOG.md 解析成 (当前版本号, {版本: {分类: [条目]}}, {版本: 日期})。

    第一个 `## [...]` 之前的内容是文件头说明，整段由 render_changelog 重新生成，
    这里一律跳过，所以文件头里可以写任意散文与注释。
    """

    sections: Sections = {}
    dates: Dates = {}
    current_version: str | None = None
    current_category: str | None = None
    seen_release = False

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()

        is_release_heading = stripped.startswith("## ")
        if not seen_release and not is_release_heading:
            continue

        if is_release_heading:
            seen_release = True
            matched = RELEASE_HEADING.match(stripped)
            if matched is None:
                raise ChangelogError(
                    f"第 {number} 行：版本标题必须形如 "
                    f"`## [v5.5.0-beta.3] - 2026-08-31` 或 `## [v5.5.0-beta.3] - {UNRELEASED}`，"
                    f"实际是 {stripped!r}"
                )
            version = matched.group("version")
            release_date = matched.group("date")
            if not VERSION_PATTERN.match(version):
                raise ChangelogError(
                    f"第 {number} 行：版本号必须形如 `v5.5.0-beta.3`，实际是 {version!r}"
                )
            if version in sections:
                raise ChangelogError(f"第 {number} 行：版本 {version} 重复出现")
            if release_date == UNRELEASED and sections:
                raise ChangelogError(
                    f"第 {number} 行：只有文件顶部的第一个版本可以标 {UNRELEASED}"
                )
            if release_date != UNRELEASED:
                try:
                    date.fromisoformat(release_date)
                except ValueError as error:
                    raise ChangelogError(
                        f"第 {number} 行：发布日期不是有效日期：{release_date}"
                    ) from error
            sections[version] = {}
            dates[version] = release_date
            current_version = version
            current_category = None
            continue

        if not stripped:
            continue

        # 底部的版本对比链接由 render 重新生成，解析时忽略
        if LINK_DEFINITION.match(stripped):
            continue

        if stripped.startswith("<!--") or stripped.startswith("# "):
            raise ChangelogError(
                f"第 {number} 行：版本段里不能写注释或一级标题，"
                "它们不会被保留，sync 会把它们删掉"
            )

        if stripped.startswith("### "):
            if current_version is None:
                raise ChangelogError(f"第 {number} 行：分类出现在任何版本标题之前")
            category = stripped[4:].strip()
            if not category:
                raise ChangelogError(f"第 {number} 行：分类名为空")
            if category in sections[current_version]:
                raise ChangelogError(
                    f"第 {number} 行：版本 {current_version} 下分类 {category} 重复出现"
                )
            sections[current_version][category] = []
            current_category = category
            continue

        if stripped.startswith("- "):
            if current_version is None or current_category is None:
                raise ChangelogError(f"第 {number} 行：条目不在任何分类下")
            if line != stripped:
                raise ChangelogError(
                    f"第 {number} 行：条目不能缩进，嵌套列表转不成 version.json"
                )
            entry = stripped[2:].strip()
            if not entry:
                raise ChangelogError(f"第 {number} 行：条目内容为空")
            items = sections[current_version][current_category]
            if entry in items:
                raise ChangelogError(
                    f"第 {number} 行：{current_version} / {current_category} 下条目重复：{entry[:40]}…"
                )
            items.append(entry)
            continue

        raise ChangelogError(
            f"第 {number} 行：无法识别的内容 {stripped[:60]!r}。"
            "条目必须写成单独一行、以 `- ` 开头。"
        )

    if not sections:
        raise ChangelogError("CHANGELOG.md 里没有任何 `## [vX.Y.Z] - 日期` 版本段")

    first_version = next(iter(sections))
    if dates[first_version] != UNRELEASED:
        raise ChangelogError(
            f"文件顶部第一个版本 {first_version} 必须标记为 {UNRELEASED}"
        )

    return first_version, sections, dates


def collect_entries(sections: Sections) -> set[Entry]:
    """把各版本的条目展开成可比较的 (版本, 分类, 条目) 三元组。"""

    return {
        (version, category, item)
        for version, categories in sections.items()
        for category, items in categories.items()
        for item in items
    }


def validate_pr_sections(
    base_version: str,
    base_sections: Sections,
    head_version: str,
    head_sections: Sections,
) -> Entry:
    """校验两份解析结果之间只有一条合法的当前版本新增记录。"""

    if head_version != base_version:
        raise ChangelogError(
            f"PR 不能切换当前未发布版本：base 为 {base_version}，head 为 {head_version}"
        )

    base_entries = collect_entries(base_sections)
    head_entries = collect_entries(head_sections)
    removed = base_entries - head_entries
    if removed:
        raise ChangelogError("PR 不能删除或修改已有的更新日志条目")

    additions = head_entries - base_entries
    historical_additions = [entry for entry in additions if entry[0] != head_version]
    if historical_additions:
        raise ChangelogError("PR 只能在当前未发布版本新增更新日志条目")

    current_additions = sorted(entry for entry in additions if entry[0] == head_version)
    if len(current_additions) != 1:
        raise ChangelogError(
            "每个 PR 必须在当前未发布版本恰好新增 1 条更新日志记录，"
            f"实际新增 {len(current_additions)} 条"
        )
    return current_additions[0]


def validate_pr_changelog(base_text: str, head_text: str) -> Entry:
    """校验 PR 只在当前未发布版本新增一条记录，并返回该记录。"""

    base_version, base_sections, base_dates = parse_changelog(base_text)
    head_version, head_sections, head_dates = parse_changelog(head_text)
    if head_dates != base_dates:
        raise ChangelogError("PR 不能修改版本段或发布日期")
    return validate_pr_sections(
        base_version,
        base_sections,
        head_version,
        head_sections,
    )


def read_ref_file(ref: str, relative_path: str) -> str:
    """读取 Git ref 上的仓库文件。"""

    try:
        return subprocess.check_output(
            ["git", "show", f"{ref}:{relative_path}"],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if error.stderr else "未知 Git 错误"
        raise ChangelogError(
            f"无法读取 {ref} 上的 {relative_path}：{detail}"
        ) from error


def read_changelog_ref(ref: str) -> str:
    """读取 Git ref 上的 CHANGELOG.md。"""

    return read_ref_file(ref, "CHANGELOG.md")


def read_version_json_ref(ref: str) -> Tuple[str, Sections]:
    """迁移 PR 的 base 尚无 CHANGELOG.md 时，从旧生成物读取条目。"""

    try:
        payload = json.loads(read_ref_file(ref, "res/version.json"))
        version = payload["version"]
        raw_sections = payload["version_info"]
        if not isinstance(version, str) or not isinstance(raw_sections, dict):
            raise TypeError
        sections: Sections = {}
        for release, raw_categories in raw_sections.items():
            if not isinstance(release, str) or not isinstance(raw_categories, dict):
                raise TypeError
            categories: Dict[str, List[str]] = {}
            for category, items in raw_categories.items():
                if (
                    not isinstance(category, str)
                    or not isinstance(items, list)
                    or not all(isinstance(item, str) for item in items)
                ):
                    raise TypeError
                normalized = LEGACY_CATEGORY_NAMES.get(category, category)
                categories.setdefault(normalized, []).extend(items)
            sections[release] = categories
        return version, sections
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ChangelogError(
            f"{ref} 上的 res/version.json 结构无效，无法建立迁移基线"
        ) from error


def order_categories(categories: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """已知分类按固定顺序排前面，未知分类保持原有相对顺序排在后面。"""

    known = [name for name in CATEGORY_ORDER if name in categories]
    unknown = [name for name in categories if name not in CATEGORY_ORDER]
    return {name: categories[name] for name in known + unknown}


def render_links(sections: Sections, dates: Dates) -> List[str]:
    """按 Keep a Changelog 的做法，在文件底部给每个版本生成对比链接。

    未发布版本对到开发分支；最老的那一版没有可比对象，指向它自己的 Release 页。
    """

    versions = list(sections)
    lines: List[str] = []
    for index, version in enumerate(versions):
        previous = versions[index + 1] if index + 1 < len(versions) else None
        if previous is None:
            target = f"{REPO_URL}/releases/tag/{version}"
        elif dates[version] == UNRELEASED:
            target = f"{REPO_URL}/compare/{previous}...{DEVELOPMENT_BRANCH}"
        else:
            target = f"{REPO_URL}/compare/{previous}...{version}"
        lines.append(f"[{version}]: {target}")
    return lines


def render_changelog(sections: Sections, dates: Dates) -> str:
    lines = [CHANGELOG_PREAMBLE.rstrip("\n"), ""]
    for version, categories in sections.items():
        lines.append(f"## [{version}] - {dates[version]}")
        lines.append("")
        for category, items in order_categories(categories).items():
            lines.append(f"### {category}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
    lines.extend(render_links(sections, dates))
    return "\n".join(lines).rstrip("\n") + "\n"


def render_version_json(current_version: str, sections: Sections) -> str:
    """生成 res/version.json。

    只写版本与分类条目，不写日期——这份 JSON 的结构是已发布客户端解析更新提示的契约，
    发布 CI 会把它整个塞进 Release 正文首行的 HTML 注释里。
    """

    payload = {
        "version": current_version,
        "version_info": {
            version: order_categories(categories)
            for version, categories in sections.items()
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=4) + "\n"


def to_pep440(version: str) -> str:
    """v5.5.0-beta.3 -> 5.5.0b3；正式版 v5.4.0 -> 5.4.0。"""

    matched = PRE_RELEASE_PATTERN.match(version)
    if matched is None:
        raise ChangelogError(
            f"版本号 {version} 无法转换成 PEP 440 写法，"
            "只支持 vX.Y.Z 与 vX.Y.Z-(alpha|beta|rc).N"
        )
    major, minor, patch, phase, ordinal = matched.groups()
    base = f"{major}.{minor}.{patch}"
    if phase is None:
        return base
    return f"{base}{PRE_RELEASE_ABBR[phase]}{ordinal}"


def substitute_once(text: str, pattern: re.Pattern[str], value: str, where: str) -> str:
    """把唯一一处版本号替换掉；命中数不是 1 就直接报错，避免改错地方。"""

    matches = pattern.findall(text)
    if len(matches) != 1:
        raise ChangelogError(
            f"{where}：预期恰好命中 1 处版本号，实际 {len(matches)} 处"
        )
    return pattern.sub(lambda m: f'{m.group(1)}"{value}"', text, count=1)


PACKAGE_JSON_VERSION = re.compile(r'(?m)^(\s*"version"\s*:\s*)"[^"]*"')
APP_CONFIG_VERSION = re.compile(r'(?m)^(\s*VERSION\s*=\s*)"[^"]*"')
PYPROJECT_VERSION = re.compile(r'(?m)^(version\s*=\s*)"[^"]*"')
UV_LOCK_VERSION = re.compile(
    r'(?m)^(\[\[package\]\]\nname = "auto-mas"\nversion = )"[^"]*"'
)


def build_expected() -> Dict[Path, str]:
    """算出每个生成物应有的完整内容。"""

    current_version, sections, dates = parse_changelog(read_text(CHANGELOG_PATH))
    pep440_version = to_pep440(current_version)

    return {
        CHANGELOG_PATH: render_changelog(sections, dates),
        VERSION_JSON_PATH: render_version_json(current_version, sections),
        PACKAGE_JSON_PATH: substitute_once(
            read_text(PACKAGE_JSON_PATH),
            PACKAGE_JSON_VERSION,
            current_version,
            "frontend/package.json",
        ),
        APP_CONFIG_PATH: substitute_once(
            read_text(APP_CONFIG_PATH),
            APP_CONFIG_VERSION,
            current_version,
            "app/core/config.py",
        ),
        PYPROJECT_PATH: substitute_once(
            read_text(PYPROJECT_PATH),
            PYPROJECT_VERSION,
            pep440_version,
            "pyproject.toml",
        ),
        UV_LOCK_PATH: substitute_once(
            read_text(UV_LOCK_PATH),
            UV_LOCK_VERSION,
            pep440_version,
            "uv.lock",
        ),
    }


def command_sync() -> int:
    changed: List[str] = []
    for path, expected in build_expected().items():
        if read_text(path) != expected:
            write_text(path, expected)
            changed.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))

    if changed:
        print("已更新：")
        for name in changed:
            print(f"  - {name}")
    else:
        print("各处版本号与生成物均已同步，无需改动")
    return 0


def command_check() -> int:
    stale: List[str] = []
    for path, expected in build_expected().items():
        if read_text(path) != expected:
            stale.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))

    if stale:
        print("以下文件与 CHANGELOG.md 不一致：", file=sys.stderr)
        for name in stale:
            print(f"  - {name}", file=sys.stderr)
        print(
            "\n请运行 `python scripts/changelog.py sync` 重新生成后提交。",
            file=sys.stderr,
        )
        return 1

    current_version, _, _ = parse_changelog(read_text(CHANGELOG_PATH))
    print(f"版本号一致: {current_version}")
    return 0


def command_current() -> int:
    current_version, _, _ = parse_changelog(read_text(CHANGELOG_PATH))
    print(current_version)
    return 0


def command_check_pr(base_ref: str, head_ref: str) -> int:
    head_text = read_changelog_ref(head_ref)
    try:
        base_text = read_changelog_ref(base_ref)
    except ChangelogError:
        # 首次把 CHANGELOG.md 迁入目标分支时，base 只有旧的 version.json；它包含
        # 同一批版本、分类和条目，足够证明迁移本身之外只新增了一条 PR 记录。
        base_version, base_sections = read_version_json_ref(base_ref)
        head_version, head_sections, _ = parse_changelog(head_text)
        version, category, item = validate_pr_sections(
            base_version,
            base_sections,
            head_version,
            head_sections,
        )
    else:
        version, category, item = validate_pr_changelog(base_text, head_text)
    print(f"PR 更新日志记录有效: {version} / {category} / {item}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command",
        choices=["sync", "check", "check-pr", "current"],
        help="sync 生成、check 校验、check-pr 校验 PR 新增记录、current 打印当前版本号",
    )
    parser.add_argument("refs", nargs="*", help="check-pr 使用的 BASE_REF HEAD_REF")
    arguments = parser.parse_args()

    handlers = {
        "sync": command_sync,
        "check": command_check,
        "current": command_current,
    }
    try:
        if arguments.command == "check-pr":
            if len(arguments.refs) != 2:
                parser.error("check-pr 需要 BASE_REF 和 HEAD_REF 两个参数")
            return command_check_pr(*arguments.refs)
        if arguments.refs:
            parser.error(f"{arguments.command} 不接受额外参数")
        return handlers[arguments.command]()
    except ChangelogError as error:
        print(f"更新日志格式有误：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Windows 上被管道接走时 stdout 默认不是 UTF-8，打印中文会直接崩。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
