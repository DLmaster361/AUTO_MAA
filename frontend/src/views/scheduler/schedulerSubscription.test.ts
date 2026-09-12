import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./useSchedulerLogic.ts', import.meta.url), 'utf8')

const sliceBetween = (start: string, end: string) => {
  const from = source.indexOf(start)
  expect(from, `缺少起始标记: ${start}`).toBeGreaterThan(-1)
  const to = source.indexOf(end, from)
  expect(to, `缺少结束标记: ${end}`).toBeGreaterThan(from)
  return source.slice(from, to)
}

describe('调度台任务订阅归属', () => {
  it('状态同步不重复订阅（运行期状态每秒推送，重复调用只会刷日志）', () => {
    const applyRuntimeState = sliceBetween(
      'const applyRuntimeStateToTab = (',
      'const applyRuntimeTaskSnapshot = ('
    )
    expect(applyRuntimeState).not.toContain('subscribeToTask(')
  })

  it('建台、启动与恢复路径仍会建立订阅', () => {
    expect(sliceBetween('const createSchedulerTabForTask = (', '// 计算属性')).toContain(
      'subscribeToTask('
    )
    expect(sliceBetween('const trackStartedTask = (', 'const removeSchedulerTab = (')).toContain(
      'subscribeToTask('
    )
    expect(sliceBetween('const startTask = async', 'const startTaskById =')).toContain(
      'subscribeToTask('
    )
    expect(
      sliceBetween('const initialize = () => {', '// 调试函数：检查所有调度台的订阅状态')
    ).toContain('subscribeToTask(')
  })
})
