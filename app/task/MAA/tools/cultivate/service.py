#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team

#   This file is part of AUTO-MAS.

#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.

#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.

#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

#   Contact: DLmaster_361@163.com

"""养成内核的应用编排层与组合根。

分层职责（DIP）：
- `types`     契约层，零依赖；
- `engine`    纯函数内核，只依赖契约；
- `providers` / `yituliu`  输入适配器与链执行器，只实现/依赖契约端口；
- 本模块     组合根与用例编排：决定用哪些适配器、如何取数据、如何组装成
  消费方（API / AutoProxy）要的形状。

组合根位于库边界：适配器不再知道自己是否被使用——换实现 = 改本模块的
池定义，或由调用方注入 chain / 数据源（见 `DepotCultivateService` 构造
参数），内核与适配器零改动。
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Awaitable, Callable, Mapping

import httpx

from .providers import (
    DefaultProgressionProvider,
    LocalInventoryProvider,
    LocalProgressionProvider,
    ManualProgressionProvider,
    resolve_inventory,
)
from .types import (
    CultivateDataSet,
    InventoryProvider,
    ProgressionProvider,
    ProviderContext,
)
from .yituliu import get_dataset_cached, stage_candidates

# 组合根：池的顺序即优先级。P4 森空岛接入 = 在 PROGRESSION_POOL 链首
# 插入 SklandProvider（self_certifying=True），双链自动生效，消费方零改动。
PROGRESSION_POOL: tuple[ProgressionProvider, ...] = (
    LocalProgressionProvider(),
    ManualProgressionProvider(),
    DefaultProgressionProvider(),
)

INVENTORY_POOL: tuple[InventoryProvider, ...] = (LocalInventoryProvider(),)


def get_progression_chain() -> tuple[ProgressionProvider, ...]:
    """需求计算链：全量池（含手填与兜底）。"""

    return PROGRESSION_POOL


def get_certifying_chain() -> tuple[ProgressionProvider, ...]:
    """达成检测链：按 self_certifying 过滤派生（手填不能自证达成）。"""

    return tuple(provider for provider in PROGRESSION_POOL if provider.self_certifying)


def get_inventory_chain() -> tuple[InventoryProvider, ...]:
    """库存链（预览与接管缺口判定用）。"""

    return INVENTORY_POOL


# 数据集加载端口签名：(配置目录, 代理) -> 数据集
DatasetLoader = Callable[
    [Path, "httpx.Proxy | str | None"], Awaitable[CultivateDataSet]
]


class DepotCultivateService:
    """MAA 库存保持编辑器的数据编排服务（组合根 + 用例）。

    依赖以端口形式注入，默认实现为生产装配：
    - `dataset_loader`：取养成数据集（默认一图流缓存加载，带磁盘/进程缓存）；
    - `progressions` / `inventory_chain`：练度与库存来源链。

    测试或未来接入第二个数据源时替换构造参数即可，本类之外零改动。
    """

    def __init__(
        self,
        *,
        dataset_loader: DatasetLoader | None = None,
        inventory_chain: tuple[InventoryProvider, ...] | None = None,
    ) -> None:
        self._dataset_loader = dataset_loader
        self._inventory_chain = inventory_chain or get_inventory_chain()

    async def stage_candidates(
        self,
        *,
        config_path: Path,
        item_id: str,
        proxy: httpx.Proxy | str | None = None,
        now_ms: int | None = None,
    ) -> list[dict[str, str]]:
        """掉落指定材料的关卡候选，按单件期望理智升序（UI 下拉形状）。

        资源关固定产出材料（采购凭证等）无单件理智，label 只展示关卡名
        与产出性质（见 yituliu._FIXED_SOURCE_STAGES）。
        """

        dataset = await self._load_dataset(config_path, proxy)
        options = stage_candidates(
            dataset,
            now_ms=now_ms if now_ms is not None else int(time.time() * 1000),
        ).get(item_id, [])
        return [
            {
                "label": (
                    f"{option['stage']}（固定产出）"
                    if option.get("fixed")
                    else f"{option['stage']}（{option['sanityPerItem']} 理智/件）"
                ),
                "value": option["stage"],
            }
            for option in options
        ]

    async def inventory(self, *, maa_data_dir: Path) -> Mapping[str, int] | None:
        """读取 MAA 仓库库存映射；数据不可用时返回 None（调用方决定兜底）。"""

        context = ProviderContext(maa_data_dir=maa_data_dir)
        result = resolve_inventory(context, self._inventory_chain)
        return result[0] if result is not None else None

    async def _load_dataset(
        self, config_path: Path, proxy: httpx.Proxy | str | None
    ) -> CultivateDataSet:
        if self._dataset_loader is not None:
            return await self._dataset_loader(config_path, proxy)
        return await get_dataset_cached(config_path, proxy)


# 生产装配的单例：消费方复用同一实例，保证数据集进程内缓存与池决策唯一。
depot_cultivate_service = DepotCultivateService()

__all__ = [
    "DepotCultivateService",
    "depot_cultivate_service",
    "get_certifying_chain",
    "get_inventory_chain",
    "get_progression_chain",
]
