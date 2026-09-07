# BetterGI 一条龙配置 — 每周配置 MAS 托管改造（Handoff）

> 整理自 `feat/bettergi-onedragon-config` 分支的开发对话，供在另一台电脑继续写作。
> 目标：让「自动秘境」「自动地脉花」的每周配置（队伍/秘境名/奖励/地区/类型，按星期切换）由 MAS 直连层（Plan）托管，而非落回 BGI 原生一条龙 JSON。

## 1. 已完成

- [x] 后端 `app/task/BetterGI/tools/one_dragon_plan.py`：新增 weekly 平铺键 ↔ Plan 嵌套的识别与重组函数（`extract_weekly_struct` / `flatten_weekly_struct` / `weekly_plan_keys` / `_secret_weekly_plan_key` / `_leyline_weekly_plan_key`）。
- [x] 后端 `app/api/scripts.py`：`_route_combat_to_plan` 把 weekly 平铺键从 `native_leftover` 剥离、走 Plan 结构化；`_read_combat_from_plan` 回显时还原为平铺键。
- [x] 执行层 `res/templates/BetterGI/MASOneDragon/main.js`：秘境/地脉花按 `new Date().getDay()` 取当天行直传执行层；秘境当天无配置则 `MAS_STEP_SKIP_WEEKDAY` 跳过。
- [x] 白名单 `BUILTIN_STEP_SETTING_KEYS` 允许 `weeklyDomain`（秘境）/ `weeklyLeyLine`（地脉花）。
- [x] 修复 `merge_rightbar_into_plan` 真实 bug：空 Plan 首次保存、或仅有 weekly 配置时，原 `if not transl: return plan_json` 会提前返回丢失数据 → 改为 `if not transl and not extra`。
- [x] 后端 round-trip 验证（stub 加载 `one_dragon_plan.py`）：秘境 12 项全 PASS；地脉花键与前端全名 `LeyLineMondayCountry`/`LeyLineRunMonday` 对齐（前端 `WEEKDAY_KEYS` 是全名，后端必须全名对齐）。

## 2. 关键数据结构

前端 weekly 表格继续用 BGI 原生**平铺 key**（前端零改动）：

- 秘境周表：`MondayPartyName` / `MondayDomainName` / `MondaySelectedValue` …；`SundayEverySelectedValue`（默认行 reward）；`PartyName` / `DomainName`（每日行 → 映射进 `default`）。
- 地脉花周表：`LeyLineMondayCountry` / `LeyLineMondayType` / `LeyLineRunMonday` …

落盘重组为 Plan settings 嵌套：

```json
自动秘境.settings.weeklyDomain = {
  "default": {"partyName": "...", "domainName": "...", "reward": 2},
  "Monday":  {"partyName": "...", "domainName": "...", "reward": 0},
  ...
}
自动地脉花.settings.weeklyLeyLine = {
  "Monday": {"country": "...", "type": "...", "run": true},
  ...
}
```

回显时 `flatten_weekly_struct` 把嵌套还原为上述平铺 key（供前端周表显示）。

注意点：

- 前端 `WEEKDAY_KEYS` 是**全名**（`Monday`…`Sunday`），后端 `WEEKDAY_KEYS` 必须与之全名对齐（不要缩写）。
- 天键大写首字母需与 `main.js` 中 `getDay()` 映射数组 `["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]` 一致。
- `PartyName`/`DomainName` 既是每日行单值（映射进 `settings.partyName`），又是 weekly `default` 行（重组进 `weeklyDomain.default`）；两者值相同，无矛盾。

## 3. 验证与限制

- 后端逻辑用 stub 加载 `one_dragon_plan.py` 验证 round-trip（参考已删除的 `_weekly_test.py`：构造平铺 key → `extract_weekly_struct` → `merge_rightbar_into_plan` → `parse_one_dragon_plan` → `flatten_weekly_struct`，逐项断言）。
- **实机执行需在 BGI 环境跑 `main.js` 确认按天取值**（本机无 BGI，执行层未实跑验证）。
- `main.js` 直连层依赖 BGI 执行层 API（`runAutoDomainTask` / `AutoLeyLineOutcrop` 等），需确认桥接（`one_dragon_bridge.py` 等）在目标环境可用。

## 4. 待办（todo #5，未做）

「右栏配置全部对接到 MAS」还剩**单值未映射字段**（当前不在 `RIGHTBAR_TO_PLAN`，会进 `native_leftover` 落原生一条龙）：

- 秘境：`resinPriorityList`、`combatStrategyPath`、`domainRoundNum`、`maxArtifactStar`（直连场景待复核）
- 地脉花：`useAdventurerHandbook`（带语义反转坑，需 `!s.useAdventurerHandbook`）、`useFragileResin`、`useTransientResin`、`team`（靠全局）、`friendshipTeam`、`isGoToSynthesizer`、`isNotification`（全缺口）
- 幽境：`resinPriorityList`、`combatScriptBagPath`
- 首领：`combatStrategyPath`（路径形式，现以名字代替）

接入步骤（每个字段）：① 前端 `BetterGIUserEdit.vue` 加编辑字段；② `RIGHTBAR_TO_PLAN` 加 frontend→plan 映射；③ `BUILTIN_STEP_SETTING_KEYS` 白名单加 plan key；④ 必要时 `main.js` 补直传逻辑（多数 `if (s.xxx != null)` 分支已写好，只差前端入口 + 映射）。

## 5. 继续工作指引

- 另一台电脑：`git clone` 你的 fork 并 `git checkout feat/bettergi-onedragon-config`，安装后端依赖。
- 跑后端验证：用 stub 加载 `one_dragon_plan.py`（参考已删除的 `_weekly_test.py`），验证 round-trip。
- **提 PR 前**必须补 `res/version.json` changelog：面向用户、一句话概括 PR 意义，归入对应分类；一条 PR 一条记录。
- 禁止 force push；`upstream` 为官方仓库，仅维护者合 `dev`→`main`。
- 当前分支推到 `origin`（你的 fork）即可；PR 目标应为 `upstream/dev`。

## 6. 相关文件速查

- `app/task/BetterGI/tools/one_dragon_plan.py`：Plan 解析 / 合并 / weekly 重组
- `app/api/scripts.py`：`_route_combat_to_plan` / `_read_combat_from_plan`
- `res/templates/BetterGI/MASOneDragon/main.js`：执行层按天路由
- `frontend/src/views/EditView/User/BetterGIUserEdit.vue`：右栏字段与 weekly 表格
- `app/task/BetterGI/tools/one_dragon_bridge.py`、`one_dragon.py`：BetterGI 任务桥接
