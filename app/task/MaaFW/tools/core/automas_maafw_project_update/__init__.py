from __future__ import annotations

from .apply import UpdateApplyError
from .updater import (
    MaaFWProjectUpdateCandidate,
    MaaFWProjectUpdateDiscovery,
    MaaFWProjectUpdateError,
    MaaFWProjectUpdateResult,
    apply_maafw_project_update,
    detect_maafw_project_shell_hint,
    discover_maafw_project_update,
    update_maafw_project_if_needed,
)

__all__ = [
    "MaaFWProjectUpdateCandidate",
    "MaaFWProjectUpdateDiscovery",
    "MaaFWProjectUpdateError",
    "MaaFWProjectUpdateResult",
    "UpdateApplyError",
    "apply_maafw_project_update",
    "detect_maafw_project_shell_hint",
    "discover_maafw_project_update",
    "update_maafw_project_if_needed",
]
