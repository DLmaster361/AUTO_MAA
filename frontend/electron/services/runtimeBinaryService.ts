/**
 * Runtime 可执行文件随本体一起更新
 *
 * `auto-mas-runtime.exe` 由安装包捆绑进 `resources/`，此前只能靠重装整包升级：本体源码
 * （`repo/`）能被 `bootstrap --version` 换成新版本，Runtime 却停在装机那天的版本，于是
 * 「新本体 + 旧 Runtime」这种从未联调过的组合会在用户机器上出现。
 *
 * 这里把 Runtime 的版本钉扎在本体源码里（`repo/res/runtime.json`），让它跟着源码走：
 *
 * 1. 发布 CI 从仓库根的 `res/runtime.json` 读版本与 SHA-256，下载并校验后捆绑进安装包；
 * 2. 本体更新把新的 `res/runtime.json` 带进 `repo/`；
 * 3. 每次经 Runtime 启动后端时（`bootstrap --if-needed` 之后、`supervise` 之前）问一次磁盘上
 *    那个 exe 自己是什么版本，与钉扎不一致就下载钉扎的那一版、校验 SHA-256 后原地替换。
 *
 * 几条刻意的取舍：
 *
 * - **判据是版本号相等，不是「钉扎的更新才换」。** 本体回退到旧版本时 Runtime 必须跟着退
 *   回去，否则回退这条路仍然会得到没联调过的组合。
 * - **判身份用自报版本，不用文件哈希；哈希只用来校验下载物。** 理由见
 *   {@link readInstalledRuntimeVersion}。
 * - **原地替换，不做多版本并存。** 校验通过的新文件直接盖回原路径，`resolveRuntimeExecutable()`
 *   与所有持有旧路径字符串的地方都不用动——`RuntimeClient` 每条命令都是重新 spawn 同一个
 *   路径。替换本身的原子性见 {@link replaceRuntimeBinary}。
 * - **镜像顺序自己实现，不复用 `MirrorRotationService`。** 后者的 `sortMirrors()` 会把 key 里
 *   含 `github` 的源提到最前（为初始化拉源码的测试版场景加的），套到这里正好把国内用户最
 *   连不上的官方源排到第一个。这里的顺序必须是「代理在前、官方兜底」。
 * - **失败不阻断启动。** 调用方只记警告继续跑：拿不到新 Runtime 时旧的仍然能监督后端，
 *   而把用户卡在「更新完就打不开」比跑在旧 Runtime 上糟得多。
 */

import * as crypto from 'crypto'
import * as fs from 'fs'
import * as path from 'path'

import { SmartDownloader } from './downloadService'
import { getLogger } from './logger'
import { RUNTIME_EXE_ENV, createRuntimeClient } from './runtime'

const logger = getLogger('Runtime二进制')

// ==================== 钉扎文件 ====================

/** 钉扎文件在源码树里的相对路径，仓库根与受管 `repo/` 下同名同位。 */
export const RUNTIME_PIN_RELATIVE_PATH = path.join('res', 'runtime.json')

/** 钉扎文件的大小上限：它只有两个字段，超过说明读到的不是它。 */
const MAX_PIN_FILE_BYTES = 64 * 1024

/**
 * 版本号的合法形态：`v` 加点分数字，可跟一段预发布/构建后缀。
 *
 * 与 `runtimeUpdateService` 里那条同源——版本号会被拼进下载 URL，带 `/` 或空白的值必须在
 * 这里挡掉，不能指望远端返回 404。
 */
const RUNTIME_VERSION_PATTERN = /^v\d+(\.\d+)*([-+][0-9A-Za-z.-]+)?$/

const SHA256_PATTERN = /^[0-9a-f]{64}$/

/** 本体对 Runtime 版本的钉扎。 */
export interface RuntimeBinaryPin {
  /** 发布标签，同时是 Release 的 tag 与资产名里的版本段，例如 `v0.1.4`。 */
  version: string
  /** `auto-mas-runtime-<version>.exe` 的 SHA-256，小写十六进制，只用来校验下载物。 */
  sha256: string
}

/**
 * 读取并校验钉扎文件。
 *
 * 文件缺失、JSON 损坏、字段非法一律返回 null（调用方按「本体没有钉扎」处理而不是报错）：
 * 携带该文件之前发布的本体版本本来就没有它，回退到那些版本时不该把启动流程弄失败。
 */
export function readRuntimeBinaryPin(sourceRoot: string): RuntimeBinaryPin | null {
  const pinPath = path.join(sourceRoot, RUNTIME_PIN_RELATIVE_PATH)
  try {
    const stat = fs.statSync(pinPath)
    if (!stat.isFile() || stat.size > MAX_PIN_FILE_BYTES) return null

    const parsed = JSON.parse(fs.readFileSync(pinPath, 'utf8')) as {
      version?: unknown
      sha256?: unknown
    }
    const version = typeof parsed.version === 'string' ? parsed.version.trim() : ''
    const sha256 = typeof parsed.sha256 === 'string' ? parsed.sha256.trim().toLowerCase() : ''

    if (!RUNTIME_VERSION_PATTERN.test(version)) {
      logger.warn(`${pinPath} 的 version 非法，忽略该钉扎: ${String(parsed.version)}`)
      return null
    }
    if (!SHA256_PATTERN.test(sha256)) {
      logger.warn(`${pinPath} 的 sha256 非法，忽略该钉扎: ${String(parsed.sha256)}`)
      return null
    }
    return { version, sha256 }
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code !== 'ENOENT') {
      logger.warn(
        `读取 ${pinPath} 失败，按未钉扎处理: ${
          error instanceof Error ? error.message : String(error)
        }`
      )
    }
    return null
  }
}

// ==================== 下载源 ====================

/**
 * GitHub Release 下载前缀，按尝试顺序排列，官方源永远兜底在最后。
 *
 * 与本仓库 `mirrorService` 的 `repo` 源、Runtime 自己 `internal/mirror` 的 uv 源用的是同一批
 * gh-proxy 家族——它们是这批用户实测能连上的那几个。这份表刻意写死在代码里而不进
 * `mirror_config.json`：云端配置是整体替换 `mirrors` 对象的，新增一类会在云端还没跟上时
 * 变成 undefined。
 */
const RUNTIME_DOWNLOAD_PREFIXES: readonly { key: string; name: string; prefix: string }[] = [
  {
    key: 'ghproxy_cloudflare',
    name: 'gh-proxy (Cloudflare)',
    prefix: 'https://gh-proxy.com/https://github.com',
  },
  {
    key: 'ghproxy_fastly',
    name: 'gh-proxy (Fastly CDN)',
    prefix: 'https://cdn.gh-proxy.com/https://github.com',
  },
  {
    key: 'ghproxy_edgeone',
    name: 'gh-proxy (EdgeOne)',
    prefix: 'https://edgeone.gh-proxy.com/https://github.com',
  },
  { key: 'github', name: 'GitHub 官方', prefix: 'https://github.com' },
]

/** Runtime 发布仓库，与发布 CI 的 `gh release download -R` 同一个。 */
const RUNTIME_RELEASE_REPO = 'AUTO-MAS-Project/AUTO-MAS-Runtime'

/** 一个候选下载源。 */
export interface RuntimeBinarySource {
  key: string
  name: string
  url: string
}

/** 按尝试顺序列出某个版本的全部候选下载地址。 */
export function buildRuntimeBinarySources(version: string): RuntimeBinarySource[] {
  const asset = `auto-mas-runtime-${version}.exe`
  return RUNTIME_DOWNLOAD_PREFIXES.map(source => ({
    key: source.key,
    name: source.name,
    url: `${source.prefix}/${RUNTIME_RELEASE_REPO}/releases/download/${version}/${asset}`,
  }))
}

// ==================== 校验 ====================

/** 流式计算 SHA-256；文件不存在或读失败返回 null。 */
export function hashFileSha256(filePath: string): Promise<string | null> {
  return new Promise(resolve => {
    const hash = crypto.createHash('sha256')
    const stream = fs.createReadStream(filePath)
    stream.on('error', () => resolve(null))
    stream.on('data', chunk => hash.update(chunk))
    stream.on('end', () => resolve(hash.digest('hex')))
  })
}

/**
 * 问磁盘上那个 exe 自己是什么版本（`auto-mas-runtime.exe version`）。
 *
 * **判据是它自报的版本而不是文件哈希**：发布资产的哈希只能证明「从网上下到的那份没坏」，
 * 一旦本地那份被任何后处理动过一个字节（重签名、杀软隔离后还原、打包工具改写），哈希就
 * 永远对不上，而版本没变——按哈希判会让每次启动都白下载十几兆。版本比对不受这些影响。
 *
 * 跑不起来或没报版本时返回 null，调用方按「需要换」处理：一个连版本都问不出来的 exe，
 * 本来也该换掉。
 */
async function readInstalledRuntimeVersion(
  runtimePath: string,
  appRoot: string
): Promise<string | null> {
  try {
    const client = createRuntimeClient({ runtimePath, appRoot })
    const outcome = await client.run(['version'])
    if (!outcome.success) return null

    const reported = outcome.result.details.runtimeVersion ?? outcome.hello?.runtimeVersion
    return typeof reported === 'string' && reported.trim() !== '' ? reported.trim() : null
  } catch (error) {
    logger.warn(
      `查询现有 Runtime 版本失败: ${error instanceof Error ? error.message : String(error)}`
    )
    return null
  }
}

// ==================== 同步结果 ====================

export type RuntimeBinarySyncStatus = 'unpinned' | 'current' | 'upgraded' | 'skipped' | 'failed'

export const RUNTIME_BINARY_DOWNLOAD_FAILED = 'RUNTIME_BINARY_DOWNLOAD_FAILED'
export const RUNTIME_BINARY_REPLACE_FAILED = 'RUNTIME_BINARY_REPLACE_FAILED'

export interface RuntimeBinarySyncResult {
  /**
   * - `unpinned`：本体没带钉扎文件（该版本发布时还没有这个机制），什么都不做；
   * - `current`：磁盘上的 exe 自报的版本就是钉扎的那一版；
   * - `upgraded`：已经换成钉扎的那一版；
   * - `skipped`：`AUTO_MAS_RUNTIME_EXE` 指定了自带的 Runtime，不去动开发者的文件；
   * - `failed`：需要换但没换成，调用方按「记警告继续用旧的」处理。
   */
  status: RuntimeBinarySyncStatus
  pin?: RuntimeBinaryPin
  error?: string
  code?: string
}

export interface RuntimeBinarySyncProgress {
  /** 0~100；总量未知时停在 0。 */
  progress: number
  message: string
}

export interface RuntimeBinarySyncOptions {
  /** 当前生效的 `auto-mas-runtime.exe` 路径。 */
  runtimePath: string
  /** 传给 Runtime 的 `--app-root`，这里只用于问它自己的版本。 */
  appRoot: string
  /** 受管源码根（`<app-root>/repo`），钉扎文件在它下面的 `res/runtime.json`。 */
  sourceRoot: string
  onProgress?: (progress: RuntimeBinarySyncProgress) => void
  /** 本轮同步的总时间预算，缺省 {@link RUNTIME_BINARY_SYNC_BUDGET_MS}。 */
  budgetMs?: number
  /** 单个下载源的时长上限，缺省 {@link RUNTIME_BINARY_SOURCE_TIMEOUT_MS}。 */
  sourceTimeoutMs?: number
  /** 测试注入；默认用真实下载器。 */
  download?: (
    url: string,
    savePath: string,
    onProgress?: (progress: { progress: number }) => void
  ) => Promise<{ success: boolean; error?: string }>
  /** 测试注入；默认真的去跑 `auto-mas-runtime.exe version`。 */
  readVersion?: (runtimePath: string, appRoot: string) => Promise<string | null>
}

// ==================== 同步 ====================

/**
 * 下载中的临时文件与让路后的旧文件都用固定后缀，便于下次同步清扫残留。
 *
 * 临时文件名是 `<exe>.download-<token>`，每次向一个源发起下载都换一个：下载器不支持取消，
 * 放弃一个慢源之后它仍在后台往自己的文件里写，若各源共用一个文件名，它会在下一个源
 * 校验通过之后把文件截断重写，让一个没校验过的文件盖到 exe 上。
 */
const DOWNLOAD_SUFFIX = '.download'
const BACKUP_SUFFIX = '.old'

/**
 * 一轮同步的总时间预算。
 *
 * 卡死的连接由 `SmartDownloader` 自己的超时兜住（HEAD 10 秒、分片 30 秒空闲），但「连得上、
 * 就是慢」不会触发那些超时——四个源依次各拉一遍十几兆，最坏能把启动挂上一个钟头。这里在
 * 换下一个源之前查一次预算，超了就当本轮失败，继续用现有 Runtime 启动，下次启动再试；
 * 已经开始的那一次由 {@link RUNTIME_BINARY_SOURCE_TIMEOUT_MS} 兜住。
 */
export const RUNTIME_BINARY_SYNC_BUDGET_MS = 10 * 60 * 1000

/**
 * 单个下载源的时长上限，与剩余预算取小。
 *
 * 取总预算的一半：一个被限速到十几 KB/s 的源最多只能吃掉半份预算，保证至少还有机会换
 * 一个源。超时后只是不再等它——下载器没有取消接口，那次下载会继续跑到自己结束为止，
 * 所以每次尝试都写自己的临时文件（见 {@link DOWNLOAD_SUFFIX}），结束后再顺手清掉。
 */
export const RUNTIME_BINARY_SOURCE_TIMEOUT_MS = RUNTIME_BINARY_SYNC_BUDGET_MS / 2

const defaultDownload: NonNullable<RuntimeBinarySyncOptions['download']> = (
  url,
  savePath,
  onProgress
) => new SmartDownloader().download(url, savePath, onProgress)

/** 正在进行的那一次同步；后来者复用它的结果而不是再开一份下载。 */
interface SyncFlight {
  promise: Promise<RuntimeBinarySyncResult>
  /** 所有等着这次同步的调用方的进度回调，后来者也能看到进度。 */
  listeners: Set<(progress: RuntimeBinarySyncProgress) => void>
}

let inFlight: SyncFlight | null = null

/**
 * 让磁盘上的 Runtime 与本体钉扎一致。
 *
 * 只在 managed 链路、`bootstrap` 已经把 `repo/` 换成目标版本之后调用；此时没有任何进程
 * 持有 exe，可以安全替换。
 *
 * 同一时刻只允许一次同步在途：两个挂接点（启动链路与更新链路）之间隔着有意重启标志，
 * 正常界面操作不会撞上，但开发者工具里的重启按钮与 `backend-start` IPC 能在更新链路的
 * 同步还没结束时再触发一次启动。两份下载各写各的临时文件不会互相污染，但会白拉一份
 * 十几兆并把同一个 exe 换两次，所以后来者直接等前一次的结果。
 */
export function syncRuntimeBinary(
  options: RuntimeBinarySyncOptions
): Promise<RuntimeBinarySyncResult> {
  if (inFlight) {
    logger.info('已有一次 Runtime 同步在进行，等待其结果')
    if (options.onProgress) inFlight.listeners.add(options.onProgress)
    return inFlight.promise
  }

  const listeners: SyncFlight['listeners'] = new Set()
  if (options.onProgress) listeners.add(options.onProgress)
  const promise = runSync({
    ...options,
    onProgress: progress => {
      for (const listener of listeners) listener(progress)
    },
  }).finally(() => {
    if (inFlight?.promise === promise) inFlight = null
  })
  inFlight = { promise, listeners }
  return promise
}

async function runSync(options: RuntimeBinarySyncOptions): Promise<RuntimeBinarySyncResult> {
  const { runtimePath, appRoot, sourceRoot } = options

  const pin = readRuntimeBinaryPin(sourceRoot)
  if (!pin) return { status: 'unpinned' }

  // 开发者用 AUTO_MAS_RUNTIME_EXE 指到自己编译的那份时，绝不能被线上钉扎覆盖掉。
  const configured = process.env[RUNTIME_EXE_ENV]?.trim()
  if (configured && path.resolve(configured) === path.resolve(runtimePath)) {
    logger.info(`${RUNTIME_EXE_ENV} 指定了 Runtime，跳过随本体更新`)
    return { status: 'skipped', pin }
  }

  // 上次被打断（应用退出、断电）留下的半截文件与让路用的旧文件在这里统一清掉，不等到
  // 真要替换时才清：版本一直对得上时那条路根本不会走到，十几兆就会一直留在安装目录里。
  const directory = path.dirname(runtimePath)
  const backupPath = `${runtimePath}${BACKUP_SUFFIX}`
  removeResiduals(runtimePath)

  const installed = await (options.readVersion ?? readInstalledRuntimeVersion)(runtimePath, appRoot)
  if (installed === pin.version) {
    logger.debug(`Runtime 已是本体要求的 ${pin.version}`)
    return { status: 'current', pin }
  }

  logger.info(`现有 Runtime ${installed ?? '版本未知'}，本体要求 ${pin.version}，开始下载并替换`)

  const downloaded = await downloadPinned(pin, runtimePath, options)
  if (!downloaded.success) {
    return {
      status: 'failed',
      pin,
      error: downloaded.error,
      code: RUNTIME_BINARY_DOWNLOAD_FAILED,
    }
  }

  try {
    replaceRuntimeBinary(runtimePath, downloaded.downloadPath, backupPath)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    logger.error(`替换 Runtime 可执行文件失败: ${message}`)
    removeQuietly(downloaded.downloadPath)
    return {
      status: 'failed',
      pin,
      error: `替换 ${directory} 下的 Runtime 失败：${message}`,
      code: RUNTIME_BINARY_REPLACE_FAILED,
    }
  }

  logger.info(`Runtime 已随本体更新到 ${pin.version}`)
  options.onProgress?.({ progress: 100, message: `Runtime 已更新到 ${pin.version}` })
  return { status: 'upgraded', pin }
}

type DownloadOutcome = { success: true; downloadPath: string } | { success: false; error: string }

/** 逐个源尝试下载并校验 SHA-256，任一源拿到正确文件即返回该文件的路径。 */
async function downloadPinned(
  pin: RuntimeBinaryPin,
  runtimePath: string,
  options: RuntimeBinarySyncOptions
): Promise<DownloadOutcome> {
  const download = options.download ?? defaultDownload
  const sources = buildRuntimeBinarySources(pin.version)
  const failures: string[] = []
  const deadline = Date.now() + (options.budgetMs ?? RUNTIME_BINARY_SYNC_BUDGET_MS)
  const sourceTimeoutMs = options.sourceTimeoutMs ?? RUNTIME_BINARY_SOURCE_TIMEOUT_MS

  for (const [index, source] of sources.entries()) {
    const remainingMs = deadline - Date.now()
    if (remainingMs <= 0) {
      failures.push('已用满本轮时间预算，剩余下载源不再尝试')
      logger.warn('Runtime 下载已用满时间预算，本轮放弃')
      break
    }

    const label = `${source.name}（${index + 1}/${sources.length}）`
    const message = `正在从 ${label} 下载 Runtime ${pin.version}`
    logger.info(`尝试从 ${label} 下载 Runtime ${pin.version}: ${source.url}`)
    options.onProgress?.({ progress: 0, message })

    const downloadPath = nextDownloadPath(runtimePath)
    const result = await downloadWithTimeout(
      download,
      source.url,
      downloadPath,
      Math.min(remainingMs, sourceTimeoutMs),
      progress => options.onProgress?.({ progress: progress.progress, message })
    )
    if (!result.success) {
      failures.push(`${source.name}: ${result.error}`)
      // 超时放弃的那次仍在后台写自己的文件，等它自己结束时再清；这里删了也会被写回来。
      if (!result.timedOut) removeQuietly(downloadPath)
      continue
    }

    const actual = await hashFileSha256(downloadPath)
    if (actual === pin.sha256) return { success: true, downloadPath }

    // 代理源可能把错误页当正文返回，也可能是发布资产被换过；两种都只能换下一个源。
    failures.push(`${source.name}: SHA-256 不匹配（得到 ${actual ?? '不可读'}）`)
    logger.warn(`${label} 下载的文件校验失败，换下一个源`)
    removeQuietly(downloadPath)
  }

  return { success: false, error: `全部下载源均失败 —— ${failures.join('；')}` }
}

let downloadSequence = 0

/** 每次尝试各用一个临时文件名，理由见 {@link DOWNLOAD_SUFFIX}。 */
function nextDownloadPath(runtimePath: string): string {
  downloadSequence += 1
  const token = `${Date.now().toString(36)}-${downloadSequence.toString(36)}`
  return `${runtimePath}${DOWNLOAD_SUFFIX}-${token}`
}

/**
 * 给一次下载加时长上限。
 *
 * 下载器没有取消接口，超时后只是不再等它：在途的那次会继续把数据写进 `savePath`，跑完后
 * 才由这里顺手删掉；它的进度也不再往上报，免得界面上出现两个源的进度交错跳动。
 */
async function downloadWithTimeout(
  download: NonNullable<RuntimeBinarySyncOptions['download']>,
  url: string,
  savePath: string,
  timeoutMs: number,
  onProgress: (progress: { progress: number }) => void
): Promise<{ success: boolean; error?: string; timedOut?: boolean }> {
  let abandoned = false
  let attempt: Promise<{ success: boolean; error?: string }>
  try {
    attempt = download(url, savePath, progress => {
      if (!abandoned) onProgress(progress)
    })
  } catch (error) {
    return { success: false, error: error instanceof Error ? error.message : String(error) }
  }
  const settled = attempt.then(
    result => (result.success ? result : { success: false, error: result.error ?? '下载失败' }),
    error => ({ success: false, error: error instanceof Error ? error.message : String(error) })
  )

  let timer: ReturnType<typeof setTimeout> | undefined
  const timeout = new Promise<{ success: false; error: string; timedOut: true }>(resolve => {
    timer = setTimeout(() => {
      resolve({
        success: false,
        timedOut: true,
        error: `超过 ${Math.ceil(timeoutMs / 1000)} 秒仍未下载完成，放弃该源`,
      })
    }, timeoutMs)
    timer.unref?.()
  })

  try {
    const result = await Promise.race([settled, timeout])
    if ('timedOut' in result) {
      abandoned = true
      logger.warn(`${url} 下载超时，换下一个源；在途的下载结束后会清掉 ${savePath}`)
      void settled.then(() => removeQuietly(savePath))
    }
    return result
  } finally {
    if (timer) clearTimeout(timer)
  }
}

/** 清掉上次留下的全部临时文件（任意 token）与让路用的旧文件。 */
function removeResiduals(runtimePath: string): void {
  const directory = path.dirname(runtimePath)
  const basename = path.basename(runtimePath)
  let entries: string[]
  try {
    entries = fs.readdirSync(directory)
  } catch {
    return
  }
  for (const entry of entries) {
    if (
      entry === `${basename}${BACKUP_SUFFIX}` ||
      entry.startsWith(`${basename}${DOWNLOAD_SUFFIX}`)
    ) {
      removeQuietly(path.join(directory, entry))
    }
  }
}

/**
 * 原地替换。
 *
 * 首选一次 `rename` 直接盖过去：Node 在 Windows 上走 `MoveFileEx` 带
 * `MOVEFILE_REPLACE_EXISTING`，是原子的——中途断电也只会看到旧文件或新文件，不会出现
 * 「目录里没有 auto-mas-runtime.exe」这种一旦发生就只能重装的状态
 * （`resolveRuntimeExecutable()` 返回 null 后连本函数都进不来，残留自己好不了）。
 *
 * 只有目标被占用（正在运行的 exe 不能被覆盖，但可以被改名）时才退回两步走：先把旧文件
 * 改名让路，再挪新文件；挪失败就把旧文件改回来。
 */
function replaceRuntimeBinary(runtimePath: string, downloadPath: string, backupPath: string): void {
  try {
    fs.renameSync(downloadPath, runtimePath)
    return
  } catch (error) {
    if (!fs.existsSync(runtimePath)) throw error
    logger.info(
      `直接替换 Runtime 失败（${
        error instanceof Error ? error.message : String(error)
      }），改用改名让路的方式`
    )
  }

  fs.renameSync(runtimePath, backupPath)
  try {
    fs.renameSync(downloadPath, runtimePath)
  } catch (error) {
    try {
      fs.renameSync(backupPath, runtimePath)
    } catch {
      // 回滚也失败时保留 .old 供人工恢复，错误照原样抛给调用方。
    }
    throw error
  }

  removeQuietly(backupPath)
}

/** 删不掉就算了：残留文件会在下一次同步开始时再清一遍。 */
function removeQuietly(target: string): void {
  try {
    fs.rmSync(target, { force: true })
  } catch {
    // 忽略：文件可能仍被占用，不影响本次结果。
  }
}
