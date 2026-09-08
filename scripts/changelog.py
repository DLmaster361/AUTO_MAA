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

`CHANGELOG.md` 是**唯一由人手写**的来源：文件里第一个 `## vX.Y.Z` 标题就是当前
（尚未发布的）版本号，它下面的条目就是这一版的更新日志。其余五处版本号与
`res/version.json` 全部由本脚本从它生成，不要手改：

- `res/version.json`   —— 整份生成（前端编译期注入、发布 CI 生成 Release 正文都读它）
- `frontend/package.json`
- `app/core/config.py`
- `pyproject.toml`     —— PEP 440 写法，如 5.5.0b3
- `uv.lock`            —— 其中 auto-mas 包自身的版本，同样是 PEP 440 写法

用法::

    python scripts/changelog.py sync      # 从 CHANGELOG.md 同步到上述各处
    python scripts/changelog.py check     # 校验各处已同步（CI 与本地打包脚本用）
    python scripts/changelog.py current   # 打印当前版本号

`sync` 也会把 `CHANGELOG.md` 自身规范化（分类按固定顺序排列、空行统一），
所以贡献者不必记住分类的先后。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
VERSION_JSON_PATH = REPO_ROOT / "res" / "version.json"
PACKAGE_JSON_PATH = REPO_ROOT / "frontend" / "package.json"
APP_CONFIG_PATH = REPO_ROOT / "app" / "core" / "config.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"

# 分类的固定顺序。写在前面的先展示；不在这张表里的分类照常保留，排在这些之后。
# 这不是白名单——新分类不需要改代码，只是排在已知分类后面。
CATEGORY_ORDER = [
    "重要变更",
    "本次亮点",
    "新增功能",
    "程序优化",
    "开发流程",
    "修复BUG",
]

VERSION_PATTERN = re.compile(r"^v\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")
PRE_RELEASE_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")
PRE_RELEASE_ABBR = {"alpha": "a", "beta": "b", "rc": "rc"}

CHANGELOG_HEADER = """<!--
  本文件是更新日志与版本号的唯一手写来源，请不要手改 res/version.json 等生成物。

  - 文件里第一个 `## vX.Y.Z` 标题即当前（尚未发布的）版本号，新条目写进它下面。
  - 每个 PR 都要在这里登记一条，写在最贴切的分类下；分类不存在就新建一个 `###`。
  - 条目写成一行，`- ` 开头，从用户视角描述这次改动带来了什么。
  - 不要手写 ` by [@用户](链接)` 署名，PR 合并后由机器人补。
  - 改完运行 `python scripts/changelog.py sync` 同步各处版本号与生成物。

  分类含义：

  - 重要变更：破坏性的、或需要用户动手确认的改动，会在更新提示里最醒目地展示。
  - 本次亮点：这一版最值得一看的三五条，正文仍写在下面对应的分类里。
  - 新增功能 / 程序优化 / 开发流程 / 修复BUG：常规分类。
-->

# 更新日志
"""


class ChangelogError(Exception):
    """CHANGELOG.md 不符合约定的格式。"""


def read_text(path: Path) -> str:
    """用 utf-8-sig 读，顺手吃掉记事本保存出来的 BOM，免得报成「无法识别的内容」。"""

    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, content: str) -> None:
    """始终以 LF 写出，避免 Windows 上写成 CRLF 与 .gitattributes 冲突。"""

    path.write_text(content, encoding="utf-8", newline="\n")


def parse_changelog(text: str) -> Tuple[str, Dict[str, Dict[str, List[str]]]]:
    """把 CHANGELOG.md 解析成 (当前版本号, {版本: {分类: [条目]}})。"""

    sections: Dict[str, Dict[str, List[str]]] = {}
    current_version: str | None = None
    current_category: str | None = None
    in_comment = False

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        stripped = line.strip()

        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue

        # 注释与一级标题只允许出现在第一个版本段之前（即文件头那段说明）。
        # 版本段里出现它们没有意义，而且 render_changelog 不会保留，
        # sync 一跑就会把它们连同被注释吞掉的条目一起删掉。
        if stripped.startswith("<!--") or stripped.startswith("# "):
            if current_version is not None:
                raise ChangelogError(
                    f"第 {number} 行：版本段里不能写注释或一级标题，"
                    "它们不会被保留，sync 会把它们删掉"
                )
            if stripped.startswith("<!--") and "-->" not in stripped:
                in_comment = True
            continue

        if not stripped:
            continue

        if stripped.startswith("## "):
            version = stripped[3:].strip()
            if not VERSION_PATTERN.match(version):
                raise ChangelogError(
                    f"第 {number} 行：版本标题必须形如 `## v5.5.0-beta.3`，实际是 {stripped!r}"
                )
            if version in sections:
                raise ChangelogError(f"第 {number} 行：版本 {version} 重复出现")
            sections[version] = {}
            current_version = version
            current_category = None
            continue

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

    if in_comment:
        raise ChangelogError(
            "文件末尾仍有未闭合的 `<!--` 注释，它后面的条目会被整段吞掉"
        )

    if not sections:
        raise ChangelogError("CHANGELOG.md 里没有任何 `## vX.Y.Z` 版本段")

    current_version = next(iter(sections))
    return current_version, sections


def order_categories(categories: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """已知分类按固定顺序排前面，未知分类保持原有相对顺序排在后面。"""

    known = [name for name in CATEGORY_ORDER if name in categories]
    unknown = [name for name in categories if name not in CATEGORY_ORDER]
    return {name: categories[name] for name in known + unknown}


def render_changelog(sections: Dict[str, Dict[str, List[str]]]) -> str:
    lines = [CHANGELOG_HEADER.rstrip("\n"), ""]
    for version, categories in sections.items():
        lines.append(f"## {version}")
        lines.append("")
        for category, items in order_categories(categories).items():
            lines.append(f"### {category}")
            lines.append("")
            lines.extend(f"- {item}" for item in items)
            lines.append("")
    return "\n".join(lines).rstrip("\n") + "\n"


def render_version_json(
    current_version: str, sections: Dict[str, Dict[str, List[str]]]
) -> str:
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

    current_version, sections = parse_changelog(read_text(CHANGELOG_PATH))
    pep440_version = to_pep440(current_version)

    return {
        CHANGELOG_PATH: render_changelog(sections),
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

    current_version, _ = parse_changelog(read_text(CHANGELOG_PATH))
    print(f"版本号一致: {current_version}")
    return 0


def command_current() -> int:
    current_version, _ = parse_changelog(read_text(CHANGELOG_PATH))
    print(current_version)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "command",
        choices=["sync", "check", "current"],
        help="sync 生成、check 校验、current 打印当前版本号",
    )
    arguments = parser.parse_args()

    handlers = {
        "sync": command_sync,
        "check": command_check,
        "current": command_current,
    }
    try:
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
