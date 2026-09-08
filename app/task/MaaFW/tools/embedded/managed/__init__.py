"""第三层（资源共享 managed）服务层。

三层规划 §4 的第三层：MAS 管理不可变 Project Store 与精确 Runtime Pool，
依赖去重与路由，lease / reference / pin / GC。

**已接线**：``MaaFWManagedConfig`` 是注册在案的脚本类型，``MaaFWEmbeddedManager``
在托管形态下走 :class:`MaaFWManagedEnvironmentService` 准备环境，HTTP 侧有
``/api/scripts/maafw/managed/*`` 一组端点。接线点见
``tests/task/test_maafw_managed_wiring.py``。

落库的是插件 ``automas_script_maafw_managed`` 中**零宿主耦合**的两个模块
（``services`` + ``environment_service``）。该包另外三个文件（``plugin`` /
``schema`` / ``adapter``）依赖 ``app.plugins`` 插件 HTTP 宿主层，按移植指南
§4 规则 6 不搬；它们承担的宿主侧职责改由树内实现：远程更新编排在
``tools/embedded/managed_update.py``，HTTP 端点在 ``app/api/scripts.py``。
"""

from __future__ import annotations

from .environment_service import MaaFWManagedEnvironmentService
from .services import (
    ManagedServiceError,
    ManagedServiceGateway,
    managed_project_identity,
)

__all__ = [
    "MaaFWManagedEnvironmentService",
    "ManagedServiceError",
    "ManagedServiceGateway",
    "managed_project_identity",
]
