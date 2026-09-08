import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { RepositoryService } from './repositoryService'

vi.mock('electron', () => ({ app: { getVersion: () => '5.5.0-beta.3' } }))
vi.mock('./logger', () => ({
  getLogger: () => ({
    error: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    verbose: vi.fn(),
    debug: vi.fn(),
    silly: vi.fn(),
  }),
}))

/**
 * ESM 下 vi.spyOn 改不了模块导出，这里把 fs 整体包一层，
 * 用 hooks 在单条用例里注入失败或记录调用顺序。
 */
const hooks: {
  copyFileSync?: (src: string, dst: string) => void
  mkdirSync?: (target: string) => void
} = {}

vi.mock('fs', async importOriginal => {
  const actual = await importOriginal<typeof import('fs')>()
  const wrapped = {
    ...actual,
    copyFileSync: (src: fs.PathLike, dst: fs.PathLike, mode?: number) => {
      hooks.copyFileSync?.(String(src), String(dst))
      return actual.copyFileSync(src, dst, mode)
    },
    mkdirSync: (target: fs.PathLike, opts?: fs.MakeDirectoryOptions & { recursive: true }) => {
      hooks.mkdirSync?.(String(target))
      return actual.mkdirSync(target, opts)
    },
  }
  return { ...wrapped, default: wrapped }
})

/**
 * copyToRoot 是私有方法，这里直接取出来调用：它是源码部署的唯一落盘出口，
 * 中断后留下残缺 app/ 正是 #544 的根因，值得单独立测。
 */
type CopyToRoot = () => Promise<void>

let appRoot = ''

const makeCopyToRoot = (): CopyToRoot => {
  const svc = new RepositoryService(appRoot, {} as never, 'dev')
  return (svc as unknown as { copyToRoot: CopyToRoot }).copyToRoot.bind(svc)
}

/** 在 repo/ 下造一份可部署的源码 */
const writeRepo = (appContent: string) => {
  const repo = path.join(appRoot, 'repo')
  fs.mkdirSync(path.join(repo, 'app', 'core'), { recursive: true })
  fs.mkdirSync(path.join(repo, 'res'), { recursive: true })
  fs.mkdirSync(path.join(repo, '.git'), { recursive: true })
  fs.writeFileSync(path.join(repo, 'app', 'core', 'timer.py'), appContent)
  fs.writeFileSync(path.join(repo, 'app', '__init__.py'), appContent)
  fs.writeFileSync(path.join(repo, 'res', 'version.json'), '{}')
  fs.writeFileSync(path.join(repo, '.git', 'HEAD'), 'ref: refs/heads/dev')
  fs.writeFileSync(path.join(repo, 'main.py'), appContent)
}

/** 在 appRoot 下造一份「上一版」已部署的源码 */
const writeExistingDeploy = () => {
  fs.mkdirSync(path.join(appRoot, 'app', 'core'), { recursive: true })
  fs.writeFileSync(path.join(appRoot, 'app', 'core', 'timer.py'), 'old')
  fs.writeFileSync(path.join(appRoot, 'app', '__init__.py'), 'old')
  fs.writeFileSync(path.join(appRoot, 'app', 'legacy.py'), 'old-only')
}

beforeEach(() => {
  appRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'mas-repo-'))
})

afterEach(() => {
  delete hooks.copyFileSync
  delete hooks.mkdirSync
  fs.rmSync(appRoot, { recursive: true, force: true })
})

describe('copyToRoot', () => {
  it('正常部署：内容换新，上一版残留被清掉，不留 .new / .old', async () => {
    writeRepo('new')
    writeExistingDeploy()

    await makeCopyToRoot()()

    expect(fs.readFileSync(path.join(appRoot, 'app', 'core', 'timer.py'), 'utf-8')).toBe('new')
    expect(fs.existsSync(path.join(appRoot, 'app', 'legacy.py'))).toBe(false)
    expect(fs.readFileSync(path.join(appRoot, '.git', 'HEAD'), 'utf-8')).toBe('ref: refs/heads/dev')
    expect(fs.existsSync(path.join(appRoot, 'app.new'))).toBe(false)
    expect(fs.existsSync(path.join(appRoot, 'app.old'))).toBe(false)
  })

  it('复制中途失败：原有 app/ 完整回滚，不会留下残缺目录', async () => {
    writeRepo('new')
    writeExistingDeploy()

    // 复制 app/ 的第二个文件时抛错，模拟杀软/占用导致的 EPERM
    let calls = 0
    hooks.copyFileSync = () => {
      calls += 1
      if (calls === 2) {
        throw Object.assign(new Error('EPERM: operation not permitted'), {
          code: 'EPERM',
        })
      }
    }

    await expect(makeCopyToRoot()()).rejects.toThrow('EPERM')

    // 关键断言：旧版本原封不动，而不是被删掉一半
    expect(fs.readFileSync(path.join(appRoot, 'app', 'core', 'timer.py'), 'utf-8')).toBe('old')
    expect(fs.readFileSync(path.join(appRoot, 'app', '__init__.py'), 'utf-8')).toBe('old')
    expect(fs.readFileSync(path.join(appRoot, 'app', 'legacy.py'), 'utf-8')).toBe('old-only')
    expect(fs.existsSync(path.join(appRoot, 'app.new'))).toBe(false)
    expect(fs.existsSync(path.join(appRoot, 'app.old'))).toBe(false)
  })

  it('.git 排在 app / res 之后，避免「版本已最新但源码残缺」', async () => {
    writeRepo('new')

    const order: string[] = []
    hooks.mkdirSync = target => {
      const name = path.basename(target)
      if (name === 'app.new' || name === 'res.new' || name === '.git.new') {
        order.push(name)
      }
    }

    await makeCopyToRoot()()

    expect(order).toEqual(['app.new', 'res.new', '.git.new'])
  })

  it('目标此前不存在时也能部署，且不留 .old', async () => {
    writeRepo('new')

    await makeCopyToRoot()()

    expect(fs.readFileSync(path.join(appRoot, 'main.py'), 'utf-8')).toBe('new')
    expect(fs.existsSync(path.join(appRoot, 'main.py.old'))).toBe(false)
    expect(fs.existsSync(path.join(appRoot, 'main.py.new'))).toBe(false)
  })
})
