/**
 * 日志文件增量读取
 *
 * 日志页每次刷新只需要上次之后新增的部分，主进程按字节偏移读取，不再整份读回。
 */

import { promises as fsPromises } from 'fs'

export interface LogIncrement {
  /** 新增内容；reset 为 true 时是当前全文 */
  content: string
  /** 读取后的字节偏移，下一次从这里继续 */
  size: number
  /** 文件变小或消失（轮转/清空）时为 true，调用方应整体替换 */
  reset: boolean
}

/**
 * 从 fromOffset（字节）起读取日志新增部分。
 *
 * 文件不存在视为空；文件长度小于 fromOffset 视为被轮转或清空，返回全文并标记 reset。
 */
export async function readLogIncrement(logPath: string, fromOffset: number): Promise<LogIncrement> {
  const start = Math.max(0, Math.floor(fromOffset))
  let handle: fsPromises.FileHandle
  try {
    handle = await fsPromises.open(logPath, 'r')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return { content: '', size: 0, reset: start > 0 }
    }
    throw error
  }

  try {
    const { size } = await handle.stat()
    const reset = size < start
    const position = reset ? 0 : start
    const length = size - position
    if (length <= 0) {
      return { content: '', size, reset }
    }
    const buffer = Buffer.alloc(length)
    const { bytesRead } = await handle.read(buffer, 0, length, position)
    return {
      content: buffer.toString('utf-8', 0, bytesRead),
      size: position + bytesRead,
      reset,
    }
  } finally {
    await handle.close()
  }
}

/**
 * 读取整份日志；lines 大于 0 时只返回最后 N 行。文件不存在返回空串。
 */
export async function readLogContent(logPath: string, lines?: number): Promise<string> {
  let content: string
  try {
    content = await fsPromises.readFile(logPath, 'utf-8')
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return ''
    }
    throw error
  }
  if (!lines || lines <= 0) {
    return content
  }
  return content.split('\n').slice(-lines).join('\n')
}
