# 案例：ZzzOd（绝区零 / zzz-od）

ZzzOd 基于 `one-dragon` 框架家族，用户级配置是 **MaaEnd 式字段化**（ConfigItem 字段为事实源，web 直接编辑），但运行方式是 **注入式**：运行时由用户字段生成 zzz-od YAML 写入绑定实例槽，zzz-od 原生一条龙负责执行与游戏内切账号。不要把 zzz-od 的实例槽当 MAS 配置目录（两者结构同构但 owner 不同），也不要用 ok-ww 的三态/快速配置模型套它。

具体字段、路径、函数名现场读 `app/task/ZzzOd/` 确认。本文件只记推不出来的部分。

## 产品决策（读代码看不出为什么）

- **用户↔实例槽固定绑定，注册表零持久写入**：绑定下标存用户配置 `Info.SlotIdx`，首次运行/配置时按全局查重分配最小空闲 idx；运行/会话窗口内以合成注册表视图临时呈现 MAS 槽（详见下节），窗口外 zzz-od 原生世界零 MAS 痕迹。不要把「槽目录持久」误解为「注册表持久」——持久的是 `config/{idx:02d}` 目录（配队等），注册表（`one_dragon.yml`）从不写入 MAS 条目。
- **任务网格只把 `DEFAULT_GROUP=True` 的应用作为可选项**。自动战斗等独立工具应用不是一条龙任务；但已保存/导入的启用非默认任务照常显示并执行（对齐 zzz-od 原生「已开启的非默认组应用保留」语义），不要在聚合层过滤掉。
- 任务编排 `OneDragon.AppList` 是 JSON 字符串字段（顺序即执行顺序），前端开关=加入/移出、箭头=调序；不做 zzz-od 式逐任务子配置页。

## 两态来源

`Info.Mode` 两态：`用户`（本配置字段，运行时注入绑定槽）/ `直控`（页面选一条龙实例直接编辑其原生配置：账号字段白名单 + 任务编排 + `instance_run`，保存即写回原始 YAML；运行仍 `--onedragon` 裸跑，MAS 不注入）。无脚本态——脚本级只保留 RootPath 与运行开关，不留用户级配置。直控账号字段读取合并 zzz-od 默认值（原生只落盘非默认字段），保存时默认值跳过不落盘。进入/退出直控页时自动对一条龙原生配置做指纹去重备份（防误操作改坏后无恢复点）。

## 固定绑定与哨兵

- **合成注册表视图**：zzz-od 的 `instance_list` 是安装级全局命名空间，持久注册会让 MAS 实例混进原生世界（GUI 混排、跨脚本槽串号、「仅运行当前」误跑）。MAS **零持久写入注册表**：运行/配置会话窗口内把 `one_dragon.yml` 临时替换为「仅本脚本用户槽」的合成视图（`write_instance_view`，active_in_od=True、instance_run=全部实例），窗口结束 `restore_instance_view` 恢复原生内容。`one_dragon.yml` 进程启动读一次、之后纯内存，替换窗口对启动器安全；闪退自愈靠 sidecar（`one_dragon.yml.mas-view.bak`）确定性恢复，每次窗口开始前先 restore。
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

## 陷阱

- **`ScriptItem.result` 是只读计算属性**（从 user_list 实时拼接），报告正文用局部变量 `build_user_result_text(...)` 承载，对其赋值会抛 AttributeError（ZzzOd 曾踩）。
- **配置会话必须双向联动**：只激活槽不注入基线 → GUI 与本页配置不一致；只注入不回读 → GUI 内改动下次运行被 MAS 字段覆盖（用户改动静默丢失）。回读时账号/密码非空才读，否则「留空沿用登录态」语义被破坏。
- **重试重判的幂等**：重试带着同一全零基准重判，推送条目按用户整体重建（clear 后重采），统计只在状态变化时写——否则 ProxyTimes 多次自增、推送重复。
- **instance_run 随视图恢复**；注册表零持久写入是设计核心，勿把合成视图改成持久注册（会重新引入 GUI 混排/跨脚本串号）。
- 直控模式不需要注入但仍校验 zzz-od 有活跃实例；用户态不需要（绑定槽自动注册）。
- manager `final_task` **所有模式**都写回 UserData（ScriptConfig 会话也会产生 SlotIdx 落盘）。
- schema 变更后离线导出再生成（`PYTHONPATH=. python .dev/export_openapi.py` → `npx openapi --input ../.dev/openapi.json`），禁止手改生成文件。

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
- [ ] 报告正文走 `build_user_result_text` 局部变量，未对 `ScriptItem.result` 赋值
