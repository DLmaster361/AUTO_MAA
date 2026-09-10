# 更新日志

本项目所有值得注意的变更都记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循[语义化版本](https://semver.org/lang/zh-CN/spec/v2.0.0.html)。

<!--
  本文件是更新日志与版本号的唯一手写来源，请不要手改 res/version.json 等生成物。

  - 文件顶部第一个 `## [vX.Y.Z] - 未发布` 标题即当前尚未发布的版本号，新条目写进它下面。
  - 每个 PR 都要在这里登记一条，写在最贴切的分类下；分类不存在就新建一个 `###`。
  - 条目写成一行，`- ` 开头，从用户视角描述这次改动带来了什么。
  - 不要手写 ` by [@用户](链接)` 署名，PR 合并后由机器人补。
  - 改完运行 `python scripts/changelog.py sync`，它会同步各处版本号、规范化本文件、
    并重新生成底部的版本对比链接。

  分类含义（中间六类来自 Keep a Changelog）：

  - 破坏性变更：需要用户动手确认或会改变既有行为的改动，在更新提示里最醒目地展示。
  - 本次亮点：这一版最值得一看的三五条，正文仍写在下面对应的分类里。
  - 新增：新添加的功能。
  - 变更：对现有功能的变更，含优化与调整。
  - 弃用：已经不建议使用、即将移除的功能。
  - 移除：已经移除的功能。
  - 修复：对 bug 的修复。
  - 安全：对安全性的改进。
  - 开发流程：只影响贡献者、用户看不见的改动。
-->

## [v5.5.0-beta.4] - 未发布

### 新增

- 绝区零一条龙专项 用户卡片新增「用户模式/直控模式」来源、区服、账号尾号与一条龙任务数标签，并修复 MaaFW 专项用户卡片不显示任何标签的问题 by [@AthenaHibou](https://github.com/AthenaHibou)
- MFW专项 使用模拟器时可顺带把游戏一起打开（包名自动识别或手动填写），任务前后自定义脚本改为每用户各跑一次、不再随重试重复

### 变更

- 全局设置 虚拟显示器改为常驻监测：运行期间检测不到真实显示输出自动挂上，恢复后自动拆掉（任务运行中等结束再拆）；说明里可直接点开 Parsec 驱动下载页 by [@qiyinxi](https://github.com/qiyinxi)
- 日志清理 MFW 项目的 MaaFramework 原生日志备份改为按保留天数一并清理，不再无限堆积

### 修复

- 调度队列 修复任务完成后没有执行设定的关机、重启等电源操作，倒计时结束后只有软件退出的问题
- 修复绝区零一条龙由 MAS 启动时报「运行环境同步失败」，且自动模式失败后不切换启动器的问题
- 修复配了网络代理的用户初始化下载仍直连、卡在「程序文件」一步的问题 by [@qiyinxi](https://github.com/qiyinxi)
- HSR专项 修复系统区域非中文时三月七助手每个模块被判失败、整轮重复运行的问题
- 修复 MFW、M9A、HSR 与主页的一批问题：多项设置从未生效、MFW 更新不上、HSR 周常与历战余响提前翻页、重返未来 1999 倒计时偏移、国内下载源缺分支导致初始化失败
- 修复后端就绪前退出时只能反复重试的问题，现同时提供「重建运行环境」入口 by [@qiyinxi](https://github.com/qiyinxi)
- MAA专项 修复未返回分服关卡数据时用户配置页打不开的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 模拟器管理 修复部分 MuMu 因命令输出混有日志而无法读取信息的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MFW专项 修复运行环境准备时 Agent 依赖不走镜像、直连 PyPI 导致「隔离 venv 依赖安装失败」的问题，现按镜像依次重试；失败原因也会写进日志并显示在提示条上，不再只有一句准备失败
- MFW专项 修复 beta.4 下 MFW 脚本完全无法运行、一开跑就报「MaaFW runner worker exited without result」并提示缺少 loguru 的问题
- MFW专项 修复 agent 运行环境装到与项目自带 MaaFramework 不匹配的 maafw 版本，导致每次运行都卡在「AgentClient 连接超时」的问题；已经装错的环境会自动重建一次

### 开发流程

- 首页卫星图标改从全局图标表取，新增专项时不再漏掉主页卫星

## [v5.5.0-beta.3] - 2026-09-09

### 破坏性变更

- 森空岛获取凭据改为扫码登录，完善社区签到、云游戏时长与日常便笺 by [@Lance0174](https://github.com/Lance0174)
- MFW 项目新增自动更新时机设置，升级后**已有脚本默认「运行前更新」**；不需要可改成「不更新」 by [@qiyinxi](https://github.com/qiyinxi)
- HSR 脚本页的「游戏启动参数」已移除，**旧配置下次保存时自动清除**；窗口大小改由「1920×1080 窗口模式」开关控制 by [@qiyinxi](https://github.com/qiyinxi)
- MAA 代理接管时**强制开启账号切换开关**以确保按配置切号；未填账号时不切号 by [@1w1w11w1](https://github.com/1w1w11w1)
- MAA、SRC、MaaEnd 与 OK-NTE 用户页配置模式**由「简洁/详细」更名为「脚本/用户」**，含义不变，自动迁移 by [@1w1w11w1](https://github.com/1w1w11w1)
- MAA 计划表不再强制关闭「库存保持」；此前开启过的升级后自动生效，**库存保持先于理智作战执行**，不需要请关闭 by [@jinghero](https://github.com/jinghero)

### 本次亮点

- 新增绝区零一条龙（ZZZ-OD）专项，支持独立模式与直控模式
- 模拟器管理新增「Emulator 2.0」：一条配置纳管多个雷电 14 / MuMu 6 实例
- 调度队列新增循环队列，任务可按固定时间或间隔持续运行
- 启动速度大幅优化，启动与初始化等待画面重做
- 通知系统支持微信 Claw 与 QQ 官方机器人接收任务通知

### 新增

- 模拟器管理 新增「Emulator 2.0」配置类型：一条配置可纳管多个雷电 14 / MuMu 6 安装路径，两家的实例合并成一张设备表统一编号；支持新建与删除实例，分辨率（含 DPI）、CPU、内存、帧率的单台与批量设置，以及一键「稳定模式」关掉高帧率、后台保活等会干扰截图识别的功能；另有「配置守卫」，把你定的设置记成基准，启动前与关闭后各核验一次，被模拟器改掉就还原回来 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MaaEnd专项 新增脚本直控模式，抢委托送货与自动采集独立为可单独配置的阶段，用户配置页改为锚点导航加分区卡片布局 by [@HarcoChen](https://github.com/HarcoChen) by [@TCddddd](https://github.com/TCddddd)
- MaaEnd专项 支持为指定任务设置每日仅执行一次以缩短后续运行，并修复仅启用自动采集时任务无法启动 by [@HarcoChen](https://github.com/HarcoChen) by [@TCddddd](https://github.com/TCddddd)
- MFW 项目支持在脚本运行前或运行后自动更新，可在项目配置中选择时机；升级后已有脚本默认为「运行前更新」，不需要可在项目配置中改为「不更新」 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MAA专项 新增绿票商店开关：开启后每月单独启动一次 MAA 自动购买绿票商店，用户配置页可查看本月状态并手动重置 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 新增绝区零一条龙（ZZZ-OD）专项适配：支持用户独立模式与直控模式 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- 调度队列 新增循环队列：队列里的每个任务可单独设定固定时间或间隔重复运行，在调度台以「循环运行」启动后会按各自的周期一直跑下去，并显示接下来要运行的任务与时间 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-NTE专项 支持启动后按用户手机号后 4 位强制切换登录账号，并支持由 MAS 经启动器拉起异环游戏、避免卡界面，新增问题包一键导出便于反馈登录失败 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- MFW 项目更新可自行选择下载源（Mirror 酱 / GitHub）与更新通道（稳定版 / 测试版） by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 调度中心 选中脚本后可再指定一个用户单独运行，只代理该用户而不跑该脚本下的其他用户 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 调度队列 完成后操作可单独设定延时，关机、休眠等操作会在队列结束后先静默等待设定的时长，再照常弹出 60 秒倒计时 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 通知系统 支持扫码绑定微信 Claw 和 QQ 官方机器人并接收任务通知，绑定与启用状态保持独立，绑定失效或推送失败时会明确提示 by [@HarcoChen](https://github.com/HarcoChen) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 用户配置页新增「额外脚本」，可在该用户任务开始前与结束后各执行一个自定义脚本（exe / bat / cmd / py 等），MAS 管控与脚本直控两种模式均生效 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 首页 快速启动支持多选并记住上次选择，可一次启动多个任务 by [@Craun718](https://github.com/Craun718) by [@TCddddd](https://github.com/TCddddd)
- MAA专项 托管结束后保存 MAA 写入配置文件的每日状态（如借战赚信用与访问好友的当天执行记录），同一天多次托管不再重复执行 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- 全局设置 新增「虚拟显示器」：显示器断开或关闭后 Windows 只保留一块占位的幻影屏，它照旧上报一个看着正常的分辨率，但背后没有任何输出，游戏渲染与截图都可能不可靠；冷启动时更会直接起在很小的分辨率上，把游戏窗口压小并被游戏自己记住。开启后 MAS 在检测到没有任何真实显示输出时临时挂一块 1920x1080 的虚拟显示器，任务结束即拆除；程序若被强制结束，下次启动会自动清理上次遗留的虚拟显示器。刷新率可选 60Hz 或更省 GPU 的 30Hz，并提供驱动检测（需自行安装 Parsec 虚拟显示驱动，MAS 不附带驱动） by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 更新提示改为按版本分区块展示，「重要变更」与「本次亮点」置顶，并可在设置页随时查看当前版本的更新日志 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- BetterGI专项 用户编辑页一条龙配置改为可视化队列：左栏队列可拖拽排序并按所排顺序执行，战斗四项（地脉花 / 秘境 / 幽境危战 / 首领讨伐）各支持配置多个独立实例、分别保存与执行；同时修复队列里已关闭的任务仍被执行、右栏设置保存报错、地脉花按星期刷取却每天都跑、秘境每周表奖励档位不按所配星期下发，以及一条龙没有可执行的日常任务时卡住结束不了的问题 by [@TCddddd](https://github.com/TCddddd)

### 变更

- 启动界面 等待画面重做，只显示当前步骤与进度条，出错给出一句话原因和主要操作，取消 60 秒自动重试；大幅优化前端加载与启动速度 by [@qiyinxi](https://github.com/qiyinxi) by [@1w1w11w1](https://github.com/1w1w11w1)
- 首页 弱网/VPN 下活动数据异常不再拖累所有请求，单张卡异常只影响自身；快速启动后自动跳转调度中心 by [@1w1w11w1](https://github.com/1w1w11w1) by [@Craun718](https://github.com/Craun718)
- HSR专项 脚本直控不再要求先导入快照，默认使用 SRA/三月七当前配置；新增 SRA 配置档案下拉；「一键从源配置导入」改名「重置为源配置」并增加确认；管控任务配置项补齐中文名与说明；切换引擎时提示配置按引擎分存；体力副本未选择或引擎缺路径时在任务前提示 by [@qiyinxi](https://github.com/qiyinxi)
- HSR专项 用户页界面文案接入多语言词表，英文与日文不再夹杂中文 by [@qiyinxi](https://github.com/qiyinxi)
- 后端更新 自动在后台下载并于下次启动生效，失败时可修复依赖后重试 by [@ClozyA](https://github.com/ClozyA)
- Runtime 接入 开启 AUTO_MAS_RUNTIME_MODE 后由 auto-mas-runtime.exe 统一完成初始化、监督与更新 by [@qiyinxi](https://github.com/qiyinxi)
- 通用脚本 未填「配置路径」时在任务前直接提示，不再跑起来后才报错 by [@qiyinxi](https://github.com/qiyinxi)
- MFW专项 进入项目配置页不再每次等运行环境确认，环境准备提前到任务开始前完成 by [@qiyinxi](https://github.com/qiyinxi)
- 帮助入口 计划管理、模拟器管理、脚本管理及编辑页增加直达文档入口，链接随语言切换 by [@1w1w11w1](https://github.com/1w1w11w1)
- 日志清理 自动清理 OCR 图片 by [@HarcoChen](https://github.com/HarcoChen)
- 前端i18n BetterGI 编辑页与配置组件接入词表 by [@qiyinxi](https://github.com/qiyinxi)
- OK-WW专项 清理无效的游戏启动选项与空配置项 by [@1w1w11w1](https://github.com/1w1w11w1)
- 代码清理 统一导入排序、合并各脚本重复逻辑、清理死代码与无用组件，行为不变 by [@1w1w11w1](https://github.com/1w1w11w1) by [@HarcoChen](https://github.com/HarcoChen)

### 移除

- 移除米游币获取任务，保留米游社各游戏签到 by [@Lance0174](https://github.com/Lance0174)

### 修复

- BetterGI专项 修复用户编辑页一条龙配置打开自动秘境等组时，秘境选择从级联弹窗退化为纯输入框、且右栏设置保存报错的问题 by [@TCddddd](https://github.com/TCddddd)
- Emulator 2.0 修复模拟器已经在运行时不打开游戏、以及雷电 0 号与 MuMu 同时运行时操作会打到另一台模拟器上的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 日志采集 修复任务运行期间脚本日志按天滚动（跨零点）后，零点前的运行日志历史与节点详情丢失的问题 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- 社区签到结果统一附加到任务报告，修复重复推送并按通知渠道展示奖励与失败原因 by [@Lance0174](https://github.com/Lance0174) by [@TCddddd](https://github.com/TCddddd)
- Runtime 接入 修复首次初始化时 uv 下载完成瞬间「安装 Python」被显示为完成、随后进度又倒退的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 修复启动界面「查看日志」打开的窗口一片空白、后端启动失败时没有查看日志入口、出错说明文字贴在窗口顶部，以及日志文件打不开时没有任何提示（历史记录页还会误报「日志文件已打开」）的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 修复深色模式下初始化界面连同标题栏整体变暗的问题 by [@ClozyA](https://github.com/ClozyA) by [@TCddddd](https://github.com/TCddddd)
- OK-NTE专项 加固切换账号流程：预防弹窗及屏保等意外情况 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- 修复同时打开两个前端窗口时互相抢占后端连接、每隔几秒断线并反复弹出提示的问题：后开的窗口接管连接，先开的窗口停止重连并只提示一次 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MaaEnd专项 修复 MaaEnd 更新后已完成任务被误判失败并重复重试的问题 by [@HarcoChen](https://github.com/HarcoChen) by [@TCddddd](https://github.com/TCddddd)
- 修复与后端断开连接时立即弹出阻塞式弹窗的问题：改为右上角非阻塞提示并在重连成功后自动收起，生产模式仅在整轮重连失败后才升级为弹窗，开发模式下开发者手动重启后端不再被弹窗打断 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 修复点击「更新后端」时弹出「与后端失去连接」弹窗的问题：更新期间的断开按计划内处理，不再提示，也不再由前端另起一个后端与更新流程抢进程 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- 修复首页读取终末地活动缓存后因日期格式异常导致黑屏的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- MAA专项 修复日常理智作战误用剿灭任务队列、导致计划表关卡被错误用于剿灭任务的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- 修复渲染进程崩溃后窗口永久黑屏的问题，崩溃会自动记录并重载窗口 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MAA专项 修复剿灭任务因体力耗尽结束时被误判为已完成本周额度的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- MaaFW专项 修复 Python 运行时损坏时直到任务中途才报出难懂错误的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MaaFW专项 新增受限网络下为 Python 解释器下载配置镜像的环境变量 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MaaFW专项 修复运行环境不可用时会反复重启模拟器与游戏、白等数分钟的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MaaFW专项 修复运行环境损坏时直到任务中途才暴露的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- MFW 建项向导在运行环境准备完成前不再允许进入下一步，准备失败时可就地重试 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-WW与OK-NTE专项 多用户切换时等待上一用户的游戏进程完全退出，避免误复用正在退出的旧游戏窗口导致任务被中止 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- OK-NTE专项 修复任务报告剩余体力计算不准确的问题：体力不足以刷满设定目标时误显「剩余体力: 0」，改为按实际刷本消耗（异象界域双倍/单倍次数、异象追猎实际消耗）精确计算剩余体力 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- 前端类型治理 清理脚本与 Electron 基础边界中的 any，并修复 BetterGI 设置会话无法接收完成和错误事件的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 修复 MAS 管控任务的文本与 JSON 配置项在输入过程中被重渲染清空、导致只有数字项能填写的问题（如货币战争的首领/投资重开条件、策略文件、开拓者名称） by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 修复 SRA 开启「使用培养目标」后历战余响一直不刷、状态始终停在本周未完成的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 修复三月七助手跑完体力后按其「任务完成后操作」自行关闭游戏，导致本已成功的模块被判失败、后续模块空跑一次的问题；MAS 管控运行时该项固定为「无操作」，游戏中途退出时不再继续启动该用户的剩余模块 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-WW专项 修复任务报告推送因漏传通知用户配置参数而失败的问题 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- 游戏签到 修复通知返回值改为 DispatchResult 后未同步两处消费方、开启签到通知时执行签到必报 TypeError 的问题（手动签到接口返回 500，慢渠道后台通知路径丢失日志） by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- BetterGI专项 修复任务跨过本地午夜后仍监控前一天日志文件、导致后续状态误判的问题 by [@Craun718](https://github.com/Craun718) by [@TCddddd](https://github.com/TCddddd)
- 修复明日方舟PC工具连接失败后每秒重试并反复弹出错误提示的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-WW专项 修复账号切换在游戏启动阶段定位不到窗口、或界面尚未进入可执行登录态就误操作而失败的问题，改为分段进展续延等待：先轮询窗口就绪，再等待界面进入「登录页/已登录主菜单」（游戏内长时间更新/加载时持续顺延，长时间无进展才判失败），兼容低性能设备启动延迟 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- OK-WW专项 账号切换未能回到登录界面时立即报错并说明原因，不再误报已就绪后在错误画面上继续选号失败 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- MAA专项 修复 MAA 更新至 v6.14 后代理时不再按用户填写的账号执行账号切换的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-WW与OK-NTE专项 修复多用户切换时误复用正在退出的旧游戏窗口导致任务被中止的问题 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- OK-NTE专项 修复体力不足以刷满目标时任务报告误显「剩余体力: 0」的问题 by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 修复 SRA / 三月七助手升级或更换配置后，单个失效的 MAS 覆盖配置项会让该引擎全部任务表单一起消失、运行时任务直接失败的问题，现在只忽略失效项并在用户页提示、可一键清理 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- BetterGI专项 修复设置会话无法接收完成和错误事件的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd)
- HSR专项 修复任务配置的文本与 JSON 项在输入时被清空、导致只有数字项能填写的问题 by [@qiyinxi](https://github.com/qiyinxi) by [@TCddddd](https://github.com/TCddddd)
- OK-WW专项 修复任务报告推送失败的问题 by [@AthenaHibou](https://github.com/AthenaHibou)
- MaaEnd专项 修复更新后已完成任务被误判失败并重试的问题；清理已停用代码与不再需要的 MFW 资源 by [@HarcoChen](https://github.com/HarcoChen)
- BetterGI专项 修复跨零点误判超时、重试报告重复、GUI 残留配置、切号首次误删仓库、管理员重复 UAC、设置会话无法接收事件等问题 by [@TCddddd](https://github.com/TCddddd) by [@1w1w11w1](https://github.com/1w1w11w1)
- BetterGI与ZZZ-OD专项 修复任务出错时提示送不到前端的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 通用脚本 修复「脚本直控配置」模式下文件被占用时配置目录被部分删除且不还原的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复明日方舟 PC 工具连接失败后每秒重试反复弹错误提示的问题 by [@qiyinxi](https://github.com/qiyinxi)

### 开发流程

- 新增 GitHub Issue 模板（Bug 按专项分区）；清理未达规范的测试文件并重新生成前端接口代码；禁止 AI 助手协助 force push by [@qiyinxi](https://github.com/qiyinxi) by [@1w1w11w1](https://github.com/1w1w11w1) by [@Craun718](https://github.com/Craun718)

## [v5.5.0-beta.2] - 2026-08-31

### 新增

- 前端i18n 新增日本語与英文界面选项，首次启动跟随系统语言；主要页面（首页、脚本、计划、模拟器、队列、调度中心、历史记录、设置及各编辑页）的界面文案与状态标签接入词表 by [@qiyinxi](https://github.com/qiyinxi)
- 日志处理 新增日志处理钩子层，支持成功/失败标志正则匹配；日志采集 API 落地为通用组件（log_box，与专项解耦），OK-WW 作为首个实例接入运行日志节点推送 by [@qiyinxi](https://github.com/qiyinxi) by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd)
- OK-WW专项 支持启动前按手机号后 4 位切换登录账号并新增问题包导出；由 MAS 自行接管鸣潮游戏更新（启动前自动检查、多 CDN 断点续传、增量补丁优先、校验后原子替换） by [@1w1w11w1](https://github.com/1w1w11w1) by [@AthenaHibou](https://github.com/AthenaHibou) by [@TCddddd](https://github.com/TCddddd) by [@qiyinxi](https://github.com/qiyinxi)
- OK-NTE专项 运行日志关键节点注入任务报告，支持用户级详情开关与日常子任务状态展示 by [@AthenaHibou](https://github.com/AthenaHibou) by [@qiyinxi](https://github.com/qiyinxi)
- OK-WW与OK-NTE专项 任务报告详情可选关闭/逐条/汇总三种模式 by [@AthenaHibou](https://github.com/AthenaHibou) by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 新增 MaaFW 脚本类型，可直接托管 MaaFramework 项目：支持 ADB 模拟器与 Win32 PC 两条链路，运行时在独立子进程中驱动、不启动项目界面也不占其配置 by [@qiyinxi](https://github.com/qiyinxi)
- 自定义 Webhook 新增 {gamedate} 变量，可引用与历史归档一致的游戏日 by [@qiyinxi](https://github.com/qiyinxi)
- 调度队列 新增每日首次启动运行队列的功能 by [@luo-luo-o](https://github.com/luo-luo-o) by [@TCddddd](https://github.com/TCddddd) by [@qiyinxi](https://github.com/qiyinxi)
- 界面设置 托盘图标右键菜单支持自定义：可增删、排序菜单项，支持启动队列/脚本、停止全部、重启等命令 by [@1w1w11w1](https://github.com/1w1w11w1) by [@TCddddd](https://github.com/TCddddd) by [@qiyinxi](https://github.com/qiyinxi)
- BetterGI专项 新增更好的原神脚本适配，支持原生 GUI 直控配置与一条龙任务自动代理 by [@TCddddd](https://github.com/TCddddd) by [@qiyinxi](https://github.com/qiyinxi)

### 变更

- 架构优化 新增 utils/services 平台层，按通用与 Windows 能力拆分底层实现 by [@HarcoChen](https://github.com/HarcoChen) by [@qiyinxi](https://github.com/qiyinxi)
- 匿名遥测 接入主进程与渲染进程错误上报，增加启动和任务执行性能指标，抑制无异常日志并遮蔽本机用户名 by [@ClozyA](https://github.com/ClozyA) by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW项目 interface 解析接上闲置缓存并修复 json5 慢解析：用户页与脚本页进入耗时由约 5.5 秒降至约 0.12 秒 by [@qiyinxi](https://github.com/qiyinxi)
- 任务调度 单独运行脚本不再受单日代理次数上限约束；配置任务成败判定改用协议中的机器可读字段 by [@qiyinxi](https://github.com/qiyinxi)
- 通知系统 各类通知统一走同一渠道分发层，失败渠道不阻断其余且可单独重试 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 运行日志记录实际加载的 MaaFramework 版本与来源，版本不一致或非官方构建时给出提示；任务失败信息指出停在哪个节点；架构不匹配时给出明确提示 by [@qiyinxi](https://github.com/qiyinxi)
- 清理无用前端资源、依赖及后端冗余代码 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)

### 修复

- 前端i18n 修复含「|」的说明文案被 vue-i18n 截断的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复 Mirror 酱一次性下载地址被版本检查缓存复用导致更新包下载失败的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MAA专项 修复任务生成覆盖用户原生高级配置、HSR 托管任务开关报错的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- 修复系统通知标题或内容过长时推送失败的问题；自定义 Webhook 推送本地/内网目标绕过代理 by [@qiyinxi](https://github.com/qiyinxi) by [@ArmedHelicopter](https://github.com/ArmedHelicopter)
- 修复 M9A 任务跨过本地午夜后日志监控仍读取前一天文件导致误判超时的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复队列「每日首次」在跨日前十秒冷启动时可能漏跑或重复运行的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复日志文件在监控期间被替换或截断后监控读不到新内容的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复系统时钟跳变（夏令时/NTP）导致运行中任务误判超时、模拟器等待提前放弃与历史记录偏移的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MAA专项 复用原生预设队列，补齐剿灭、活动关优先和库存保持并移除生息演算 by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 修复 Win32 项目定位窗口因超时类型不符而失败、MXU 外壳项目识别不出家族导致更新包选不出、内置运行未加载项目自带 MaaFramework 而回落到另一份、Python 绑定版本不符项目实际运行库的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 修复运行期间界面日志停止更新与停止按钮无响应的问题；修复删除脚本或升级后旧环境永久占用磁盘、中止后 Agent 进程残留的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 修复单个任务失败时日志不即时提示、游戏启动失败后仍空转到各自超时、用户级通知配置形同虚设的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MaaFW专项 修复框架调试日志轮转时只保存后半段的问题 by [@qiyinxi](https://github.com/qiyinxi)
- 修复接入词表后 MaaEnd 与 HSR 编辑页无法加载、HSR 只填三月七路径时任务被分配给 SRA、HSR 未配 SRA 路径时多用户静默跑同一账号的问题 by [@qiyinxi](https://github.com/qiyinxi)

### 开发流程

- 开发环境改用独立端口与 userData，可与正式版同时运行 by [@qiyinxi](https://github.com/qiyinxi)
- 前端检查与格式化由 ESLint/Prettier 迁移至 oxlint/oxfmt by [@Craun718](https://github.com/Craun718)
- 添加 pyproject 和 ruff 配置；清理 MaaFW 未发布的外部运行路径与未接入的配置复用模块 by [@HarcoChen](https://github.com/HarcoChen) by [@qiyinxi](https://github.com/qiyinxi)

## [v5.5.0-beta.1] - 2026-08-28

### 新增

- MAA专项 支持启动前检查并更新明日方舟客户端 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- OK-WW专项 支持启动前自动更新鸣潮客户端 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- 日志采集 支持将运行节点推送至任务报告 by [@AthenaHibou](https://github.com/AthenaHibou) by [@qiyinxi](https://github.com/qiyinxi)
- 调度队列 支持每日首次启动时运行队列 by [@luo-luo-o](https://github.com/luo-luo-o) by [@qiyinxi](https://github.com/qiyinxi)
- 界面设置 支持自定义托盘菜单及任务控制命令；支持一键备份数据 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)

### 变更

- MAA专项 重构用户配置页面 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- 专项任务移除人工排查模式并统一签到入口 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- 前端界面 统一编辑页样式并优化状态管理 by [@ClozyA](https://github.com/ClozyA) by [@qiyinxi](https://github.com/qiyinxi)

### 修复

- SRC专项 修复任务结束后的进程与配置清理问题 by [@Craun718](https://github.com/Craun718) by [@qiyinxi](https://github.com/qiyinxi)
- MaaEnd专项 修复脚本退出后任务持续等待问题 by [@HarcoChen](https://github.com/HarcoChen) by [@qiyinxi](https://github.com/qiyinxi)
- HSR专项 修复 M7A 切换界面失败未重启任务问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@qiyinxi](https://github.com/qiyinxi)
- 修复开机自启动后台任务异常未记录、通知服务延迟加载导致错误的问题 by [@1w1w11w1](https://github.com/1w1w11w1) by [@AthenaHibou](https://github.com/AthenaHibou) by [@qiyinxi](https://github.com/qiyinxi)
- 日志采集 修复多用户节点详情被合并推送的问题；统一推送配置区样式，修复新增/删除规则时过早弹出缺字段提示的问题 by [@AthenaHibou](https://github.com/AthenaHibou) by [@qiyinxi](https://github.com/qiyinxi)

### 开发流程

- 修复前端类型与 lint 检查问题 by [@1w1w11w1](https://github.com/1w1w11w1)

## [v5.4.0] - 2026-08-26

### 变更

- MaaEnd专项 增强账号切换 by [@qiyinxi](https://github.com/qiyinxi)

### 修复

- OK-WW专项 修复任务在日志产生前手动终止时历史记录误显示未捕获到日志的问题 by [@qiyinxi](https://github.com/qiyinxi)
- OK-NTE专项 修复任务结束后异环启动器进程残留并持续占用内存的问题 by [@qiyinxi](https://github.com/qiyinxi)
- MAA专项 修复开启活动关优先后普通理智作战的理智药额度被静默清零的问题，两个作战任务各自使用独立理智药额度 by [@qiyinxi](https://github.com/qiyinxi)

[v5.5.0-beta.4]: https://github.com/AUTO-MAS-Project/AUTO-MAS/compare/v5.5.0-beta.3...dev
[v5.5.0-beta.3]: https://github.com/AUTO-MAS-Project/AUTO-MAS/compare/v5.5.0-beta.2...v5.5.0-beta.3
[v5.5.0-beta.2]: https://github.com/AUTO-MAS-Project/AUTO-MAS/compare/v5.5.0-beta.1...v5.5.0-beta.2
[v5.5.0-beta.1]: https://github.com/AUTO-MAS-Project/AUTO-MAS/compare/v5.4.0...v5.5.0-beta.1
[v5.4.0]: https://github.com/AUTO-MAS-Project/AUTO-MAS/releases/tag/v5.4.0
