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

"""Emulator 2.0 的「大雷主人模式」。

沿用全局 ``Function.IfBlockAd`` 开关，启动时应用或恢复设置；失败只记警告。
雷电使用安装级 ``globalsetting --cleanmode``，VM 冷启动后生效，游戏中心仍可打开。
MuMu 处理宿主缓存及五个桌面组件，关闭时撤销占位并恢复组件；组件状态跨重启保留。
``MuMuManager sh`` 不要求开启 ``root_permission``；组件必须用 ``pm disable``，
``pm disable-user`` 会静默返回 default，不能代替。
"""

import os
import shutil
from pathlib import Path

from app.utils import get_logger

logger = get_logger("Emulator2 大雷主人模式")

#: MuMu 6 商店包名与模式管理的五个桌面组件。
MUMU_STORE_PACKAGE = "com.mumu.store"
MUMU_MODE_COMPONENTS: tuple[str, ...] = (
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


def is_master_mode_enabled() -> bool:
    """从旧版全局开关读取「大雷主人模式」状态，读取失败按关闭处理。"""
    try:
        from app.core import Config

        return bool(Config.get("Function", "IfBlockAd"))
    except Exception as e:  # noqa: BLE001 - 配置层的问题不该拖垮启动
        logger.warning(f"读取「大雷主人模式」配置失败，按关闭处理: {e}")
        return False


# ---- 雷电 ----------------------------------------------------------------


def ldplayer_clean_mode_args(enabled: bool) -> tuple[str, ...]:
    """``ldconsole globalsetting --cleanmode 1|0`` 的参数。"""
    return ("globalsetting", "--cleanmode", "1" if enabled else "0")


# ---- MuMu：安卓端 ----------------------------------------------------------


def mumu_component_shell(enabled: bool) -> str:
    """一条 ``sh -c`` 里把五个组件一起禁用 / 启用。

    合成一条是为了只起一次 ``NemuShell.exe``：它连不上就无限重试，起五次就有五次机会卡住。
    """
    verb = "pm disable --user 0" if enabled else "pm enable"
    return "; ".join(
        f"{verb} {MUMU_STORE_PACKAGE}/{component}" for component in MUMU_MODE_COMPONENTS
    )


def mumu_component_applied(output: str, enabled: bool) -> bool:
    """从 ``pm disable`` / ``pm enable`` 的合并输出判断五条是否都落了。

    ``pm`` 每条成功都会打 ``new state: disabled``（或 ``enabled``）；少一条就是有组件没处理到。
    """
    wanted = "new state: disabled" if enabled else "new state: enabled"
    return output.count(wanted) >= len(MUMU_MODE_COMPONENTS)


# ---- MuMu：Windows 侧占位 --------------------------------------------------


def mumu_splash_placeholder_paths(appdata: Path | None = None) -> list[Path]:
    """MuMu 6 在 Windows 侧需要处理的两个启动缓存目录。"""
    base = appdata if appdata is not None else Path(os.getenv("APPDATA") or "")
    data = base / "Netease" / "MuMuPlayer" / "data"
    return [data / "startupImage", data / "ProgramAds"]


def apply_splash_placeholders(paths: list[Path], enabled: bool) -> None:
    """占位或撤销占位。

    开着：目录整个删掉、原地放一个同名空文件，MuMu 就写不进缓存图；实测它启动时不会把文件
    改回目录，也不报错。关着：只删我们放的那个空文件，目录让 MuMu 自己重建。
    任何一处失败只记警告，继续处理下一处。
    """
    for path in paths:
        try:
            if enabled:
                if path.is_dir():
                    shutil.rmtree(path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()
            elif path.is_file():
                path.unlink()
        except OSError as e:
            logger.warning(f"处理「大雷主人模式」缓存占位失败 {path}: {e}")
