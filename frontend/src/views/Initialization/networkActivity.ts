/**
 * 初始化页「网络细节」的纯状态归并。
 *
 * Runtime（M14 起）在下载前会对各镜像源测速，下载时会报出当前文件、字节进度、速度与来源；
 * 这些都随进度事件一条条到达，页面需要把它们攒成两种可展示的形态：
 *
 * - 测速：按到达顺序累积每个源的实测速度，`succeeded` 时记下 Runtime 给的最终顺序文案；
 * - 传输：只保留最新一条带文件名的进度。
 *
 * 判定只看 `runtimeStage` / `runtimeStatus` 与几个数值字段，不解析 `message` 文案。
 * 旧版 Runtime 与旧链路的进度没有这些字段，状态始终为空，界面与以前一致。
 */

/** 下载前测速的 Runtime stage。与 electron 侧 `NETWORK_PROBE_STAGE` 同值。 */
export const NETWORK_PROBE_STAGE = 'network.probe'

export interface NetworkProbeEntry {
  source: string
  /** 该源实测吞吐（字节/秒），探测失败为 0。 */
  bytesPerSecond: number
}

export interface NetworkProbe {
  entries: NetworkProbeEntry[]
  /** 本轮测速结束后 Runtime 给出的最终顺序文案；还在测时为 null。 */
  summary: string | null
}

export interface NetworkTransfer {
  /** 产生这条进度的 Runtime stage，用于判断后续无文件名的事件是否还属于同一次下载。 */
  stage: string
  item: string
  source?: string
  bytesPerSecond?: number
  current?: number
  total?: number
}

export interface NetworkActivity {
  probe: NetworkProbe | null
  transfer: NetworkTransfer | null
}

export const EMPTY_NETWORK_ACTIVITY: NetworkActivity = Object.freeze({
  probe: null,
  transfer: null,
})

/** 进度载荷里与网络细节有关的字段，全部可选。 */
export interface NetworkActivityPayload {
  runtimeStage?: string
  runtimeStatus?: string
  message?: string
  item?: string
  source?: string
  bytesPerSecond?: number
  current?: number
  total?: number
}

function reduceProbe(state: NetworkActivity, payload: NetworkActivityPayload): NetworkActivity {
  // 上一轮已经收口（有 summary）后再来的事件属于新一轮：uv/git、python、package-index
  // 各测各的，列表不能把几轮混在一起。
  const ongoing = state.probe && state.probe.summary === null ? state.probe : null

  if (payload.runtimeStatus === 'running' && payload.source) {
    const entry: NetworkProbeEntry = {
      source: payload.source,
      bytesPerSecond: payload.bytesPerSecond ?? 0,
    }
    const entries = ongoing ? [...ongoing.entries] : []
    const existing = entries.findIndex(item => item.source === entry.source)
    if (existing >= 0) {
      entries[existing] = entry
    } else {
      entries.push(entry)
    }
    return { probe: { entries, summary: null }, transfer: null }
  }

  if (payload.runtimeStatus === 'succeeded') {
    return {
      probe: { entries: ongoing?.entries ?? [], summary: payload.message ?? '' },
      transfer: null,
    }
  }

  return state
}

/**
 * 用一条进度载荷推进网络细节状态；无关的载荷原样返回同一个对象，方便调用方省掉一次赋值。
 */
export function reduceNetworkActivity(
  state: NetworkActivity,
  payload: NetworkActivityPayload
): NetworkActivity {
  if (payload.runtimeStage === NETWORK_PROBE_STAGE) {
    return reduceProbe(state, payload)
  }

  if (payload.item && payload.runtimeStage) {
    return {
      probe: null,
      transfer: {
        stage: payload.runtimeStage,
        item: payload.item,
        source: payload.source,
        bytesPerSecond: payload.bytesPerSecond,
        current: payload.current,
        total: payload.total,
      },
    }
  }

  // 同一个 stage 里没带文件名的事件（例如两个文件之间的间隙）不清掉正在展示的文件；
  // stage 换了（校验、解压、下一段）才说明这次下载已经结束。
  if (state.transfer && state.transfer.stage !== payload.runtimeStage) {
    return { probe: state.probe, transfer: null }
  }
  return state
}
