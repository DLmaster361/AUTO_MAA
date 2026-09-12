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

"""BAAH 自动代理模式。

以子进程方式启动 BAAH 的指定配置并监控其日志，按成功/失败关键字判定结果，
失败时按配置重试。BAAH 自身没有心跳与看门狗，进程卡死只能靠日志静默与进程
存活共同判定。

运行前会写入本软件所需的托管配置项（运行结束自动退出、日志落盘等），
运行结束后恢复用户原值，详见 ``.tools.config_manager``。
"""

import asyncio
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.core import Config
from app.core.ws import Publisher, protocol
from app.models.config import BAAHConfig, BAAHUserConfig
from app.models.ConfigBase import MultipleConfig
from app.models.emulator import DeviceBase
from app.models.schema import WSTaskNoticeData
from app.models.task import LogRecord, ScriptItem, TaskExecuteBase
from app.services import Notify, System
from app.utils import LogMonitor, ProcessManager, compile_log_signs, get_logger
from app.utils.constants import UTC4

from .tools import (
    SOFTWARE_CONFIG_RELATIVE,
    ManagedConfigBackup,
    apply_managed_config,
    latest_log_file,
    resolve_config_dir,
    resolve_config_name,
    resolve_log_dir,
    resolve_user_config_path,
    restore_managed_config,
)

logger = get_logger("BAAH 自动代理")

## BAAH 日志行格式为「{版本} - {分:秒} - {级别} : {消息}」，例如：
##   2.4.13 - 24:19 - INFO : 执行任务EnterGame
## ⚠️ 该区间是 LogMonitor 直接对这一整行做的**字符切片**（line[start:end]），
## 不是按分隔符分词后的字段下标。版本号占 6 个字符、其后是「 - 」共 3 个字符，
## 因此时间戳「24:19」落在 [9, 14)。
## ⚠️ 若 BAAH 版本号位数变化（如 2.4.13 → 2.4.130），此区间会失配，须同步调整。
BAAH_LOG_TIME_RANGE = (9, 14)

## BAAH 只输出「分:秒」，不带日期与小时
BAAH_LOG_TIME_FORMAT = "%M:%S"

## 完成任务时 BAAH 固定输出的日志文本（只在成功路径出现）
BAAH_SUCCESS_LOG = "所有任务结束|All tasks are finished"

## 运行失败时 BAAH 顶层异常处理输出的日志文本
BAAH_ERROR_LOG = "运行出错:|Error occurred:"

## 等待日志文件生成的超时（秒）
_LOG_FILE_WAIT_SECONDS = 60

## 一次运行结束后等待相关进程退出的时间（秒）
_PROCESS_EXIT_WAIT_SECONDS = 10


class AutoProxyTask(TaskExecuteBase):
    """自动代理模式"""

    def __init__(
        self,
        script_info: ScriptItem,
        script_config: BAAHConfig,
        user_config: MultipleConfig[BAAHUserConfig],
        emulator_manager: DeviceBase | None,
    ):
        super().__init__()

        if script_info.task_info is None:
            raise RuntimeError("ScriptItem 未绑定到 TaskItem")

        self.task_info = script_info.task_info
        self.script_info = script_info
        self.script_config = script_config
        self.user_config = user_config
        self.emulator_manager = emulator_manager
        self.cur_user_item = self.script_info.user_list[self.script_info.current_index]
        self.cur_user_uid = uuid.UUID(self.cur_user_item.user_id)
        self.cur_user_config = self.user_config[self.cur_user_uid]
        self.check_result = "-"
        self.run_book = False
        self.managed_backup: ManagedConfigBackup | None = None
        self.process_manager: ProcessManager | None = None
        self.log_monitor: LogMonitor | None = None
        ## 两个总开关在 prepare() 里按脚本配置初始化，这里给出保守默认值
        self.if_manage_config = True
        self.push_log_enabled = True
        self.script_log_path: Path | None = None
        self.emulator_adb_address: str = ""

        self._resolve_paths()

    def _resolve_paths(self) -> None:
        """解析 BAAH 程序目录、配置目录与日志目录"""

        self.root_path = Path(self.script_config.get("Info", "RootPath"))
        self.config_dir = resolve_config_dir(
            self.root_path, self.script_config.get("Script", "ConfigDir")
        )
        self.log_dir = resolve_log_dir(
            self.root_path, self.script_config.get("Script", "LogDir")
        )
        self.baah_path = Path(self.script_config.get("Script", "BAAHPath"))
        self.software_config_path = self.root_path / SOFTWARE_CONFIG_RELATIVE

    async def check(self) -> str:
        """校验 BAAH 运行所需的路径与用户配置"""

        if not self.root_path.is_dir():
            self.cur_user_item.status = "异常"
            return "未找到 BAAH 程序目录, 请检查脚本配置中的程序目录设置！"

        if not self.baah_path.is_file():
            self.cur_user_item.status = "异常"
            return "未找到 BAAH 主程序, 请检查脚本配置中的主程序路径设置！"

        try:
            config_name = resolve_config_name(
                str(self.cur_user_config.get("Info", "ConfigName"))
            )
        except ValueError as e:
            self.cur_user_item.status = "异常"
            return f"{e}, 请在用户配置中填写 BAAH 配置文件名称！"

        if not resolve_user_config_path(self.config_dir, config_name).is_file():
            self.cur_user_item.status = "异常"
            return (
                f"未找到 BAAH 配置文件 {config_name}.json, "
                "请先在 BAAH 界面中创建同名配置！"
            )

        return "Pass"

    async def prepare(self):
        """运行前准备"""

        self.process_manager = ProcessManager()
        self.wait_event = asyncio.Event()
        self.log_start_time = datetime.now()
        self.log_start_at = time.monotonic()

        ## 成功与失败关键字固定：成功文本只出现在 BAAH 的成功路径，
        ## 失败文本是其顶层异常处理的输出
        self.success_log = compile_log_signs(BAAH_SUCCESS_LOG, "Split")
        self.error_log = compile_log_signs(BAAH_ERROR_LOG, "Split")

        self.log_monitor = LogMonitor(
            BAAH_LOG_TIME_RANGE,
            BAAH_LOG_TIME_FORMAT,
            self.check_log,
        )

        ## 配置托管总开关：关闭时照常启动 BAAH，但不改动它的任何配置文件
        self.if_manage_config = bool(
            self.script_config.get("Script", "IfManageConfig")
        )
        ## 日志推送开关：关闭时仍监控日志用于判定结果，但不写进任务记录与报告
        self.push_log_enabled = bool(
            self.script_config.get("Script", "PushLogEnabled")
        )

        config_name = resolve_config_name(
            str(self.cur_user_config.get("Info", "ConfigName"))
        )
        self.user_config_path = resolve_user_config_path(self.config_dir, config_name)

    async def main_task(self):
        """自动代理模式主逻辑"""

        self.check_result = await self.check()
        if self.check_result != "Pass":
            logger.warning(f"未通过配置检查: {self.check_result}")
            await Publisher.send(
                id=self.task_info.task_id,
                type=protocol.TASK_NOTICE,
                data=WSTaskNoticeData(
                    level="error",
                    message=f"用户 {self.cur_user_item.name} 检查未通过: {self.check_result}",
                ),
            )
            return

        await self.prepare()

        logger.info(f"开始代理用户: {self.cur_user_uid}")
        self.cur_user_item.status = "运行"

        for i in range(self.script_config.get("Run", "RunTimesLimit")):
            if self.run_book:
                break

            logger.info(
                f"用户 {self.cur_user_item.name} - 尝试次数: "
                f"{i + 1}/{self.script_config.get('Run', 'RunTimesLimit')}"
            )
            self.log_start_time = datetime.now()
            self.log_start_at = time.monotonic()
            self.cur_user_item.log_record[self.log_start_time] = self.cur_user_log = (
                LogRecord()
            )

            await self.run_once()

            if self.cur_user_log.status == "Success!":
                self.run_book = True
                self.cur_user_item.status = "完成"
                logger.success(f"用户: {self.cur_user_uid} - BAAH 完成代理任务")
                break

            self.cur_user_item.status = "异常"
            logger.warning(
                f"用户: {self.cur_user_uid} - 代理任务异常: {self.cur_user_log.status}"
            )
            await asyncio.sleep(3)

    async def _ensure_emulator_online(self) -> bool:
        """由本软件拉起模拟器并等待其在线。

        模拟器的启动与关闭统一由 MAS 调度，BAAH 只负责连接；冷启动耗时较长，
        在这里等它就绪，避免占用 BAAH 自身的等待窗口。
        """

        if self.emulator_manager is None:
            return True

        self.script_info.log = "正在启动模拟器"
        self.cur_user_item.status = "运行 - 启动模拟器"

        try:
            device_info = await self.emulator_manager.open(
                str(self.script_config.get("Emulator", "Index"))
            )
        except Exception as e:
            logger.opt(exception=True).warning(f"启动模拟器失败: {e}")
            await self.handle_pre_script_error("启动模拟器失败", e)
            return False

        self.emulator_adb_address = str(device_info.adb_address or "")
        logger.success(f"模拟器已就绪, ADB 地址: {self.emulator_adb_address}")
        return True

    def _emulator_runtime_values(self) -> dict[str, object]:
        """把模拟器调度结果折算成 BAAH 侧的托管项。

        BAAH 的目标设备由 ``TARGET_IP_PATH`` 与 ``TARGET_PORT`` 拼成，
        这里直接写入 MAS 解析出的地址，用户无需在 BAAH 侧维护端口。
        """

        address = self.emulator_adb_address.strip()
        host, separator, port = address.rpartition(":")
        if not separator or not host:
            return {}

        return {
            "TARGET_IP_PATH": host,
            "TARGET_PORT": int(port) if port.isdigit() else port,
        }

    async def run_once(self) -> None:
        """执行一次 BAAH 运行。

        启动模拟器、写入托管配置、启动进程、等待日志判定，
        最后无论成功失败都恢复托管配置。
        """

        self.wait_event.clear()

        if not await self._ensure_emulator_online():
            return

        if self.if_manage_config:
            try:
                self.managed_backup = apply_managed_config(
                    self.user_config_path,
                    self.software_config_path,
                    self._emulator_runtime_values(),
                )
            except Exception as e:
                logger.opt(exception=True).warning(f"写入 BAAH 托管配置失败: {e}")
                await self.handle_pre_script_error("写入 BAAH 托管配置失败", e)
                return
        else:
            ## 用户关闭了配置托管：模拟器地址等运行期取值也不再注入，
            ## BAAH 完全按它自己的配置文件运行
            logger.info("未开启「托管 BAAH 运行配置」, 跳过配置托管")

        try:
            await self._run_launched()
        finally:
            await self._restore_managed_config()

    async def _restore_managed_config(self) -> None:
        """恢复托管配置，并把恢复失败明确告知用户。

        恢复失败不能让整个任务失败（此时任务往往已经跑完），但也绝不能静默：
        用户的配置文件会一直带着本次运行写入的托管值，界面却显示一切正常。
        """

        failures = restore_managed_config(self.managed_backup)
        self.managed_backup = None

        if not failures:
            return

        message = "恢复 BAAH 配置失败, 请检查配置文件是否可写: " + "; ".join(failures)
        logger.error(message)
        await Publisher.send(
            id=self.task_info.task_id,
            type=protocol.TASK_NOTICE,
            data=WSTaskNoticeData(level="error", message=message),
        )

    async def _run_launched(self) -> None:
        """启动 BAAH 进程并等待日志给出结果"""

        if self.process_manager is None or self.log_monitor is None:
            raise RuntimeError("自动代理任务尚未完成初始化")

        config_name = self.user_config_path.name
        logger.info(f"运行 BAAH 任务: {self.baah_path}, 配置: {config_name}")

        ## 记录启动时刻：BAAH 每次运行都会新建日志文件，据此锁定本次日志
        launch_at = time.time()

        try:
            await self.process_manager.open_process(self.baah_path, config_name)
        except Exception as e:
            logger.opt(exception=True).warning(f"启动 BAAH 进程失败: {e}")
            await self.handle_pre_script_error("启动 BAAH 进程失败", e)
            return

        self.script_info.log = "正在等待 BAAH 日志文件生成"
        log_path: Path | None = None
        wait_started_at = time.monotonic()
        deadline = wait_started_at + _LOG_FILE_WAIT_SECONDS
        while time.monotonic() < deadline:
            log_path = latest_log_file(self.log_dir, launch_at)
            if log_path is not None:
                break
            ## 状态带上已等待秒数：否则界面在整个等待窗口里都是一句静止的
            ## 文案，用户无法区分「正在等」与「已经卡死」
            self.script_info.log = (
                f"正在等待 BAAH 日志文件生成（已等待 "
                f"{int(time.monotonic() - wait_started_at)} 秒）"
            )
            await asyncio.sleep(1)

        if log_path is None:
            await self.handle_pre_script_error("未找到 BAAH 日志文件")
            return

        self.script_log_path = log_path
        logger.success(f"成功定位到日志文件: {self.script_log_path}")
        ## 定位成功后立刻改写状态：日志监控要等 BAAH 写出首批日志行才会回调，
        ## 不改写的话界面会继续停在「正在等待日志文件生成」，看起来像没进展
        self.script_info.log = f"已定位 BAAH 日志文件 {log_path.name}, 正在读取日志"

        await self.log_monitor.start_monitor_file(
            self._resolve_log_file_path, self.log_start_time
        )
        await self.wait_event.wait()
        await self.log_monitor.stop()

        await self.kill_managed_process()
        await asyncio.sleep(_PROCESS_EXIT_WAIT_SECONDS)

    def _resolve_log_file_path(self) -> Path:
        """返回当前会话的日志文件路径"""

        if self.script_log_path is None:
            raise RuntimeError("尚未定位到 BAAH 日志文件")
        return self.script_log_path

    async def check_log(self, log_content: list[str], latest_time: datetime) -> None:
        """日志回调：判定本次运行的结果"""

        log = "".join(log_content)
        ## 日志内容只在开启推送时写入任务记录：结果判定始终依赖完整日志，
        ## 关闭推送只是不让它进报告
        if self.push_log_enabled:
            self.cur_user_log.content = log_content
        self.script_info.log = log

        if self.success_log.search(log) is not None:
            self.cur_user_log.status = "Success!"
        elif self.is_log_stalled(
            latest_time, minutes=self.script_config.get("Run", "RunTimeLimit")
        ):
            self.cur_user_log.status = "脚本进程超时"
        elif self.error_log.search(log) is not None:
            self.cur_user_log.status = "BAAH 运行出错"
        elif self.process_manager is not None and await self.process_manager.is_running():
            self.cur_user_log.status = "BAAH 正常运行中"
        else:
            ## 进程已退出但未命中成功标记：不能确认任务完成
            self.cur_user_log.status = "BAAH 在完成任务前退出"

        logger.debug(f"BAAH 日志分析结果: {self.cur_user_log.status}")
        if self.cur_user_log.status != "BAAH 正常运行中":
            logger.info(f"BAAH 任务结果: {self.cur_user_log.status}, 日志锁已释放")
            self.wait_event.set()

    async def kill_managed_process(self) -> None:
        """中止本次运行托管的进程"""

        if self.process_manager is None:
            return

        try:
            logger.info(f"中止 BAAH 进程: {self.baah_path}")
            await self.process_manager.kill()
            await System.kill_process(self.baah_path)
        except Exception as e:
            logger.opt(exception=True).warning(f"中止 BAAH 进程失败: {e}")

    async def handle_pre_script_error(
        self, error_message: str, e: Exception | None = None
    ) -> None:
        """处理运行前的准备阶段错误"""

        if e is None:
            logger.warning(f"用户: {self.cur_user_uid} - {error_message}")
            await Publisher.send(
                id=self.task_info.task_id,
                type=protocol.TASK_NOTICE,
                data=WSTaskNoticeData(level="error", message=error_message),
            )
        else:
            logger.opt(exception=True).warning(
                f"用户: {self.cur_user_uid} - {error_message}: {e}"
            )
            await Publisher.send(
                id=self.task_info.task_id,
                type=protocol.TASK_NOTICE,
                data=WSTaskNoticeData(level="error", message=f"{error_message}: {e}"),
            )

        self.cur_user_log.content = [f"{error_message}, 无日志记录"]
        self.cur_user_log.status = error_message

        await self.kill_managed_process()

        await Notify.push_plyer(
            "用户自动代理出现异常！",
            f"用户 {self.cur_user_item.name} 自动代理时{error_message}",
            f"{self.cur_user_item.name}的自动代理出现异常",
            3,
        )

    async def final_task(self):
        """运行结束后的收尾工作"""

        if self.check_result != "Pass":
            self.cur_user_item.status = "异常"
            return

        if self.log_monitor is not None:
            await self.log_monitor.stop()

        await self.kill_managed_process()

        await self._restore_managed_config()

        for t, log_item in self.cur_user_item.log_record.items():
            log_path = Config.build_history_log_path(
                script_name=self.script_info.name,
                user_name=self.cur_user_item.name,
                log_time=t.astimezone(UTC4),
            )

            if log_item.status == "BAAH 正常运行中":
                log_item.status = "任务被用户手动中止"

            if len(log_item.content) == 0:
                if self.push_log_enabled:
                    log_item.content = ["未捕获到任何日志内容"]
                    log_item.status = "未捕获到日志"
                else:
                    ## 用户主动关闭推送与「没采集到」不是一回事，不能据此改判状态
                    log_item.content = ["未开启日志推送, 本次未保留日志内容"]

            await Config.save_general_log(log_path, log_item.content, log_item.status)

    async def on_crash(self, e: Exception):
        """任务异常时的清理"""

        self.cur_user_item.status = "异常"
        logger.opt(exception=True).warning(f"BAAH 任务出现异常: {e}")

        try:
            if self.log_monitor is not None:
                await self.log_monitor.stop()
        except Exception as stop_error:
            logger.opt(exception=True).warning(f"停止日志监控失败: {stop_error}")

        try:
            await self.kill_managed_process()
        except Exception as kill_error:
            logger.opt(exception=True).warning(f"清理 BAAH 进程失败: {kill_error}")

        try:
            await self._restore_managed_config()
        except Exception as restore_error:
            logger.opt(exception=True).warning(
                f"恢复 BAAH 托管配置失败: {restore_error}"
            )

        await Publisher.send(
            id=self.task_info.task_id,
            type=protocol.TASK_NOTICE,
            data=WSTaskNoticeData(level="error", message=f"BAAH 任务出现异常: {e}"),
        )
