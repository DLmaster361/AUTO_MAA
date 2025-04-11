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
AUTO_MAA组件
v4.2
作者：DLmaster_361
"""

from PySide6.QtWidgets import (
    QWidget,
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QSizePolicy,
)
from PySide6.QtCore import Qt, QTime, QTimer, QEvent, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter, QPainterPath
from qfluentwidgets import (
    LineEdit,
    PasswordLineEdit,
    MessageBoxBase,
    MessageBox,
    SubtitleLabel,
    SettingCard,
    SpinBox,
    FluentIconBase,
    Signal,
    ComboBox,
    EditableComboBox,
    CheckBox,
    IconWidget,
    FluentIcon,
    CardWidget,
    BodyLabel,
    QConfig,
    ConfigItem,
    TimeEdit,
    OptionsConfigItem,
    TeachingTip,
    TransparentToolButton,
    TeachingTipTailPosition,
    ExpandSettingCard,
    ToolButton,
    PushButton,
    PrimaryPushButton,
    ProgressRing,
    TextBrowser,
    HeaderCardWidget,
    SwitchButton,
    IndicatorPosition,
    Slider,
)
from qfluentwidgets.common.overload import singledispatchmethod
import os
import re
import markdown
from datetime import datetime
from urllib.parse import urlparse
from functools import partial
from typing import Optional, Union, List, Dict

from app.core import Config
from app.services import Crypto


class LineEditMessageBox(MessageBoxBase):
    """输入对话框"""

    def __init__(self, parent, title: str, content: Union[str, None], mode: str):
        super().__init__(parent)
        self.title = SubtitleLabel(title)

        if mode == "明文":
            self.input = LineEdit()
            self.input.setClearButtonEnabled(True)
        elif mode == "密码":
            self.input = PasswordLineEdit()

        self.input.returnPressed.connect(self.yesButton.click)
        self.input.setPlaceholderText(content)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.title)
        self.viewLayout.addWidget(self.input)


class ComboBoxMessageBox(MessageBoxBase):
    """选择对话框"""

    def __init__(self, parent, title: str, content: List[str], list: List[List[str]]):
        super().__init__(parent)
        self.title = SubtitleLabel(title)

        Widget = QWidget()
        Layout = QHBoxLayout(Widget)

        self.input: List[ComboBox] = []

        for i in range(len(content)):

            self.input.append(ComboBox())
            self.input[i].addItems(list[i])
            self.input[i].setCurrentIndex(-1)
            self.input[i].setPlaceholderText(content[i])
            Layout.addWidget(self.input[i])

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.title)
        self.viewLayout.addWidget(Widget)


class ProgressRingMessageBox(MessageBoxBase):
    """进度环倒计时对话框"""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title = SubtitleLabel(title)

        self.time = 100
        Widget = QWidget()
        Layout = QHBoxLayout(Widget)
        self.ring = ProgressRing()
        self.ring.setRange(0, 100)
        self.ring.setValue(100)
        self.ring.setTextVisible(True)
        self.ring.setFormat("%p 秒")
        self.ring.setFixedSize(100, 100)
        self.ring.setStrokeWidth(4)
        Layout.addWidget(self.ring)

        self.yesButton.hide()
        self.cancelButton.clicked.connect(self.__quit_timer)
        self.buttonLayout.insertStretch(1)

        # 将组件添加到布局中
        self.viewLayout.addWidget(self.title)
        self.viewLayout.addWidget(Widget)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.__update_time)
        self.timer.start(1000)

    def __update_time(self):

        self.time -= 1
        self.ring.setValue(self.time)

        if self.time == 0:
            self.timer.stop()
            self.timer.deleteLater()
            self.yesButton.click()

    def __quit_timer(self):
        self.timer.stop()
        self.timer.deleteLater()


class NoticeMessageBox(MessageBoxBase):
    """公告对话框"""

    def __init__(self, parent, title: str, content: Dict[str, str]):
        super().__init__(parent)

        self.index = self.NoticeIndexCard(title, content, self)
        self.text = TextBrowser(self)
        self.text.setOpenExternalLinks(True)
        self.button_yes = PrimaryPushButton("确认", self)
        self.button_cancel = PrimaryPushButton("取消", self)

        self.buttonGroup.hide()

        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(self.text)
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.button_yes)
        self.button_layout.addWidget(self.button_cancel)
        self.v_layout.addLayout(self.button_layout)

        self.h_layout = QHBoxLayout()
        self.h_layout.addWidget(self.index)
        self.h_layout.addLayout(self.v_layout)
        self.h_layout.setStretch(0, 1)
        self.h_layout.setStretch(1, 3)

        # 将组件添加到布局中
        self.viewLayout.addLayout(self.h_layout)
        self.widget.setFixedSize(800, 600)

        self.index.index_changed.connect(self.__update_text)
        self.button_yes.clicked.connect(self.yesButton.click)
        self.button_cancel.clicked.connect(self.cancelButton.click)
        self.index.index_cards[0].clicked.emit()

    def __update_text(self, text: str):

        html = markdown.markdown(text).replace("\n", "")
        html = re.sub(
            r"<code>(.*?)</code>",
            r"<span style='color: #009faa;'>\1</span>",
            html,
        )
        html = re.sub(
            r'(<a\s+[^>]*href="[^"]+"[^>]*)>', r'\1 style="color: #009faa;">', html
        )
        html = re.sub(r"<li><p>(.*?)</p></li>", r"<p><strong>◆ </strong>\1</p>", html)
        html = re.sub(r"<ul>(.*?)</ul>", r"\1", html)

        self.text.setHtml(f"<body>{html}</body>")

    class NoticeIndexCard(HeaderCardWidget):

        index_changed = Signal(str)

        def __init__(self, title: str, content: Dict[str, str], parent=None):
            super().__init__(parent)
            self.setTitle(title)

            self.Layout = QVBoxLayout()
            self.viewLayout.addLayout(self.Layout)
            self.viewLayout.setContentsMargins(3, 0, 3, 3)

            self.index_cards: List[QuantifiedItemCard] = []

            for index, text in content.items():

                self.index_cards.append(QuantifiedItemCard([index, ""]))
                self.index_cards[-1].clicked.connect(
                    partial(self.index_changed.emit, text)
                )
                self.Layout.addWidget(self.index_cards[-1])

            if not content:
                self.Layout.addWidget(QuantifiedItemCard(["暂无信息", ""]))

            self.Layout.addStretch(1)


class SwitchSettingCard(SettingCard):
    """Setting card with switch button"""

    checkedChanged = Signal(bool)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.switchButton = SwitchButton(self.tr("Off"), self, IndicatorPosition.RIGHT)

        if configItem:
            self.setValue(self.qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """switch button checked state changed slot"""
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)

    def setValue(self, isChecked: bool):
        if self.configItem:
            self.qconfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText(self.tr("On") if isChecked else self.tr("Off"))

    def setChecked(self, isChecked: bool):
        self.setValue(isChecked)

    def isChecked(self):
        return self.switchButton.isChecked()


class RangeSettingCard(SettingCard):
    """Setting card with a slider"""

    valueChanged = Signal(int)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.slider = Slider(Qt.Horizontal, self)
        self.valueLabel = QLabel(self)
        self.slider.setMinimumWidth(268)

        self.slider.setSingleStep(1)
        self.slider.setRange(*configItem.range)
        self.slider.setValue(configItem.value)
        self.valueLabel.setNum(configItem.value)

        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.valueLabel, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(6)
        self.hBoxLayout.addWidget(self.slider, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.valueLabel.setObjectName("valueLabel")
        configItem.valueChanged.connect(self.setValue)
        self.slider.valueChanged.connect(self.__onValueChanged)

    def __onValueChanged(self, value: int):
        """slider value changed slot"""
        self.setValue(value)
        self.valueChanged.emit(value)

    def setValue(self, value):
        self.qconfig.set(self.configItem, value)
        self.valueLabel.setNum(value)
        self.valueLabel.adjustSize()
        self.slider.setValue(value)


class ComboBoxSettingCard(SettingCard):
    """Setting card with a combo box"""

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        texts: List[str],
        qconfig: QConfig,
        configItem: OptionsConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.comboBox = ComboBox(self)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.optionToText = {o: t for o, t in zip(configItem.options, texts)}
        for text, option in zip(texts, configItem.options):
            self.comboBox.addItem(text, userData=option)

        self.comboBox.setCurrentText(self.optionToText[self.qconfig.get(configItem)])
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        configItem.valueChanged.connect(self.setValue)

    def _onCurrentIndexChanged(self, index: int):

        self.qconfig.set(self.configItem, self.comboBox.itemData(index))

    def setValue(self, value):
        if value not in self.optionToText:
            return

        self.comboBox.setCurrentText(self.optionToText[value])
        self.qconfig.set(self.configItem, value)


class LineEditSettingCard(SettingCard):
    """Setting card with LineEdit"""

    textChanged = Signal(str)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        text: str,
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.LineEdit = LineEdit(self)
        self.LineEdit.setMinimumWidth(250)
        self.LineEdit.setPlaceholderText(text)

        if configItem:
            self.setValue(self.qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        self.hBoxLayout.addWidget(self.LineEdit, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.LineEdit.textChanged.connect(self.__textChanged)

    def __textChanged(self, content: str):
        self.setValue(content.strip())
        self.textChanged.emit(content.strip())

    def setValue(self, content: str):
        if self.configItem:
            self.qconfig.set(self.configItem, content.strip())

        self.LineEdit.setText(content.strip())


class PasswordLineEditSettingCard(SettingCard):
    """Setting card with PasswordLineEdit"""

    textChanged = Signal()

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        text: str,
        algorithm: str,
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.algorithm = algorithm
        self.qconfig = qconfig
        self.configItem = configItem
        self.LineEdit = PasswordLineEdit(self)
        self.LineEdit.setMinimumWidth(200)
        self.LineEdit.setPlaceholderText(text)
        if algorithm == "AUTO":
            self.LineEdit.setViewPasswordButtonVisible(False)
        self.if_setValue = False

        if configItem:
            self.setValue(self.qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        self.hBoxLayout.addWidget(self.LineEdit, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.LineEdit.textChanged.connect(self.__textChanged)

    def __textChanged(self, content: str):

        if self.if_setValue:
            return None

        if self.algorithm == "DPAPI":
            self.setValue(Crypto.win_encryptor(content))
        elif self.algorithm == "AUTO":
            self.setValue(Crypto.AUTO_encryptor(content))
        self.textChanged.emit()

    def setValue(self, content: str):

        self.if_setValue = True

        if self.configItem:
            self.qconfig.set(self.configItem, content)

        if self.algorithm == "DPAPI":
            self.LineEdit.setText(Crypto.win_decryptor(content))
        elif self.algorithm == "AUTO":
            if Crypto.check_PASSWORD(Config.PASSWORD):
                self.LineEdit.setText(Crypto.AUTO_decryptor(content, Config.PASSWORD))
                self.LineEdit.setPasswordVisible(True)
                self.LineEdit.setReadOnly(False)
            elif Config.PASSWORD:
                self.LineEdit.setText("管理密钥错误")
                self.LineEdit.setPasswordVisible(True)
                self.LineEdit.setReadOnly(True)
            else:
                self.LineEdit.setText("************")
                self.LineEdit.setPasswordVisible(False)
                self.LineEdit.setReadOnly(True)

        self.if_setValue = False


class UserLableSettingCard(SettingCard):
    """Setting card with User's Lable"""

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        qconfig: QConfig,
        configItems: Dict[str, ConfigItem],
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItems = configItems
        self.Lable = SubtitleLabel(self)

        if configItems:
            for configItem in configItems.values():
                configItem.valueChanged.connect(self.setValue)
            self.setValue()

        self.hBoxLayout.addWidget(self.Lable, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

    def setValue(self):
        if self.configItems:

            text_list = []
            if not self.qconfig.get(self.configItems["IfPassCheck"]):
                text_list.append("未通过人工排查")
            text_list.append(
                f"今日已代理{self.qconfig.get(self.configItems["ProxyTimes"])}次"
                if Config.server_date()
                == self.qconfig.get(self.configItems["LastProxyDate"])
                else "今日未进行代理"
            )
            text_list.append(
                "本周剿灭已完成"
                if datetime.strptime(
                    self.qconfig.get(self.configItems["LastAnnihilationDate"]),
                    "%Y-%m-%d",
                ).isocalendar()[:2]
                == datetime.strptime(Config.server_date(), "%Y-%m-%d").isocalendar()[:2]
                else "本周剿灭未完成"
            )

        self.Lable.setText(" | ".join(text_list))


class PushAndSwitchButtonSettingCard(SettingCard):
    """Setting card with push & switch button"""

    checkedChanged = Signal(bool)
    clicked = Signal()

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        text: str,
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.switchButton = SwitchButton("关", self, IndicatorPosition.RIGHT)
        self.button = PushButton(text, self)
        self.hBoxLayout.addWidget(self.button, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)
        self.button.clicked.connect(self.clicked)

        if configItem:
            self.setValue(self.qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        # add switch button to layout
        self.hBoxLayout.addWidget(self.switchButton, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.switchButton.checkedChanged.connect(self.__onCheckedChanged)

    def __onCheckedChanged(self, isChecked: bool):
        """switch button checked state changed slot"""
        self.setValue(isChecked)
        self.checkedChanged.emit(isChecked)

    def setValue(self, isChecked: bool):
        if self.configItem:
            self.qconfig.set(self.configItem, isChecked)

        self.switchButton.setChecked(isChecked)
        self.switchButton.setText("开" if isChecked else "关")


class SpinBoxSettingCard(SettingCard):
    """Setting card with SpinBox"""

    textChanged = Signal(int)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        range: tuple[int, int],
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.SpinBox = SpinBox(self)
        self.SpinBox.setRange(range[0], range[1])
        self.SpinBox.setMinimumWidth(150)

        if configItem:
            self.setValue(qconfig.get(configItem))
            configItem.valueChanged.connect(self.setValue)

        self.hBoxLayout.addWidget(self.SpinBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.SpinBox.valueChanged.connect(self.__valueChanged)

    def __valueChanged(self, value: int):
        self.setValue(value)
        self.textChanged.emit(value)

    def setValue(self, value: int):
        if self.configItem:
            self.qconfig.set(self.configItem, value)

        self.SpinBox.setValue(value)


class NoOptionComboBoxSettingCard(SettingCard):

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        value: List[str],
        texts: List[str],
        qconfig: QConfig,
        configItem: OptionsConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.comboBox = ComboBox(self)
        self.comboBox.setMinimumWidth(250)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.optionToText = {o: t for o, t in zip(value, texts)}
        for text, option in zip(texts, value):
            self.comboBox.addItem(text, userData=option)

        self.comboBox.setCurrentText(self.optionToText[self.qconfig.get(configItem)])
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        configItem.valueChanged.connect(self.setValue)

    def _onCurrentIndexChanged(self, index: int):

        self.qconfig.set(self.configItem, self.comboBox.itemData(index))

    def setValue(self, value):
        if value not in self.optionToText:
            return

        self.comboBox.setCurrentText(self.optionToText[value])
        self.qconfig.set(self.configItem, value)

    def reLoadOptions(self, value: List[str], texts: List[str]):

        self.comboBox.currentIndexChanged.disconnect()
        self.comboBox.clear()
        self.optionToText = {o: t for o, t in zip(value, texts)}
        for text, option in zip(texts, value):
            self.comboBox.addItem(text, userData=option)
        self.comboBox.setCurrentText(
            self.optionToText[self.qconfig.get(self.configItem)]
        )
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)


class EditableComboBoxSettingCard(SettingCard):
    """Setting card with EditableComboBox"""

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        value: List[str],
        texts: List[str],
        qconfig: QConfig,
        configItem: OptionsConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.comboBox = self._EditableComboBox(self)
        self.comboBox.setMinimumWidth(100)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.optionToText = {o: t for o, t in zip(value, texts)}
        for text, option in zip(texts, value):
            self.comboBox.addItem(text, userData=option)

        if qconfig.get(configItem) not in self.optionToText:
            self.optionToText[qconfig.get(configItem)] = qconfig.get(configItem)
            self.comboBox.addItem(
                qconfig.get(configItem), userData=qconfig.get(configItem)
            )

        self.comboBox.setCurrentText(self.optionToText[qconfig.get(configItem)])
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)
        configItem.valueChanged.connect(self.setValue)

    def _onCurrentIndexChanged(self, index: int):

        self.qconfig.set(
            self.configItem,
            (
                self.comboBox.itemData(index)
                if self.comboBox.itemData(index)
                else self.comboBox.itemText(index)
            ),
        )

    def setValue(self, value):
        if value not in self.optionToText:
            self.optionToText[value] = value
            if self.comboBox.findText(value) == -1:
                self.comboBox.addItem(value, userData=value)
            else:
                self.comboBox.setItemData(self.comboBox.findText(value), value)

        self.comboBox.setCurrentText(self.optionToText[value])
        self.qconfig.set(self.configItem, value)

    def reLoadOptions(self, value: List[str], texts: List[str]):

        self.comboBox.currentIndexChanged.disconnect()
        self.comboBox.clear()
        self.optionToText = {o: t for o, t in zip(value, texts)}
        for text, option in zip(texts, value):
            self.comboBox.addItem(text, userData=option)
        if self.qconfig.get(self.configItem) not in self.optionToText:
            self.optionToText[self.qconfig.get(self.configItem)] = self.qconfig.get(
                self.configItem
            )
            self.comboBox.addItem(
                self.qconfig.get(self.configItem),
                userData=self.qconfig.get(self.configItem),
            )
        self.comboBox.setCurrentText(
            self.optionToText[self.qconfig.get(self.configItem)]
        )
        self.comboBox.currentIndexChanged.connect(self._onCurrentIndexChanged)

    class _EditableComboBox(EditableComboBox):
        """EditableComboBox"""

        def __init__(self, parent=None):
            super().__init__(parent)

        def _onReturnPressed(self):
            if not self.text():
                return

            index = self.findText(self.text())
            if index >= 0 and index != self.currentIndex():
                self._currentIndex = index
                self.currentIndexChanged.emit(index)
            elif index == -1:
                self.addItem(self.text())
                self.setCurrentIndex(self.count() - 1)
                self.currentIndexChanged.emit(self.count() - 1)


class TimeEditSettingCard(SettingCard):

    enabledChanged = Signal(bool)
    timeChanged = Signal(str)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        qconfig: QConfig,
        configItem_bool: ConfigItem,
        configItem_time: ConfigItem,
        parent=None,
    ):

        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem_bool = configItem_bool
        self.configItem_time = configItem_time
        self.CheckBox = CheckBox(self)
        self.CheckBox.setTristate(False)
        self.TimeEdit = TimeEdit(self)
        self.TimeEdit.setDisplayFormat("HH:mm")
        self.TimeEdit.setMinimumWidth(150)

        if configItem_bool:
            self.setValue_bool(qconfig.get(configItem_bool))
            configItem_bool.valueChanged.connect(self.setValue_bool)

        if configItem_time:
            self.setValue_time(qconfig.get(configItem_time))
            configItem_time.valueChanged.connect(self.setValue_time)

        self.hBoxLayout.addWidget(self.CheckBox, 0, Qt.AlignRight)
        self.hBoxLayout.addWidget(self.TimeEdit, 0, Qt.AlignRight)
        self.hBoxLayout.addSpacing(16)

        self.CheckBox.stateChanged.connect(self.__enableChanged)
        self.TimeEdit.timeChanged.connect(self.__timeChanged)

    def __timeChanged(self, value: QTime):
        self.setValue_time(value.toString("HH:mm"))
        self.timeChanged.emit(value.toString("HH:mm"))

    def __enableChanged(self, value: int):
        if value == 0:
            self.setValue_bool(False)
            self.enabledChanged.emit(False)
        else:
            self.setValue_bool(True)
            self.enabledChanged.emit(True)

    def setValue_bool(self, value: bool):
        if self.configItem_bool:
            self.qconfig.set(self.configItem_bool, value)

        self.CheckBox.setChecked(value)

    def setValue_time(self, value: str):
        if self.configItem_time:
            self.qconfig.set(self.configItem_time, value)

        self.TimeEdit.setTime(QTime.fromString(value, "HH:mm"))


class UrlItem(QWidget):
    """Url item"""

    removed = Signal(QWidget)

    def __init__(self, url: str, parent=None):
        super().__init__(parent=parent)
        self.url = url
        self.hBoxLayout = QHBoxLayout(self)
        self.folderLabel = QLabel(url, self)
        self.removeButton = ToolButton(FluentIcon.CLOSE, self)

        self.removeButton.setFixedSize(39, 29)
        self.removeButton.setIconSize(QSize(12, 12))

        self.setFixedHeight(53)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.hBoxLayout.setContentsMargins(48, 0, 60, 0)
        self.hBoxLayout.addWidget(self.folderLabel, 0, Qt.AlignLeft)
        self.hBoxLayout.addSpacing(16)
        self.hBoxLayout.addStretch(1)
        self.hBoxLayout.addWidget(self.removeButton, 0, Qt.AlignRight)
        self.hBoxLayout.setAlignment(Qt.AlignVCenter)

        self.removeButton.clicked.connect(lambda: self.removed.emit(self))


class UrlListSettingCard(ExpandSettingCard):
    """Url list setting card"""

    urlChanged = Signal(list)

    def __init__(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        title: str,
        content: Union[str, None],
        qconfig: QConfig,
        configItem: ConfigItem,
        parent=None,
    ):
        super().__init__(icon, title, content, parent)
        self.qconfig = qconfig
        self.configItem = configItem
        self.addUrlButton = PushButton("添加代理网址", self)

        self.urls: List[str] = self.qconfig.get(configItem).copy()
        self.__initWidget()

    def __initWidget(self):
        self.addWidget(self.addUrlButton)

        # initialize layout
        self.viewLayout.setSpacing(0)
        self.viewLayout.setAlignment(Qt.AlignTop)
        self.viewLayout.setContentsMargins(0, 0, 0, 0)
        for url in self.urls:
            self.__addUrlItem(url)

        self.addUrlButton.clicked.connect(self.__showUrlDialog)

    def __showUrlDialog(self):
        """show url dialog"""

        choice = LineEditMessageBox(
            self.window(), "添加代理网址", "请输入代理网址", "明文"
        )
        if choice.exec() and self.__validate(choice.input.text()):

            if choice.input.text()[-1] == "/":
                url = choice.input.text()
            else:
                url = f"{choice.input.text()}/"

            if url in self.urls:
                return

            self.__addUrlItem(url)
            self.urls.append(url)
            self.qconfig.set(self.configItem, self.urls)
            self.urlChanged.emit(self.urls)

    def __addUrlItem(self, url: str):
        """add url item"""
        item = UrlItem(url, self.view)
        item.removed.connect(self.__showConfirmDialog)
        self.viewLayout.addWidget(item)
        item.show()
        self._adjustViewSize()

    def __showConfirmDialog(self, item: UrlItem):
        """show confirm dialog"""

        choice = MessageBox(
            "确认",
            f"确定要删除 {item.url} 代理网址吗？",
            self.window(),
        )
        if choice.exec():
            self.__removeUrl(item)

    def __removeUrl(self, item: UrlItem):
        """remove folder"""
        if item.url not in self.urls:
            return

        self.urls.remove(item.url)
        self.viewLayout.removeWidget(item)
        item.deleteLater()
        self._adjustViewSize()

        self.urlChanged.emit(self.urls)
        self.qconfig.set(self.configItem, self.urls)

    def __validate(self, value):

        try:
            result = urlparse(value)
            return all([result.scheme, result.netloc])
        except ValueError:
            return False


class StatefulItemCard(CardWidget):

    def __init__(self, item: list, parent=None):
        super().__init__(parent)

        self.Layout = QHBoxLayout(self)

        self.Label = BodyLabel(item[0], self)
        self.icon = IconWidget(FluentIcon.MORE, self)
        self.icon.setFixedSize(16, 16)
        self.update_status(item[1])

        self.Layout.addWidget(self.icon)
        self.Layout.addWidget(self.Label)
        self.Layout.addStretch(1)

    def update_status(self, status: str):

        if status == "完成":
            self.icon.setIcon(FluentIcon.ACCEPT)
            self.Label.setTextColor("#0eb840", "#0eb840")
        elif status == "等待":
            self.icon.setIcon(FluentIcon.MORE)
            self.Label.setTextColor("#161823", "#e3f9fd")
        elif status == "运行":
            self.icon.setIcon(FluentIcon.PLAY)
            self.Label.setTextColor("#177cb0", "#70f3ff")
        elif status == "跳过":
            self.icon.setIcon(FluentIcon.REMOVE)
            self.Label.setTextColor("#75878a", "#7397ab")
        elif status == "异常":
            self.icon.setIcon(FluentIcon.CLOSE)
            self.Label.setTextColor("#ff2121", "#ff2121")


class QuantifiedItemCard(CardWidget):

    def __init__(self, item: list, parent=None):
        super().__init__(parent)

        self.Layout = QHBoxLayout(self)

        self.Name = BodyLabel(item[0], self)
        self.Numb = BodyLabel(str(item[1]), self)

        self.Layout.addWidget(self.Name)
        self.Layout.addStretch(1)
        self.Layout.addWidget(self.Numb)


class IconButton(TransparentToolButton):
    """包含下拉框的自定义设置卡片类。"""

    @singledispatchmethod
    def __init__(self, parent: QWidget = None):
        TransparentToolButton.__init__(self, parent)

        self._tooltip: Optional[TeachingTip] = None

    @__init__.register
    def _(self, icon: Union[str, QIcon, FluentIconBase], parent: QWidget = None):
        self.__init__(parent)
        self.setIcon(icon)

    @__init__.register
    def _(
        self,
        icon: Union[str, QIcon, FluentIconBase],
        isTooltip: bool,
        tip_title: str,
        tip_content: Union[str, None],
        parent: QWidget = None,
    ):
        self.__init__(parent)
        self.setIcon(icon)

        # 处理工具提示
        if isTooltip:
            self.installEventFilter(self)

        self.tip_title: str = tip_title
        self.tip_content: str = tip_content

    def eventFilter(self, obj, event: QEvent) -> bool:
        """处理鼠标事件。"""
        if event.type() == QEvent.Type.Enter:
            self._show_tooltip()
        elif event.type() == QEvent.Type.Leave:
            self._hide_tooltip()
        return super().eventFilter(obj, event)

    def _show_tooltip(self) -> None:
        """显示工具提示。"""
        self._tooltip = TeachingTip.create(
            target=self,
            title=self.tip_title,
            content=self.tip_content,
            tailPosition=TeachingTipTailPosition.RIGHT,
            isClosable=False,
            duration=-1,
            parent=self,
        )
        # 设置偏移
        if self._tooltip:
            tooltip_pos = self.mapToGlobal(self.rect().topRight())

            tooltip_pos.setX(
                tooltip_pos.x() - self._tooltip.size().width() - 40
            )  # 水平偏移
            tooltip_pos.setY(
                tooltip_pos.y() - self._tooltip.size().height() / 2 + 35
            )  # 垂直偏移

            self._tooltip.move(tooltip_pos)

    def _hide_tooltip(self) -> None:
        """隐藏工具提示。"""
        if self._tooltip:
            self._tooltip.close()
            self._tooltip = None

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self is other


class Banner(QWidget):
    """展示带有圆角的固定大小横幅小部件"""

    def __init__(self, image_path: str = None, parent=None):
        QWidget.__init__(self, parent)
        self.image_path = None
        self.banner_image = None
        self.scaled_image = None

        if image_path:
            self.set_banner_image(image_path)

    def set_banner_image(self, image_path: str):
        """设置横幅图片"""
        self.image_path = image_path
        self.banner_image = self.load_banner_image(image_path)
        self.update_scaled_image()

    def load_banner_image(self, image_path: str) -> QPixmap:
        """加载横幅图片，或创建渐变备用图片"""
        if os.path.isfile(image_path):
            return QPixmap(image_path)
        return self._create_fallback_image()

    def _create_fallback_image(self):
        """创建渐变备用图片"""
        fallback_image = QPixmap(2560, 1280)  # 使用原始图片的大小
        fallback_image.fill(Qt.GlobalColor.gray)
        return fallback_image

    def update_scaled_image(self):
        """按高度缩放图片，宽度保持比例，超出裁剪"""
        if self.banner_image:
            self.scaled_image = self.banner_image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.update()

    def paintEvent(self, event):
        """重载 paintEvent 以绘制缩放后的图片"""
        if self.scaled_image:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

            # 创建圆角路径
            path = QPainterPath()
            path.addRoundedRect(self.rect(), 20, 20)
            painter.setClipPath(path)

            # 计算绘制位置，使图片居中
            x = (self.width() - self.scaled_image.width()) // 2
            y = (self.height() - self.scaled_image.height()) // 2

            # 绘制缩放后的图片
            painter.drawPixmap(x, y, self.scaled_image)

    def resizeEvent(self, event):
        """重载 resizeEvent 以更新缩放后的图片"""
        self.update_scaled_image()
        QWidget.resizeEvent(self, event)

    def set_percentage_size(self, width_percentage, height_percentage):
        """设置 Banner 的大小为窗口大小的百分比"""
        parent = self.parentWidget()
        if parent:
            new_width = int(parent.width() * width_percentage)
            new_height = int(parent.height() * height_percentage)
            self.setFixedSize(new_width, new_height)
            self.update_scaled_image()
