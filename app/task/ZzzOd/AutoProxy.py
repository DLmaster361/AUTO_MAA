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

"""ZZZ-OD 自动代理：按配置来源与账号切换方式拉起一条龙并监控日志。

MAS 用户与 zzz-od 实例槽**固定绑定**：每个用户绑定一个槽（绑定下标存于
用户配置 Info.SlotIdx，首次运行/配置时按全局查重分配），槽目录持久保留
（用户经「在一条龙内配置」维护配队等复杂配置）；注册表不持久写入——
运行/会话窗口内以**合成注册表视图**临时替换 one_dragon.yml（仅本脚本
用户槽），窗口结束恢复原生内容，zzz-od 原生世界零 MAS 痕迹。

- 用户态 + 「一条龙内置」切换（脚本级下拉，默认）：把全部启用用户的配置
  注入各自绑定槽（备份 → 注入并清运行记录），随后
  ``--onedragon --instance {slot1,slot2,...}`` 一次性运行多账号一条龙——
  zzz-od 内部依次执行各实例并自行切换游戏账号；结果按各实例槽运行记录
  diff 归属到对应用户。
- 用户态 + 「MAS账号切换」：逐用户循环（注入该用户配置到其绑定槽 → 运行
  → 结束），当前依赖一条龙账密登录切换账号；MAS 侧主动切换能力后续版本
  接入。
- 直控态：不注入不建视图，直接 ``--onedragon`` 裸跑，完全尊重 zzz-od 自己
  的 instance_run / 活跃实例 / 多账号运行设置；结果按全部实例运行记录聚合
  diff 判定。

启动器（OneDragon-RuntimeLauncher / OneDragon-Launcher）CLI 一条龙为进程内
同步运行、结束即退出；一条龙按任务粒度失败不中断（GroupApplication 继续跑
下一个），日志监控负责实时展示与致命错误 / 超时兜底。
"""

import asyncio
import json
import time
import uuid
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path

from app.core import Config
from app.models.config import ZzzOdConfig, ZzzOdUserConfig
from app.models.ConfigBase import MultipleConfig
from app.models.task import LogRecord, ScriptItem, TaskExecuteBase, UserItem
from app.services import Notify, System
from app.task.general.tools import execute_script_task
from app.utils import ProcessInfo, ProcessManager, get_logger
from app.utils.constants import UTC4
from app.utils.LogMonitor import LogMonitor

from .tools import (
    RUN_STATUS_FAILED,
    RUN_STATUS_RUNNING,
    RUN_STATUS_SUCCESS,
    archive_mas_backup,
    archive_onedragon_backup,
    backup_instance,
    clear_run_records,
    diff_run_records,
    find_active_instance,
    find_free_instance_idx,
    instance_dir,
    list_app_catalog,
    list_instances,
    push_notification,
    restore_instance,
    restore_instance_view,
    snapshot_run_records,
    write_app_group,
    write_game_account,
    write_instance_view,
)

logger = get_logger("ZZZ-OD 自动代理")

# 启动器标签 → exe 文件名（集成=WithRuntime 打包的 RuntimeLauncher；原始=旧安装器
# Launcher；.bak 为启动器自更新残留，不参与发现）。元组顺序即默认发现顺序（集成优先）
_ZZZOD_LAUNCHER_BOOK = {
    "集成": "OneDragon-RuntimeLauncher.exe",
    "原始": "OneDragon-Launcher.exe",
}

_ZZZOD_LAUNCHERS = tuple(_ZZZOD_LAUNCHER_BOOK.values())

# 启动器成功启动的证据：出现 zzz-od 应用层运行上下文即视为已启动（两种启动器的
# 一条龙运行日志都汇聚 .log/log.txt；启动器自身未起来时该文件无任何应用层条目）
_ZZZOD_LAUNCH_STARTED_MARKERS = (
    "[application_launcher.py",
    "[one_dragon_context.py",
    "[application_factory_manager.py",
)

# zzz-od 统一日志（log_utils，按日期滚动，当天固定为 log.txt）
_ZZZOD_REL_LOG = Path(".log") / "log.txt"

# 日志行格式：[HH:mm:ss.SSS] [file.py NN] [LEVEL]: message
_ZZZOD_LOG_TIME_START = 1
_ZZZOD_LOG_TIME_END = 13
_ZZZOD_LOG_TIME_FORMAT = "%H:%M:%S.%f"

# ── 内置失败关键词（zzz-od 原生日志，不向用户暴露配置）──────────────
#   「未找到有效的实例」—— --instance 无效后 ApplicationLauncher 直接退出；
#   「请先结束其他运行中的功能 再启动」—— 上一次运行未完全退出（残影进程）；
#   「运行应用 one_dragon 失败」—— 一条龙 app 执行抛异常（application_run_context）。
_ZZZOD_BUILTIN_FATAL: tuple[tuple[str, str], ...] = (
    ("未找到有效的实例", "ZZZ-OD 未找到有效的实例, 请检查账号配置"),
    ("请先结束其他运行中的功能 再启动", "ZZZ-OD 有运行中的功能未结束, 请稍后重试"),
    ("运行应用 one_dragon 失败", "ZZZ-OD 一条龙运行出现异常"),
)


def find_launcher_exe(root: Path) -> Path:
    """在安装根目录下发现 OneDragon 启动器。

    Raises:
        ValueError: 未找到任何启动器。
    """

    for name in _ZZZOD_LAUNCHERS:
        path = root / name
        if path.is_file():
            return path
    raise ValueError(f"{root} 下未找到 OneDragon 启动器, 请确认绝区零一条龙安装目录")


def find_launchers(root: Path) -> dict[str, Path]:
    """返回安装根目录下实际安装的启动器（标签 → exe 路径，未安装的不在结果中）。"""

    return {
        label: root / name
        for label, name in _ZZZOD_LAUNCHER_BOOK.items()
        if (root / name).is_file()
    }


def resolve_launcher(
    root: Path, mode: str, last_good: str = ""
) -> tuple[Path, str]:
    """按用户选择返回 (启动器 exe, 标签)。

    - 自动：优先「上次成功」的启动器（``last_good``），否则按默认顺序（集成优先）；
    - 原始/集成：固定用对应 exe，所选项未安装时回退默认顺序可用项并告警。

    Raises:
        ValueError: 安装根目录下没有任何启动器。
    """

    available = find_launchers(root)
    if available.get(mode):
        return available[mode], mode
    if mode == "自动" and last_good in available:
        return available[last_good], last_good
    # 固定模式所选未安装或无记忆：按默认顺序取首个可用（集成优先）
    for name in _ZZZOD_LAUNCHERS:
        path = root / name
        if path.is_file():
            label = next(
                (tag for tag, exe in _ZZZOD_LAUNCHER_BOOK.items() if exe == name),
                name,
            )
            if mode in ("原始", "集成"):
                logger.warning(
                    f"所选{mode}启动器未安装，已回退使用{label}启动器"
                )
            return path, label
    raise ValueError(f"{root} 下未找到 OneDragon 启动器, 请确认绝区零一条龙安装目录")


def _other_launcher_label(root: Path, label: str) -> str | None:
    """返回另一启动器的标签；未安装返回 None。"""

    other = "原始" if label == "集成" else "集成"
    return other if (root / _ZZZOD_LAUNCHER_BOOK[other]).is_file() else None


async def ensure_user_slot(
    root: Path, user_config: ZzzOdUserConfig, used_idxs: set[int]
) -> int:
    """解析/分配用户的绑定实例槽（纯分配，不触碰注册表——注册表由合成视图提供）。

    绑定下标存于用户配置 ``Info.SlotIdx``：有效 = 不与原生实例、其他 MAS
    用户已绑定槽冲突；无效则分配最小空闲 idx（全局查重）并把绑定落回用户
    配置。槽目录持久保留（配队等复杂配置），注册表只在运行/会话窗口内以
    合成视图出现。
    """

    bound = int(user_config.get("Info", "SlotIdx") or -1)
    native_idxs = {
        int(item.get("idx", -1))
        for item in list_instances(root)
        if isinstance(item, dict)
    }
    if bound > 0 and bound not in native_idxs and bound not in used_idxs:
        slot = bound
    else:
        slot = find_free_instance_idx(root, used_idxs)
    used_idxs.add(slot)
    if slot != bound:
        await user_config.set("Info", "SlotIdx", slot)
    return slot


def collect_used_slot_idxs(
    exclude_uids: set[uuid.UUID] | None = None,
) -> set[int]:
    """收集所有 ZzzOd 脚本用户已绑定的实例槽 idx（跨脚本全局查重用）。

    槽目录 config/{idx:02d} 跨脚本共享文件系统，idx 分配必须全局唯一，
    否则不同脚本的用户会写入同一目录互相覆盖配置。本次要注入/会话的用户
    经 ``exclude_uids`` 排除——它们通过自身 SlotIdx 重认领绑定。
    """

    used: set[int] = set()
    excluded = exclude_uids or set()
    for script_config in Config.ScriptConfig.values():
        if not isinstance(script_config, ZzzOdConfig):
            continue
        for uid, cfg in script_config.UserData.items():
            if uid in excluded:
                continue
            bound = int(cfg.get("Info", "SlotIdx") or -1)
            if bound > 0:
                used.add(bound)
    return used


def find_duplicate_user_names(
    exclude_uid: uuid.UUID, name: str, user_config: MultipleConfig[ZzzOdUserConfig]
) -> bool:
    """同脚本内是否已有其他用户使用给定名称（ZzzOd 要求同脚本用户名唯一）。"""

    return any(
        str(cfg.get("Info", "Name") or "").strip() == name
        for uid, cfg in user_config.items()
        if uid != exclude_uid
    )


def parse_user_apps(user_config: ZzzOdUserConfig) -> list[dict]:
    """解析用户配置的一条龙任务编排（JSON），返回 enabled 项列表。

    Raises:
        ValueError: AppList 不是合法 JSON 或结构异常。
    """

    try:
        raw = json.loads(str(user_config.get("OneDragon", "AppList") or "[]"))
    except json.JSONDecodeError as e:
        raise ValueError("一条龙任务编排数据异常, 请重新编辑任务配置") from e
    if not isinstance(raw, list):
        raise ValueError("一条龙任务编排数据异常, 请重新编辑任务配置")
    return [item for item in raw if isinstance(item, dict) and item.get("enabled")]


def user_field_patch(user_config: ZzzOdUserConfig) -> dict[str, str]:
    """MAS 用户字段 → ``game_account.yml`` patch（仅非空字段，其余保留槽值）。"""

    patch: dict[str, str] = {}
    for yaml_key, section, field in (
        ("game_region", "Game", "GameRegion"),
        ("game_path", "Game", "GamePath"),
        ("game_language", "Game", "GameLanguage"),
        ("account", "Game", "Account"),
        ("password", "Game", "Password"),
        ("bilibili_account_name", "Game", "BilibiliAccountName"),
    ):
        value = str(user_config.get(section, field) or "").strip()
        if value:
            patch[yaml_key] = value
    return patch


def inject_user_fields(
    root: Path, slot_idx: int, user_config: ZzzOdUserConfig, apps: list[dict]
) -> None:
    """把 MAS 用户字段写入绑定槽（game_account patch + 任务编排整表）。

    不清运行记录、不备份——配置会话（以本页配置为基线打开 GUI）与运行时
    注入（配合 clear_run_records）共用。
    """

    slot_dir = instance_dir(root, slot_idx)
    write_game_account(slot_dir, user_field_patch(user_config))
    write_app_group(slot_dir, apps)


def _snapshot_all_run_records(root: Path) -> dict[str, int]:
    """聚合全部实例的运行记录（直控态基准）：失败 > 运行中 > 成功 > 未跑。"""

    aggregated: dict[str, int] = {}
    for item in list_instances(root):
        for app_id, status in snapshot_run_records(
            root, int(item.get("idx", -1))
        ).items():
            prev = aggregated.get(app_id)
            if status == RUN_STATUS_RUNNING or prev == RUN_STATUS_RUNNING:
                aggregated[app_id] = RUN_STATUS_RUNNING
            elif status == RUN_STATUS_FAILED or prev == RUN_STATUS_FAILED:
                aggregated[app_id] = RUN_STATUS_FAILED
            elif status == RUN_STATUS_SUCCESS or prev == RUN_STATUS_SUCCESS:
                aggregated[app_id] = RUN_STATUS_SUCCESS
    return aggregated


class AutoProxyTask(TaskExecuteBase):
    """ZZZ-OD 自动代理：逐用户按三态来源拉起启动器 CLI 一条龙并监控"""

    # 取消时等 final_task 完整收尾（SRC/MaaFW 同款）：不设此 flag 时外层取消会
    # 立刻打断 shield 的 final_task，导致 kill_managed_process 没跑——取消任务后
    # zzz-od 启动器/一行龙本体仍继续运行
    wait_for_finalizer_on_cancel = True

    def __init__(
        self,
        script_info: ScriptItem,
        script_config: ZzzOdConfig,
        user_config: MultipleConfig[ZzzOdUserConfig],
    ):
        super().__init__()
        if script_info.task_info is None:
            raise RuntimeError("ScriptItem 未绑定到 TaskItem")

        self.task_info = script_info.task_info
        self.script_info = script_info
        self.script_config = script_config
        self.user_config = user_config

        self.cur_user_item: UserItem = self.script_info.user_list[
            self.script_info.current_index
        ]
        self.cur_user_uid = uuid.UUID(self.cur_user_item.user_id)
        self.cur_user_config: ZzzOdUserConfig = self.user_config[self.cur_user_uid]
        # 两态配置来源（用户=本配置字段 / 直控=zzz-od 原生配置）
        self.mode = str(self.cur_user_config.get("Info", "Mode") or "用户")
        # 账号切换方式（脚本级下拉，仅用户态生效）：
        # 一条龙内置=多用户注入多实例槽一次跑；MAS账号切换=逐用户循环
        self.account_switch = str(
            self.script_config.get("Game", "AccountSwitch") or "一条龙内置"
        )
        self.cur_user_log: LogRecord | None = None
        self.launcher_process_manager: ProcessManager | None = None
        self.wait_event: asyncio.Event | None = None
        self.script_root_path: Path | None = None
        self.launcher_exe_path: Path | None = None
        # 当前使用的启动器标签（原始/集成）、本任务启动时的模式快照（运行中途
        # 改配置不影响本轮判定）与是否已切换过
        self._launcher_label: str | None = None
        self._launcher_mode = "自动"
        self._launcher_switched = False
        self.script_log_path: Path | None = None
        self.log_monitor: LogMonitor | None = None
        # 注入现场（用户态共用）：绑定槽 → 备份目录（None=槽目录为本运行新建）
        self._injected_slots: list[tuple[int, Path | None]] = []
        # 槽位归属与注入基准（内置切换按槽归属用户；单用户模式只有一个槽）
        self._slot_users: dict[int, tuple[UserItem, ZzzOdUserConfig]] = {}
        self._slot_records_before: dict[int, dict[str, int]] = {}
        self._multi_uids: set[str] = set()
        self._multi_judged: set[int] = set()
        self._multi_ran = False
        self.run_book = False
        # app_id → 中文名（用于结果与推送日志展示）
        self._app_name_book: dict[str, str] = {}

    @staticmethod
    def _parse_app_list(cfg: ZzzOdUserConfig) -> list[dict]:
        """当前用户的一条龙任务编排 enabled 项列表（模块级共享实现）。"""

        return parse_user_apps(cfg)

    def _enabled_app_list(self) -> list[dict]:
        """当前用户的一条龙任务编排 enabled 项列表。"""

        return parse_user_apps(self.cur_user_config)

    def _is_multi_account(self) -> bool:
        """用户态且脚本级账号切换方式为「一条龙内置」时走多账号一次跑。"""

        return self.mode == "用户" and self.account_switch == "一条龙内置"

    def _collect_inject_users(
        self,
    ) -> list[tuple[UserItem, ZzzOdUserConfig, list[dict]]]:
        """内置切换的注入名单：启用且有任务编排的用户（按调度顺序）。

        逐用户施加跳过条件（剩余天数 / 今日代理次数上限 / 任务编排为空），
        命中的用户标记「跳过」不入列。
        """

        limit = int(self.script_config.get("Run", "ProxyTimesLimit"))
        users: list[tuple[UserItem, ZzzOdUserConfig, list[dict]]] = []
        for user_item in self.script_info.user_list:
            uid = uuid.UUID(user_item.user_id)
            cfg = self.user_config[uid]
            if not cfg.get("Info", "Status"):
                continue
            if cfg.get("Info", "RemainedDay") == 0:
                user_item.status = "跳过"
                continue
            if limit != 0 and cfg.get("Data", "ProxyTimes") >= limit:
                user_item.status = "跳过"
                continue
            try:
                apps = self._parse_app_list(cfg)
            except ValueError:
                user_item.status = "异常"
                continue
            if not apps:
                user_item.status = "跳过"
                continue
            users.append((user_item, cfg, apps))
        return users

    def _inject_user_config(
        self, slot_idx: int, user_config: ZzzOdUserConfig, apps: list[dict]
    ) -> None:
        """把用户配置字段生成 zzz-od YAML 写入实例槽（MaaEnd 式字段下发）。

        只覆盖 MAS 侧非空字段，槽内 game_account.yml 的其余字段（platform、
        自定义窗口标题等）原样保留；随后清空运行记录让本次任务全部重跑。
        """

        inject_user_fields(self.script_root_path, slot_idx, user_config, apps)
        clear_run_records(self.script_root_path, slot_idx)

    async def _prepare_injection(
        self, users: list[tuple[UserItem, ZzzOdUserConfig, list[dict]]]
    ) -> None:
        """用户态注入：合成注册表视图 + 各用户字段写入绑定槽。

        内置切换=全部启用用户各注入各槽（多账号一次跑）；MAS账号切换=仅当前
        用户（逐用户循环）。槽目录持久保留（配队等复杂配置），运行内容由
        备份/恢复保证零痕迹；注册表以合成视图呈现（仅本脚本用户槽）。
        """

        backup_base = (
            Path.cwd() / "data" / self.script_info.script_id / "Temp" / "InstanceBackup"
        )
        # 闪退自愈：上次运行/会话若残留合成视图，先还原原生注册表
        restore_instance_view(self.script_root_path)
        # 归档点：一条龙原生配置快照（one_dragon.yml + 原生实例目录）——
        # 必须在 ensure_user_slot（可能注册新槽）与合成视图写入之前，
        # 捕获的是未被本次 MAS 操作触碰的原生状态；MAS 槽快照在下方循环内逐槽归档
        with suppress(Exception):
            archive_onedragon_backup(self.script_info.script_id, self.script_root_path)
        used_idxs = collect_used_slot_idxs(
            exclude_uids={uuid.UUID(u.user_id) for u, _, _ in users}
        )

        for user_item, cfg, apps in users:
            slot = await ensure_user_slot(self.script_root_path, cfg, used_idxs)
            backup_dir = backup_base / f"{slot:02d}"
            if instance_dir(self.script_root_path, slot).is_dir():
                backup_instance(self.script_root_path, slot, backup_dir)
                # 时间戳归档：MAS 用户槽快照（含配队等全部内容），供配置恢复
                archive_mas_backup(
                    self.script_info.script_id,
                    slot,
                    instance_dir(self.script_root_path, slot),
                )
                self._injected_slots.append((slot, backup_dir))
            else:
                self._injected_slots.append((slot, None))
            self._inject_user_config(slot, cfg, apps)
            self._slot_users[slot] = (user_item, cfg)
            self._slot_records_before[slot] = snapshot_run_records(
                self.script_root_path, slot
            )
            self._multi_uids.add(user_item.user_id)

        # 合成注册表视图：仅本脚本注入槽，一条龙窗口内原生实例完全不在场
        write_instance_view(
            self.script_root_path,
            [
                (slot, f"MAS-{self._slot_users[slot][1].get('Info', 'Name')}")
                for slot, _ in self._injected_slots
            ],
            active_idx=self._injected_slots[0][0],
        )

    async def check(self) -> str:
        root = Path(self.script_config.get("Info", "RootPath"))
        if not root.is_dir():
            return "请设置绝区零一条龙安装目录"
        try:
            find_launcher_exe(root)
        except ValueError as e:
            return str(e)

        if self.mode not in ("用户", "直控"):
            return f"不支持的配置来源: {self.mode}"

        if self.mode == "用户":
            # 同脚本用户名唯一（绑定槽名与统计都依赖名字区分）
            names = [
                str(cfg.get("Info", "Name") or "").strip()
                for cfg in self.user_config.values()
                if cfg.get("Info", "Status")
            ]
            duplicates = sorted({n for n in names if names.count(n) > 1})
            if duplicates:
                return (
                    f"存在同名用户: {'、'.join(duplicates)}, 请为每个用户设置不同的名称"
                )
            if self._is_multi_account():
                # 内置切换：cur_user 只是触发者，逐用户跳过条件在注入名单中施加
                if not self._collect_inject_users():
                    return "没有可注入的用户, 请确认用户已启用且任务配置非空"
            else:
                try:
                    if not self._enabled_app_list():
                        return "未启用任何一条龙任务, 请在用户配置中开启至少一个任务"
                except ValueError as e:
                    return str(e)
                if self.script_config.get(
                    "Run", "ProxyTimesLimit"
                ) != 0 and self.cur_user_config.get(
                    "Data", "ProxyTimes"
                ) >= self.script_config.get("Run", "ProxyTimesLimit"):
                    self.cur_user_item.status = "跳过"
                    return "今日代理次数已达上限, 跳过该用户"
                if self.cur_user_config.get("Info", "RemainedDay") == 0:
                    self.cur_user_item.status = "跳过"
                    return "用户剩余天数为 0, 跳过该用户"
        elif find_active_instance(root) is None:
            return "zzz-od 中没有可运行的实例, 请先在一条龙中创建账号"

        return "Pass"

    async def prepare(self):
        self.launcher_process_manager = ProcessManager()
        self.wait_event = asyncio.Event()

        self.user_start_time = datetime.now()
        self.script_root_path = Path(self.script_config.get("Info", "RootPath"))
        self.launcher_exe_path = find_launcher_exe(self.script_root_path)
        self.script_log_path = self.script_root_path / _ZZZOD_REL_LOG
        self.log_monitor = LogMonitor(
            (_ZZZOD_LOG_TIME_START, _ZZZOD_LOG_TIME_END),
            _ZZZOD_LOG_TIME_FORMAT,
            self.check_log,
        )

        with suppress(Exception):
            self._app_name_book = {
                item["app_id"]: item["app_name"]
                for item in list_app_catalog(self.script_root_path)
            }

        # 用户级节点详情推送模式（build_user_result_text 按此渲染）
        self.cur_user_item.push_log_mode = str(
            self.cur_user_config.get("Notify", "PushLogMode") or "汇总"
        )
        self.run_book = False

    async def main_task(self):
        await self.prepare()
        self.curdate = datetime.now(tz=UTC4).strftime("%Y-%m-%d")
        if self.cur_user_config.get("Data", "LastProxyDate") != self.curdate:
            await self.cur_user_config.set("Data", "LastProxyDate", self.curdate)
            await self.cur_user_config.set("Data", "ProxyTimes", 0)

        self.cur_user_item.status = "运行"

        run_limit = int(self.script_config.get("Run", "RunTimesLimit"))
        try:
            # 注入现场（用户态）：绑定槽备份 → 由用户配置字段生成 YAML 写入槽 →
            # 临时切 instance_run。注入只做一次——重试不清运行记录，
            # 让 zzz-od 按记录跳过已完成任务。
            if self.mode == "直控":
                records_before = _snapshot_all_run_records(self.script_root_path)
                launcher_args = ["--onedragon"]
            else:
                if self._is_multi_account():
                    # 内置切换：全部启用用户 → 各自绑定槽，一条龙多账号一次跑
                    inject_users = self._collect_inject_users()
                    if not inject_users:
                        raise RuntimeError(
                            "没有可注入的用户, 请确认用户已启用且任务配置非空"
                        )
                else:
                    # MAS账号切换：仅当前用户（逐用户循环）
                    inject_users = [
                        (
                            self.cur_user_item,
                            self.cur_user_config,
                            self._enabled_app_list(),
                        )
                    ]
                await self._prepare_injection(inject_users)
                launcher_args = [
                    "--onedragon",
                    "--instance",
                    ",".join(str(slot) for slot, _ in self._injected_slots),
                ]

            if self.script_config.get("Game", "CloseOnFinish"):
                launcher_args.append("--close-game")

            # 启动器选择：直控/用户统一按配置——自动=优先上次成功项，原始/集成=固定
            # 对应项（未安装回退可用项）；直控默认「自动」时行为等同原强绑定默认顺序
            self._launcher_mode = str(
                self.cur_user_config.get("Info", "LauncherMode") or "自动"
            )
            self.launcher_exe_path, self._launcher_label = resolve_launcher(
                self.script_root_path,
                self._launcher_mode,
                str(self.cur_user_config.get("Data", "LauncherLastGood") or ""),
            )

            for i in range(run_limit):
                if self.run_book:
                    break
                logger.info(
                    f"用户 {self.cur_user_item.name} - 尝试次数: {i + 1}/{run_limit}"
                )
                # 内置切换时触发者可能不在注入名单（如无任务被跳过），
                # 不能把它的「跳过」状态覆盖为「运行」
                if (
                    not self._is_multi_account()
                    or self.cur_user_item.user_id in self._multi_uids
                ):
                    self.cur_user_item.status = "运行"
                self.log_start_time = datetime.now()
                self.cur_user_item.log_record[self.log_start_time] = LogRecord()
                self.cur_user_log = self.cur_user_item.log_record[self.log_start_time]
                self.script_info.log = ""

                if self.cur_user_config.get("Info", "IfScriptBeforeTask"):
                    await execute_script_task(
                        Path(self.cur_user_config.get("Info", "ScriptBeforeTask")),
                        "脚本前任务",
                    )

                run_desc = (
                    f"{self.mode}配置·内置切换·{len(self._injected_slots)}个用户"
                    if self._is_multi_account()
                    else f"{self.mode}配置"
                )
                await self._push_dispatch_log(f"启动 ZZZ-OD 一条龙（{run_desc}）")
                logger.info(
                    f"启动 ZZZ-OD 启动器: {self.launcher_exe_path} "
                    f"{' '.join(launcher_args)}"
                )

                await self.launcher_process_manager.open_process(
                    self.launcher_exe_path,
                    *launcher_args,
                    target_process=ProcessInfo(
                        name=self.launcher_exe_path.name,
                        exe=str(self.launcher_exe_path),
                        cmdline=None,
                    ),
                    elevated=True,
                )

                await asyncio.sleep(1)
                await self.log_monitor.start_monitor_file(
                    self.script_log_path, self.log_start_time
                )

                self.wait_event.clear()
                await self.wait_event.wait()
                await self.log_monitor.stop()

                # 进程退出后按运行记录 diff 判定终态
                log = "".join(self.cur_user_log.content)
                if self._is_multi_account():
                    await self._judge_multi(log)
                elif self.mode == "直控":
                    records_after = _snapshot_all_run_records(self.script_root_path)
                    self._judge_final(records_before, records_after, log)
                else:
                    slot0 = self._injected_slots[0][0]
                    records_before = self._slot_records_before[slot0]
                    records_after = snapshot_run_records(self.script_root_path, slot0)
                    self._judge_final(records_before, records_after, log)

                if self.cur_user_log.status == "Success!":
                    self.run_book = True
                    if (
                        self._launcher_label is not None
                        and self._launcher_mode == "自动"
                    ):
                        # 自动模式：把本次成功使用的启动器记忆为下次优先项
                        await self.cur_user_config.set(
                            "Data", "LauncherLastGood", self._launcher_label
                        )
                    if not self._is_multi_account():
                        self._collect_push_log(records_before, records_after)
                    self.script_info.log = "检测到 ZZZ-OD 已完成任务"
                    if self.cur_user_config.get("Info", "IfScriptAfterTask"):
                        await execute_script_task(
                            Path(self.cur_user_config.get("Info", "ScriptAfterTask")),
                            "脚本后任务",
                        )
                    break

                # 自动模式：启动器未能启动（无应用层日志且运行记录无变化）时，
                # 自动切换到另一启动器并占用下一轮重试
                if await self._maybe_switch_launcher(log):
                    continue

                logger.warning(
                    f"用户 {self.cur_user_item.name} - ZZZ-OD 代理异常: "
                    f"{self.cur_user_log.status}"
                )
                self.script_info.log = f"{self.cur_user_log.status}\n正在中止相关程序"
                await self.kill_managed_process()
                try:
                    await Notify.push_plyer(
                        "ZZZ-OD 自动代理出现异常！",
                        f"用户 {self.cur_user_item.name} 的自动代理出现一次异常",
                        f"{self.cur_user_item.name}的自动代理出现异常",
                        3,
                    )
                except Exception:
                    pass
                if self.cur_user_config.get("Info", "IfScriptAfterTask"):
                    await execute_script_task(
                        Path(self.cur_user_config.get("Info", "ScriptAfterTask")),
                        "脚本后任务",
                    )
                if i + 1 < run_limit:
                    self.script_info.log += f"\n将在稍后重试 ({i + 1}/{run_limit})"
                    await asyncio.sleep(10)
        finally:
            # 无论成败/异常，注入现场立即恢复（MAS 不留痕迹，zzz-od 原生配置零接触）
            await self._restore_injection()

    def _app_display_name(self, app_id: str) -> str:
        """app_id 的中文展示名；目录未收录时回退 app_id。"""

        return self._app_name_book.get(app_id, app_id)

    def _judge_final(self, records_before: dict, records_after: dict, log: str) -> None:
        """进程退出后的终态判定（优先级：致命日志 > 失败任务 > 成功任务 > 无变化）。"""

        log_status = "ZZZ-OD 正常运行中"
        user_status: str | None = None

        for needle, msg in _ZZZOD_BUILTIN_FATAL:
            if needle in log:
                log_status = msg
                user_status = "异常"
                break
        else:
            diffs = diff_run_records(records_before, records_after)
            failed_apps = [
                app_id for app_id, _, new in diffs if new == RUN_STATUS_FAILED
            ]
            if failed_apps:
                failed_names = "、".join(
                    self._app_display_name(app_id) for app_id in failed_apps
                )
                log_status = f"ZZZ-OD 部分任务执行失败: {failed_names}"
                user_status = "异常"
            elif any(new == RUN_STATUS_SUCCESS for _, _, new in diffs):
                log_status = "Success!"
                user_status = "完成"
            else:
                # 运行记录无变化：直控态=今日任务早已全部完成（或无启用任务）
                log_status = "今日任务均已完成"
                user_status = "完成"

        self.cur_user_log.status = log_status
        if user_status is not None:
            self.cur_user_item.status = user_status

    def _launch_evidence(self, log: str, records_changed: bool) -> bool:
        """启动器是否已成功启动：出现应用层运行上下文日志或运行记录有变化即视为已启动。

        两种启动器的一条龙运行日志都汇聚 .log/log.txt；启动器自身未能启动
        （exe 缺失环境、同步失败早退等）时该文件没有任何应用层条目。
        """

        return records_changed or any(
            marker in log for marker in _ZZZOD_LAUNCH_STARTED_MARKERS
        )

    async def _maybe_switch_launcher(self, log: str) -> bool:
        """自动模式：判定启动器未能启动且另一启动器可用时，切换后占用下一轮重试。

        返回 True 表示已切换（调用方 continue，切换本身消耗一轮重试额度）；
        非自动 / 已切换过 / 无另一启动器 / 已有启动证据时不切换。
        """

        if self._launcher_mode != "自动":
            return False
        if self._launcher_switched or self._launcher_label is None:
            return False

        records_changed = False
        if self._injected_slots:
            slot0 = self._injected_slots[0][0]
            records_changed = bool(
                diff_run_records(
                    self._slot_records_before.get(slot0, {}),
                    snapshot_run_records(self.script_root_path, slot0),
                )
            )
        if self._launch_evidence(log, records_changed):
            return False

        other = _other_launcher_label(self.script_root_path, self._launcher_label)
        if other is None:
            return False

        self._launcher_label = other
        self.launcher_exe_path = (
            self.script_root_path / _ZZZOD_LAUNCHER_BOOK[other]
        )
        self._launcher_switched = True
        logger.warning(
            f"检测到 {other}启动器未能启动，已切换为另一启动器重试"
        )
        return True

    def _collect_push_log(self, records_before: dict, records_after: dict) -> None:
        """把任务粒度结果采集进 push_log（用户级 PushLogMode 控制是否采报）。"""

        self._append_user_push_log(
            self.cur_user_item, records_before, records_after, time.time()
        )

    def _append_user_push_log(
        self,
        user_item: UserItem,
        records_before: dict,
        records_after: dict,
        now: float,
    ) -> None:
        """按指定用户的 PushLogMode 采集任务粒度结果到其 push_log。"""

        if user_item.push_log_mode == "关闭":
            return

        diffs = diff_run_records(records_before, records_after)
        for app_id, _, new in diffs:
            name = self._app_display_name(app_id)
            if new == RUN_STATUS_SUCCESS:
                user_item.push_log.append(("普通", f"✅ 成功: {name}", now))
            elif new == RUN_STATUS_FAILED:
                user_item.push_log.append(("错误", f"❌ 失败: {name}", now))
        # 本次未重跑的已完成任务（before==after==成功）用跳过行呈现，
        # 让用户区分「本次跑了」与「早已完成」（直控态由 zzz-od 按记录跳过）
        changed_ids = {app_id for app_id, _, _ in diffs}
        for app_id, status in records_after.items():
            if status == RUN_STATUS_SUCCESS and app_id not in changed_ids:
                user_item.push_log.append(
                    ("普通", f"⏭ 跳过: {self._app_display_name(app_id)}", now)
                )

    async def _judge_multi(self, log: str) -> None:
        """内置切换：按各实例槽运行记录 diff 归属每个用户的结果。

        致命日志优先：整轮异常时未完成的用户一律标记异常。全部用户完成时
        cur_user_log.status 置 ``Success!`` 以复用主流程的成功分支；任一用户
        未完成则进入重试（zzz-od 按运行记录跳过已完成任务）。
        """

        fatal = next(
            (msg for needle, msg in _ZZZOD_BUILTIN_FATAL if needle in log), None
        )
        now = time.time()
        all_ok = True

        for slot, (user_item, cfg) in self._slot_users.items():
            before = self._slot_records_before.get(slot, {})
            after = snapshot_run_records(self.script_root_path, slot)
            diffs = diff_run_records(before, after)
            failed = any(new == RUN_STATUS_FAILED for _, _, new in diffs)
            success = any(new == RUN_STATUS_SUCCESS for _, _, new in diffs)
            ok = fatal is None and success and not failed
            all_ok = all_ok and ok

            user_item.status = "完成" if ok else "异常"
            # 重试会带着同一全零基准重判：推送条目整体重建避免重复；
            # 数据落库只在状态变化时写，防止重试期间 ProxyTimes 多次自增
            if slot in self._multi_judged:
                user_item.push_log.clear()
            self._append_user_push_log(user_item, before, after, now)
            if slot not in self._multi_judged or ok:
                await self._persist_multi_user_result(
                    cfg, ok, slot in self._multi_judged
                )
            self._multi_judged.add(slot)

        if fatal is not None:
            self.cur_user_log.status = fatal
            if self.cur_user_item.user_id in self._multi_uids:
                self.cur_user_item.status = "异常"
        elif all_ok:
            self.cur_user_log.status = "Success!"
        else:
            failed_users = "、".join(
                user_item.name
                for user_item, _ in self._slot_users.values()
                if user_item.status != "完成"
            )
            self.cur_user_log.status = f"ZZZ-OD 部分用户执行失败: {failed_users}"

        self.run_book = all_ok
        self._multi_ran = True

    async def _persist_multi_user_result(
        self, cfg: ZzzOdUserConfig, ok: bool, judged_before: bool
    ) -> None:
        """内置切换：逐用户写回代理数据（对齐 _persist_user_run_result 语义）。

        ok → 成功（幂等：重试时已写过的用户跳过自增）；ok=False → 仅当本次
        运行尚未写过该用户时落「失败」，重试成功后仍可翻转为成功。
        """

        if ok:
            if cfg.get("Data", "LastProxyStatus") == "成功" and judged_before:
                return
            if (
                cfg.get("Data", "ProxyTimes") == 0
                and cfg.get("Info", "RemainedDay") != -1
            ):
                await cfg.set("Info", "RemainedDay", cfg.get("Info", "RemainedDay") - 1)
            await cfg.set("Data", "ProxyTimes", cfg.get("Data", "ProxyTimes") + 1)
            await cfg.set("Data", "LastProxyStatus", "成功")
        else:
            if judged_before:
                return
            await cfg.set("Data", "LastProxyStatus", "失败")

    async def _push_dispatch_log(self, line: str) -> None:
        """向调度台追加流程日志（赋值 script_info.log 会触发 WebSocket 推送）。"""

        prev = self.script_info.log
        self.script_info.log = f"{prev}\n{line}" if prev else line
        await asyncio.sleep(0)

    async def _restore_injection(self) -> None:
        """恢复注入现场（用户态接管过时生效；幂等，恢复一次后置空）。

        先还原合成视图（原生注册表回来，含原生 instance_run），再逐槽恢复
        备份；槽目录一律保留（配队等复杂配置持久供配置会话维护）。
        """

        restore_instance_view(self.script_root_path)
        slots, self._injected_slots = self._injected_slots, []
        self._slot_users = {}
        self._slot_records_before = {}
        self._multi_uids = set()
        self._multi_judged = set()
        if not slots:
            return
        try:
            for slot, backup_dir in slots:
                if backup_dir is not None and backup_dir.is_dir():
                    restore_instance(self.script_root_path, slot, backup_dir)
        except Exception as e:
            logger.opt(exception=True).warning(f"恢复 ZZZ-OD 注入现场失败: {e}")

    async def check_log(self, log_content: list[str], latest_time: datetime) -> None:
        """按内置日志监控运行；致命错误与超时立即终止，进程退出触发统一终判。"""

        log = "".join(log_content)
        self.cur_user_log.content = log_content
        self.script_info.log = log[-4000:] if len(log) > 4000 else log

        log_status = "ZZZ-OD 正常运行中"
        user_item_status: str | None = None
        need_stop = False

        for needle, msg in _ZZZOD_BUILTIN_FATAL:
            if needle in log:
                log_status = msg
                user_item_status = "异常"
                need_stop = True
                break
        else:
            if not await self.launcher_process_manager.is_running():
                # 启动器进程退出 = 一条龙运行结束（正常路径也如此），
                # 终态成败由 main_task 的运行记录 diff 统一判定
                need_stop = True
            elif datetime.now() - latest_time > timedelta(
                minutes=self.script_config.get("Run", "RunTimeLimit")
            ):
                log_status = "ZZZ-OD 运行超时"
                user_item_status = "异常"
                need_stop = True

        self.cur_user_log.status = log_status
        if user_item_status is not None and (
            not self._is_multi_account()
            or self.cur_user_item.user_id in self._multi_uids
        ):
            self.cur_user_item.status = user_item_status

        logger.debug(f"ZZZ-OD 日志分析结果: {self.cur_user_log.status}")
        if need_stop:
            logger.info(f"ZZZ-OD 任务结果: {self.cur_user_log.status}, 日志锁已释放")
            self.wait_event.set()

    async def final_task(self):
        # 结束时先清理进程与监控
        if self.log_monitor is not None:
            with suppress(Exception):
                await self.log_monitor.stop()
        await self.kill_managed_process()
        await self._restore_injection()

        # 写入历史记录（对齐 General/SRC/MaaEnd/Okww/BetterGI 行为）
        statistic_paths: list[Path] = []
        for t, log_item in self.cur_user_item.log_record.items():
            dt = t.replace(tzinfo=datetime.now().astimezone().tzinfo).astimezone(UTC4)
            log_path = Config.build_history_log_path(
                script_name=self.script_info.name,
                user_name=self.cur_user_item.name,
                log_time=dt,
            )

            if log_item.status == "ZZZ-OD 正常运行中":
                log_item.status = "任务被用户手动中止"

            if len(log_item.content) == 0:
                log_item.content = ["未捕获到任何日志内容"]
                log_item.status = "未捕获到日志"

            await Config.save_general_log(log_path, log_item.content, log_item.status)
            statistic_paths.append(log_path.with_suffix(".json"))

        if statistic_paths:
            try:
                statistics = await Config.merge_statistic_info(statistic_paths)
                statistics["user_info"] = self.cur_user_item.name
                start_time = getattr(self, "user_start_time", datetime.now())
                statistics["start_time"] = start_time.strftime("%Y-%m-%d %H:%M:%S")
                statistics["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                statistics["user_result"] = (
                    "代理任务全部完成" if self.run_book else self.cur_user_item.result
                )
                success_symbol = "√" if self.run_book else "X"
                await push_notification(
                    "统计信息",
                    f"{datetime.now().strftime('%m-%d')} |{success_symbol}|  "
                    f"{self.cur_user_item.name} 的 ZZZ-OD 自动代理统计报告",
                    statistics,
                    self.cur_user_config,
                )
            except Exception as e:
                # 失败不再静默：既记 ERROR 日志，也推到调度台实时日志
                await self._push_dispatch_log(f"推送用户统计通知失败: {e}")
                logger.opt(exception=True).error(
                    f"推送 ZZZ-OD 用户统计通知时出现异常: {e}"
                )

        await self._persist_user_run_result()

    async def _persist_user_run_result(self) -> None:
        if self.cur_user_config is None:
            return

        # 内置切换：各用户的数据已在 _judge_multi 逐用户写回，避免重复计数
        if self._multi_ran:
            return

        if self.run_book:
            if (
                self.cur_user_config.get("Data", "ProxyTimes") == 0
                and self.cur_user_config.get("Info", "RemainedDay") != -1
            ):
                await self.cur_user_config.set(
                    "Info",
                    "RemainedDay",
                    self.cur_user_config.get("Info", "RemainedDay") - 1,
                )
            await self.cur_user_config.set(
                "Data",
                "ProxyTimes",
                self.cur_user_config.get("Data", "ProxyTimes") + 1,
            )
            await self.cur_user_config.set("Data", "LastProxyStatus", "成功")
            self.cur_user_item.status = "完成"
            logger.success(f"用户 {self.cur_user_uid} 的 ZZZ-OD 自动代理任务已完成")
        else:
            await self.cur_user_config.set("Data", "LastProxyStatus", "失败")
            if self.cur_user_item.status != "完成":
                self.cur_user_item.status = "异常"

    async def on_crash(self, e: Exception):
        self.cur_user_item.status = "异常"
        if self.cur_user_log is not None:
            self.cur_user_log.status = f"ZZZ-OD 运行异常: {e}"
        logger.opt(exception=True).warning(f"ZZZ-OD 自动代理任务出现异常: {e}")
        if self.wait_event is not None:
            self.wait_event.set()
        with suppress(Exception):
            await Config.send_websocket_message(
                id=self.task_info.task_id,
                type="Info",
                data={"Error": f"ZZZ-OD 自动代理任务出现异常: {e}"},
            )
        with suppress(Exception):
            await self.kill_managed_process()
        with suppress(Exception):
            await self._restore_injection()
        with suppress(Exception):
            await self._persist_user_run_result()

        # 推送通知（复用 Notify）
        try:
            if (
                self.cur_user_log is not None
                and self.cur_user_log.status
                and self.cur_user_log.status != "Success!"
            ):
                await Notify.push_plyer(
                    "ZZZ-OD 运行异常",
                    f"用户 {self.cur_user_item.name}：{self.cur_user_log.status}",
                    "异常",
                    3,
                )
        except Exception:
            pass

    async def kill_managed_process(self) -> None:
        """中止 ZZZ-OD 启动器进程（游戏进程由 zzz-od 自行管理）。"""

        if self.launcher_process_manager is not None:
            try:
                await self.launcher_process_manager.kill()
            except Exception as e:
                logger.opt(exception=True).warning(
                    f"通过进程管理器中止 ZZZ-OD 进程失败: {e}"
                )
        if self.launcher_exe_path is not None:
            try:
                await System.kill_process(self.launcher_exe_path)
            except Exception as e:
                logger.opt(exception=True).warning(f"中止 ZZZ-OD 主进程失败: {e}")
