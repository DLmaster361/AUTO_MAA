import ctypes
import datetime
import os
import sys
import time
import winreg
from PySide6 import QtCore


class MainTimer(QtCore.QThread):

    GetConfig = QtCore.Signal()
    StartForTimer = QtCore.Signal()
    AppPath = os.path.realpath(sys.argv[0])  # 获取软件自身的路径
    AppName = os.path.basename(AppPath)  # 获取软件自身的名称
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    isMaaRun = False

    def __init__(self, config):
        super(MainTimer, self).__init__()
        self.config = config

    def run(self):
        while True:
            self.GetConfig.emit()
            self.setSystem()
            TimeSet = [
                self.config["Default"]["TimeSet.run" + str(k + 1)]
                for k in range(10)
                if self.config["Default"]["TimeSet.set" + str(k + 1)] == "True"
            ]
            curtime = datetime.datetime.now().strftime("%H:%M")
            if (curtime in TimeSet) and not self.isMaaRun:
                self.StartForTimer.emit()
            time.sleep(1)

    def setSystem(self):

        # 同步系统休眠状态
        if self.config["Default"]["SelfSet.IfSleep"] == "True":
            # 设置系统电源状态
            ctypes.windll.kernel32.SetThreadExecutionState(
                self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED
            )
        elif self.config["Default"]["SelfSet.IfSleep"] == "False":
            # 恢复系统电源状态
            ctypes.windll.kernel32.SetThreadExecutionState(self.ES_CONTINUOUS)

        # 同步开机自启
        if (
            self.config["Default"]["SelfSet.IfSelfStart"] == "True"
            and not self.IsStartup()
        ):
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                winreg.KEY_SET_VALUE,
                winreg.KEY_ALL_ACCESS | winreg.KEY_WRITE | winreg.KEY_CREATE_SUB_KEY,
            )
            winreg.SetValueEx(key, self.AppName, 0, winreg.REG_SZ, self.AppPath)
            winreg.CloseKey(key)
        elif (
            self.config["Default"]["SelfSet.IfSelfStart"] == "False"
            and self.IsStartup()
        ):
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                winreg.KEY_SET_VALUE,
                winreg.KEY_ALL_ACCESS | winreg.KEY_WRITE | winreg.KEY_CREATE_SUB_KEY,
            )
            winreg.DeleteValue(key, self.AppName)
            winreg.CloseKey(key)

    def IsStartup(self):
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        try:
            value, _ = winreg.QueryValueEx(key, self.AppName)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)