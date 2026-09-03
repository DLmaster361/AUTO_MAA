#   AUTO-MAS: A Multi-Script, Multi-Config Management and Automation Software
#   Copyright © 2025-2026 AUTO-MAS Team
#
#   This file is part of AUTO-MAS.
#
#   AUTO-MAS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License
#   as published by the Free Software Foundation, either version 3 of
#   the License, or (at your option) any later version.
#
#   AUTO-MAS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with AUTO-MAS. If not, see <https://www.gnu.org/licenses/>.

from .app_options import (
    get_task_app_fields,
    read_app_config,
    write_app_config,
)
from .backup_archive import (
    archive_mas_backup,
    archive_onedragon_backup,
    get_mas_backup_dir,
    get_onedragon_backup_dir,
    list_mas_backups,
    list_onedragon_backups,
    restore_mas_backup,
    restore_onedragon_backup,
)
from .catalog import list_app_catalog
from .native_config import (
    NATIVE_INSTANCE_RUN_OPTIONS,
    native_account_field_meta,
    read_native_account_fields,
    read_native_instance_run,
    read_native_tasks,
    save_native_account_fields,
    save_native_instance_run,
    save_native_tasks,
)
from .notify import push_notification
from .zzz_od_config import (
    INSTANCE_RUN_ALL,
    RUN_STATUS_FAILED,
    RUN_STATUS_NOT_RUN,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    ZZZOD_GAME_LANGUAGE_LABELS,
    ZZZOD_GAME_LANGUAGE_VALUES,
    ZZZOD_GAME_REGION_LABELS,
    ZZZOD_GAME_REGION_VALUES,
    backup_instance,
    clear_run_records,
    diff_run_records,
    find_active_instance,
    find_free_instance_idx,
    instance_dir,
    list_instances,
    read_app_group,
    read_game_account,
    restore_instance,
    restore_instance_view,
    snapshot_run_records,
    validate_root,
    write_app_group,
    write_game_account,
    write_instance_view,
)

__all__ = [
    "INSTANCE_RUN_ALL",
    "RUN_STATUS_FAILED",
    "RUN_STATUS_NOT_RUN",
    "RUN_STATUS_RUNNING",
    "RUN_STATUS_SUCCESS",
    "ZZZOD_GAME_LANGUAGE_LABELS",
    "ZZZOD_GAME_LANGUAGE_VALUES",
    "ZZZOD_GAME_REGION_LABELS",
    "ZZZOD_GAME_REGION_VALUES",
    "archive_mas_backup",
    "archive_onedragon_backup",
    "backup_instance",
    "clear_run_records",
    "diff_run_records",
    "find_active_instance",
    "find_free_instance_idx",
    "get_mas_backup_dir",
    "get_onedragon_backup_dir",
    "get_task_app_fields",
    "instance_dir",
    "list_app_catalog",
    "list_instances",
    "list_mas_backups",
    "list_onedragon_backups",
    "NATIVE_INSTANCE_RUN_OPTIONS",
    "native_account_field_meta",
    "push_notification",
    "read_app_config",
    "read_app_group",
    "read_game_account",
    "read_native_account_fields",
    "read_native_instance_run",
    "read_native_tasks",
    "restore_instance",
    "restore_instance_view",
    "restore_mas_backup",
    "restore_onedragon_backup",
    "save_native_account_fields",
    "save_native_instance_run",
    "save_native_tasks",
    "snapshot_run_records",
    "validate_root",
    "write_app_config",
    "write_app_group",
    "write_game_account",
    "write_instance_view",
]
