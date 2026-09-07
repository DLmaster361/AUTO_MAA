# 通用配置恢复：后端服务 + 前端组件 + 会话遮罩

> 适用：专项需要在用户/脚本配置页提供「配置恢复」（历史备份列表 / 预览摘要 /
> 查看详细配置 / 一键恢复）时。已解耦为三层：
>
> - **后端**：`app/utils/config_restore.py` 的 `ConfigRestoreService`（按 key 分发
>   列表/预览/恢复，专项只提供目标池回调）；
> - **前端**：`frontend/src/views/EditView/User/components/ConfigRestoreSection.vue`
>   （恢复弹窗 + 预览弹窗，props 传专项名/目标池/API/字段映射）；
> - **会话遮罩**：`frontend/src/components/GuiSessionMask.vue`（拉起原生 GUI 时
>   的全屏遮罩，纯 UI，与会话状态解耦）。
>
> 参考实现：ZzzOd（`app.core.config.zzzod_restore_service` +
> `ZzzOdUserEdit.vue`）。备份文件级快照/回写原语见 `config-archive.md`。

---

## 1. 专项统一名（文案参数化）

配置恢复文案里 `{script}` 用**专项统一名**插值，不是脚本实例名：
zzz-od 统一叫「一条龙」，ok-ww 统一叫「ok-ww」，各专项接入时传入自己的名字。
前端在接入处定义常量并传给组件（如 `const ZZZOD_DISPLAY_NAME = '一条龙'`）。

i18n 词条（`edit.configRestore*`）示例：

- `configRestoreTargetMas`：`恢复MAS用户配置`
- `configRestoreTargetScript`：`恢复{script}原生配置`（MAS 在前，脚本在后）
- `configRestoreMasDesc`：`MAS独立用户配置的备份，恢复会直接作用于MAS配置页；运行{script}或打开配置前会自动去重创建，保留最近 10 份`
- `configRestoreScriptDesc`：`{script}原生配置的备份，恢复会直接作用于{script}本体；运行{script}、在直控模式下修改或打开配置前会自动去重创建，保留最近 10 份`

## 2. 后端接入（ConfigRestoreService）

`ConfigRestoreTarget` 四个异步回调（闭包捕获脚本/用户上下文；前三个必填，
`snapshot` 可选）：

| 回调 | 职责 |
| --- | --- |
| `list_backups() -> list[str]` | 该目标全部备份时间戳（倒序） |
| `preview(ts) -> dict` | 预览摘要（纯读；info/account/tasks/instances 结构见下） |
| `restore(ts)` | 执行恢复（恢复前归档当前由回调自理；返回前端展示结果） |
| `snapshot() -> dict` | 按需归档当前配置（指纹去重，无变化跳过）；返回 `{"created": bool, "time": str}`；供三时机 `service.ensure(key)` 调用 |

组装示例（ZzzOd）：

```python
def zzzod_restore_service(self, script_id, user_id) -> "ConfigRestoreService":
    from app.utils.config_restore import ConfigRestoreService, ConfigRestoreTarget
    # 定义 list_mas/list_onedragon/preview_*/restore_* 回调（闭包捕获 script_id/user_id）
    return ConfigRestoreService(
        script_name="一条龙",  # 专项统一名
        targets=[
            ConfigRestoreTarget(key="mas", list_backups=list_mas,
                                preview=preview_mas, restore=restore_mas),
            ConfigRestoreTarget(key="onedragon", list_backups=list_onedragon,
                                preview=preview_onedragon, restore=restore_onedragon),
        ],
    )
```

- **目标池顺序 = 前端 segmented 展示顺序**：MAS（`key` 任选，`kind='user'`）在前、
  脚本原生（`kind='script'`）在后。
- `preview` 返回结构约定：`info`（基本信息字段 `{key,value}`）、`account`（账号字段）、
  `tasks`（`{app_id,app_name,enabled}`）、`instances`（脚本级实例列表，每条含
  `account`/`tasks` 供展开）。前端组件按 `kind` 渲染：user=描述表+任务标签，
  script=实例折叠列表。
- `list_zzzod_backups` 等对外方法改为 `service.list(target)` 薄委托，API 路由不变。

## 3. 前端接入（ConfigRestoreSection）

```vue
<ConfigRestoreSection
  v-model:open="restoreOpen"
  :script-name="ZZZOD_DISPLAY_NAME"   <!-- 专项统一名 -->
  :targets="restoreTargets"           <!-- [{key,kind}] 顺序即展示顺序 -->
  :api="restoreApi"                    <!-- {list,preview,restore} 函数 -->
  :field-labels="previewFieldLabels"   <!-- 账号字段 key→标题 -->
  :format-value="formatPreviewValue"   <!-- 枚举值转词表 -->
  :on-restored="handleRestored"        <!-- 一键恢复成功后（刷新表单） -->
  :on-detail="handleRestoreView"       <!-- 查看详细配置（拉起会话） -->
/>
```

- `targets` 示例：`[{ key: 'mas', kind: 'user' }, { key: 'onedragon', kind: 'script' }]`
- `api` 三个函数签名：`(target) => Promise<{code,message,data?}>` /
  `(target, time) => Promise<预览结构>` / `(target, time) => Promise<{code,message}>`；
  target 字符串传给生成客户端时按需断言（如 `as ZzzOdBackupRestoreIn['target']`）。
- `onRestored`：一键恢复成功后父组件处理（MAS 恢复含字段回填 → 刷新表单；
  脚本级由组件自行刷新列表）。
- `onDetail`：查看详细配置，父组件负责「确认弹窗 → 恢复该备份 → 拉起脚本 GUI
  查看会话」。

**自定义预览（`#preview` 插槽）**：内置预览按 `kind` 渲染（user=描述表+任务标签，
script=实例折叠列表，ZzzOd 结构）。不完全适配的专项（字段型：M9A/MaaFW/HSR 等）
可传 `#preview` 插槽**完全接管预览区**，插槽上下文为
`{ data, target, formatValue, fieldLabel }`——专项用自身字段结构渲染键值摘要：

```vue
<ConfigRestoreSection ...>
  <template #preview="{ data, target }">
    <a-descriptions :column="1" size="small" bordered>
      <a-descriptions-item v-for="f in data.fields ?? []" :key="f.key" :label="f.key">
        {{ f.value }}
      </a-descriptions-item>
    </a-descriptions>
  </template>
</ConfigRestoreSection>
```

插槽为空时回落到内置渲染（向后兼容，文件树型适配器零改动）。

**自定义预览标题（`#preview-title` 插槽）**：预览弹窗标题区同样开放，专项可覆盖
标题/说明文案，上下文暴露 `{ time }`；缺省为「配置预览 · 时间」：

```vue
<ConfigRestoreSection ...>
  <template #preview-title="{ time }">
    {{ myTitle }} · {{ time }}
  </template>
</ConfigRestoreSection>
```

设计原则：`#preview` / `#preview-title` 均为**可选覆盖**，缺省即内置行为——专项
按需配置，不为不完全适配的形态改通用件。

## 4. 会话遮罩（GuiSessionMask）

「查看详细配置/在原生 GUI 里配置」拉起会话期间需全屏遮罩阻断页面操作。
`GuiSessionMask` 是纯展示组件（props：`open`/`title`/`icon`/`description` +
`#actions` 插槽），与会话状态解耦：

```vue
<GuiSessionMask
  :open="showZzzodViewMask"
  :icon="EyeOutlined"
  :title="t('edit.zzzodViewingTitle')"
  :description="`${t('edit.zzzodViewingDesc')}\n${t('edit.zzzodViewingDesc2')}`"
>
  <template #actions>
    <a-button :loading="stopping" @click="closeView">{{ t('...') }}</a-button>
  </template>
</GuiSessionMask>
```

专项只负责「何时显示/隐藏（会话状态）+ 按钮行为」，遮罩视觉组件统一复用。

## 5. 检查清单

- [ ] 后端 `ConfigRestoreService.script_name` 传专项统一名（一条龙/ok-ww…），非脚本实例名
- [ ] 目标池顺序 MAS 在前、脚本原生在后；`key` 与前端 `targets` 一致
- [ ] `preview` 返回结构遵循 info/account/tasks/instances 约定
- [ ] 恢复回调内恢复前 `force` 归档当前（误恢复可找回）
- [ ] **归档三时机**（`snapshot` + `service.ensure`）：进入编辑页归档原生配置（操作前原始态）、退出编辑页归档 MAS 侧终态、运行前归档；全部指纹去重
- [ ] 覆盖性操作（导入/恢复）前强制归档
- [ ] 前端 `api` 函数闭包捕获 scriptId/userId，target 字符串按需断言为生成类型
- [ ] `onDetail` 完成「确认 → 恢复 → 拉起查看会话 + GuiSessionMask」
- [ ] i18n 词条用 `{script}` 插值，专项统一名传入
- [ ] 公共服务/组件无专项分支；专有逻辑（守卫/回填/会话）留在专项
