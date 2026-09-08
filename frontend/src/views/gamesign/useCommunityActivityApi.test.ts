import { beforeEach, describe, expect, it, vi } from 'vitest'

class FakeApiError extends Error {
  body: unknown
  constructor(message: string, body?: unknown) {
    super(message)
    this.body = body
  }
}

const queryActivityRequest = vi.fn()

vi.mock('@/api', () => ({
  ApiError: FakeApiError,
  CommunityService: {
    queryCommunityActivityApiToolsCommunityActivityQueryPost: (...args: unknown[]) =>
      queryActivityRequest(...args),
  },
}))

const { useCommunityActivityApi } = await import('./useCommunityActivityApi')

describe('useCommunityActivityApi.queryActivity', () => {
  beforeEach(() => {
    queryActivityRequest.mockReset()
  })

  it('把账号筛选原样传给后端', async () => {
    queryActivityRequest.mockResolvedValue({ code: 200, data: [] })

    await useCommunityActivityApi().queryActivity(['account-1'])

    expect(queryActivityRequest).toHaveBeenCalledWith({ accountIds: ['account-1'] })
  })

  it('默认查询全部账号', async () => {
    queryActivityRequest.mockResolvedValue({ code: 200, data: [] })

    await useCommunityActivityApi().queryActivity()

    expect(queryActivityRequest).toHaveBeenCalledWith({ accountIds: null })
  })

  it('补齐缺省字段：可选数组变空数组，可选文本变空串', async () => {
    queryActivityRequest.mockResolvedValue({
      code: 200,
      data: [
        {
          account: '账号组',
          accountUid: 'account-1',
          game: '原神',
          platform: '米游社',
          status: 'success',
        },
      ],
    })

    const [snapshot] = await useCommunityActivityApi().queryActivity()

    expect(snapshot).toMatchObject({
      completed: null,
      target: null,
      tasks: [],
      resources: [],
      reason: '',
      updatedAt: '',
      roleName: '',
      roleUid: '',
      server: '',
      source: '',
    })
  })

  it('任务缺少 period 时补成 daily，已有值保持不变', async () => {
    queryActivityRequest.mockResolvedValue({
      code: 200,
      data: [
        {
          account: '账号组',
          accountUid: 'account-1',
          game: '终末地',
          platform: '森空岛',
          status: 'success',
          tasks: [
            { name: '每日事务', completed: 1, target: 3, status: '进行中' },
            {
              name: '蚀像寻遗',
              completed: 2,
              target: 5,
              status: '进行中',
              period: 'periodic',
            },
          ],
        },
      ],
    })

    const [snapshot] = await useCommunityActivityApi().queryActivity()

    expect(snapshot.tasks.map(task => task.period)).toEqual(['daily', 'periodic'])
  })

  it('completed / target 为 0 时保留 0，不被当成缺省', async () => {
    queryActivityRequest.mockResolvedValue({
      code: 200,
      data: [
        {
          account: '账号组',
          accountUid: 'account-1',
          game: '原神',
          platform: '米游社',
          status: 'success',
          completed: 0,
          target: 0,
        },
      ],
    })

    const [snapshot] = await useCommunityActivityApi().queryActivity()

    expect(snapshot.completed).toBe(0)
    expect(snapshot.target).toBe(0)
  })

  it('业务码非 200 时抛出后端给的消息', async () => {
    queryActivityRequest.mockResolvedValue({ code: 409, message: '日常便笺正在查询中' })

    await expect(useCommunityActivityApi().queryActivity()).rejects.toThrow('日常便笺正在查询中')
  })

  it('data 不是数组时按响应格式无效处理', async () => {
    queryActivityRequest.mockResolvedValue({ code: 200, data: null })

    await expect(useCommunityActivityApi().queryActivity()).rejects.toThrow('日常便笺响应格式无效')
  })

  it('ApiError 优先取响应体里的 message', async () => {
    queryActivityRequest.mockRejectedValue(
      new FakeApiError('Internal Server Error', { message: '社区接口暂时不可用' })
    )

    await expect(useCommunityActivityApi().queryActivity()).rejects.toThrow('社区接口暂时不可用')
  })

  it('ApiError 响应体没有 message 时回落到 HTTP 消息', async () => {
    queryActivityRequest.mockRejectedValue(new FakeApiError('Internal Server Error', {}))

    await expect(useCommunityActivityApi().queryActivity()).rejects.toThrow('Internal Server Error')
  })

  it('非 Error 抛出物被包成统一的查询失败', async () => {
    queryActivityRequest.mockRejectedValue('boom')

    await expect(useCommunityActivityApi().queryActivity()).rejects.toThrow('日常便笺查询失败')
  })
})
