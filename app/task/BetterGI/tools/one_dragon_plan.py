#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team
#
#   This file is part of AUTO-MAS.
#
#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

"""BetterGI 一条龙：MAS 自编排的「执行计划（Plan）」模型与工具。

一条龙的可视化队列 ``OneDragon.Queue`` 只是 ``[{kind, name}]`` 的有序列表，
无法携带 per-任务的执行层参数，也不能表达「同一任务跑两遍、参数不同」。
``Plan`` 取代/并列于它，结构为：

    {
      "version": 1,
      "steps": [
        {"uid", "kind", "name", "enabled", "settings": {...}}
      ]
    }

其中 ``settings`` 携带该步骤的 per-任务执行层参数（路径 B 下战斗 4 项直连执行层用）。

本模块**只做解析 / 校验 / 迁移**，不触碰 BetterGI 运行链路；真正的执行切换由
``AutoProxy`` 在灰度开关 ``OneDragon.UseExecutionLayer`` 打开后接入（桥接期）。
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Literal

from app.utils import get_logger, resource_path
from app.utils.io import read_file

logger = get_logger("BetterGI 一条龙计划")

# 步骤来源类型，与前端队列 kind 保持一致
StepKind = Literal["builtin", "js", "pathing", "scriptgroup", "custom"]
_STEP_KINDS: frozenset[str] = frozenset(
    {"builtin", "js", "pathing", "scriptgroup", "custom"}
)

# 8 个内置一条龙步骤的标准名（与 BGI 一条龙 TaskDefinitions 值一致）
BUILTIN_STEP_NAMES: frozenset[str] = frozenset(
    {
        "领取邮件",
        "合成树脂",
        "自动地脉花",
        "自动秘境",
        "自动首领讨伐",
        "自动幽境危战",
        "领取每日奖励",
        "领取尘歌壶奖励",
    }
)

# 内置战斗 4 项（路径 B 下由执行层直连；日常 4 项无执行层入口，继续走一条龙）
BUILTIN_COMBAT_STEP_NAMES: frozenset[str] = frozenset(
    {
        "自动秘境",
        "自动地脉花",
        "自动幽境危战",
        "自动首领讨伐",
    }
)

# 各内置步骤在执行层（BetterGI 原生任务 Param）的可传参白名单，键名采用
# ``bettergi.d.ts`` 的 Param 字段名（camelCase）。路径 B 下：
#   - 战斗 4 项（秘境/地脉花/幽境危战/首领讨伐）可由 JS 桥接直传执行层；
#   - 日常 4 项（邮件/合成树脂/尘歌壶/每日奖励）执行层无入口，settings 仅持久化、
#     Runtime 忽略，继续走一条龙。
# 白名单用于校验告警（未知键记日志但不阻断），字段语义以目标版本 d.ts 复核为准。
BUILTIN_STEP_SETTING_KEYS: dict[str, frozenset[str]] = {
    "自动秘境": frozenset(
        {
            "partyName",
            "domainName",
            "sundaySelectedValue",
            "weeklyDomainEnabled",
            "autoArtifactSalvage",
            "maxArtifactStar",
            "rewardRecognitionEnabled",
            "specifyResinUse",
            "originalResinUseCount",
            "condensedResinUseCount",
            "transientResinUseCount",
            "fragileResinUseCount",
            "resinPriorityList",
            "combatStrategyPath",
            "weeklyDomain",
        }
    ),
    "自动地脉花": frozenset(
        {
            "isResinExhaustionMode",
            "openModeCountMin",
            "count",
            "country",
            "leyLineOutcropType",
            "team",
            "leyLineOneDragonMode",
            "timeout",
            "runMonday",
            "runTuesday",
            "runWednesday",
            "runThursday",
            "runFriday",
            "runSaturday",
            "runSunday",
            "weeklyLeyLine",
        }
    ),
    "自动幽境危战": frozenset(
        {
            "bossNum",
            "fightTeamName",
            "strategyName",
            "autoArtifactSalvage",
            "specifyResinUse",
            "originalResinUseCount",
            "condensedResinUseCount",
            "transientResinUseCount",
            "fragileResinUseCount",
            "resinPriorityList",
        }
    ),
    "自动首领讨伐": frozenset(
        {
            "bossName",
            "teamName",
            "strategyName",
            "specifyRunCount",
            "runCount",
            "useTransientResin",
            "useFragileResin",
            "rviveRetryCount",
            "returnToStatueAfterEachRound",
            "rewardRecognitionEnabled",
            "timeout",
        }
    ),
}

PLAN_VERSION = 1


def _gen_uid() -> str:
    """生成步骤实例唯一标识（对应前端 dragonRowSeq 概念）。"""
    return uuid.uuid4().hex


def parse_one_dragon_plan(raw: Any) -> list[dict[str, Any]]:
    """解析前端保存的一条龙 Plan JSON（字符串或已是列表），非法时返回空列表。

    每个 step 归一为 ``{"uid", "kind", "name", "enabled", "settings"}``：
    - ``name`` 命中内置 8 组时 ``kind`` 强制为 ``builtin``；
    - 其余 kind 仅在白名单内保留，否则回退 ``builtin``；
    - 空名与非字典项丢弃；**允许同名条目重复**（每个实例是独立 uid）。
    """
    if isinstance(raw, list):
        data = raw
    elif isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("一条龙 Plan JSON 解析失败，返回空计划")
            return []
    else:
        return []

    # 兼容 ``plan_to_json`` 产出的 ``{"version", "steps": [...]}`` 包装结构，
    # 也兼容裸 list（或字符串化的 list）。否则顶层 dict 会被误判为非法而返回空。
    if isinstance(data, dict) and isinstance(data.get("steps"), list):
        data = data["steps"]
    if not isinstance(data, list):
        return []

    steps: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        kind = str(item.get("kind", "builtin"))
        if kind not in _STEP_KINDS:
            kind = "builtin"
        if name in BUILTIN_STEP_NAMES:
            kind = "builtin"
        uid = str(item.get("uid") or "").strip() or _gen_uid()
        enabled = bool(item.get("enabled", True))
        settings = item.get("settings") or {}
        if not isinstance(settings, dict):
            settings = {}
        steps.append(
            {
                "uid": uid,
                "kind": kind,
                "name": name,
                "enabled": enabled,
                "settings": settings,
            }
        )
    return steps


def queue_to_plan(queue_raw: Any) -> list[dict[str, Any]]:
    """把旧的可视化队列（``OneDragon.Queue``）迁移为 Plan。

    kind/name/enabled 直接映射；``settings`` 留空，运行时走 BGI / 全局现有值
    （与文档迁移策略一致）。
    """
    # 复用一条龙队列的归一化语义（允许同名重复）
    try:
        from .one_dragon import parse_one_dragon_queue
    except Exception:  # pragma: no cover - 仅在 import 异常时兜底为空
        logger.opt(exception=True).warning("导入 parse_one_dragon_queue 失败")
        return []

    queue = parse_one_dragon_queue(queue_raw)
    steps: list[dict[str, Any]] = []
    for item in queue:
        name = item["name"]
        kind = "builtin" if name in BUILTIN_STEP_NAMES else item.get("kind", "builtin")
        steps.append(
            {
                "uid": _gen_uid(),
                "kind": kind,
                "name": name,
                "enabled": item.get("enabled", True),
                "settings": {},
            }
        )
    return steps


def default_plan() -> list[dict[str, Any]]:
    """基于模板 ``默认配置.json`` 的 TaskOrder 生成默认 8 步 Plan。"""
    template_path = (
        resource_path("templates", "BetterGI") / "OneDragon" / "默认配置.json"
    )
    template = read_file(template_path)
    if not isinstance(template, dict):
        logger.warning(f"一条龙默认配置模板缺失或无效: {template_path}")
        return []
    order = template.get("TaskOrder") or []
    defs = template.get("TaskDefinitions") or {}
    enabled_map = template.get("TaskEnabledList") or {}
    steps: list[dict[str, Any]] = []
    for uid_key in order:
        name = defs.get(uid_key)
        if not name:
            continue
        steps.append(
            {
                "uid": str(uid_key),
                "kind": "builtin",
                "name": name,
                "enabled": bool(enabled_map.get(uid_key, True)),
                "settings": {},
            }
        )
    return steps


def resolve_plan(queue_raw: Any, plan_raw: Any) -> list[dict[str, Any]]:
    """解析 Plan；为空则回退从 Queue 迁移（一次性，调用方负责写回）。

    用于灰度期平滑过渡：用户尚未保存过 Plan 时，沿用既有队列语义，不破坏现状。
    """
    plan = parse_one_dragon_plan(plan_raw)
    if plan:
        return plan
    return queue_to_plan(queue_raw)


def validate_step_settings(step: dict[str, Any]) -> dict[str, Any]:
    """按 kind/name 校验 step 的 settings，返回清理后的 settings（未知键仅告警）。

    战斗 4 项按 ``BUILTIN_STEP_SETTING_KEYS`` 白名单过滤；日常 4 项与自定义类步骤
    当前不限制（路径 B 下非直连项由一条龙 / 脚本自行处理）。
    """
    name = str(step.get("name", ""))
    settings = step.get("settings") or {}
    if not isinstance(settings, dict):
        return {}
    allowed = BUILTIN_STEP_SETTING_KEYS.get(name)
    if allowed is None:
        return dict(settings)
    cleaned: dict[str, Any] = {}
    for key, value in settings.items():
        if key in allowed:
            cleaned[key] = value
        else:
            logger.warning(f"一条龙步骤「{name}」含未知设置键「{key}」，已忽略")
    return cleaned


def plan_to_json(steps: list[dict[str, Any]]) -> str:
    """把 steps 序列化为持久化的 Plan JSON 字符串。"""
    payload = {
        "version": PLAN_VERSION,
        "steps": [
            {
                "uid": s.get("uid") or _gen_uid(),
                "kind": s.get("kind", "builtin"),
                "name": s.get("name", ""),
                "enabled": s.get("enabled", True),
                "settings": s.get("settings") or {},
            }
            for s in steps
        ],
    }
    return json.dumps(payload, ensure_ascii=False)


# ── 右栏 → 执行层 Plan 键翻译（仅战斗 4 项、仅可对齐字段）────────────────────
# 右栏字段按 source 分三条存储（dragon / globalDomain / globalStygian），但键名唯一；
# 这里按「战斗组内名」统一映射。global* 端点不带组名，由调用方按段固定映射：
#   globalStygian → 自动幽境危战；globalDomain → 自动秘境。
# 键名全部来自 BUILTIN_STEP_SETTING_KEYS 白名单（已逐项核对），未列出的右栏字段
# （如秘境每周秘境表、地脉花每工作日 country/type、maxArtifactStar）
# 属结构化/全局共享，无法对齐到单值 Plan，留在原生存储。
# 注：地脉花「跳过准备流程」(LeyLineOneDragonMode) 现已对齐进 Plan；其执行层
# 字段层级（Param 还是 Task cfg）待实机确认，见 main.js 地脉花分支 TODO。
RIGHTBAR_TO_PLAN: dict[str, dict[str, str]] = {
    "自动幽境危战": {
        "bossNum": "bossNum",
        "fightTeamName": "fightTeamName",
        "strategyName": "strategyName",
        "autoArtifactSalvage": "autoArtifactSalvage",
        "specifyResinUse": "specifyResinUse",
        "originalResinUseCount": "originalResinUseCount",
        "condensedResinUseCount": "condensedResinUseCount",
        "transientResinUseCount": "transientResinUseCount",
        "fragileResinUseCount": "fragileResinUseCount",
    },
    "自动秘境": {
        "autoArtifactSalvage": "autoArtifactSalvage",
        "rewardRecognitionEnabled": "rewardRecognitionEnabled",
        "specifyResinUse": "specifyResinUse",
        "originalResinUseCount": "originalResinUseCount",
        "condensedResinUseCount": "condensedResinUseCount",
        "transientResinUseCount": "transientResinUseCount",
        "fragileResinUseCount": "fragileResinUseCount",
        "PartyName": "partyName",
        "DomainName": "domainName",
        "SundayEverySelectedValue": "sundaySelectedValue",
    },
    "自动首领讨伐": {
        "AutoBossName": "bossName",
        "AutoBossTeamName": "teamName",
        "AutoBossStrategyName": "strategyName",
        "AutoBossSpecifyRunCount": "specifyRunCount",
        "AutoBossRunCount": "runCount",
        "AutoBossUseTransientResin": "useTransientResin",
        "AutoBossUseFragileResin": "useFragileResin",
        "AutoBossReviveRetryCount": "rviveRetryCount",
        "AutoBossReturnToStatueAfterEachRound": "returnToStatueAfterEachRound",
        "AutoBossRewardRecognitionEnabled": "rewardRecognitionEnabled",
        "AutoBossTimeout": "timeout",
    },
    "自动地脉花": {
        "LeyLineResinExhaustionMode": "isResinExhaustionMode",
        "LeyLineOpenModeCountMin": "openModeCountMin",
        "LeyLineRunCount": "count",
        "LeyLineOneDragonMode": "leyLineOneDragonMode",
        "LeyLineTimeout": "timeout",
        "LeyLineRunMon": "runMonday",
        "LeyLineRunTue": "runTuesday",
        "LeyLineRunWed": "runWednesday",
        "LeyLineRunThu": "runThursday",
        "LeyLineRunFri": "runFriday",
        "LeyLineRunSat": "runSaturday",
        "LeyLineRunSun": "runSunday",
    },
}


# ── 每周配置：右栏平铺键 ↔ Plan 嵌套结构 ───────────────────────────────
# 前端 weekly 表格仍用 BGI 原生平铺键（MondayPartyName / LeyLineMondayCountry …），
# 后端落盘时重组为 Plan settings 内的嵌套对象，执行层 main.js 按「今天星期」取值。
# 嵌套键：秘境 weeklyDomain / 地脉花 weeklyLeyLine，值形如
#   { "default": {partyName, domainName, reward}, "Monday": {...}, ... }
#   { "Monday": {country, type, run}, ... }
WEEKDAY_KEYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _secret_weekly_plan_key(field_key: str):
    """秘境 weekly 平铺键 → (天键, 嵌套字段)；非 weekly 返 None。"""
    if field_key == "PartyName":
        return "default", "partyName"
    if field_key == "DomainName":
        return "default", "domainName"
    if field_key == "SundayEverySelectedValue":
        return "default", "reward"
    for day in WEEKDAY_KEYS:
        if field_key == f"{day}PartyName":
            return day, "partyName"
        if field_key == f"{day}DomainName":
            return day, "domainName"
        if field_key == f"{day}SelectedValue":
            return day, "reward"
    return None


def _leyline_weekly_plan_key(field_key: str):
    """地脉花 weekly 平铺键 → (天键, 嵌套字段)；非 weekly 返 None。"""
    for day in WEEKDAY_KEYS:
        if field_key == f"LeyLine{day}Country":
            return day, "country"
        if field_key == f"LeyLine{day}Type":
            return day, "type"
        if field_key == f"LeyLineRun{day}":
            return day, "run"
    return None


def extract_weekly_struct(group: str, settings: dict[str, Any]) -> dict[str, Any]:
    """从右栏 settings 提取 weekly 嵌套结构；无则返空 dict。"""
    result: dict[str, Any] = {}
    if group == "自动秘境":
        struct: dict[str, Any] = {}
        for k, v in settings.items():
            parsed = _secret_weekly_plan_key(k)
            if parsed:
                day, field = parsed
                struct.setdefault(day, {})[field] = v
        if struct:
            result["weeklyDomain"] = struct
    elif group == "自动地脉花":
        struct = {}
        for k, v in settings.items():
            parsed = _leyline_weekly_plan_key(k)
            if parsed:
                day, field = parsed
                struct.setdefault(day, {})[field] = v
        if struct:
            result["weeklyLeyLine"] = struct
    return result


def weekly_plan_keys(group: str) -> set[str]:
    """该组所有 weekly 平铺键集合（用于从原生剩余中剥离）。"""
    keys: set[str] = set()
    if group == "自动秘境":
        keys.add("SundayEverySelectedValue")
        for day in WEEKDAY_KEYS:
            keys.update({f"{day}PartyName", f"{day}DomainName", f"{day}SelectedValue"})
    elif group == "自动地脉花":
        for day in WEEKDAY_KEYS:
            keys.update({f"LeyLine{day}Country", f"LeyLine{day}Type", f"LeyLineRun{day}"})
    return keys


def flatten_weekly_struct(group: str, settings: dict[str, Any]) -> dict[str, Any]:
    """把 Plan settings 里的 weeklyDomain/weeklyLeyLine 还原为平铺右栏键（回显）。"""
    out: dict[str, Any] = {}
    if group == "自动秘境" and isinstance(settings.get("weeklyDomain"), dict):
        for day, vals in settings["weeklyDomain"].items():
            if not isinstance(vals, dict):
                continue
            if day == "default":
                if "reward" in vals:
                    out["SundayEverySelectedValue"] = vals["reward"]
                if "partyName" in vals:
                    out["PartyName"] = vals["partyName"]
                if "domainName" in vals:
                    out["DomainName"] = vals["domainName"]
            else:
                if "partyName" in vals:
                    out[f"{day}PartyName"] = vals["partyName"]
                if "domainName" in vals:
                    out[f"{day}DomainName"] = vals["domainName"]
                if "reward" in vals:
                    out[f"{day}SelectedValue"] = vals["reward"]
    if group == "自动地脉花" and isinstance(settings.get("weeklyLeyLine"), dict):
        for day, vals in settings["weeklyLeyLine"].items():
            if not isinstance(vals, dict):
                continue
            if "country" in vals:
                out[f"LeyLine{day}Country"] = vals["country"]
            if "type" in vals:
                out[f"LeyLine{day}Type"] = vals["type"]
            if "run" in vals:
                out[f"LeyLineRun{day}"] = vals["run"]
    return out


def is_combat_group(group: str) -> bool:
    """是否为带执行层 Plan 的战斗 4 项组名。"""
    return group in RIGHTBAR_TO_PLAN


def merge_rightbar_into_plan(
    plan_json: str,
    group: str,
    settings: dict[str, Any],
    extra: dict[str, Any] | None = None,
) -> str:
    """把右栏设置（frontend 键）翻译后合并进 Plan 中名为 ``group`` 的步骤 settings。

    找不到该步骤则新建（kind=builtin, enabled=True）。合并后仅保留白名单键。
    非战斗组或无可映射键时原样返回 ``plan_json``。
    """
    mapping = RIGHTBAR_TO_PLAN.get(group)
    if not mapping or not settings:
        return plan_json
    transl: dict[str, Any] = {
        pk: settings[k] for k, pk in mapping.items() if k in settings
    }
    if not transl and not extra:
        return plan_json
    steps = parse_one_dragon_plan(plan_json) if plan_json else []
    target = next((s for s in steps if s.get("name") == group), None)
    if target is None:
        target = {
            "uid": _gen_uid(),
            "kind": "builtin",
            "name": group,
            "enabled": True,
            "settings": {},
        }
        steps.append(target)
    merged = {**(target.get("settings") or {}), **transl}
    if extra:
        merged.update(extra)
    target["settings"] = validate_step_settings({"name": group, "settings": merged})
    return plan_to_json(steps)


def extract_rightbar_from_plan(plan_json: str, group: str) -> dict[str, Any]:
    """从 Plan 中名为 ``group`` 的步骤 settings 反查回右栏 frontend 键。"""
    mapping = RIGHTBAR_TO_PLAN.get(group)
    if not mapping:
        return {}
    steps = parse_one_dragon_plan(plan_json) if plan_json else []
    target = next((s for s in steps if s.get("name") == group), None)
    if not target:
        return {}
    settings = target.get("settings") or {}
    return {fk: settings[pk] for fk, pk in mapping.items() if pk in settings}
