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

"""养成计算内核：需求 → 聚合 → 折算 → 选关 → 达成判定 → 状态流转。

全部为纯函数：输入契约类型、输出契约类型，零 IO、零日志、零 app.* 依赖
（规则 1.3-3）。任何外部数据都由调用方（AutoProxy / API）注入。
"""

from __future__ import annotations

import math
from datetime import date, datetime
from datetime import time as dt_time
from typing import Mapping

from .types import (
    Achievement,
    CultivateDataSet,
    CultivatePlan,
    DropEntry,
    FarmEntry,
    Goal,
    GoalRef,
    OperatorTarget,
    Progression,
    ProgressionSnapshot,
    Recipe,
    Requirement,
)

# 合成路径搜索的深度上限（composite 表无环，防御性限制）
_MAX_PATH_DEPTH = 5


def _goal_current_level(progression: Progression, goal: Goal) -> int:
    """从练度取目标维度的当前等级（干员未拥有时用 default 全 0 起算）。"""

    if goal.kind == "elite":
        return progression.elite
    if goal.kind == "mastery":
        return progression.masteries.get(goal.target_id, 0)
    return progression.modules.get(goal.target_id, 0)


def build_requirements(
    targets: list[OperatorTarget] | tuple[OperatorTarget, ...],
    snapshots: Mapping[str, ProgressionSnapshot],
    demands: Mapping[str, tuple],
) -> list[Requirement]:
    """把目标展开为逐材料区间需求（current → to 的逐档求和）。

    等级路径严格顺序不可跳级：区间=逐档求和，天然包含中间档材料
    （中间档是要真实消耗的，属正确行为）。已达成（achieved）与待确认
    （pending_confirm，可能已养成但无法自证）的目标不参与计算。
    """

    requirements: dict[str, Requirement] = {}
    for target in targets:
        snapshot = snapshots.get(target.operator_id)
        progression = snapshot.data if snapshot is not None else Progression.default()
        for goal_index, goal in enumerate(target.goals):
            # 已达成不参与计算；待确认（可能已养成但无法自证）暂停刷取，
            # 避免用户确认前无限补刷——确认后移除，否认则恢复 in_progress
            if goal.state in ("achieved", "pending_confirm"):
                continue
            current = _goal_current_level(progression, goal)
            for entry in demands.get(target.operator_id, ()):
                if (
                    entry.kind != goal.kind
                    or entry.target_id != goal.target_id
                    or not current < entry.level <= goal.to_level
                ):
                    continue
                for item_id, amount in entry.items.items():
                    existing = requirements.get(item_id)
                    if existing is None:
                        requirements[item_id] = Requirement(
                            item_id=item_id,
                            amount=amount,
                            sources=(GoalRef(target.operator_id, goal_index, amount),),
                        )
                    else:
                        requirements[item_id] = Requirement(
                            item_id=item_id,
                            amount=existing.amount + amount,
                            sources=existing.sources
                            + (GoalRef(target.operator_id, goal_index, amount),),
                        )
    return list(requirements.values())


def aggregate(requirements: list[Requirement]) -> list[Requirement]:
    """多目标需求按物品 ID 求和（取 sum 不取 max：养完 A 还得够 B）。"""

    merged: dict[str, Requirement] = {}
    for requirement in requirements:
        existing = merged.get(requirement.item_id)
        if existing is None:
            merged[requirement.item_id] = requirement
        else:
            merged[requirement.item_id] = Requirement(
                item_id=requirement.item_id,
                amount=existing.amount + requirement.amount,
                sources=existing.sources + requirement.sources,
            )
    return list(merged.values())


def _build_recipe_map(data: CultivateDataSet) -> dict[str, Recipe]:
    return {recipe.result_item_id: recipe for recipe in data.recipes}


def _stage_unusable(
    stage_id: str, data: CultivateDataSet, blacklist: frozenset[str]
) -> bool:
    """关卡是否结构性不可用（缺失/无关卡代码/被黑名单排除）。

    只做与时间、星期无关的结构判定：固定产出资源关有固定开放日，按当天
    过滤会让用户在不开放的日子拿不到该材料，开放时间由 MAA 执行时判断。
    """

    meta = data.stages.get(stage_id)
    return meta is None or not meta.stage_code or meta.stage_code in blacklist


def _direct_cost(
    item_id: str,
    data: CultivateDataSet,
    now_ms: int | None = None,
    weekday: int | None = None,
    blacklist: frozenset[str] = frozenset(),
) -> float | None:
    """直刷获得 1 个物品的等效理智成本 = 物品价值 ÷ 关卡综合效率。

    综合效率 = Σ(每次掉落期望×物品价值)/理智，副产品按价值自动抵扣
    （一图流综合效率口径）。取各候选关最小值；不可直刷/价值未知/今天
    无开放关（now_ms/weekday 提供时）返回 None。
    """

    value = data.item_value.get(item_id)
    if value is None or value <= 0:
        return None
    best: float | None = None
    for drop in data.drops:
        if drop.item_id != item_id:
            continue
        meta = data.stages.get(drop.stage_id)
        if meta is None or meta.ap_cost <= 0 or meta.stage_code in blacklist:
            continue
        if now_ms is not None and not _window_open(drop, now_ms):
            continue
        if weekday is not None and meta.open_weekdays is not None:
            if weekday not in meta.open_weekdays:
                continue
        if meta.composite <= 0:
            continue
        cost = value / meta.composite
        best = cost if best is None else min(best, cost)
    return best


def _best_path(
    item_id: str,
    data: CultivateDataSet,
    recipe_map: Mapping[str, Recipe],
    memo: dict[str, tuple[float, dict[str, float]] | None],
    now_ms: int | None = None,
    weekday: int | None = None,
    blacklist: frozenset[str] = frozenset(),
    depth: int = 0,
) -> tuple[float, dict[str, float]] | None:
    """计算获得 1 个物品的最低理智成本与对应路径（{可刷材料: 数量}）。

    直刷与合成按每理智成本择优，直刷只计今天实际开放的关卡；不可获取
    返回 None。返回的路径中数量为浮点倍率，调用方在最终条目上取整。
    """

    if depth > _MAX_PATH_DEPTH:
        return None
    if item_id in memo:
        return memo[item_id]

    candidates: list[tuple[float, dict[str, float]]] = []
    direct_cost = _direct_cost(item_id, data, now_ms, weekday, blacklist)
    if direct_cost is not None:
        candidates.append((direct_cost, {item_id: 1.0}))

    recipe = recipe_map.get(item_id)
    if recipe is not None:
        total_cost = 0.0
        path: dict[str, float] = {}
        feasible = True
        for ingredient_id, count in recipe.ingredients.items():
            sub = _best_path(
                ingredient_id,
                data,
                recipe_map,
                memo,
                now_ms,
                weekday,
                blacklist,
                depth + 1,
            )
            if sub is None:
                feasible = False
                break
            total_cost += sub[0] * count
            for farm_item, multiplier in sub[1].items():
                path[farm_item] = path.get(farm_item, 0.0) + multiplier * count
        if feasible:
            candidates.append((total_cost, path))

    result = min(candidates, key=lambda candidate: candidate[0]) if candidates else None
    memo[item_id] = result
    return result


def synthesize(
    requirements: list[Requirement],
    data: CultivateDataSet,
    today: date | None = None,
    blacklist: frozenset[str] = frozenset(),
) -> tuple[list[Requirement], list[Requirement]]:
    """把需求折算到可刷取材料（金色 T5 等按合成路径展开到原料）。

    资源关固定产出材料（龙门币 ← CE-6、采购凭证 ← AP-5 等）只按资源关
    处理：无掉落统计、无配方，直接进入刷取需求，钉到对应资源关，固定
    产出关被黑名单排除时才归入不可获取。

    不可获取类（模组凭证等）原样返回，供 UI 单列"需另行获取"，
    绝不进刷取条目。路径选择为 P1 基础版：每理智成本择优，不计现有库存
    对路径选择的影响（完整口径 P3 对齐）；库存缺口由 MAA 执行时现算，
    因此条目数量取路径总量（保有量目标语义）而非扣减后的差额。

    today 提供时直刷可行性按当天开放性评估——直刷关今天没开的材料自动
    落到合成路径（例：固源岩组直刷候选全是已过期的复刻/限时节，大量需求
    会折叠为"刷固源岩×5 合成"）；连合成路径今天也走不通的，保留为未展开
    的刷取需求（recommend_stages 自然不产条目，demands 仍展示缺口）；
    结构性不可获取（无直掉关且无配方）才进不可获取清单。不提供 today 则
    不做开放性过滤（仅限测试）。
    """

    recipe_map = _build_recipe_map(data)
    structural_memo: dict[str, tuple[float, dict[str, float]] | None] = {}
    today_memo: dict[str, tuple[float, dict[str, float]] | None] = {}
    now_ms = (
        int(datetime.combine(today, dt_time.min).timestamp()) * 1000
        if today is not None
        else None
    )
    weekday = today.weekday() if today is not None else None
    farm_totals: dict[str, float] = {}
    unobtainable_totals: dict[str, int] = {}
    sources_by_item: dict[str, tuple[GoalRef, ...]] = {}

    for requirement in requirements:
        item_id = requirement.item_id
        if data.material_class.get(item_id) == "unobtainable":
            unobtainable_totals[item_id] = (
                unobtainable_totals.get(item_id, 0) + requirement.amount
            )
            sources_by_item.setdefault(item_id, requirement.sources)
            continue
        # 资源关固定产出（龙门币 ← CE-6、采购凭证 ← AP-5 等）：只按资源关
        # 处理，不参与掉落统计与合成折算。不在此过滤开放日，开放时间由
        # MAA 执行时自行判断（与 recommend_stages 口径一致）。
        fixed_stage_id = data.fixed_source_stages.get(item_id)
        if fixed_stage_id is not None:
            if _stage_unusable(fixed_stage_id, data, blacklist):
                unobtainable_totals[item_id] = (
                    unobtainable_totals.get(item_id, 0) + requirement.amount
                )
                sources_by_item.setdefault(item_id, requirement.sources)
            else:
                farm_totals[item_id] = (
                    farm_totals.get(item_id, 0.0) + requirement.amount
                )
                sources_by_item[item_id] = (
                    sources_by_item.get(item_id, ()) + requirement.sources
                )
            continue
        # 结构可行性（不看今天）：决定该材料是"可刷/可合成"还是"不可获取"
        structural = _best_path(item_id, data, recipe_map, structural_memo)
        if structural is None:
            unobtainable_totals[item_id] = (
                unobtainable_totals.get(item_id, 0) + requirement.amount
            )
            sources_by_item.setdefault(item_id, requirement.sources)
            continue
        # 今日可行性：直刷关今天没开 → 落到合成路径；合成也走不通 →
        # 按原物品保留需求（不产条目，不误标不可获取）
        path = (
            _best_path(
                item_id, data, recipe_map, today_memo, now_ms, weekday, blacklist
            )
            if now_ms is not None
            else structural
        )
        if path is None:
            farm_totals[item_id] = farm_totals.get(item_id, 0.0) + requirement.amount
            sources_by_item[item_id] = (
                sources_by_item.get(item_id, ()) + requirement.sources
            )
            continue
        for farm_item, multiplier in path[1].items():
            farm_totals[farm_item] = (
                farm_totals.get(farm_item, 0.0) + multiplier * requirement.amount
            )
            # 折算到同一材料的多个需求项，来源档案合并（UI 展开来源明细需完整）
            sources_by_item[farm_item] = (
                sources_by_item.get(farm_item, ()) + requirement.sources
            )

    farm = sorted(
        (
            Requirement(
                item_id=item_id,
                amount=math.ceil(total),
                sources=sources_by_item.get(item_id, ()),
            )
            for item_id, total in farm_totals.items()
        ),
        key=lambda requirement: requirement.item_id,
    )
    unobtainable = sorted(
        (
            Requirement(item_id=item_id, amount=amount)
            for item_id, amount in unobtainable_totals.items()
        ),
        key=lambda requirement: requirement.item_id,
    )
    return farm, unobtainable


def _window_open(drop: DropEntry, now_ms: int) -> bool:
    if drop.start_ms and drop.start_ms > now_ms:
        return False
    return drop.end_ms is None or drop.end_ms == 0 or now_ms <= drop.end_ms


def recommend_stages(
    requirements: list[Requirement],
    data: CultivateDataSet,
    today: date,
    blacklist: frozenset[str] = frozenset(),
) -> list[FarmEntry]:
    """为每个可直刷材料选最优关（单件期望理智最低者）。

    统计口径与库存保持选择器一致：单件期望理智 = 理智 ÷ 每次期望掉落，
    只衡量目标材料本身，不计关卡副产物。

    过滤：活动关时间窗、资源本/芯片本星期开放规则、用户黑名单。
    无可用候选的材料不产条目（仍保留在 demands 供 UI 展示缺口）。
    """

    now_ms = int(datetime.combine(today, dt_time.min).timestamp()) * 1000
    weekday = today.weekday()
    entries: list[FarmEntry] = []
    for requirement in requirements:
        best_stage: str | None = None
        best_sanity_per_item: float | None = None
        best_per_run = 0.0
        best_cost = 0
        seen: set[str] = set()
        for drop in data.drops:
            if drop.item_id != requirement.item_id or drop.stage_id in seen:
                continue
            seen.add(drop.stage_id)
            meta = data.stages.get(drop.stage_id)
            if meta is None or not meta.stage_code or meta.stage_code in blacklist:
                continue
            if meta.ap_cost <= 0 or not _window_open(drop, now_ms):
                continue
            if drop.expected_per_run <= 0:
                continue
            if meta.open_weekdays is not None and weekday not in meta.open_weekdays:
                continue
            # 判据是单件期望理智而非每次期望：后者会把"期望高但理智也高"
            # 的关排前面（如固源岩 S2-12 每次 2.29/15 理智 vs 1-7 每次
            # 1.245/6 理智），总理智消耗更高
            sanity_per_item = meta.ap_cost / drop.expected_per_run
            if best_sanity_per_item is None or sanity_per_item < best_sanity_per_item:
                best_sanity_per_item = sanity_per_item
                best_per_run = drop.expected_per_run
                best_cost = meta.ap_cost
                best_stage = meta.stage_code

        # 资源关固定产出（龙门币 ← CE-6、采购凭证 ← AP-5 等）：无掉落统计，
        # 直接给出对应关。期望次数/理智不可算（产出恒定但单次产量未知），
        # 保持 0.0 中性值，由 MAA 按保有量目标执行时现算。
        #
        # 不做星期过滤：资源关有固定开放日，若在此按当天过滤，用户在不开放
        # 的日子选该材料就拿不到任何关卡、无法保存计划。MAA 执行时会自行
        # 判断开放时间并安排到开放日刷取，计划层不该替它做这个决定。
        if best_stage is None:
            fixed_stage_id = data.fixed_source_stages.get(requirement.item_id)
            if fixed_stage_id is None or _stage_unusable(
                fixed_stage_id, data, blacklist
            ):
                continue
            entries.append(
                FarmEntry(
                    item_id=requirement.item_id,
                    amount=requirement.amount,
                    stage_code=data.stages[fixed_stage_id].stage_code,
                    sources=requirement.sources,
                )
            )
            continue

        expected_runs = requirement.amount / best_per_run
        entries.append(
            FarmEntry(
                item_id=requirement.item_id,
                amount=requirement.amount,
                stage_code=best_stage,
                expected_runs=round(expected_runs, 1),
                expected_sanity=round(expected_runs * best_cost, 1),
                sources=requirement.sources,
            )
        )
    return entries


def build_plan(
    *,
    targets: list[OperatorTarget] | tuple[OperatorTarget, ...],
    snapshots: Mapping[str, ProgressionSnapshot],
    data: CultivateDataSet,
    today: date,
    blacklist: frozenset[str] = frozenset(),
) -> CultivatePlan:
    """完整管线：目标 + 观测 + 数据 → 中性养成计划。

    不接收库存：保有量目标语义下缺口由 MAA 执行时现算（库存只在
    has_material_gap 的接管判定中使用）。
    """

    requirements = aggregate(build_requirements(targets, snapshots, data.demands))
    farm, unobtainable = synthesize(requirements, data, today, blacklist)
    entries = recommend_stages(farm, data, today, blacklist)

    # 排序不变量：精英化条目最前（专精/模组的前置）→ 按用户添加目标顺序
    # → 折算原料条目紧随其目标材料（按最早来源目标排序即自然满足）
    sort_keys: dict[tuple[str, int], tuple[int, int, int]] = {
        (target.operator_id, goal_index): (
            0 if goal.kind == "elite" else 1,
            target_index,
            goal_index,
        )
        for target_index, target in enumerate(targets)
        for goal_index, goal in enumerate(target.goals)
    }

    def sort_key(entry: FarmEntry) -> tuple[int, int, int, str]:
        first_goal_order = min(
            (
                sort_keys.get((ref.operator_id, ref.goal_index), (2, 10**9, 10**9))
                for ref in entry.sources
            ),
            default=(2, 10**9, 10**9),
        )
        return (*first_goal_order, entry.item_id)

    entries = sorted(entries, key=sort_key)

    # demands 保留全部折算后需求（含暂无可刷关的材料，供 UI 展示缺口）；
    # entries 只含有可用推荐关的材料
    demands = tuple(farm) + tuple(unobtainable)
    return CultivatePlan(
        entries=tuple(entries),
        demands=demands,
        unobtainable=tuple(unobtainable),
    )


def _unmet_by_stock(
    requirements: list[Requirement],
    inventory: Mapping[str, int],
    data: CultivateDataSet,
) -> list[Requirement]:
    """按库存递归抵扣后的未满足需求（原始需求粒度，保留来源档案）。

    抵扣沿合成链进行：先扣本体库存，不足的再逐级扣原料库存（等价于
    立即合成消耗）。用户已持有的高阶材料与中间材料因此都能抵扣目标，
    不会出现"材料全齐仍判缺口"。贪心按需求顺序消耗、不求解最优分配：
    缺口判定只取布尔结果，且真实配方都是可刷材料的逐级合成，逐项贪心
    与最优分配在此口径下结论一致。
    """

    recipe_map = _build_recipe_map(data)
    stock = dict(inventory)

    def consume(item_id: str, amount: int, depth: int) -> int:
        """从库存消耗 amount 个 item（本体直用，不足沿配方合成）。

        返回仍缺的数量。数量精度对布尔判定无关：原料不足时消耗现有
        部分后按本体剩余计缺口——无论之后直刷本体还是补刷原料，都
        存在需要刷取的缺口。
        """

        if depth > _MAX_PATH_DEPTH:
            return amount
        use = min(amount, stock.get(item_id, 0))
        if use:
            stock[item_id] -= use
        unmet = amount - use
        if unmet <= 0:
            return 0
        recipe = recipe_map.get(item_id)
        if recipe is None:
            return unmet
        for ingredient_id, count in recipe.ingredients.items():
            if consume(ingredient_id, count * unmet, depth + 1) > 0:
                return unmet
        return 0

    unmet_requirements: list[Requirement] = []
    for requirement in requirements:
        remaining = consume(requirement.item_id, requirement.amount, 0)
        if remaining > 0:
            unmet_requirements.append(
                Requirement(
                    item_id=requirement.item_id,
                    amount=remaining,
                    sources=requirement.sources,
                )
            )
    return unmet_requirements


def has_material_gap(
    targets: list[OperatorTarget] | tuple[OperatorTarget, ...],
    snapshots: Mapping[str, ProgressionSnapshot],
    inventory: Mapping[str, int],
    data: CultivateDataSet,
    today: date,
    blacklist: frozenset[str] = frozenset(),
) -> bool:
    """注入时接管判定第三步：存在今日可刷、且库存（含沿配方立即合成）
    满足不了的材料缺口。

    库存先沿合成链递归抵扣原始需求（本体直用 → 原料合成，见
    _unmet_by_stock），仍缺的才走选关过滤（时间窗/星期/黑名单，与
    build_plan 同口径）。因此"当前无开放关"的材料不计入缺口——它们
    即使缺也刷不了，不应抑制库存保持；不可获取类（模组凭证等）靠用户
    游戏内获取，同样不计入。
    """

    requirements = aggregate(build_requirements(targets, snapshots, data.demands))
    unmet = _unmet_by_stock(requirements, inventory, data)
    farm, _ = synthesize(unmet, data, today, blacklist)
    return bool(recommend_stages(farm, data, today, blacklist))


def judge_achievements(
    targets: list[OperatorTarget] | tuple[OperatorTarget, ...],
    snapshots: Mapping[str, ProgressionSnapshot],
) -> list[Achievement]:
    """按练度观测逐目标判定达成；来源不可自证时 confident=False。

    快照缺失（干员不在练度数据中）= 未达成，计划继续挂起等待。
    """

    achievements: list[Achievement] = []
    for target in targets:
        snapshot = snapshots.get(target.operator_id)
        confident = snapshot is not None and snapshot.source in ("local", "skland")
        progression = snapshot.data if snapshot is not None else Progression.default()
        for goal_index, goal in enumerate(target.goals):
            achieved = _goal_current_level(progression, goal) >= goal.to_level
            achievements.append(
                Achievement(
                    operator_id=target.operator_id,
                    goal_index=goal_index,
                    achieved=achieved,
                    confident=confident,
                )
            )
    return achievements


def apply_achievements(
    targets: list[OperatorTarget] | tuple[OperatorTarget, ...],
    achievements: list[Achievement],
    snapshots: Mapping[str, ProgressionSnapshot] | None = None,
    inventory: Mapping[str, int] | None = None,
    data: CultivateDataSet | None = None,
    today: date | None = None,
) -> list[OperatorTarget]:
    """按判定结果流转目标状态：达成移除 / 不可自证转待确认。

    snapshots + inventory + data（+today）同时提供时，剩余目标按缺口
    刷新 not_started / in_progress；共享材料的重聚合在下一次 build_plan
    由剩余目标自然重建，无需在此单独处理。
    """

    def refresh_state(goal: Goal, goal_has_gap: bool) -> Goal:
        if goal.state in ("not_started", "in_progress"):
            return Goal(
                goal.kind,
                goal.target_id,
                goal.to_level,
                "in_progress" if goal_has_gap else "not_started",
            )
        return goal

    gap_index: set[tuple[str, int]] = set()
    should_refresh = (
        snapshots is not None
        and inventory is not None
        and data is not None
        and today is not None
    )
    if should_refresh:
        requirements = aggregate(build_requirements(targets, snapshots, data.demands))
        # 库存递归抵扣后再折算：已有高阶材料库存能抵掉目标，材料备齐的
        # 目标回到 not_started 而不是被反复刷取（与 has_material_gap 同口径）
        unmet = _unmet_by_stock(requirements, inventory, data)
        farm, _ = synthesize(unmet, data, today)
        for requirement in farm:
            for ref in requirement.sources:
                gap_index.add((ref.operator_id, ref.goal_index))

    removed_achievements = {
        (achievement.operator_id, achievement.goal_index)
        for achievement in achievements
        if achievement.achieved
    }
    new_targets: list[OperatorTarget] = []
    for target in targets:
        new_goals: list[Goal] = []
        for goal_index, goal in enumerate(target.goals):
            if (target.operator_id, goal_index) in removed_achievements:
                achievement = next(
                    achievement
                    for achievement in achievements
                    if achievement.operator_id == target.operator_id
                    and achievement.goal_index == goal_index
                )
                if achievement.confident:
                    continue  # 达成且可自证：移除
                new_goals.append(
                    Goal(goal.kind, goal.target_id, goal.to_level, "pending_confirm")
                )
                continue
            if should_refresh:
                new_goals.append(
                    refresh_state(goal, (target.operator_id, goal_index) in gap_index)
                )
            else:
                new_goals.append(goal)
        if new_goals:
            new_targets.append(OperatorTarget(target.operator_id, tuple(new_goals)))
    return new_targets
