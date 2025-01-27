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
AUTO_MAA主程序
v4.2
作者：DLmaster_361
"""

from loguru import logger
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from qfluentwidgets import FluentTranslator
import sys


# @logger.catch
def main():

    application = QApplication(sys.argv)
    QApplication.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)

    translator = FluentTranslator()
    application.installTranslator(translator)

    from app.ui.main_window import AUTO_MAA

    window = AUTO_MAA()
    window.show_ui("显示主窗口")
    window.start_up_task()
    sys.exit(application.exec())


if __name__ == "__main__":

    main()
