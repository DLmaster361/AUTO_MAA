# 通用配置恢复：基座统一分发 + 专项池声明 + 前端组件

> 适用：专项需要在用户/脚本配置页提供「配置恢复」（历史备份列表 / 预览摘要 /
> 一键恢复）时。三层解耦：
>
> - **后端基座**：`app/utils/config_restore.py`（`RestoreContext` /
>   `ConfigRestorePool` / `build_restore_service` / `ConfigRestoreService`）；
> - **HTTP 层**：一组通用端点 `/api/scripts/backup/list|ensure|restore|preview`
>   （schema 通用 `ConfigBackup*` 模型），所有专项共用，**接入专项不改这层**；
> - **前端**：`frontend/src/views/EditView/User/components/ConfigRestoreSection.vue`
>   （恢复弹窗 + 预览弹窗，props 传专项名/目标池/API/字段映射），会话遮罩用
>   `GuiSessionMask.vue`（纯 UI，与会话状态解耦）。
>
> 参考实现：OkNte（`app/task/OkNte/tools/restore_service.py`，池函数自包含）
> 与 ZzzOd（`app/task/ZzzOd/tools/restore_service.py`，薄委托门面内部方法）。
> 备份文件级快照/回写原语见 [config-archive.md](config-archive.md)。

---

## 1. 专项统一名（文案参数化）

配置恢复文案里 `{script}` 用**专项统一名**插值，不是脚本实例名：
zzz-od 统一叫「一条龙」，ok-nte 统一叫「ok-nte」。专项在
`tools/restore_service.py` 用 `RESTORE_SCRIPT_NAME` 常量声明。

i18n 词条（`edit.configRestore*`）已 `{script}` 参数化；专项归档时机措辞
与通用词条不同时（如 ok-nte 无直控模式），在编辑页用组件的
`script-desc`/`user-desc` props 传专项词条覆写。

## 2. 专项侧：声明目标池表（唯一要写的接入代码）

在专项 `tools/restore_service.py` 声明 `RESTORE_POOLS` + `RESTORE_SCRIPT_NAME`。
池函数是**普通函数，显式收 `RestoreContext`**（config 门面 / script_config /
script_id / user_id），不闭包捕获——可直接单测：

```python
async def _list_mas(ctx) -> list[str]:
    return list_mas_backups(ctx.script_id, ctx.user_id)

async def _restore_mas(ctx, ts: str) -> object:
    _user_guard(ctx)                      # 守卫/回填等专项语义留在池函数
    restore_mas_backup(ctx.script_id, ctx.user_id, ts, mas_config_dir(...))

RESTORE_POOLS = [
    ConfigRestorePool(key="mas", kind="user",
                      list_backups=_list_mas, preview=_preview_mas,
                      restore=_restore_mas, snapshot=_snapshot_mas),
    ConfigRestorePool(key="native", kind="script", ...),
]
```

- 池表顺序 = 前端 segmented 展示顺序（`kind='user'` 的 MAS 池在前、
  `kind='script'` 的脚本原生池在后）；`key` 任取（如 `mas`/`onedragon`/
  `native`），前后端靠它对齐，非法 key 统一 400。
- `preview` 返回**专项自定义载荷 dict**（结构不用对齐其他专项，前端按
  target 消费）；`snapshot` 返回 `{"created": bool, "time": str}`。
- 内部业务依赖门面 helper 的专项（如 ZzzOd 的 `_zzzod_user`/槽占用守卫）：
  池函数经 `ctx.config` 薄委托门面公开方法，内部方法留在门面；能自包含的
  专项（如 OkNte，守卫走 `ctx.script_config.UserData`）全部自包含。

## 3. core 门面：分发链加一个分支（每专项 ~3 行）

`app/core/config.py` 的 `restore_service(script_id, user_id)` 按
`isinstance(script_config, ...)` 取专项池表，`build_restore_service(ctx,
RESTORE_SCRIPT_NAME, RESTORE_POOLS)` 一次性绑定上下文；`list/ensure/restore/
preview_config_backup` 四个通用方法全专项共用，勿再新增专项包装方法。

## 4. 前端接入（ConfigRestoreSection）

```vue
<ConfigRestoreSection
  v-model:open="restoreOpen"
  :script-name="DISPLAY_NAME"        <!-- 专项统一名 -->
  :targets="[{ key: 'mas', kind: 'user' }, { key: 'native', kind: 'script' }]"
  :api="restoreApi"
  :on-restored="handleRestored"      <!-- MAS 恢复后刷新表单，防旧值写回撤销恢复 -->
  <!-- onDetail 缺省时组件自动隐藏「查看详细配置」按钮（无查看会话的专项不必提供） -->
/>
```

`api` 三个函数闭包捕获 scriptId/userId，统一调生成的 `BackupService`
通用函数（`listConfigBackupsApiApiScriptsBackupListGet` 等）；`target`
是普通字符串，无需枚举断言。组件对预览响应自动解包 `data` 载荷
（`resp.data ?? resp`），内置预览渲染按 `kind`（user=描述表、script=实例
折叠列表，ZzzOd 结构）；载荷结构不同的专项用 `#preview` 插槽完全接管
（上下文 `{ data, raw, target, formatValue, fieldLabel }`，OkNte 用
`raw.files` 渲染文件集摘要）。

**归档三时机**（前端）：进入编辑页 `onMounted`、退出编辑页 `onUnmounted`
调通用 ensure（target=用户侧池）；运行前归档由专项任务流程直接调专项
`archive_*` 函数（不经 HTTP）。

## 5. 检查清单

- [ ] 专项统一名传 `RESTORE_SCRIPT_NAME`（一条龙/ok-nte…），前端 `scriptName` 一致
- [ ] 池表顺序 user 在前 script 在后；key 与前端 `targets` 一致
- [ ] 池函数收显式 `RestoreContext`，无闭包捕获；守卫/回填/预览载荷在专项层
- [ ] 恢复回调内恢复前 `force` 归档当前（误恢复可找回）
- [ ] **归档三时机**：进入编辑页归档原生配置（操作前原始态）、退出编辑页归档 MAS 侧终态、运行前归档；全部指纹去重
- [ ] 覆盖性操作（导入/恢复）前强制归档
- [ ] 前端 `api` 闭包捕获 scriptId/userId，调 BackupService 通用函数
- [ ] 预览载荷结构不同的专项用 `#preview` 插槽；无查看会话的专项不传 `onDetail`
- [ ] i18n 词条用 `{script}` 插值；措辞不符的专项传 desc 覆写
- [ ] 公共服务/组件/端点无专项分支；新专项接入只改专项模块 + core 分支
