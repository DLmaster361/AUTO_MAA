import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  RUNTIME_APP_ENV,
  RUNTIME_HTTPS_PROXY_ENV,
  RUNTIME_HTTP_PROXY_ENV,
  RUNTIME_NO_PROXY_ENV,
  RUNTIME_TELEMETRY_ENV,
  buildRuntimeEnv,
} from './runtimeEnv'

const warn = vi.fn()

vi.mock('../logger', () => ({
  getLogger: () => ({
    error: vi.fn(),
    warn: (...args: unknown[]) => warn(...args),
    info: vi.fn(),
    verbose: vi.fn(),
    debug: vi.fn(),
    silly: vi.fn(),
  }),
}))

let appRoot: string

function writeBackendConfig(value: unknown): void {
  const configDir = path.join(appRoot, 'config')
  fs.mkdirSync(configDir, { recursive: true })
  fs.writeFileSync(path.join(configDir, 'Config.json'), JSON.stringify(value), 'utf8')
}

beforeEach(() => {
  warn.mockClear()
  appRoot = fs.mkdtempSync(path.join(os.tmpdir(), 'auto-mas-runtime-env-'))
})

afterEach(() => {
  fs.rmSync(appRoot, { recursive: true, force: true })
})

describe('buildRuntimeEnv', () => {
  it('Config.json 不存在时按开启处理，不设 AUTO_MAS_TELEMETRY', () => {
    expect(buildRuntimeEnv(appRoot)).toEqual({})
    expect(warn).not.toHaveBeenCalled()
  })

  it('IfEnableTelemetry 缺失时按开启处理', () => {
    writeBackendConfig({ Function: {} })

    expect(buildRuntimeEnv(appRoot)).toEqual({})
  })

  it('IfEnableTelemetry 为 true 时按开启处理', () => {
    writeBackendConfig({ Function: { IfEnableTelemetry: true } })

    expect(buildRuntimeEnv(appRoot)).toEqual({})
  })

  it('IfEnableTelemetry 为 false 时透传 AUTO_MAS_TELEMETRY=disabled', () => {
    writeBackendConfig({ Function: { IfEnableTelemetry: false } })

    expect(buildRuntimeEnv(appRoot)).toEqual({ [RUNTIME_TELEMETRY_ENV]: 'disabled' })
  })

  it('结果里不含任何 offline 相关的键——遥测与联网开关是两回事', () => {
    writeBackendConfig({ Function: { IfEnableTelemetry: false } })

    const env = buildRuntimeEnv(appRoot)
    expect(Object.keys(env)).toEqual([RUNTIME_TELEMETRY_ENV])
    expect(env).not.toHaveProperty('offline')
    expect(env).not.toHaveProperty('--offline')
  })

  it('Config.json 损坏时记 warning 并按开启处理', () => {
    const configDir = path.join(appRoot, 'config')
    fs.mkdirSync(configDir, { recursive: true })
    fs.writeFileSync(path.join(configDir, 'Config.json'), '{not json', 'utf8')

    expect(buildRuntimeEnv(appRoot)).toEqual({})
    expect(warn).toHaveBeenCalledOnce()
  })
})

describe('buildRuntimeEnv：出站代理', () => {
  it('配了合法代理时同时透传 HTTP_PROXY / HTTPS_PROXY / NO_PROXY', () => {
    writeBackendConfig({ Update: { ProxyAddress: 'http://127.0.0.1:7890' } })

    expect(buildRuntimeEnv(appRoot)).toEqual({
      [RUNTIME_HTTP_PROXY_ENV]: 'http://127.0.0.1:7890/',
      [RUNTIME_HTTPS_PROXY_ENV]: 'http://127.0.0.1:7890/',
      [RUNTIME_NO_PROXY_ENV]: '127.0.0.1,localhost,::1',
    })
    expect(warn).not.toHaveBeenCalled()
  })

  it('socks5 代理同样透传', () => {
    writeBackendConfig({ Update: { ProxyAddress: 'socks5://127.0.0.1:1080' } })

    expect(buildRuntimeEnv(appRoot)[RUNTIME_HTTPS_PROXY_ENV]).toBe('socks5://127.0.0.1:1080')
    expect(warn).not.toHaveBeenCalled()
  })

  // 真机上出现过：用户把模拟器安装路径填进了「网络代理」。原样导出会让 Runtime
  // 一条网络路都走不通，比不设代理更糟。
  it('本地路径这类非 URL 值一律忽略并记 warning', () => {
    writeBackendConfig({ Update: { ProxyAddress: 'D:\\虚拟C盘\\MuMuPlayer-12.0\\nx_main' } })

    expect(buildRuntimeEnv(appRoot)).toEqual({})
    expect(warn).toHaveBeenCalledOnce()
  })

  it('协议不在白名单里的一律忽略并记 warning', () => {
    writeBackendConfig({ Update: { ProxyAddress: 'file:///D:/proxy' } })

    expect(buildRuntimeEnv(appRoot)).toEqual({})
    expect(warn).toHaveBeenCalledOnce()
  })

  it('缺少主机名的一律忽略并记 warning', () => {
    writeBackendConfig({ Update: { ProxyAddress: 'http://' } })

    expect(buildRuntimeEnv(appRoot)).toEqual({})
    expect(warn).toHaveBeenCalledOnce()
  })

  it('空串与非字符串按没配处理，不记 warning', () => {
    writeBackendConfig({ Update: { ProxyAddress: '   ' } })
    expect(buildRuntimeEnv(appRoot)).toEqual({})

    writeBackendConfig({ Update: { ProxyAddress: 7890 } })
    expect(buildRuntimeEnv(appRoot)).toEqual({})

    expect(warn).not.toHaveBeenCalled()
  })

  it('代理与遥测开关互不影响', () => {
    writeBackendConfig({
      Function: { IfEnableTelemetry: false },
      Update: { ProxyAddress: 'http://127.0.0.1:7890' },
    })

    const env = buildRuntimeEnv(appRoot)
    expect(env[RUNTIME_TELEMETRY_ENV]).toBe('disabled')
    expect(env[RUNTIME_HTTPS_PROXY_ENV]).toBe('http://127.0.0.1:7890/')
  })
})

describe('buildRuntimeEnv：开发标记', () => {
  it('development 模式追加 AUTO_MAS_ENV=development', () => {
    expect(buildRuntimeEnv(appRoot, 'development')).toEqual({ [RUNTIME_APP_ENV]: 'development' })
  })

  it('development 模式且关闭遥测时两项同时透传', () => {
    writeBackendConfig({ Function: { IfEnableTelemetry: false } })

    expect(buildRuntimeEnv(appRoot, 'development')).toEqual({
      [RUNTIME_TELEMETRY_ENV]: 'disabled',
      [RUNTIME_APP_ENV]: 'development',
    })
  })

  it('managed / off / 未指定模式都不碰 AUTO_MAS_ENV', () => {
    expect(buildRuntimeEnv(appRoot, 'managed')).toEqual({})
    expect(buildRuntimeEnv(appRoot, 'off')).toEqual({})
    expect(buildRuntimeEnv(appRoot)).toEqual({})
  })
})
