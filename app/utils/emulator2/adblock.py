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

"""Emulator 2.0 的「屏蔽广告」：两家各自实测有效的那几步，纯逻辑部分放这里。

全局开关是 ``Config.get("Function", "IfBlockAd")``，两家后端在启动流程里读它，
开着就做、关着就还原。所有步骤都**只记警告不抛异常**：广告去不掉不该让模拟器启动失败。

雷电 14
    官方纯净模式 ``ldconsole globalsetting --cleanmode 1``。它是**整个安装全局**的，
    宿主在 **VM 冷启动**时把它作为系统属性 ``phone.cleanmode`` 推进客户机，launcher 据此
    不再构建顶栏搜索条、底部推广栏和首屏推广，并把游戏中心图标从桌面过滤掉（包没禁，
    界面上的「打开游戏中心」按钮照常能拉起）。实例跑着的时候翻开关没有反应，所以只在
    启动前设置一次。早先「纯净模式无效」的结论是当时没冷启动 VM，见去广告实验记录。

MuMu 6
    安卓端四类广告（顶栏搜索条、全屏弹窗、两块桌面 widget）都由商店包 ``com.mumu.store``
    的组件承载或触发，用 ``MuMuManager sh``（uid=0 的 root 通道，**不需要**打开
    ``root_permission``）``pm disable`` 五个组件即可，商店本身保留、跨重启保留、``pm enable``
    可逆。其中 ``LoginServerReceiver`` 是 launcher 查会员状态的应答方，禁掉之后 launcher
    收不到回复、按「会员」处理而藏起顶栏和弹窗。对组件必须用 ``pm disable``：
    ``pm disable-user`` 对组件会静默返回 ``new state: default``，等于没做。
    Windows 侧开屏广告与小程序弹窗落在 ``%APPDATA%\\Netease\\MuMuPlayer\\data`` 下两个目录，
    删目录、建同名空文件占位即可（与旧配置的 ``EMULATOR_SPLASH_ADS_PATH_BOOK`` 同一手法）。
"""

import os
import shutil
from pathlib import Path

from app.utils import get_logger

logger = get_logger("Emulator2 屏蔽广告")

#: MuMu 6 商店包名与要禁用的五个组件（四个桌面广告 widget 的 provider + 会员状态应答器）。
MUMU_STORE_PACKAGE = "com.mumu.store"
MUMU_AD_COMPONENTS: tuple[str, ...] = (
    "com.mumu.store.widget.appWidgetProvider.AdBannerWidgetProvider",
    "com.mumu.store.widget.appWidgetProvider.DailyDiscoveryWidgetProvider",
    "com.mumu.store.widget.appWidgetProvider.HotActivityWidgetProvider",
    "com.mumu.store.widget.appWidgetProvider.FlashSaleWidgetProvider",
    "com.mumu.login_handler.LoginServerReceiver",
)

#: MuMu 6 的安卓桌面（魔改 Lawnchair）。组件状态变了之后要重启它才会重画。
MUMU_LAUNCHER_PACKAGE = "app.lawnchair"

#: 一条 ``MuMuManager sh`` 最多等多久。它底层的 ``NemuShell.exe`` 连不上管道会**无限重试**，
#: 见过一次卡死，所以必须带超时；正常一批 pm 命令一两秒就完。
MUMU_SH_TIMEOUT = 20.0

#: ``MuMuManager sh`` 超时后要顺手清掉的孤儿进程名。
MUMU_SH_HELPER_IMAGE = "NemuShell.exe"


def is_block_ad_enabled() -> bool:
    """读全局「屏蔽广告」开关。读不到按关处理，并记一条警告。"""
    try:
        from app.core import Config

        return bool(Config.get("Function", "IfBlockAd"))
    except Exception as e:  # noqa: BLE001 - 配置层的问题不该拖垮启动
        logger.warning(f"读取「屏蔽广告」开关失败，按关闭处理: {e}")
        return False


# ---- 雷电 ----------------------------------------------------------------


def ldplayer_clean_mode_args(block: bool) -> tuple[str, ...]:
    """``ldconsole globalsetting --cleanmode 1|0`` 的参数。"""
    return ("globalsetting", "--cleanmode", "1" if block else "0")


# ---- MuMu：安卓端 ----------------------------------------------------------


def mumu_component_shell(block: bool) -> str:
    """一条 ``sh -c`` 里把五个组件一起禁用 / 启用。

    合成一条是为了只起一次 ``NemuShell.exe``：它连不上就无限重试，起五次就有五次机会卡住。
    """
    verb = "pm disable --user 0" if block else "pm enable"
    return "; ".join(
        f"{verb} {MUMU_STORE_PACKAGE}/{component}" for component in MUMU_AD_COMPONENTS
    )


def mumu_component_applied(output: str, block: bool) -> bool:
    """从 ``pm disable`` / ``pm enable`` 的合并输出判断五条是否都落了。

    ``pm`` 每条成功都会打 ``new state: disabled``（或 ``enabled``）；少一条就是有组件没处理到。
    """
    wanted = "new state: disabled" if block else "new state: enabled"
    return output.count(wanted) >= len(MUMU_AD_COMPONENTS)


# ---- MuMu：Windows 侧占位 --------------------------------------------------


def mumu_splash_placeholder_paths(appdata: Path | None = None) -> list[Path]:
    """MuMu 6 在 Windows 侧缓存开屏广告与小程序弹窗的两个目录。"""
    base = appdata if appdata is not None else Path(os.getenv("APPDATA") or "")
    data = base / "Netease" / "MuMuPlayer" / "data"
    return [data / "startupImage", data / "ProgramAds"]


def apply_splash_placeholders(paths: list[Path], block: bool) -> None:
    """占位或撤销占位。

    开着：目录整个删掉、原地放一个同名空文件，MuMu 就写不进缓存图；实测它启动时不会把文件
    改回目录，也不报错。关着：只删我们放的那个空文件，目录让 MuMu 自己重建。
    任何一处失败只记警告，继续处理下一处。
    """
    for path in paths:
        try:
            if block:
                if path.is_dir():
                    shutil.rmtree(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            elif path.is_file():
                path.unlink()
        except OSError as e:
            logger.warning(f"处理开屏广告占位失败 {path}: {e}")
