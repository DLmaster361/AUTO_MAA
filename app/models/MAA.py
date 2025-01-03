#   <AUTO_MAA:A MAA Multi Account Management and Automation Tool>
#   Copyright © <2024> <DLmaster361>

#   This file is part of AUTO_MAA.

#   AUTO_MAA is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published
#   by the Free Software Foundation, either version 3 of the License,
#   or (at your option) any later version.

#   AUTO_MAA is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty
#   of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
#   the GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with AUTO_MAA. If not, see <https://www.gnu.org/licenses/>.

#   DLmaster_361@163.com

"""
AUTO_MAA
MAA功能组件
v4.2
作者：DLmaster_361
"""

from PySide6 import QtCore
import json
import datetime
import os
import subprocess
import shutil
import time
from pathlib import Path

from app import AppConfig


class MaaManager(QtCore.QThread):
    """MAA控制器"""

    question = QtCore.Signal()
    push_notification = QtCore.Signal(str, str, str, int)
    send_mail = QtCore.Signal(str, str)
    update_gui = QtCore.Signal(str, str, str, str, str)
    update_user_info = QtCore.Signal(list, list, list, list, list, list)
    set_silence = QtCore.Signal(str, str, list)
    accomplish = QtCore.Signal()
    get_json = QtCore.Signal(list)

    def __init__(self, config: AppConfig):
        super(MaaManager, self).__init__()

        self.config = config
        self.mode = None
        self.data = None
        self.get_json_path = [0, 0, 0]

    def configure(self):
        """提取配置信息"""

        self.maa_root_path = Path(self.config.content["Default"]["MaaSet.path"])
        self.set_path = self.maa_root_path / "config/gui.json"
        self.log_path = self.maa_root_path / "debug/gui.log"
        self.maa_path = self.maa_root_path / "MAA.exe"
        self.json_path = self.config.app_path / "data/MAAconfig"
        self.routine = self.config.content["Default"]["TimeLimit.routine"]
        self.annihilation = self.config.content["Default"]["TimeLimit.annihilation"]
        self.num = self.config.content["Default"]["TimesLimit.run"]
        self.boss_key = [
            _.strip().lower()
            for _ in self.config.content["Default"]["SelfSet.BossKey"].split("+")
        ]
        self.if_send_mail = bool(
            self.config.content["Default"]["SelfSet.IfSendMail"] == "True"
        )
        self.if_send_error_only = bool(
            self.config.content["Default"]["SelfSet.IfSendMail.OnlyError"] == "True"
        )
        self.if_silence = bool(
            self.config.content["Default"]["SelfSet.IfSilence"] == "True"
        )

    def run(self):
        """主进程，运行MAA代理进程"""

        curdate = self.server_date()
        begin_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.configure()

        # 整理用户数据，筛选需代理的用户
        self.data = sorted(self.data, key=lambda x: (-len(x[15]), x[16]))
        wait_index = []
        over_index = []
        error_index = []
        all_index = [
            _
            for _ in range(len(self.data))
            if (self.data[_][3] != 0 and self.data[_][4] == "y")
        ]

        # 日常代理模式
        if self.mode == "日常代理":

            # 执行情况预处理
            for _ in all_index:
                if self.data[_][5] != curdate:
                    self.data[_][5] = curdate
                    self.data[_][14] = 0
                self.data[_][0] += f"_第{str(self.data[_][14] + 1)}次代理"

            # 开始代理
            for index in all_index:

                if self.isInterruptionRequested():
                    break

                # 初始化代理情况记录和模式替换记录
                run_book = [False for _ in range(2)]
                mode_book = ["日常代理_剿灭", "日常代理_日常"]

                # 简洁模式用户默认开启日常代理
                if self.data[index][15] == "simple":
                    self.data[index][9] = "y"

                # 尝试次数循环
                for i in range(self.num):

                    if self.isInterruptionRequested():
                        break

                    # 剿灭-日常模式循环
                    for j in range(2):

                        if self.isInterruptionRequested():
                            break

                        if self.data[index][10 - j] == "n":
                            run_book[j] = True
                            continue
                        if run_book[j]:
                            continue

                        # 配置MAA
                        self.set_maa(mode_book[j], index)
                        # 记录当前时间
                        start_time = datetime.datetime.now()
                        # 创建MAA任务
                        maa = subprocess.Popen(
                            [self.maa_path],
                            shell=True,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
                        # 启动静默进程
                        if self.if_silence:
                            self.set_silence.emit(
                                "启用", self.get_emulator_path(), self.boss_key
                            )
                        # 记录是否超时的标记
                        self.if_time_out = False
                        # 更新运行信息
                        wait_index = [
                            _
                            for _ in all_index
                            if (not _ in over_index + error_index + [index])
                        ]

                        # 监测MAA运行状态
                        while not self.isInterruptionRequested():

                            # 获取MAA日志
                            logs = self.get_maa_log(start_time)

                            # 判断是否超时
                            if len(logs) > 0:
                                latest_time = datetime.datetime.now()
                                for _ in range(-1, 0 - len(logs) - 1, -1):
                                    try:
                                        latest_time = datetime.datetime.strptime(
                                            logs[_][1:20], "%Y-%m-%d %H:%M:%S"
                                        )
                                        break
                                    except ValueError:
                                        pass
                                now_time = datetime.datetime.now()
                                if (
                                    j == 0
                                    and now_time - latest_time
                                    > datetime.timedelta(minutes=self.annihilation)
                                ) or (
                                    j == 1
                                    and now_time - latest_time
                                    > datetime.timedelta(minutes=self.routine)
                                ):
                                    self.if_time_out = True

                            # 合并日志
                            log = "".join(logs)

                            # 更新MAA日志
                            if len(logs) > 100:
                                self.update_gui.emit(
                                    f"{self.data[index][0]}_第{i + 1}次_{mode_book[j][5:7]}",
                                    "\n".join([self.data[_][0] for _ in wait_index]),
                                    "\n".join([self.data[_][0] for _ in over_index]),
                                    "\n".join([self.data[_][0] for _ in error_index]),
                                    "".join(logs[-100:]),
                                )
                            else:
                                self.update_gui.emit(
                                    f"{self.data[index][0]}_第{i + 1}次_{mode_book[j][5:7]}",
                                    "\n".join([self.data[_][0] for _ in wait_index]),
                                    "\n".join([self.data[_][0] for _ in over_index]),
                                    "\n".join([self.data[_][0] for _ in error_index]),
                                    "".join(logs),
                                )

                            # 判断MAA程序运行状态
                            result = self.if_maa_success(log, mode_book[j])
                            if result == "Success!":
                                run_book[j] = True
                                self.update_gui.emit(
                                    f"{self.data[index][0]}_第{i + 1}次_{mode_book[j][5:7]}",
                                    "\n".join([self.data[_][0] for _ in wait_index]),
                                    "\n".join([self.data[_][0] for _ in over_index]),
                                    "\n".join([self.data[_][0] for _ in error_index]),
                                    "检测到MAA进程完成代理任务\n正在等待相关程序结束\n请等待10s",
                                )
                                # 关闭静默进程
                                if self.if_silence:
                                    self.set_silence.emit("禁用", "", [])
                                for _ in range(10):
                                    if self.isInterruptionRequested():
                                        break
                                    time.sleep(1)
                                break
                            elif result == "Wait":
                                # 检测时间间隔
                                time.sleep(1)
                            else:
                                # 打印中止信息
                                # 此时，log变量内存储的就是出现异常的日志信息，可以保存或发送用于问题排查
                                self.update_gui.emit(
                                    f"{self.data[index][0]}_第{i + 1}次_{mode_book[j][5:7]}",
                                    "\n".join([self.data[_][0] for _ in wait_index]),
                                    "\n".join([self.data[_][0] for _ in over_index]),
                                    "\n".join([self.data[_][0] for _ in error_index]),
                                    result,
                                )
                                # 无命令行中止MAA与其子程序
                                killprocess = subprocess.Popen(
                                    f"taskkill /F /T /PID {maa.pid}",
                                    shell=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW,
                                )
                                killprocess.wait()
                                # 关闭静默进程
                                if self.if_silence:
                                    self.set_silence.emit("禁用", "", [])
                                # 推送异常通知
                                self.push_notification.emit(
                                    "用户日常代理出现异常！",
                                    f"用户 {self.data[index][0].replace("_", " 今天的")}的{mode_book[j][5:7]}部分出现一次异常",
                                    f"{self.data[index][0].replace("_", " ")}的{mode_book[j][5:7]}出现异常",
                                    1,
                                )
                                for _ in range(10):
                                    if self.isInterruptionRequested():
                                        break
                                    time.sleep(1)
                                break

                    # 成功完成代理的用户修改相关参数
                    if run_book[0] and run_book[1]:
                        if self.data[index][14] == 0 and self.data[index][3] != -1:
                            self.data[index][3] -= 1
                        self.data[index][14] += 1
                        over_index.append(index)
                        self.push_notification.emit(
                            "成功完成一个日常代理任务！",
                            f"已完成用户 {self.data[index][0].replace("_", " 今天的")}任务",
                            f"已完成 {self.data[index][0].replace("_", " 的")}",
                            3,
                        )
                        break

                # 录入代理失败的用户
                if not (run_book[0] and run_book[1]):
                    error_index.append(index)

        # 人工排查模式
        elif self.mode == "人工排查":

            # 标记是否需要启动模拟器
            if_strat_app = True
            # 标识排查模式
            for _ in all_index:
                self.data[_][0] += "_排查模式"

            # 开始排查
            for index in all_index:

                if self.isInterruptionRequested():
                    break

                if self.data[index][15] == "beta":
                    if_strat_app = True

                run_book = [False for _ in range(2)]

                # 启动重试循环
                while not self.isInterruptionRequested():

                    # 配置MAA
                    if if_strat_app:
                        self.set_maa("人工排查_启动模拟器", index)
                        if_strat_app = False
                    else:
                        self.set_maa("人工排查_仅切换账号", index)

                    # 记录当前时间
                    start_time = datetime.datetime.now()
                    # 创建MAA任务
                    maa = subprocess.Popen(
                        [self.maa_path],
                        shell=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    # 更新运行信息
                    wait_index = [
                        _
                        for _ in all_index
                        if (not _ in over_index + error_index + [index])
                    ]

                    # 监测MAA运行状态
                    while not self.isInterruptionRequested():

                        # 获取MAA日志
                        logs = self.get_maa_log(start_time)
                        # 合并日志
                        log = "".join(logs)

                        # 更新MAA日志
                        if len(logs) > 100:
                            self.update_gui.emit(
                                self.data[index][0],
                                "\n".join([self.data[_][0] for _ in wait_index]),
                                "\n".join([self.data[_][0] for _ in over_index]),
                                "\n".join([self.data[_][0] for _ in error_index]),
                                "".join(logs[-100:]),
                            )
                        else:
                            self.update_gui.emit(
                                self.data[index][0],
                                "\n".join([self.data[_][0] for _ in wait_index]),
                                "\n".join([self.data[_][0] for _ in over_index]),
                                "\n".join([self.data[_][0] for _ in error_index]),
                                "".join(logs),
                            )

                        # 判断MAA程序运行状态
                        result = self.if_maa_success(log, "人工排查")
                        if result == "Success!":
                            run_book[0] = True
                            self.update_gui.emit(
                                self.data[index][0],
                                "\n".join([self.data[_][0] for _ in wait_index]),
                                "\n".join([self.data[_][0] for _ in over_index]),
                                "\n".join([self.data[_][0] for _ in error_index]),
                                "检测到MAA进程成功登录PRTS",
                            )
                            break
                        elif result == "Wait":
                            # 检测时间间隔
                            time.sleep(1)
                        else:
                            self.update_gui.emit(
                                self.data[index][0],
                                "\n".join([self.data[_][0] for _ in wait_index]),
                                "\n".join([self.data[_][0] for _ in over_index]),
                                "\n".join([self.data[_][0] for _ in error_index]),
                                result,
                            )
                            # 无命令行中止MAA与其子程序
                            killprocess = subprocess.Popen(
                                f"taskkill /F /T /PID {maa.pid}",
                                shell=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                            killprocess.wait()
                            if_strat_app = True
                            for _ in range(10):
                                if self.isInterruptionRequested():
                                    break
                                time.sleep(1)
                            break

                    # 登录成功，结束循环
                    if run_book[0]:
                        break
                    # 登录失败，询问是否结束循环
                    elif not self.isInterruptionRequested():
                        self.question_title = "操作提示"
                        self.question_info = "MAA未能正确登录到PRTS，是否重试？"
                        self.question_choice = "wait"
                        self.question.emit()
                        while self.question_choice == "wait":
                            time.sleep(1)
                        if self.question_choice == "No":
                            break

                # 登录成功，录入人工排查情况
                if run_book[0] and not self.isInterruptionRequested():
                    self.question_title = "操作提示"
                    self.question_info = "请检查用户代理情况，如无异常请按下确认键。"
                    self.question_choice = "wait"
                    self.question.emit()
                    while self.question_choice == "wait":
                        time.sleep(1)
                    if self.question_choice == "Yes":
                        run_book[1] = True

                # 结果录入用户备注栏
                if run_book[0] and run_book[1]:
                    if "未通过人工排查" in self.data[index][13]:
                        self.data[index][13] = self.data[index][13].replace(
                            "未通过人工排查|", ""
                        )
                    over_index.append(index)
                elif not (run_book[0] and run_book[1]):
                    if not "未通过人工排查" in self.data[index][13]:
                        self.data[index][13] = f"未通过人工排查|{self.data[index][13]}"
                    error_index.append(index)

        # 设置MAA模式
        elif "设置MAA" in self.mode:

            # 配置MAA
            self.set_maa(self.mode, "")
            # 创建MAA任务
            maa = subprocess.Popen(
                [self.maa_path],
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            # 记录当前时间
            start_time = datetime.datetime.now()

            # 监测MAA运行状态
            while not self.isInterruptionRequested():

                # 获取MAA日志
                logs = self.get_maa_log(start_time)
                # 合并日志
                log = "".join(logs)

                # 判断MAA程序运行状态
                result = self.if_maa_success(log, "设置MAA")
                if result == "Success!":
                    break
                elif result == "Wait":
                    # 检测时间间隔
                    time.sleep(1)

            # 保存MAA配置文件
            if "全局" in self.mode:
                self.get_json.emit(["Default"])
            elif "用户" in self.mode:
                self.get_json.emit(self.get_json_path)

            self.accomplish.emit()

        # 导出结果
        if self.mode in ["日常代理", "人工排查"]:

            # 关闭可能未正常退出的MAA进程
            if self.isInterruptionRequested():
                killprocess = subprocess.Popen(
                    f"taskkill /F /T /PID {maa.pid}",
                    shell=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                killprocess.wait()

            # 更新用户数据
            modes = [self.data[_][15] for _ in all_index]
            uids = [self.data[_][16] for _ in all_index]
            days = [self.data[_][3] for _ in all_index]
            lasts = [self.data[_][5] for _ in all_index]
            notes = [self.data[_][13] for _ in all_index]
            numbs = [self.data[_][14] for _ in all_index]
            self.update_user_info.emit(modes, uids, days, lasts, notes, numbs)

            # 保存运行日志
            end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            end_log = (
                f"任务开始时间：{begin_time}，结束时间：{end_time}\n"
                f"已完成数：{len(over_index)}，未完成数：{len(error_index) + len(wait_index)}\n\n"
            )

            if len(error_index) != 0:
                end_log += (
                    f"{self.mode[2:4]}未成功的用户：\n"
                    f"{"\n".join([self.data[_][0] for _ in error_index])}\n"
                )
            wait_index = [_ for _ in all_index if (not _ in over_index + error_index)]
            if len(wait_index) != 0:
                end_log += (
                    f"\n未开始{self.mode[2:4]}的用户：\n"
                    f"{"\n".join([self.data[_][0] for _ in wait_index])}\n"
                )

            (self.config.app_path / "log.txt").write_text(
                end_log,
                encoding="utf-8",
            )

            # 恢复GUI运行面板
            self.update_gui.emit("", "", "", "", end_log)

            # 推送代理结果通知
            self.push_notification.emit(
                f"{self.mode[2:4]}任务已完成！",
                f"已完成用户数：{len(over_index)}，未完成用户数：{len(error_index) + len(wait_index)}",
                f"已完成用户数：{len(over_index)}，未完成用户数：{len(error_index) + len(wait_index)}",
                10,
            )
            if self.if_send_mail and (
                not self.if_send_error_only
                or (self.if_send_error_only and len(error_index) + len(wait_index) != 0)
            ):
                self.send_mail.emit(
                    f"{self.mode[:4]}任务报告",
                    f"{end_log}\n\nAUTO_MAA 敬上\n\n我们根据您在 AUTO_MAA 中的设置发送了这封电子邮件，本邮件无需回复\n",
                )

            if not self.isInterruptionRequested():
                self.accomplish.emit()

    def get_maa_log(self, start_time):
        """获取MAA日志"""

        logs = []
        if_log_start = False
        with self.log_path.open(mode="r", encoding="utf-8") as f:
            for entry in f:
                if not if_log_start:
                    try:
                        entry_time = datetime.datetime.strptime(
                            entry[1:20], "%Y-%m-%d %H:%M:%S"
                        )
                        if entry_time > start_time:
                            if_log_start = True
                            logs.append(entry)
                    except ValueError:
                        pass
                else:
                    logs.append(entry)
        return logs

    def if_maa_success(self, log, mode):
        """判断MAA程序运行状态"""

        if "日常代理" in mode:
            if mode == "日常代理_日常" and "任务出错: Fight" in log:
                return "检测到MAA未能实际执行任务\n正在中止相关程序\n请等待10s"
            if "任务出错: StartUp" in log:
                return "检测到MAA未能正确登录PRTS\n正在中止相关程序\n请等待10s"
            elif "任务已全部完成！" in log:
                return "Success!"
            elif (
                ("请「检查连接设置」或「尝试重启模拟器与 ADB」或「重启电脑」" in log)
                or ("已停止" in log)
                or ("MaaAssistantArknights GUI exited" in log)
            ):
                return "检测到MAA进程异常\n正在中止相关程序\n请等待10s"
            elif self.if_time_out:
                return "检测到MAA进程超时\n正在中止相关程序\n请等待10s"
            elif self.isInterruptionRequested():
                return "您中止了本次任务\n正在中止相关程序\n请等待"
            else:
                return "Wait"

        elif mode == "人工排查":
            if "完成任务: StartUp" in log:
                return "Success!"
            elif (
                ("请「检查连接设置」或「尝试重启模拟器与 ADB」或「重启电脑」" in log)
                or ("已停止" in log)
                or ("MaaAssistantArknights GUI exited" in log)
            ):
                return "检测到MAA进程异常\n正在中止相关程序\n请等待10s"
            elif self.isInterruptionRequested():
                return "您中止了本次任务\n正在中止相关程序\n请等待"
            else:
                return "Wait"

        elif mode == "设置MAA":
            if "MaaAssistantArknights GUI exited" in log:
                return "Success!"
            else:
                return "Wait"

    def set_maa(self, mode, index):
        """配置MAA运行参数"""

        # 预导入MAA配置文件
        if mode == "设置MAA_用户":
            set_book = ["simple", "beta"]
            if (
                self.json_path
                / f"{set_book[self.get_json_path[0]]}/{self.get_json_path[1]}/{self.get_json_path[2]}/gui.json"
            ).exists():
                shutil.copy(
                    self.json_path
                    / f"{set_book[self.get_json_path[0]]}/{self.get_json_path[1]}/{self.get_json_path[2]}/gui.json",
                    self.set_path,
                )
            else:
                shutil.copy(
                    self.json_path / "Default/gui.json",
                    self.set_path,
                )
        elif (mode == "设置MAA_全局") or (
            ("日常代理" in mode or "人工排查" in mode)
            and self.data[index][15] == "simple"
        ):
            shutil.copy(
                self.json_path / "Default/gui.json",
                self.set_path,
            )
        elif "日常代理" in mode and self.data[index][15] == "beta":
            if mode == "日常代理_剿灭":
                shutil.copy(
                    self.json_path
                    / f"beta/{self.data[index][16]}/annihilation/gui.json",
                    self.set_path,
                )
            elif mode == "日常代理_日常":
                shutil.copy(
                    self.json_path / f"beta/{self.data[index][16]}/routine/gui.json",
                    self.set_path,
                )
        elif "人工排查" in mode and self.data[index][15] == "beta":
            shutil.copy(
                self.json_path / f"beta/{self.data[index][16]}/routine/gui.json",
                self.set_path,
            )
        with self.set_path.open(mode="r", encoding="utf-8") as f:
            data = json.load(f)

        # 日常代理配置
        if "日常代理" in mode:

            data["Current"] = "Default"  # 切换配置
            for i in range(1, 9):
                data["Global"][f"Timer.Timer{i}"] = "False"  # 时间设置
            data["Configurations"]["Default"][
                "MainFunction.PostActions"
            ] = "12"  # 完成后退出MAA和模拟器
            data["Global"]["Start.RunDirectly"] = "True"  # 启动MAA后直接运行
            data["Global"][
                "Start.OpenEmulatorAfterLaunch"
            ] = "True"  # 启动MAA后自动开启模拟器

            if self.if_silence:
                data["Global"]["Start.MinimizeDirectly"] = "True"  # 启动MAA后直接最小化
                data["Global"]["GUI.UseTray"] = "True"  # 显示托盘图标
                data["Global"]["GUI.MinimizeToTray"] = "True"  # 最小化时隐藏至托盘

            if self.data[index][15] == "simple":

                data["Global"][
                    "VersionUpdate.ScheduledUpdateCheck"
                ] = "True"  # 定时检查更新
                data["Global"][
                    "VersionUpdate.AutoDownloadUpdatePackage"
                ] = "True"  # 自动下载更新包
                data["Global"][
                    "VersionUpdate.AutoInstallUpdatePackage"
                ] = "True"  # 自动安装更新包
                data["Configurations"]["Default"]["Start.ClientType"] = self.data[
                    index
                ][
                    2
                ]  # 客户端类型
                # 账号切换
                if self.data[index][2] == "Official":
                    data["Configurations"]["Default"][
                        "Start.AccountName"
                    ] = f"{self.data[index][1][:3]}****{self.data[index][1][7:]}"
                elif self.data[index][2] == "Bilibili":
                    data["Configurations"]["Default"]["Start.AccountName"] = self.data[
                        index
                    ][1]

                if "剿灭" in mode:

                    data["Configurations"]["Default"][
                        "TaskQueue.WakeUp.IsChecked"
                    ] = "True"  # 开始唤醒
                    data["Configurations"]["Default"][
                        "TaskQueue.Recruiting.IsChecked"
                    ] = "False"  # 自动公招
                    data["Configurations"]["Default"][
                        "TaskQueue.Base.IsChecked"
                    ] = "False"  # 基建换班
                    data["Configurations"]["Default"][
                        "TaskQueue.Combat.IsChecked"
                    ] = "True"  # 刷理智
                    data["Configurations"]["Default"][
                        "TaskQueue.Mission.IsChecked"
                    ] = "False"  # 领取奖励
                    data["Configurations"]["Default"][
                        "TaskQueue.Mall.IsChecked"
                    ] = "False"  # 获取信用及购物
                    data["Configurations"]["Default"][
                        "TaskQueue.AutoRoguelike.IsChecked"
                    ] = "False"  # 自动肉鸽
                    data["Configurations"]["Default"][
                        "TaskQueue.Reclamation.IsChecked"
                    ] = "False"  # 生息演算
                    data["Configurations"]["Default"][
                        "MainFunction.Stage1"
                    ] = "Annihilation"  # 主关卡
                    data["Configurations"]["Default"][
                        "MainFunction.Stage2"
                    ] = ""  # 备选关卡1
                    data["Configurations"]["Default"][
                        "MainFunction.Stage3"
                    ] = ""  # 备选关卡2
                    data["Configurations"]["Default"][
                        "Fight.RemainingSanityStage"
                    ] = ""  # 剩余理智关卡
                    data["Configurations"]["Default"][
                        "MainFunction.Series.Quantity"
                    ] = "1"  # 连战次数
                    data["Configurations"]["Default"][
                        "Penguin.IsDrGrandet"
                    ] = "False"  # 博朗台模式
                    data["Configurations"]["Default"][
                        "GUI.CustomStageCode"
                    ] = "True"  # 手动输入关卡名
                    data["Configurations"]["Default"][
                        "GUI.UseAlternateStage"
                    ] = "False"  # 使用备选关卡
                    data["Configurations"]["Default"][
                        "Fight.UseRemainingSanityStage"
                    ] = "False"  # 使用剩余理智
                    data["Configurations"]["Default"][
                        "Fight.UseExpiringMedicine"
                    ] = "True"  # 无限吃48小时内过期的理智药
                    data["Configurations"]["Default"][
                        "GUI.HideSeries"
                    ] = "False"  # 隐藏连战次数

                elif "日常" in mode:

                    data["Configurations"]["Default"][
                        "TaskQueue.WakeUp.IsChecked"
                    ] = "True"  # 开始唤醒
                    data["Configurations"]["Default"][
                        "TaskQueue.Recruiting.IsChecked"
                    ] = "True"  # 自动公招
                    data["Configurations"]["Default"][
                        "TaskQueue.Base.IsChecked"
                    ] = "True"  # 基建换班
                    data["Configurations"]["Default"][
                        "TaskQueue.Combat.IsChecked"
                    ] = "True"  # 刷理智
                    data["Configurations"]["Default"][
                        "TaskQueue.Mission.IsChecked"
                    ] = "True"  # 领取奖励
                    data["Configurations"]["Default"][
                        "TaskQueue.Mall.IsChecked"
                    ] = "True"  # 获取信用及购物
                    data["Configurations"]["Default"][
                        "TaskQueue.AutoRoguelike.IsChecked"
                    ] = "False"  # 自动肉鸽
                    data["Configurations"]["Default"][
                        "TaskQueue.Reclamation.IsChecked"
                    ] = "False"  # 生息演算
                    # 主关卡
                    if self.data[index][6] == "-":
                        data["Configurations"]["Default"]["MainFunction.Stage1"] = ""
                    else:
                        data["Configurations"]["Default"]["MainFunction.Stage1"] = (
                            self.data[index][6]
                        )
                    # 备选关卡1
                    if self.data[index][7] == "-":
                        data["Configurations"]["Default"]["MainFunction.Stage2"] = ""
                    else:
                        data["Configurations"]["Default"]["MainFunction.Stage2"] = (
                            self.data[index][7]
                        )
                    # 备选关卡2
                    if self.data[index][8] == "-":
                        data["Configurations"]["Default"]["MainFunction.Stage3"] = ""
                    else:
                        data["Configurations"]["Default"]["MainFunction.Stage3"] = (
                            self.data[index][8]
                        )
                    data["Configurations"]["Default"][
                        "Fight.RemainingSanityStage"
                    ] = ""  # 剩余理智关卡
                    # 连战次数
                    if self.data[index][6] == "1-7":
                        data["Configurations"]["Default"][
                            "MainFunction.Series.Quantity"
                        ] = "6"
                    else:
                        data["Configurations"]["Default"][
                            "MainFunction.Series.Quantity"
                        ] = "1"
                    data["Configurations"]["Default"][
                        "Penguin.IsDrGrandet"
                    ] = "False"  # 博朗台模式
                    data["Configurations"]["Default"][
                        "GUI.CustomStageCode"
                    ] = "True"  # 手动输入关卡名
                    # 备选关卡
                    if self.data[index][7] == "-" and self.data[index][8] == "-":
                        data["Configurations"]["Default"][
                            "GUI.UseAlternateStage"
                        ] = "False"
                    else:
                        data["Configurations"]["Default"][
                            "GUI.UseAlternateStage"
                        ] = "True"
                    data["Configurations"]["Default"][
                        "Fight.UseRemainingSanityStage"
                    ] = "False"  # 使用剩余理智
                    data["Configurations"]["Default"][
                        "Fight.UseExpiringMedicine"
                    ] = "True"  # 无限吃48小时内过期的理智药
                    # 自定义基建配置
                    if self.data[index][11] == "n":
                        data["Configurations"]["Default"][
                            "Infrast.CustomInfrastEnabled"
                        ] = "False"  # 禁用自定义基建配置
                    else:
                        data["Configurations"]["Default"][
                            "Infrast.CustomInfrastEnabled"
                        ] = "True"  # 启用自定义基建配置
                        data["Configurations"]["Default"][
                            "Infrast.CustomInfrastPlanIndex"
                        ] = "1"  # 自定义基建配置索引
                        data["Configurations"]["Default"][
                            "Infrast.DefaultInfrast"
                        ] = "user_defined"  # 内置配置
                        data["Configurations"]["Default"][
                            "Infrast.IsCustomInfrastFileReadOnly"
                        ] = "False"  # 自定义基建配置文件只读
                        data["Configurations"]["Default"][
                            "Infrast.CustomInfrastFile"
                        ] = f"{self.json_path}/simple/{self.data[index][16]}/infrastructure/infrastructure.json"  # 自定义基建配置文件地址

        # 人工排查配置
        elif "人工排查" in mode:

            data["Current"] = "Default"  # 切换配置
            for i in range(1, 9):
                data["Global"][f"Timer.Timer{i}"] = "False"  # 时间设置
            data["Configurations"]["Default"][
                "MainFunction.PostActions"
            ] = "8"  # 完成后退出MAA
            data["Global"]["Start.RunDirectly"] = "True"  # 启动MAA后直接运行
            data["Global"]["Start.MinimizeDirectly"] = "True"  # 启动MAA后直接最小化
            data["Global"]["GUI.UseTray"] = "True"  # 显示托盘图标
            data["Global"]["GUI.MinimizeToTray"] = "True"  # 最小化时隐藏至托盘
            # 启动MAA后自动开启模拟器
            if "启动模拟器" in mode:
                data["Global"]["Start.OpenEmulatorAfterLaunch"] = "True"
            elif "仅切换账号" in mode:
                data["Global"]["Start.OpenEmulatorAfterLaunch"] = "False"

            if self.data[index][15] == "simple":

                data["Global"][
                    "VersionUpdate.ScheduledUpdateCheck"
                ] = "False"  # 定时检查更新
                data["Global"][
                    "VersionUpdate.AutoDownloadUpdatePackage"
                ] = "False"  # 自动下载更新包
                data["Global"][
                    "VersionUpdate.AutoInstallUpdatePackage"
                ] = "False"  # 自动安装更新包
                data["Configurations"]["Default"]["Start.ClientType"] = self.data[
                    index
                ][
                    2
                ]  # 客户端类型
                # 账号切换
                if self.data[index][2] == "Official":
                    data["Configurations"]["Default"][
                        "Start.AccountName"
                    ] = f"{self.data[index][1][:3]}****{self.data[index][1][7:]}"
                elif self.data[index][2] == "Bilibili":
                    data["Configurations"]["Default"]["Start.AccountName"] = self.data[
                        index
                    ][1]

            data["Configurations"]["Default"][
                "TaskQueue.WakeUp.IsChecked"
            ] = "True"  # 开始唤醒
            data["Configurations"]["Default"][
                "TaskQueue.Recruiting.IsChecked"
            ] = "False"  # 自动公招
            data["Configurations"]["Default"][
                "TaskQueue.Base.IsChecked"
            ] = "False"  # 基建换班
            data["Configurations"]["Default"][
                "TaskQueue.Combat.IsChecked"
            ] = "False"  # 刷理智
            data["Configurations"]["Default"][
                "TaskQueue.Mission.IsChecked"
            ] = "False"  # 领取奖励
            data["Configurations"]["Default"][
                "TaskQueue.Mall.IsChecked"
            ] = "False"  # 获取信用及购物
            data["Configurations"]["Default"][
                "TaskQueue.AutoRoguelike.IsChecked"
            ] = "False"  # 自动肉鸽
            data["Configurations"]["Default"][
                "TaskQueue.Reclamation.IsChecked"
            ] = "False"  # 生息演算

        # 设置MAA配置
        elif "设置MAA" in mode:

            data["Current"] = "Default"  # 切换配置
            for i in range(1, 9):
                data["Global"][f"Timer.Timer{i}"] = "False"  # 时间设置
            data["Configurations"]["Default"][
                "MainFunction.PostActions"
            ] = "0"  # 完成后无动作
            data["Global"]["Start.RunDirectly"] = "False"  # 启动MAA后直接运行
            data["Global"][
                "Start.OpenEmulatorAfterLaunch"
            ] = "False"  # 启动MAA后自动开启模拟器

            if self.if_silence:
                data["Global"][
                    "Start.MinimizeDirectly"
                ] = "False"  # 启动MAA后直接最小化

            if "全局" in mode:

                data["Global"][
                    "VersionUpdate.ScheduledUpdateCheck"
                ] = "False"  # 定时检查更新
                data["Global"][
                    "VersionUpdate.AutoDownloadUpdatePackage"
                ] = "False"  # 自动下载更新包
                data["Global"][
                    "VersionUpdate.AutoInstallUpdatePackage"
                ] = "False"  # 自动安装更新包
                data["Configurations"]["Default"][
                    "TaskQueue.WakeUp.IsChecked"
                ] = "False"  # 开始唤醒
                data["Configurations"]["Default"][
                    "TaskQueue.Recruiting.IsChecked"
                ] = "False"  # 自动公招
                data["Configurations"]["Default"][
                    "TaskQueue.Base.IsChecked"
                ] = "False"  # 基建换班
                data["Configurations"]["Default"][
                    "TaskQueue.Combat.IsChecked"
                ] = "False"  # 刷理智
                data["Configurations"]["Default"][
                    "TaskQueue.Mission.IsChecked"
                ] = "False"  # 领取奖励
                data["Configurations"]["Default"][
                    "TaskQueue.Mall.IsChecked"
                ] = "False"  # 获取信用及购物
                data["Configurations"]["Default"][
                    "TaskQueue.AutoRoguelike.IsChecked"
                ] = "False"  # 自动肉鸽
                data["Configurations"]["Default"][
                    "TaskQueue.Reclamation.IsChecked"
                ] = "False"  # 生息演算

        # 覆写配置文件
        with self.set_path.open(mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        return True

    def get_emulator_path(self):
        """获取模拟器路径"""

        # 读取配置文件
        with self.set_path.open(mode="r", encoding="utf-8") as f:
            set = json.load(f)
        # 获取模拟器路径
        return Path(set["Configurations"]["Default"]["Start.EmulatorPath"])

    def server_date(self):
        """获取当前的服务器日期"""

        dt = datetime.datetime.now()
        if dt.time() < datetime.datetime.min.time().replace(hour=4):
            dt = dt - datetime.timedelta(days=1)
        return dt.strftime("%Y-%m-%d")
