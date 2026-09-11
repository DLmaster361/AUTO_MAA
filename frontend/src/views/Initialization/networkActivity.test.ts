import { describe, expect, it } from 'vitest'
import {
  EMPTY_NETWORK_ACTIVITY,
  NETWORK_PROBE_STAGE,
  reduceNetworkActivity,
} from './networkActivity'
import type { NetworkActivity } from './networkActivity'

function probeRunning(source: string, bytesPerSecond?: number) {
  return { runtimeStage: NETWORK_PROBE_STAGE, runtimeStatus: 'running', source, bytesPerSecond }
}

function probeDone(message: string) {
  return { runtimeStage: NETWORK_PROBE_STAGE, runtimeStatus: 'succeeded', message }
}

const download = {
  runtimeStage: 'uv.download',
  runtimeStatus: 'running',
  item: 'uv-x86_64-pc-windows-msvc.zip',
  source: 'aliyun',
  bytesPerSecond: 3355443,
  current: 9437184,
  total: 18874368,
}

describe('reduceNetworkActivity', () => {
  it('旧链路与旧版 Runtime 的进度没有这些字段，状态原样不动', () => {
    const state = reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, {
      runtimeStage: 'workspace.clone',
      runtimeStatus: 'running',
    })
    expect(state).toBe(EMPTY_NETWORK_ACTIVITY)
    expect(reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, {})).toBe(EMPTY_NETWORK_ACTIVITY)
  })

  it('测速按到达顺序累积，同一个源再来一次就地替换，succeeded 记下最终顺序并保留列表', () => {
    let state: NetworkActivity = EMPTY_NETWORK_ACTIVITY
    state = reduceNetworkActivity(state, probeRunning('aliyun', 3355443))
    state = reduceNetworkActivity(state, probeRunning('github', 0))
    state = reduceNetworkActivity(state, probeRunning('cnb', 2202010))
    state = reduceNetworkActivity(state, probeRunning('github', 524288))

    expect(state.probe).toEqual({
      entries: [
        { source: 'aliyun', bytesPerSecond: 3355443 },
        { source: 'github', bytesPerSecond: 524288 },
        { source: 'cnb', bytesPerSecond: 2202010 },
      ],
      summary: null,
    })

    state = reduceNetworkActivity(state, probeDone('测速完成，下载顺序：aliyun → cnb → github'))
    expect(state.probe?.summary).toBe('测速完成，下载顺序：aliyun → cnb → github')
    expect(state.probe?.entries).toHaveLength(3)
  })

  it('探测失败没带速度时按 0 记', () => {
    const state = reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, probeRunning('github'))
    expect(state.probe?.entries).toEqual([{ source: 'github', bytesPerSecond: 0 }])
  })

  it('上一轮收口后再来的测速属于新一轮，不和旧列表混在一起', () => {
    let state: NetworkActivity = EMPTY_NETWORK_ACTIVITY
    state = reduceNetworkActivity(state, probeRunning('aliyun', 3355443))
    state = reduceNetworkActivity(state, probeDone('测速完成，下载顺序：aliyun'))
    state = reduceNetworkActivity(state, probeRunning('gh-proxy', 2097152))

    expect(state.probe).toEqual({
      entries: [{ source: 'gh-proxy', bytesPerSecond: 2097152 }],
      summary: null,
    })

    // 没有 running 直接 succeeded 的一轮也是空列表 + 新文案
    state = reduceNetworkActivity(state, probeDone('测速完成，下载顺序：gh-proxy'))
    state = reduceNetworkActivity(state, probeDone('测速完成，没有可用源'))
    expect(state.probe).toEqual({ entries: [], summary: '测速完成，没有可用源' })
  })

  it('pending 之类的测速事件不改状态', () => {
    const state = reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, {
      runtimeStage: NETWORK_PROBE_STAGE,
      runtimeStatus: 'pending',
      source: 'aliyun',
    })
    expect(state).toBe(EMPTY_NETWORK_ACTIVITY)
  })

  it('带文件名的进度换成传输细节并清掉测速列表', () => {
    let state: NetworkActivity = EMPTY_NETWORK_ACTIVITY
    state = reduceNetworkActivity(state, probeRunning('aliyun', 3355443))
    state = reduceNetworkActivity(state, download)

    expect(state).toEqual({
      probe: null,
      transfer: {
        stage: 'uv.download',
        item: 'uv-x86_64-pc-windows-msvc.zip',
        source: 'aliyun',
        bytesPerSecond: 3355443,
        current: 9437184,
        total: 18874368,
      },
    })
  })

  it('同一 stage 里没带文件名的事件不清传输细节，换了 stage 才清', () => {
    let state = reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, download)
    const kept = reduceNetworkActivity(state, {
      runtimeStage: 'uv.download',
      runtimeStatus: 'running',
    })
    expect(kept).toBe(state)

    state = reduceNetworkActivity(state, { runtimeStage: 'uv.verify', runtimeStatus: 'succeeded' })
    expect(state.transfer).toBeNull()
  })

  it('桥接合成的段收口（没有 runtimeStage）也会清掉传输细节', () => {
    const state = reduceNetworkActivity(reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, download), {})
    expect(state.transfer).toBeNull()
  })

  it('测速开始时清掉上一次的传输细节', () => {
    const state = reduceNetworkActivity(
      reduceNetworkActivity(EMPTY_NETWORK_ACTIVITY, download),
      probeRunning('pypi', 419430)
    )
    expect(state.transfer).toBeNull()
    expect(state.probe?.entries).toEqual([{ source: 'pypi', bytesPerSecond: 419430 }])
  })
})
