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
AUTO_MAA更新器
v1.2
作者：DLmaster_361
"""

import sys
import json
import zipfile
import requests
import subprocess
import time
from functools import partial
from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QVBoxLayout
from qfluentwidgets import (
    ProgressBar,
    IndeterminateProgressBar,
    BodyLabel,
    setTheme,
    Theme,
)
from PySide6.QtGui import QIcon, QCloseEvent
from PySide6.QtCore import QThread, Signal, QTimer, QEventLoop

from typing import List, Dict, Union


def version_text(version_numb: list) -> str:
    """将版本号列表转为可读的文本信息"""

    if version_numb[3] == 0:
        version = f"v{'.'.join(str(_) for _ in version_numb[0:3])}"
    else:
        version = (
            f"v{'.'.join(str(_) for _ in version_numb[0:3])}-beta.{version_numb[3]}"
        )
    return version


class DownloadProcess(QThread):
    """分段下载子线程"""

    progress = Signal(int)
    accomplish = Signal(float)

    def __init__(
        self,
        url: str,
        start_byte: int,
        end_byte: int,
        download_path: Path,
        check_times: int = -1,
    ) -> None:
        super(DownloadProcess, self).__init__()

        self.url = url
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.download_path = download_path
        self.check_times = check_times

    def run(self) -> None:

        # 清理可能存在的临时文件
        if self.download_path.exists():
            self.download_path.unlink()

        headers = {"Range": f"bytes={self.start_byte}-{self.end_byte}"}

        while not self.isInterruptionRequested() and self.check_times != 0:

            try:

                start_time = time.time()

                response = requests.get(
                    self.url, headers=headers, timeout=10, stream=True
                )

                print(self.download_path.suffix, response.status_code)

                if response.status_code != 206:

                    if self.check_times != -1:
                        self.check_times -= 1

                    time.sleep(1)
                    continue

                downloaded_size = 0
                with self.download_path.open(mode="wb") as f:

                    for chunk in response.iter_content(chunk_size=8192):

                        if self.isInterruptionRequested():
                            print(
                                f"{self.download_path.suffix}: isInterruptionRequested"
                            )
                            break

                        f.write(chunk)
                        downloaded_size += len(chunk)

                        self.progress.emit(downloaded_size)

                if self.isInterruptionRequested():

                    if self.download_path.exists():
                        self.download_path.unlink()
                    self.accomplish.emit(0)

                else:

                    self.accomplish.emit(time.time() - start_time)

                break

            except Exception as e:

                if self.check_times != -1:
                    self.check_times -= 1
                time.sleep(1)

        else:
            print(
                f"{self.download_path.suffix}: isInterruptionRequested---{self.check_times}/{self.isInterruptionRequested()}"
            )
            if self.download_path.exists():
                self.download_path.unlink()
            self.accomplish.emit(0)


class DownloadManager(QDialog):
    """下载管理器"""

    speed_test_accomplish = Signal()
    download_accomplish = Signal()
    download_process_clear = Signal()

    isInterruptionRequested = False

    def __init__(
        self,
        app_path: Path,
        name: str,
        main_version: list,
        updater_version: list,
        config: dict,
    ) -> None:
        super().__init__()

        self.app_path = app_path
        self.name = name
        self.main_version = main_version
        self.updater_version = updater_version
        self.config = config
        self.download_path = app_path / "DOWNLOAD_TEMP.zip"  #  临时下载文件的路径
        self.version_path = app_path / "resources/version.json"
        self.download_process_dict: Dict[str, DownloadProcess] = {}
        self.timer_dict: Dict[str, QTimer] = {}

        self.setWindowTitle("AUTO_MAA更新器")
        self.setWindowIcon(
            QIcon(str(app_path / "resources/icons/AUTO_MAA_Updater.ico"))
        )
        self.setFixedSize(700, 70)

        setTheme(Theme.AUTO, lazy=True)

        # 创建垂直布局
        self.Layout = QVBoxLayout(self)

        self.info = BodyLabel("正在初始化", self)
        self.progress_1 = IndeterminateProgressBar(self)
        self.progress_2 = ProgressBar(self)

        self.update_progress(0, 0, 0)

        self.Layout.addWidget(self.info)
        self.Layout.addStretch(1)
        self.Layout.addWidget(self.progress_1)
        self.Layout.addWidget(self.progress_2)
        self.Layout.addStretch(1)

    def run(self) -> None:

        if self.name == "MAA":
            self.download_task1()
        else:
            self.test_speed_task1()
            self.speed_test_accomplish.connect(self.download_task1)

    def get_download_url(self, mode: str) -> Union[str, Dict[str, str]]:
        """获取下载链接"""

        url_dict = {}

        if mode == "测速":

            url_dict["GitHub站"] = (
                f"https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"
            )
            url_dict["官方镜像站"] = (
                f"https://gitee.com/DLmaster_361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"
            )
            url_dict["官方下载站"] = (
                f"https://jp-download.fearr.xyz/AUTO_MAA/AUTO_MAA_{version_text(self.main_version)}.zip"
            )
            for proxy_url in self.config["proxy_list"]:
                url_dict[proxy_url] = (
                    f"{proxy_url}https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"
                )
            return url_dict

        elif mode == "下载":

            if self.name == "MAA":
                return f"https://jp-download.fearr.xyz/MAA/MAA-{version_text(self.main_version)}-win-x64.zip"

            if "selected" in self.config:
                proxy_url = self.config["selected"]
            elif "speed_result" in self.config:
                proxy_url = max(
                    self.config["speed_result"], key=self.config["speed_result"].get
                )

            if self.name == "AUTO_MAA主程序":

                if proxy_url == "GitHub站":
                    return f"https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"
                elif proxy_url == "官方镜像站":
                    return f"https://gitee.com/DLmaster_361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"
                elif proxy_url == "官方下载站":
                    return f"https://jp-download.fearr.xyz/AUTO_MAA/AUTO_MAA_{version_text(self.main_version)}.zip"
                else:
                    return f"{proxy_url}https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/AUTO_MAA_{version_text(self.main_version)}.zip"

            elif self.name == "AUTO_MAA更新器":

                if proxy_url == "GitHub站":
                    return f"https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/Updater_{version_text(self.updater_version)}.zip"
                elif proxy_url == "官方镜像站":
                    return f"https://gitee.com/DLmaster_361/AUTO_MAA/releases/download/{version_text(self.main_version)}/Updater_{version_text(self.updater_version)}.zip"
                elif proxy_url == "官方下载站":
                    return f"https://jp-download.fearr.xyz/AUTO_MAA/Updater_{version_text(self.updater_version)}.zip"
                else:
                    return f"{proxy_url}https://github.com/DLmaster361/AUTO_MAA/releases/download/{version_text(self.main_version)}/Updater_{version_text(self.updater_version)}.zip"

    def test_speed_task1(self) -> None:

        if self.isInterruptionRequested:
            return None

        url_dict = self.get_download_url("测速")
        self.test_speed_result: Dict[str, float] = {}

        for name, url in url_dict.items():

            if self.isInterruptionRequested:
                break

            # 创建测速线程，下载4MB文件以测试下载速度
            self.download_process_dict[name] = DownloadProcess(
                url,
                0,
                4194304,
                self.app_path / f"{name.replace('/','').replace(':','')}.zip",
                10,
            )
            self.test_speed_result[name] = -1
            self.download_process_dict[name].accomplish.connect(
                partial(self.test_speed_task2, name)
            )

            self.download_process_dict[name].start()
            timer = QTimer(self)
            timer.setSingleShot(True)
            timer.timeout.connect(partial(self.kill_speed_test, name))
            timer.start(30000)
            self.timer_dict[name] = timer

        self.update_info("正在测速，预计用时30秒")
        self.update_progress(0, 1, 0)

    def kill_speed_test(self, name: str) -> None:

        print(f"time: {name}")

        if name in self.download_process_dict:
            self.download_process_dict[name].requestInterruption()
            print(f"kill_speed_test: {name}")

    def test_speed_task2(self, name: str, t: float) -> None:

        # 计算下载速度
        if self.isInterruptionRequested:
            self.update_info(f"已中止测速进程：{name}")
            self.test_speed_result[name] = 0
        elif t != 0:
            self.update_info(f"{name}：{ 4 / t:.2f} MB/s")
            self.test_speed_result[name] = 4 / t
        else:
            self.update_info(f"{name}：{ 0:.2f} MB/s")
            self.test_speed_result[name] = 0
        self.update_progress(
            0,
            len(self.test_speed_result),
            sum(1 for speed in self.test_speed_result.values() if speed != -1),
        )

        # 删除临时文件
        if (self.app_path / f"{name.replace('/','').replace(':','')}.zip").exists():
            (self.app_path / f"{name.replace('/','').replace(':','')}.zip").unlink()

        # 清理下载线程
        self.timer_dict[name].stop()
        self.timer_dict[name].deleteLater()
        self.timer_dict.pop(name)
        self.download_process_dict[name].requestInterruption()
        self.download_process_dict[name].quit()
        self.download_process_dict[name].wait()
        self.download_process_dict[name].deleteLater()
        self.download_process_dict.pop(name)
        if not self.download_process_dict:
            self.download_process_clear.emit()

        print(self.download_process_dict.keys())

        if any(speed == -1 for _, speed in self.test_speed_result.items()):
            return None

        # 保存测速结果
        self.config["speed_result"] = self.test_speed_result

        self.update_info("测速完成！")
        self.speed_test_accomplish.emit()

    def download_task1(self) -> None:

        if self.isInterruptionRequested:
            return None

        url = self.get_download_url("下载")
        self.downloaded_size_list: List[List[int, bool]] = []

        response = requests.head(url)

        self.file_size = int(response.headers.get("content-length", 0))
        part_size = self.file_size // self.config["thread_numb"]
        self.downloaded_size = 0
        self.last_download_size = 0
        self.last_time = time.time()
        self.speed = 0

        # 拆分下载任务，启用多线程下载
        for i in range(self.config["thread_numb"]):

            if self.isInterruptionRequested:
                break

            # 计算单任务下载范围
            start_byte = i * part_size
            end_byte = (
                (i + 1) * part_size - 1
                if (i != self.config["thread_numb"] - 1)
                else self.file_size - 1
            )

            # 创建下载子线程
            self.download_process_dict[f"part{i}"] = DownloadProcess(
                url, start_byte, end_byte, self.download_path.with_suffix(f".part{i}")
            )
            self.downloaded_size_list.append([0, False])
            self.download_process_dict[f"part{i}"].progress.connect(
                partial(self.download_task2, i)
            )
            self.download_process_dict[f"part{i}"].accomplish.connect(
                partial(self.download_task3, i)
            )
            self.download_process_dict[f"part{i}"].start()

    def download_task2(self, index: str, current: int) -> None:
        """更新下载进度"""

        self.downloaded_size_list[index][0] = current
        self.downloaded_size = sum([_[0] for _ in self.downloaded_size_list])
        self.update_progress(0, self.file_size, self.downloaded_size)

        if time.time() - self.last_time >= 1.0:
            self.speed = (
                (self.downloaded_size - self.last_download_size)
                / (time.time() - self.last_time)
                / 1024
            )
            self.last_download_size = self.downloaded_size
            self.last_time = time.time()

        if self.speed >= 1024:
            self.update_info(
                f"正在下载：{self.name} 已下载：{self.downloaded_size / 1048576:.2f}/{self.file_size / 1048576:.2f} MB （{self.downloaded_size / self.file_size * 100:.2f}%） 下载速度：{self.speed / 1024:.2f} MB/s",
            )
        else:
            self.update_info(
                f"正在下载：{self.name} 已下载：{self.downloaded_size / 1048576:.2f}/{self.file_size / 1048576:.2f} MB （{self.downloaded_size / self.file_size * 100:.2f}%） 下载速度：{self.speed:.2f} KB/s",
            )

    def download_task3(self, index: str, t: float) -> None:

        # 标记下载线程完成
        self.downloaded_size_list[index][1] = True

        # 清理下载线程
        self.download_process_dict[f"part{index}"].requestInterruption()
        self.download_process_dict[f"part{index}"].quit()
        self.download_process_dict[f"part{index}"].wait()
        self.download_process_dict[f"part{index}"].deleteLater()
        self.download_process_dict.pop(f"part{index}")
        if not self.download_process_dict:
            self.download_process_clear.emit()

        if (
            any([not _[1] for _ in self.downloaded_size_list])
            or self.isInterruptionRequested
        ):
            return None

        # 合并下载的分段文件
        with self.download_path.open(mode="wb") as outfile:
            for i in range(self.config["thread_numb"]):
                with self.download_path.with_suffix(f".part{i}").open(
                    mode="rb"
                ) as infile:
                    outfile.write(infile.read())
                self.download_path.with_suffix(f".part{i}").unlink()

        # # 解压
        try:

            while True:
                if self.isInterruptionRequested:
                    self.download_path.unlink()
                    return None
                try:
                    self.update_info("正在解压更新文件")
                    self.update_progress(0, 0, 0)
                    with zipfile.ZipFile(self.download_path, "r") as zip_ref:
                        zip_ref.extractall(self.app_path)
                    break
                except PermissionError:
                    self.info.emit(f"解压出错：{self.name}正在运行，正在等待其关闭")
                    time.sleep(1)

            self.update_info("正在删除临时文件")
            self.update_progress(0, 0, 0)
            self.download_path.unlink()

            self.update_info(f"{self.name}更新成功！")
            self.update_progress(0, 100, 100)

        except Exception as e:

            e = str(e)
            e = "\n".join([e[_ : _ + 75] for _ in range(0, len(e), 75)])
            self.update_info(f"解压更新时出错：\n{e}")
            return None

        # 更新version文件
        if not self.isInterruptionRequested and self.name in [
            "AUTO_MAA主程序",
            "AUTO_MAA更新器",
        ]:
            with open(self.version_path, "r", encoding="utf-8") as f:
                version_info = json.load(f)
            if self.name == "AUTO_MAA主程序":
                version_info["main_version"] = ".".join(map(str, self.main_version))
            elif self.name == "AUTO_MAA更新器":
                version_info["updater_version"] = ".".join(
                    map(str, self.updater_version)
                )
            with open(self.version_path, "w", encoding="utf-8") as f:
                json.dump(version_info, f, ensure_ascii=False, indent=4)

        # 主程序更新完成后打开对应程序
        if not self.isInterruptionRequested and self.name == "AUTO_MAA主程序":
            subprocess.Popen(
                str(self.app_path / "AUTO_MAA.exe"),
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print(str(self.app_path / "AUTO_MAA.exe"))
        elif not self.isInterruptionRequested and self.name == "MAA":
            subprocess.Popen(
                str(self.app_path / "MAA.exe"),
                shell=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )

        self.download_accomplish.emit()

    def update_info(self, text: str) -> None:
        self.info.setText(text)

    def update_progress(self, begin: int, end: int, current: int) -> None:

        if begin == 0 and end == 0:
            self.progress_2.setVisible(False)
            self.progress_1.setVisible(True)
        else:
            self.progress_1.setVisible(False)
            self.progress_2.setVisible(True)
            self.progress_2.setRange(begin, end)
            self.progress_2.setValue(current)

    def requestInterruption(self) -> None:

        self.isInterruptionRequested = True

        print(self.download_process_dict)
        for process in self.download_process_dict.values():
            process.requestInterruption()

        if self.download_process_dict:
            loop = QEventLoop()
            self.download_process_clear.connect(loop.quit)
            loop.exec()

    def closeEvent(self, event: QCloseEvent):
        """清理残余进程"""

        self.requestInterruption()

        print(self.download_process_dict)

        event.accept()


class AUTO_MAA_Downloader(QApplication):
    def __init__(
        self,
        app_path: Path,
        name: str,
        main_version: list,
        updater_version: list,
        config: dict,
    ) -> None:
        super().__init__()

        self.main = DownloadManager(
            app_path, name, main_version, updater_version, config
        )
        self.main.show()
        self.main.run()


if __name__ == "__main__":

    # 获取软件自身的路径
    app_path = Path(sys.argv[0]).resolve().parent

    # 从本地版本信息文件获取当前版本信息
    if (app_path / "resources/version.json").exists():
        with (app_path / "resources/version.json").open(
            mode="r", encoding="utf-8"
        ) as f:
            version_current = json.load(f)
        main_version_current = list(
            map(int, version_current["main_version"].split("."))
        )
    else:
        main_version_current = [0, 0, 0, 0]

    # 从本地配置文件获取更新信息
    if (app_path / "config/config.json").exists():
        with (app_path / "config/config.json").open(mode="r", encoding="utf-8") as f:
            config = json.load(f)
        if "Update" in config and "UpdateType" in config["Update"]:
            update_type = config["Update"]["UpdateType"]
        else:
            update_type = "main"
        if "Update" in config and "ProxyUrlList" in config["Update"]:
            proxy_list = config["Update"]["ProxyUrlList"]
        else:
            proxy_list = []
        if "Update" in config and "ThreadNumb" in config["Update"]:
            thread_numb = config["Update"]["ThreadNumb"]
        else:
            thread_numb = 8
    else:
        update_type = "main"
        proxy_list = []
        thread_numb = 8

    # 从远程服务器获取最新版本信息
    for _ in range(3):
        try:
            response = requests.get(
                f"https://gitee.com/DLmaster_361/AUTO_MAA/raw/{update_type}/resources/version.json"
            )
            version_remote = response.json()
            main_version_remote = list(
                map(int, version_remote["main_version"].split("."))
            )
            remote_proxy_list = version_remote["proxy_list"]
            break
        except Exception as e:
            err = e
            time.sleep(0.1)
    else:
        sys.exit(f"获取版本信息时出错：\n{err}")

    # 合并代理列表
    download_config = {
        "proxy_list": list(set(proxy_list + remote_proxy_list)),
        "thread_numb": thread_numb,
    }

    # 启动更新线程
    if main_version_remote > main_version_current:
        app = AUTO_MAA_Downloader(
            app_path,
            "AUTO_MAA主程序",
            main_version_remote,
            [],
            download_config,
        )
        sys.exit(app.exec())
