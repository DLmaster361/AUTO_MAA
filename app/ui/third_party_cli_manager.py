import json
import shutil
import subprocess
from pathlib import Path

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QFileDialog, QVBoxLayout, QPushButton, QStackedWidget, QLabel, QSizePolicy
)
from qfluentwidgets import (
    Action, CommandBar, FluentIcon, MessageBox, Pivot, PushSettingCard
)
from .Widget import LineEditSettingCard


class ThirdPartySoftwareManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("第三方软件管理")
        layout = QVBoxLayout(self)

        self.tools = CommandBar()
        self.software_manager = SoftwareSettingBox(self)

        self.tools.addActions([
            Action(FluentIcon.ADD_TO, "新建软件实例", triggered=self.add_software_instance),
            Action(FluentIcon.REMOVE_FROM, "删除软件实例", triggered=self.del_software_instance),
        ])
        self.tools.addSeparator()
        self.tools.addActions([
            Action(FluentIcon.LEFT_ARROW, "向左移动", triggered=self.left_software_instance),
            Action(FluentIcon.RIGHT_ARROW, "向右移动", triggered=self.right_software_instance),
        ])

        layout.addWidget(self.tools)
        layout.addWidget(self.software_manager)

    def add_software_instance(self):
        index = len(self.software_manager.search_software()) + 1
        self.software_manager.add_SoftwareSettingBox(index)
        self.software_manager.switch_SettingBox(index)

    def del_software_instance(self):
        name = self.software_manager.pivot.currentRouteKey()
        if name is None:
            MessageBox("警告", "未选择软件实例", self).exec()
            return

        choice = MessageBox("确认", f"确定要删除 {name} 实例吗？", self)
        if choice.exec():
            shutil.rmtree(Path("config/SoftwareConfig/") / name, ignore_errors=True)
            self.software_manager.clear_SettingBox()
            self.software_manager.show_SettingBox(1)

    def left_software_instance(self):
        self.software_manager.move_SettingBox(-1)

    def right_software_instance(self):
        self.software_manager.move_SettingBox(1)


class SoftwareSettingBox(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pivot = Pivot(self)
        self.stackedWidget = QStackedWidget(self)
        self.Layout = QVBoxLayout(self)
        self.script_list = []

        self.Layout.addWidget(self.pivot, 0, Qt.AlignHCenter)
        self.Layout.addWidget(self.stackedWidget)
        self.Layout.setContentsMargins(0, 0, 0, 0)

        self.pivot.currentItemChanged.connect(
            lambda index: self.switch_SettingBox(int(index[3:]))
        )

        self.show_SettingBox(1)

    def show_SettingBox(self, index):
        software_list = self.search_software()
        for software in software_list:
            self.add_SoftwareSettingBox(int(software[3:]))
        self.switch_SettingBox(index)

    def switch_SettingBox(self, index):
        if index > len(self.script_list):
            return
        self.pivot.setCurrentItem(f"软件_{index}")
        self.stackedWidget.setCurrentWidget(self.script_list[index - 1])

    def clear_SettingBox(self):
        for sub_interface in self.script_list:
            self.stackedWidget.removeWidget(sub_interface)
            sub_interface.deleteLater()
        self.script_list.clear()
        self.pivot.clear()

    def add_SoftwareSettingBox(self, uid):
        software_setting_box = SoftwareSetting(uid, self)
        self.script_list.append(software_setting_box)
        self.stackedWidget.addWidget(software_setting_box)
        self.pivot.addItem(routeKey=f"软件_{uid}", text=f"软件 {uid}")

    def search_software(self):
        software_list = []
        config_path = Path("config/SoftwareConfig")
        if config_path.exists():
            for subdir in config_path.iterdir():
                if subdir.is_dir():
                    software_list.append(subdir.name)
        return software_list

    def move_SettingBox(self, direction):
        name = self.pivot.currentRouteKey()
        index = int(name[3:])
        new_index = index + direction
        if 1 <= new_index <= len(self.script_list):
            self.switch_SettingBox(new_index)


class SoftwareSetting(QWidget):
    def __init__(self, uid, parent=None):
        super().__init__(parent)
        self.setObjectName(f"软件_{uid}")
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # 添加一个 QLabel 作为说明框
        self.description_label = QLabel(
            "🔹 此界面用于管理第三方软件实例。\n"
            "🔹 您可以选择软件路径，并输入额外参数运行软件。\n"
            "🔹 目前测试过的软件有 BetterGI 的 startOneDragon 参数可以正常使用。",
            self
        )

        self.description_label.setStyleSheet("font-size: 16px;")
        self.description_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.description_label.setMinimumWidth(800)
        self.description_label.setFixedHeight(80)

        config_dir = Path(f"config/SoftwareConfig/{self.objectName()}")
        config_path = config_dir / "config.json"
        config_dir.mkdir(parents=True, exist_ok=True)

        if not config_path.exists():
            with config_path.open("w", encoding="utf-8") as f:
                json.dump({"software_path": "", "extra_args": ""}, f, ensure_ascii=False, indent=4)

        with config_path.open("r", encoding="utf-8") as f:
            self.config_data = json.load(f)

        self.software_path_card = PushSettingCard("选择软件文件", FluentIcon.FOLDER, "软件路径",
                                                  self.config_data["software_path"], self)
        self.software_path_card.clicked.connect(self.select_software)

        # 用 ConfigItemWrapper 让 configItem 变成对象
        self.extra_args_item = ConfigItemWrapper("extra_args", self.config_data["extra_args"])

        self.args_input = LineEditSettingCard(
            text="输入额外参数",
            icon=FluentIcon.PAGE_RIGHT,
            title="额外参数",
            content="运行时的额外参数",
            configItem=self.extra_args_item  # 传入对象，而不是字符串，不然会报错
        )
        # 监听参数变化，确保 UI 实时更新
        self.extra_args_item.valueChanged.connect(self.args_input.setValue)

        self.args_input.textChanged.connect(self.save_extra_args)

        self.run_button = QPushButton("测试软件是否可以正常运行", self)
        self.run_button.setFixedHeight(40)

        self.run_button.setIcon(QIcon(FluentIcon.PLAY.icon()))
        self.run_button.clicked.connect(self.run_software)

        layout.addWidget(self.software_path_card)
        layout.addWidget(self.args_input)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

    def save_extra_args(self, text):
        """当用户输入额外参数时，自动保存到 JSON 文件"""
        self.config_data["extra_args"] = text
        config_path = Path(f"config/SoftwareConfig/{self.objectName()}/config.json")
        with config_path.open("w", encoding="utf-8") as f:
            json.dump(self.config_data, f, ensure_ascii=False, indent=4)

        # 更新 ConfigItemWrapper 的值
        self.extra_args_item.value = text

    def run_software(self):
        config_path = Path(f"config/SoftwareConfig/{self.objectName()}/config.json")
        with config_path.open("r", encoding="utf-8") as f:
            config_data = json.load(f)

        software_path = config_data.get("software_path", "")
        extra_args = config_data.get("extra_args", "")

        if software_path:
            subprocess.Popen([software_path] + extra_args.split(), shell=True)
        else:
            MessageBox("错误", "未设置软件路径", self).exec()

    def select_software(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "选择软件", "./", "可执行文件 (*.exe)")
        if file_path:
            self.software_path_card.setContent(file_path)
            self.config_data["software_path"] = file_path
            config_path = Path(f"config/SoftwareConfig/{self.objectName()}/config.json")
            with config_path.open("w", encoding="utf-8") as f:
                json.dump(self.config_data, f, ensure_ascii=False, indent=4)


class ConfigItemWrapper(QObject):
    """包装 config.json 的配置项，模拟 qconfig.ConfigItem"""

    valueChanged = Signal(str)

    def __init__(self, key: str, value: str):
        super().__init__()
        self.key = key
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value: str):
        if self._value != new_value:
            self._value = new_value
            self.valueChanged.emit(new_value)
