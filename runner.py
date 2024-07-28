import json
import os
import subprocess
import sys
import datetime
import time
from PySide6 import QtCore

def ServerDate():
    dt = datetime.datetime.now()
    if dt.time() < datetime.datetime.min.time().replace(hour=4):
        dt = dt - datetime.timedelta(days=1)
    return dt.strftime("%Y-%m-%d")


class MaaRunner(QtCore.QThread):

    UpGui = QtCore.Signal(str, str, str, str, str)
    UpUserInfo = QtCore.Signal(list, list, list, list)
    Accomplish = QtCore.Signal()
    AppPath = os.path.dirname(os.path.realpath(sys.argv[0])).replace(
        "\\", "/"
    )  # 获取软件自身的路径
    ifRun = False

    def __init__(self, setPath, logPath, maaPath, routine, annihilation, num, data):
        super(MaaRunner, self).__init__()
        self.SetPath = setPath
        self.LogPath = logPath
        self.MaaPath = maaPath
        self.Routine = routine
        self.Annihilation = annihilation
        self.Num = num
        self.data = data

    def run(self):
        self.ifRun = True
        curdate = ServerDate()
        begintime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        OverUid = []
        ErrorUid = []
        AllUid = [
            self.data[i][13]
            for i in range(len(self.data))
            if (self.data[i][2] > 0 and self.data[i][3] == "y")
        ]
        # MAA预配置
        self.SetMaa(0, 0)
        # 执行情况预处理
        for i in AllUid:
            if self.data[i][4] != curdate:
                self.data[i][4] = curdate
                self.data[i][12] = 0
            self.data[i][0] += "_第" + str(self.data[i][12] + 1) + "次代理"
        # 开始代理
        for uid in AllUid:
            if not self.ifRun:
                break
            runbook = [False for k in range(2)]
            for i in range(self.Num):
                if not self.ifRun:
                    break
                for j in range(2):
                    if not self.ifRun:
                        break
                    if j == 0 and self.data[uid][8] == "n":
                        runbook[0] = True
                        continue
                    if runbook[j]:
                        continue
                    # 配置MAA
                    self.SetMaa(j + 1, uid)
                    # 创建MAA任务
                    maa = subprocess.Popen([self.MaaPath])
                    # 记录当前时间
                    StartTime = datetime.datetime.now()
                    # 初始化log记录列表
                    if j == 0:
                        logx = [k for k in range(self.Annihilation * 60)]
                    elif j == 1:
                        logx = [k for k in range(self.Routine * 60)]
                    logi = 0
                    # 更新运行信息
                    WaitUid = [
                        idx for idx in AllUid if (not idx in OverUid + ErrorUid + [uid])
                    ]
                    # 监测MAA运行状态
                    while True:
                        # 更新MAA日志
                        with open(self.LogPath, "r", encoding="utf-8") as f:
                            logs = []
                            for entry in f:
                                try:
                                    entry_time = datetime.datetime.strptime(
                                        entry[1:20], "%Y-%m-%d %H:%M:%S"
                                    )
                                    if entry_time > StartTime:
                                        logs.append(entry)
                                except ValueError:
                                    pass
                            log = "".join(logs)
                            if j == 0:
                                self.UpGui.emit(
                                    self.data[uid][0] + "_第" + str(i + 1) + "次_剿灭",
                                    "\n".join([self.data[k][0] for k in WaitUid]),
                                    "\n".join([self.data[k][0] for k in OverUid]),
                                    "\n".join([self.data[k][0] for k in ErrorUid]),
                                    log,
                                )
                            elif j == 1:
                                self.UpGui.emit(
                                    self.data[uid][0] + "_第" + str(i + 1) + "次_日常",
                                    "\n".join([self.data[k][0] for k in WaitUid]),
                                    "\n".join([self.data[k][0] for k in OverUid]),
                                    "\n".join([self.data[k][0] for k in ErrorUid]),
                                    log,
                                )
                            if len(logs) != 0:
                                logx[logi] = logs[-1]
                                logi = (logi + 1) % len(logx)
                        # 判断MAA程序运行状态
                        if "任务已全部完成！" in log:
                            runbook[j] = True
                            self.UpGui.emit(
                                self.data[uid][0] + "_第" + str(i + 1) + "次_日常",
                                "\n".join([self.data[k][0] for k in WaitUid]),
                                "\n".join([self.data[k][0] for k in OverUid]),
                                "\n".join([self.data[k][0] for k in ErrorUid]),
                                "检测到MAA进程完成代理任务\n正在等待相关程序结束\n请等待10s",
                            )
                            time.sleep(10)
                            break
                        elif (
                            ("请检查连接设置或尝试重启模拟器与 ADB 或重启电脑" in log)
                            or ("已停止" in log)
                            or ("MaaAssistantArknights GUI exited" in log)
                            or self.TimeOut(logx)
                            or not self.ifRun
                        ):
                            # 打印中止信息
                            if (
                                (
                                    "请检查连接设置或尝试重启模拟器与 ADB 或重启电脑"
                                    in log
                                )
                                or ("已停止" in log)
                                or ("MaaAssistantArknights GUI exited" in log)
                            ):
                                info = "检测到MAA进程异常\n正在中止相关程序\n请等待10s"
                            elif self.TimeOut(logx):
                                info = "检测到MAA进程超时\n正在中止相关程序\n请等待10s"
                            elif not self.ifRun:
                                info = "您中止了本次任务\n正在中止相关程序\n请等待"
                            self.UpGui.emit(
                                self.data[uid][0] + "_第" + str(i + 1) + "次_日常",
                                "\n".join([self.data[k][0] for k in WaitUid]),
                                "\n".join([self.data[k][0] for k in OverUid]),
                                "\n".join([self.data[k][0] for k in ErrorUid]),
                                info,
                            )
                            os.system("taskkill /F /T /PID " + str(maa.pid))
                            if self.ifRun:
                                time.sleep(10)
                            break
                        # 检测时间间隔
                        time.sleep(1)
                if runbook[0] and runbook[1]:
                    if self.data[uid][12] == 0:
                        self.data[uid][2] -= 1
                    self.data[uid][12] += 1
                    OverUid.append(uid)
                    break
            if not (runbook[0] and runbook[1]):
                ErrorUid.append(uid)
        # 更新用户数据
        days = [self.data[k][2] for k in AllUid]
        lasts = [self.data[k][4] for k in AllUid]
        numbs = [self.data[k][12] for k in AllUid]
        self.UpUserInfo.emit(AllUid, days, lasts, numbs)
        # 保存运行日志
        endtime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.AppPath + "log.txt", "w", encoding="utf-8") as f:
            print("任务开始时间：" + begintime + "，结束时间：" + endtime, file=f)
            print(
                "已完成数：" + str(len(OverUid)) + "，未完成数：" + str(len(ErrorUid)),
                file=f,
            )
            ErrorUid = [idx for idx in AllUid if (not idx in OverUid)]
            if len(ErrorUid) != 0:
                print("代理未完成的用户：", file=f)
                print("\n".join([self.data[k][0] for k in ErrorUid]), file=f)
            WaitUid = [idx for idx in AllUid if (not idx in OverUid + ErrorUid + [uid])]
            if len(WaitUid) != 0:
                print("未代理的用户：", file=f)
                print("\n".join([self.data[k][0] for k in WaitUid]), file=f)
        with open(self.AppPath + "log.txt", "r", encoding="utf-8") as f:
            EndLog = f.read()
        # 恢复GUI运行面板
        self.UpGui.emit("", "", "", "", EndLog)
        self.Accomplish.emit()
        self.ifRun = False

    # 配置MAA运行参数
    def SetMaa(self, s, uid):
        with open(self.SetPath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if s == 0:
            data["Configurations"]["Default"][
                "MainFunction.ActionAfterCompleted"
            ] = "ExitEmulatorAndSelf"  # 完成后退出MAA和模拟器
            data["Configurations"]["Default"][
                "Start.RunDirectly"
            ] = "True"  # 启动MAA后直接运行
            data["Configurations"]["Default"][
                "Start.StartEmulator"
            ] = "True"  # 启动MAA后自动开启模拟器
        elif s == 1:
            data["Configurations"]["Default"]["Start.AccountName"] = (
                self.data[uid][1][:3] + "****" + self.data[uid][1][7:]
            )  # 账号切换
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
                "MainFunction.Stage1"
            ] = "Annihilation"  # 主关卡
            data["Configurations"]["Default"]["MainFunction.Stage2"] = ""  # 备选关卡1
            data["Configurations"]["Default"]["MainFunction.Stage3"] = ""  # 备选关卡2
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
        elif s == 2:
            data["Configurations"]["Default"]["Start.AccountName"] = (
                self.data[uid][1][:3] + "****" + self.data[uid][1][7:]
            )  # 账号切换
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
            data["Configurations"]["Default"]["MainFunction.Stage1"] = self.data[uid][
                5
            ]  # 主关卡
            data["Configurations"]["Default"]["MainFunction.Stage2"] = self.data[uid][
                6
            ]  # 备选关卡1
            data["Configurations"]["Default"]["MainFunction.Stage3"] = self.data[uid][
                7
            ]  # 备选关卡2
            data["Configurations"]["Default"][
                "Fight.RemainingSanityStage"
            ] = ""  # 剩余理智关卡
            if self.data[uid][5] == "1-7":
                data["Configurations"]["Default"][
                    "MainFunction.Series.Quantity"
                ] = "6"  # 连战次数
            else:
                data["Configurations"]["Default"][
                    "MainFunction.Series.Quantity"
                ] = "1"  # 连战次数
            data["Configurations"]["Default"][
                "Penguin.IsDrGrandet"
            ] = "False"  # 博朗台模式
            data["Configurations"]["Default"][
                "GUI.CustomStageCode"
            ] = "True"  # 手动输入关卡名
            if self.data[uid][6] == "-" and self.data[uid][7] == "-":
                data["Configurations"]["Default"][
                    "GUI.UseAlternateStage"
                ] = "False"  # 不使用备选关卡
            else:
                data["Configurations"]["Default"][
                    "GUI.UseAlternateStage"
                ] = "True"  # 使用备选关卡
            data["Configurations"]["Default"][
                "Fight.UseRemainingSanityStage"
            ] = "False"  # 使用剩余理智
            data["Configurations"]["Default"][
                "Fight.UseExpiringMedicine"
            ] = "True"  # 无限吃48小时内过期的理智药
            if self.data[uid][9] == "-":
                data["Configurations"]["Default"][
                    "Infrast.CustomInfrastEnabled"
                ] = "False"  # 禁用自定义基建配置
            else:
                data["Configurations"]["Default"][
                    "Infrast.CustomInfrastEnabled"
                ] = "True"  # 启用自定义基建配置
                data["Configurations"]["Default"][
                    "Infrast.DefaultInfrast"
                ] = "user_defined"  # 内置配置
                data["Configurations"]["Default"][
                    "Infrast.IsCustomInfrastFileReadOnly"
                ] = "False"  # 自定义基建配置文件只读
                data["Configurations"]["Default"][
                    "Infrast.CustomInfrastFile"
                ] = self.data[uid][
                    9
                ]  # 自定义基建配置文件地址
        with open(self.SetPath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True

    # 超时判断
    def TimeOut(self, logx):
        log0 = logx[0]
        for i in logx:
            if i != log0:
                return False
        return True