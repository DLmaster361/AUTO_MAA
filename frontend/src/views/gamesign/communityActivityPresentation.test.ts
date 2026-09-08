import { describe, expect, it } from 'vitest'
import { presentActivity } from './communityActivityPresentation'
import type { ActivityResource, ActivitySnapshot, ActivityTask } from './useCommunityActivityApi'

const task = (name: string, extra: Partial<ActivityTask> = {}): ActivityTask => ({
  name,
  completed: 1,
  target: 3,
  status: '进行中',
  period: 'daily',
  ...extra,
})

const resource = (name: string, extra: Partial<ActivityResource> = {}): ActivityResource => ({
  name,
  current: 60,
  target: 200,
  status: '恢复中',
  ...extra,
})

const snapshot = (game: string, extra: Partial<ActivitySnapshot> = {}): ActivitySnapshot =>
  ({
    account: '账号组',
    accountUid: 'account-1',
    game,
    platform: '米游社',
    status: 'success',
    completed: 1,
    target: 3,
    tasks: [],
    resources: [],
    reason: '',
    updatedAt: '2026-09-08T10:00:00+08:00',
    roleName: '旅行者',
    roleUid: '100000000',
    server: '天空岛',
    source: 'dailyNote',
    ...extra,
  }) as ActivitySnapshot

describe('presentActivity', () => {
  it('把该游戏的重点资源按配置顺序提到 featured', () => {
    const result = presentActivity(
      snapshot('原神', {
        resources: [resource('洞天宝钱'), resource('参量质变仪'), resource('原粹树脂')],
      })
    )

    expect(result.featured.map(metric => metric.name)).toEqual(['原粹树脂', '洞天宝钱'])
    expect(result.groups.flatMap(group => group.metrics.map(metric => metric.name))).toEqual([
      '参量质变仪',
    ])
  })

  it('过滤掉经验类指标，任务与资源两侧都不展示', () => {
    const result = presentActivity(
      snapshot('原神', {
        tasks: [task('每日委托'), task('战令经验'), task('Battle Pass EXP')],
        resources: [resource('原粹树脂'), resource('experience pool')],
      })
    )

    const shown = [
      ...result.featured.map(metric => metric.name),
      ...result.groups.flatMap(group => group.metrics.map(metric => metric.name)),
    ]
    expect(shown).toEqual(['原粹树脂', '每日委托'])
  })

  it('把任务的 completed / target 映射成指标的 current / target', () => {
    const result = presentActivity(
      snapshot('原神', { tasks: [task('每日委托', { completed: 2, target: 4 })] })
    )

    expect(result.groups[0].metrics[0]).toMatchObject({
      name: '每日委托',
      current: 2,
      target: 4,
      period: 'daily',
    })
  })

  it('绝区零把「今日活跃度」任务也提到 featured', () => {
    const result = presentActivity(
      snapshot('绝区零', {
        tasks: [task('今日活跃度', { completed: 400, target: 400 }), task('每日委托')],
        resources: [resource('电量'), resource('刮刮乐进度')],
      })
    )

    expect(result.featured.map(metric => metric.name)).toEqual(['电量', '今日活跃度'])
    expect(result.overview).toBe(true)
    expect(result.groups.map(group => group.labelKey)).toEqual([
      'gamesign.activity.noteTasks',
      'gamesign.activity.resources',
    ])
    expect(result.groups[0].metrics.map(metric => metric.name)).toEqual(['每日委托'])
    expect(result.groups[1].metrics.map(metric => metric.name)).toEqual(['刮刮乐进度'])
  })

  it('明日方舟同样是概览布局，但资源分组排在任务分组之前', () => {
    const result = presentActivity(
      snapshot('明日方舟', {
        tasks: [task('每日任务')],
        resources: [resource('理智'), resource('公开招募')],
      })
    )

    expect(result.overview).toBe(true)
    expect(result.featured.map(metric => metric.name)).toEqual(['理智'])
    expect(result.groups.map(group => group.labelKey)).toEqual([
      'gamesign.activity.resources',
      'gamesign.activity.noteTasks',
    ])
  })

  it('其余游戏合并成一个无标题分组，任务排在资源之前', () => {
    const result = presentActivity(
      snapshot('星穹铁道', {
        tasks: [task('每日实训')],
        resources: [resource('开拓力'), resource('每日活跃')],
      })
    )

    expect(result.overview).toBe(false)
    expect(result.groups).toHaveLength(1)
    expect(result.groups[0].labelKey).toBe('')
    expect(result.groups[0].metrics.map(metric => metric.name)).toEqual(['每日实训', '每日活跃'])
  })

  it('丢弃空分组，全部指标都进 featured 时不留下空壳', () => {
    const result = presentActivity(snapshot('绝区零', { resources: [resource('电量')] }))

    expect(result.featured.map(metric => metric.name)).toEqual(['电量'])
    expect(result.groups).toEqual([])
  })

  it('未知游戏没有重点资源，全部落到普通分组', () => {
    const result = presentActivity(
      snapshot('未知游戏', { resources: [resource('理智')], tasks: [task('每日任务')] })
    )

    expect(result.featured).toEqual([])
    expect(result.groups[0].metrics.map(metric => metric.name)).toEqual(['每日任务', '理智'])
  })
})
