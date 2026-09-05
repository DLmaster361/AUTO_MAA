# 案例：ZzzOd（绝区零 / zzz-od）

ZzzOd 基于 `one-dragon` 框架家族，用户级配置是 **MaaEnd 式字段化**（ConfigItem 字段为事实源，web 直接编辑），但运行方式是 **注入式**：运行时由用户字段生成 zzz-od YAML 写入绑定实例槽，zzz-od 原生一条龙负责执行与游戏内切账号。不要把 zzz-od 的实例槽当 MAS 配置目录（两者结构同构但 owner 不同），也不要用 ok-ww 的三态/快速配置模型套它。

具体字段、路径、函数名现场读 `app/task/ZzzOd/` 确认。本文件只记推不出来的部分。

## 产品决策（读代码看不出为什么）

- **用户↔实例槽固定绑定，注册表零持久写入**：绑定下标存用户配置 `Info.SlotIdx`，首次运行/配置时按全局查重分配最小空闲 idx；运行/会话窗口内以合成注册表视图临时呈现 MAS 槽（详见下节），窗口外 zzz-od 原生世界零 MAS 痕迹。不要把「槽目录持久」误解为「注册表持久」——持久的是 `config/{idx:02d}` 目录（配队等），注册表（`one_dragon.yml`）从不写入 MAS 条目。
- **任务网格只把 `DEFAULT_GROUP=True` 的应用作为可选项**。自动战斗等独立工具应用不是一条龙任务；但已保存/导入的启用非默认任务照常显示并执行（对齐 zzz-od 原生「已开启的非默认组应用保留」语义），不要在聚合层过滤掉。
- 任务编排 `OneDragon.AppList` 是 JSON 字符串字段（顺序即执行顺序），前端开关=加入/移出、箭头=调序；不做 zzz-od 式逐任务子配置页。

## 存储模型：为什么与 MAA/OK-WW 系不同

MAS 通用模型是「每用户一份完整配置，脚本级=`data/{script_id}/Default/ConfigFile`、用户级=`data/{script_id}/{user}/ConfigFile`」（MAA/OK-WW/OK-NTE/HSR 系全如此）。ZzzOd **刻意不走目录副本**，物理形态必须跟目标脚本的吞入方式走：

| | MAA/OK-WW/OK-NTE/HSR 系 | ZzzOd（one-dragon） |
|---|---|---|
| 脚本配置形态 | 每用户自包含文件树，脚本按目录切换即换账号 | 单一共享树 `config/`：全局注册表 `one_dragon.yml` + 实例槽 `config/{idx:02d}`，配队/应用配置跨槽共享 |
| 用户配置落盘 | `data/{script_id}/{user}/ConfigFile/` 整树副本 | 脚本配置 `UserData` 的 `ZzzOdUserConfig` 字段对象（web 编辑的事实源），运行时物化注入绑定槽 |
| 运行方式 | 脚本读对应目录即该用户 | 内置切换=一进程内注入全部启用用户槽（合成视图 + `--instance`） |

不能照搬 MAA 目录副本的三条硬理由：① **N 倍重复**——每棵副本树都含全局注册表、全部原生实例与资源文件；② **破坏共享语义**——一条龙原生模型里配队/应用配置按实例槽组织、跨文件引用，拆成独立副本会割裂引用关系；③ **多账号跑不了**——一条龙没有「跨多棵树跑多账号」的运行模式，内置切换依赖单树多槽。

结论：统一的是「每用户一份完整配置」的语义（ZzzOd=`UserData 字段 + 绑定槽物化`两半合一），不是物理目录布局。

## 两态来源

`Info.Mode` 两态：`用户`（本配置字段，运行时注入绑定槽）/ `直控`（页面选一条龙实例直接编辑其原生配置：账号字段白名单 + 任务编排 + `instance_run`，保存即写回原始 YAML；运行仍 `--onedragon` 裸跑，MAS 不注入）。无脚本态——脚本级只保留 RootPath 与运行开关，不留用户级配置。直控账号字段读取合并 zzz-od 默认值（原生只落盘非默认字段），保存时默认值跳过不落盘。进入/退出直控页时自动对一条龙原生配置做指纹去重备份（防误操作改坏后无恢复点）。

## 直控模式：单一用户 + 实例管理（2026-09 定稿）

**每脚本仅允许一个直控用户**（前端切模式拦截 + 后端 `update_user` ZzzOd 守卫抛 ValueError，双保险）。为什么不能多个：直控是**脚本级全局视图**——实例列表、活跃实例、`instance_run` 全在一份 `one_dragon.yml` 里，多直控用户读到写的都是同一份状态，互相干扰且"每个用户独立运行意图"从架构上不成立（曾按多用户实现踩实这一坑：用户1 配 A、用户2 配 B，但活跃/运行实例互相覆盖，运行也分不开）。多账号直接在这**唯一**直控用户的实例管理里配置（实例即账号），或走用户模式注入——两态各司其职。

直控实例管理（全部映射 `one_dragon.yml`，MAS 零消费，变更前指纹备份）：

| UI | 映射字段 | 端点 | 说明 |
| --- | --- | --- | --- |
| 添加/重命名/删除实例 | `instance_list` 条目 | `instances/add` `rename` `delete` | 删除受 MAS 绑定槽保护 + 至少留一个；删除连带实例目录 |
| 「设为活跃」（灰 tag 点击） | 实例条目 `active` | `instances/set-active` | **显式**操作；页面选实例编辑不自动改活跃（自动同步曾导致用户间互相切活跃，已移除） |
| 「启动实例」开关 | 实例条目 `active_in_od` | `instances/active-in-od` | 参与「全部启用实例」运行的名单 |
| 「运行前切换账号」开关 | 实例条目 `force_login_before_run` | `instances/force-login` | 一条龙原生能力，作用点见下节 |
| 「运行实例」下拉 | 全局 `instance_run` | `instances/run-mode` | **全局设置，与编辑哪个实例无关**——独立端点，不要挂回 native-config/save 的实例通道（旧实现把 disabled 和保存都耦合在"所选实例"上，未选实例时既灰又存不了，已修） |

「在一条龙内配置」在直控下走**脚本级原生会话**（`startSession(scriptId)`）：完整原生实例列表，不隔离不注入；启动前 `restore_instance_view` 自愈崩溃残留的合成视图。用户模式仍走合成视图会话。会话关闭后直控页重拉所选实例配置。

直控账号字段区：账号/密码（B服为 B服账号名）带红色 `*` 必填标记（区服联动），因账号切换需要完整登录信息（见下节）；字段顺序=后端 `_NATIVE_ACCOUNT_FIELDS` 元数据顺序（数据驱动栅格），**options 必须随元数据一起走**——曾把 `game_language` 的 options 写丢导致下拉退化为文本框显示原始值 `cn`。

## 一条龙侧账号切换链路（直控开关的真实作用点）

完整排查见 `.dev/zzzod-account-switch.md`。要点（`zzz-od` 源码）：

- **多账号循环（instance_run=全部实例）里，同 game_path 的实例切换由 `SwitchAccount` 无条件执行游戏内登出+重登，与 `force_login_before_run` 开关无关**；game_path 不同则关游戏重开对应客户端（天然切换）。
- `force_login_before_run`（每实例开关）的作用点是 `EnterGame(switch=False)`：该实例「启动游戏并进入」时是否先强制重新登录（覆盖仅运行当前、每实例首次进游戏、不同 game_path 重开后）。
- 前提 `has_login_info`：国服/国际服要 `account`+`password`，B服要 `bilibili_account_name`；**缺失时一条龙主动跳过强制登录**（日志 warning「登录信息未配置完整」）——开关开了没执行的排查首选。直控页密码留空不落盘（默认值跳过语义），要用强制登录必须实际填密码。
- 一条龙还有自动判定 `should_force_login`：全部实例 + 参与实例>1 + 存在同客户端实例 → 即使不开开关也强制登录。
- 边界：MAS 用户模式注入的合成注册表视图不含 `force_login_before_run`（用户模式跑 MAS 槽，本就不该生效）；一条龙本体运行中读内存值，MAS 改开关要等一条龙结束再跑才读到。

## 固定绑定与哨兵

- **合成注册表视图**：zzz-od 的 `instance_list` 是安装级全局命名空间，持久注册会让 MAS 实例混进原生世界（GUI 混排、跨脚本槽串号、「仅运行当前」误跑）。MAS **零持久写入注册表**：运行/配置会话窗口内把 `one_dragon.yml` 临时替换为「仅本脚本用户槽」的合成视图（`write_instance_view`，active_in_od=True、instance_run=全部实例），窗口结束 `restore_instance_view` 恢复原生内容。`one_dragon.yml` 进程启动读一次、之后纯内存，替换窗口对启动器安全；闪退自愈靠 sidecar（`one_dragon.yml.mas-view.bak`）确定性恢复，每次窗口开始前先 restore。
- **会话/运行窗口内「只见 MAS 槽」是刻意的场景隔离，不是 bug**：视图只注册本场景的槽（配置会话=唯一槽、内置切换=全部注入槽），`--instance` 只认视图注册表内的 idx（未注册的静默丢弃）——目的是配置态不误碰/误跑原生实例、隔离跨脚本槽，与"文件层面只增量加槽目录"不冲突。要看原生实例：等窗口结束注册表还原后由一条龙自己打开（在一条龙内配置/查询会话天然只呈现 MAS 世界）；直控模式则在同一原生世界里选实例直接编辑（读的就是原生注册表）。
- **槽目录持久**：配队等复杂配置持久保留在 `config/{idx:02d}`；运行恢复只还原 MAS 注入的字段（备份内容），不删目录。
- **绑定持久在用户配置**（`Info.SlotIdx`），idx 分配全局查重：原生实例 idx ∪ 所有 ZzzOd 脚本用户 SlotIdx（`collect_used_slot_idxs`，排除本次注入/会话用户）——槽目录跨脚本共享，idx 不唯一会互相覆盖。绑定有效性要求 idx 不与原生实例/其他用户冲突（无注册表可查名字，旧版 MAS- 前缀校验随持久注册一起废弃）。
- **同脚本用户名唯一**（前端改名查重 + `check()` 兜底）：视图内槽名 `MAS-{用户名}`，重名会混；跨脚本重名由视图天然隔离。
- 有效根目录哨兵：`find_launcher_exe` 按序找 `OneDragon-RuntimeLauncher.exe` / `OneDragon-Launcher.exe`（`.bak` 不算）；离线校验另见 `tools.zzz_od_config.validate_root`（src + config/one_dragon.yml）。
- **启动器选择（用户字段 `Info.LauncherMode`，直控/用户两态通用）**：标签映射——集成=`OneDragon-RuntimeLauncher.exe`（WithRuntime 打包）、原始=`OneDragon-Launcher.exe`（旧安装器，外部 uv 拉起）。**自动**=优先 `Data.LauncherLastGood`（上次成功项），失败换另一个重试并记住下次成功的那个；原始/集成=固定（所选 exe 未安装回退默认顺序并告警）。**启动级失败靠日志证据判定**：两种启动器的一条龙运行日志都汇聚 `.log/log.txt`，启动器自身没起来（uv 缺失/同步失败早退）时该文件无应用层条目——以 `[application_launcher.py`/`[one_dragon_context.py`/`[application_factory_manager.py` 任一出现或运行记录有变化为「已启动」，避免把功能级失败误判成启动失败。原始启动器的框架日志另写 `python_launcher_framework.log`，不进 log.txt。

## 注入运行与判态

- `--instance 1,2,...`（逗号分隔多实例）**只在 `instance_run=全部实例` 分支被读取**——instance_run 由合成视图统一落盘（窗口结束随视图恢复原生值）；且 idx 必须在视图注册表内，未注册的会被启动器静默丢弃。
- 注入只做一次，**重试不清运行记录**（zzz-od 按记录跳过已完成任务）；新建槽的目录保留（配队持久）。
- 判态：内置致命日志（未找到有效的实例 / 请先结束其他运行中的功能 再启动 / 运行应用 one_dragon 失败）→ 各槽 `app_run_record` 前后 diff；启动器进程退出即本轮结束。
- 恢复在 `main_task` finally、`final_task`、`on_crash` 三处幂等执行：先还原合成视图，再逐槽备份恢复（目录一律保留）。

## 账号切换两模式（脚本级 `Game.AccountSwitch` 下拉）

- **一条龙内置**（默认）：全部启用用户注入各自绑定槽，`--onedragon --instance s1,s2,...` 单进程覆盖所有用户（zzz-od 内部 SwitchAccount 切游戏账号）。**manager 只 spawn 一个代理**；结果按各槽 diff 归属用户（`_judge_multi`），逐用户写回统计并按各自 `PushLogMode` 推送。
- **MAS账号切换**（预留）：逐用户循环（注入该用户绑定槽 → 运行 → 结束），当前依赖一条龙账密登录，MAS 侧主动切换能力后续接入；走原逐用户 spawn + `_judge_final`。
- 跳过条件（剩余天数/代理次数上限/任务编排为空）在**注入名单内逐用户施加**；内置切换的触发者可能被跳过，不要把其「跳过」状态覆盖为「运行」。

## 在一条龙内配置（配置会话，双向联动）

用户配置界面只覆盖高频字段；配队等复杂配置由用户在原生界面维护。用户页顶部按钮**两种模式常显**，`useZzzodGuiSession` 派发 `SCRIPT_CONFIG`（taskId=userId）。会话与 MAS 字段**双向联动**，不是旁观式打开：

- **打开前基线注入**：`inject_user_fields` 把本页字段写入绑定槽（不清运行记录）——GUI 所见即本页配置；先归档原生配置快照，再以合成视图呈现（`write_instance_view` 仅含本槽、`active` 指向本槽）；
- **关闭时回读**：`_readback_user_fields` 把 GUI 落盘的任务编排（`_group.yml` 全量顺序、仅启用项进 AppList）与账号字段写回 MAS 字段——区服/路径/语言/B服名无条件回读，账号/密码仅槽值非空才回读（留空=沿用登录态，避免清空被读回）；前端遮罩关闭时重拉表单；
- 配队等 MAS 不管的内容不注入不回读，持久留在槽里；
- Default（脚本级）会话直接拉起 GUI，无注入/回读。

## 配置恢复（通用服务 + 通用组件）

ZzzOd 的「配置恢复」接入通用能力（专项只喂参数）：

- 后端：`app.core.config.zzzod_restore_service()` 用 `ConfigRestoreService` 组装双目标
  （mas 在前、onedragon 在后，`script_name="一条龙"` 专项统一名）；`list_zzzod_backups`
  等改为 `service.list(target)` 薄委托。
- 前端：`ZzzOdUserEdit.vue` 用 `ConfigRestoreSection` 组件（传 `scriptName="一条龙"`
  而非脚本实例名、`targets`/`api`/字段映射/`onRestored`/`onDetail`）。
- 会话遮罩：配置/查看会话拉起原生 GUI 期间用 `GuiSessionMask`（纯 UI，专项传
  开关/文案/按钮）。
- 完整用法见 [config-restore.md](config-restore.md)。

## 陷阱

- **`ScriptItem.result` 是只读计算属性**（从 user_list 实时拼接），报告正文用局部变量 `build_user_result_text(...)` 承载，对其赋值会抛 AttributeError（ZzzOd 曾踩）。
- **配置会话必须双向联动**：只激活槽不注入基线 → GUI 与本页配置不一致；只注入不回读 → GUI 内改动下次运行被 MAS 字段覆盖（用户改动静默丢失）。回读时账号/密码非空才读，否则「留空沿用登录态」语义被破坏。
- **重试重判的幂等**：重试带着同一全零基准重判，推送条目按用户整体重建（clear 后重采），统计只在状态变化时写——否则 ProxyTimes 多次自增、推送重复。
- **instance_run 随视图恢复**；注册表零持久写入是设计核心，勿把合成视图改成持久注册（会重新引入 GUI 混排/跨脚本串号）。
- 直控模式不需要注入但仍校验 zzz-od 有活跃实例；用户态不需要（绑定槽自动注册）。
- manager `final_task` **所有模式**都写回 UserData（ScriptConfig 会话也会产生 SlotIdx 落盘）。
- schema 变更后离线导出再生成（`PYTHONPATH=. python .dev/export_openapi.py` → `npx openapi --input ../.dev/openapi.json`），禁止手改生成文件。
- **openapi-typescript-codegen 三个坑**（0.29.0 实测）：① 请求模型用中文 `Literal[...]` 会生成重复 `_` 标识符导致 TS 编译失败——枚举校验放后端原语（如白名单校验），schema 用 `str`；② **路径前缀重叠的端点会被静默丢弃**（`/instances/active` 被 `/instances/active-in-od` 吞掉，无任何报错）——端点命名避免互为前缀（用 `set-active` 不用 `active`）；③ 生成器 `--output ./src/api` 是相对 cwd 的——必须在 `frontend/` 目录下执行，曾误生成整套到仓库根 `src/api`。

## 审查清单

- [ ] 用户↔槽绑定经 `ensure_user_slot` 唯一入口；MAS- 命名空间校验未被绕过
- [ ] 内置切换只 spawn 一个代理；注入名单逐用户施加跳过条件
- [ ] `--instance` 与 `instance_run=全部实例` 成对出现且结束恢复
- [ ] 槽内容在成功/失败/取消/超时/异常五条路径恢复；注册表按设计保留
- [ ] 任务网格只提供默认组任务；已保存非默认任务不被静默过滤
- [ ] 结果按槽归属用户；推送按各用户 PushLogMode 且重试不重复
- [ ] 配置会话双向联动：基线注入 + 关闭回读 + 恢复原活跃实例；SlotIdx 与回读结果落盘
- [ ] 查看会话（viewOnly，如「查看历史备份」）：不注入基线、不回读字段、无保存入口——预览不得污染 MAS 字段
- [ ] 直控页面编辑：账号保存走「保存设置」按钮，任务/运行实例即时增量提交（不把未保存的账号草稿一并落盘）；账号字段白名单过滤且默认值不落盘
- [ ] 直控单一用户约束：切「直控」时前端拦截 + 后端 `update_user` 守卫都校验（每脚本仅一个直控用户）
- [ ] 直控实例管理的字段映射走 one_dragon.yml 原语（`_registry_rmw`），变更前指纹备份；删除受 MAS 绑定槽与「至少一个实例」保护
- [ ] 运行实例（`instance_run`）走独立 run-mode 端点，不与「编辑所选实例」的通道/disabled 耦合
- [ ] 直控账号字段元数据（顺序与 options）一致；`game_language` 等下拉字段的 options 未丢失
- [ ] 报告正文走 `build_user_result_text` 局部变量，未对 `ScriptItem.result` 赋值
