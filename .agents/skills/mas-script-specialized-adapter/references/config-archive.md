# 配置归档：共享持久快照 / 恢复原语用法

> 适用：专项需要把「运行或配置会话前会被 MAS 触碰的配置文件」做**跨会话持久**
> 快照（可列出、可一键恢复）时。原语在 `app/utils/config_archive.py`，与脚本
> 解耦——专项只提供**备份对象**（目录或文件集）与**恢复后的语义钩子**，不关心
> 时间戳、去重、保留清理怎么做。

一句话链路：专项在「动手前」喂备份对象 + `store_root` → 原语时间戳归档 /
指纹去重 / 保留清理 → Web 或本地按时间倒序列出 → `restore_dir` 整目录回写 →
专项执行恢复后语义（字段回填、重建视图、清残留）。

> 上层「配置恢复」（列表 / 预览 / 一键恢复的服务与前端组件、会话遮罩）见
> [config-restore.md](config-restore.md)；本文件只讲文件级快照/回写原语。

参考实现：`app/task/ZzzOd/tools/backup_archive.py`（两条视角：一条龙原生配置
= 文件集、MAS 用户槽 = 整目录）。

## 原语一览（签名现场读模块确认）

| 原语 | 用途 |
| --- | --- |
| `archive_dir(src, store_root, *, keep, force)` | 整个目录快照；内容与最近一份一致时跳过，返回 `None` |
| `archive_files(files, store_root, *, keep, force)` | 文件集快照（`{rel_key: Path}`），保留相对结构，供分散/部分备份 |
| `restore_dir(store_root, ts, target)` | 整目录替换 `target`（先删后拷） |
| `list_times(root)` | 时间倒序时间戳（目录名即时间戳） |
| `get_backup_dir(store_root, ts)` | 定位单份归档；`ts` 非法格式或目录不存在返回 `None`（报错由调用方/`restore_dir` 负责） |
| `dir_files(source)` | 目录 → 相对文件集 |
| `file_set_hash(files)` | 文件集指纹（rel 键 + 大小 + 字节） |

关键语义：

- **去重**：与最近一份指纹一致则跳过（`file_set_hash` 相同）。
- **`force=True`**：内容一致也强制归档——恢复前存底，让「恢复前的配置」必然有
  自己的时间戳条目。
- **`keep`**：每个 `store_root` 独立保留池，超出清理最旧；默认 `KEEP_COUNT=10`。
- 目录名即时间戳（`%Y%m%d-%H%M%S`，同秒冲突加 `-N` 后缀）。

## 分层职责（关键，别混）

`app/utils/config_archive.py` 只做**文件/目录级快照与回写**，不感知任何脚本结构：

- 什么算「配置」（含排除规则，如 ZzzOd 排除 `MAS-` 槽）由**专项的收集函数**决定。
- 归档时机（`set_*` 注入前、配置会话基线注入前、直控页进入前）由专项编排。
- 恢复后动作（字段回填到 MAS 表单、重建合成视图、清 sidecar）由专项在
  `restore_dir` 之后执行——原语不隐含任何业务。

**不要往公共原语里加专项分支或 any 类型参数**；专有逻辑进专项或邻近 helper。

## 接入步骤

1. 定 `store_root` 布局，专项独立（如 `data/{script_id}/{Adapter}Backups/...`）；
   一个根下分多类（如 `onedragon` / `mas/{slot}`）各自成独立保留池。
2. 定备份对象：整目录 → `archive_dir`；只挑部分文件 → 收集函数 + `archive_files`。
3. 在「动手前」挂归档点，用 `suppress(Exception)` 包裹——归档失败绝不中止运行
   （ZzzOd `AutoProxy._prepare_injection` / `ScriptConfigTask` 为参考）。
4. 恢复：先 `force=True` 归档当前 → `restore_dir` 回写 → 专项执行恢复后语义；
   误恢复必须可找回（「恢复前状态」在列表里有明确条目）。
5. UI 列备份：`list_times` 倒序。

## 参数化兼容（槽原理不同也成立）

| 专项差异 | 吸收方式 |
| --- | --- |
| 槽/目录布局不同 | `src` 任意目录；`store_root` 按专项定义（模块级 layout 函数归专项） |
| 只备份子集 / 需排除运行时内容 | `archive_files` + 专项收集函数 |
| 保留份数不同 | `keep` 参数 |
| 恢复语义（回填/视图/sidecar） | 专项恢复后钩子，原语只回写文件 |
| 运行中实时共享文件 | 原语不覆盖；用专项既有锁（SRC 式串行化）防恢复与运行抢文件 |

硬限制：原语只覆盖**文件型**配置；非文件状态（注册表快照如 HSR 分辨率、进程态）
由专项自理。ConfigItem 字段与原生 YAML 的往返留在专项，归档层从不解析脚本配置。

## 检查清单

- [ ] `store_root` 专项独立，保留池边界明确
- [ ] 归档点捕获的是未被本次 MAS 操作触碰的状态（动手前）
- [ ] 恢复前 `force` 归档当前，误恢复可找回
- [ ] 恢复后业务（回填 / 视图 / sidecar）在专项层
- [ ] 归档包 `suppress`，失败不中止运行
- [ ] 公共原语无专项分支
- [ ] `tests/task/` 有最小回归（去重跳过 + 恢复闭环，参照 `test_zzzod_config_yaml.py`）