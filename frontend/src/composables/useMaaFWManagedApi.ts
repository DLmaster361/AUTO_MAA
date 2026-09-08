import { ref } from 'vue'

import { MaaFwService } from '@/api'
import type {
  MaaFWManagedImportData,
  MaaFWManagedProjection,
  MaaFWManagedVersionItem,
} from '@/api'

/**
 * 托管 Project Store 的前端封装。
 *
 * 一律走生成的客户端，不手拼 axios。后端把闸门拒绝与删除阻断的原因放在 `message`
 * 里，这里原样交给调用方——那句话正是用户需要看到的东西。
 */
export function useMaaFWManagedApi() {
  const importing = ref(false)
  const loadingVersions = ref(false)
  const busy = ref(false)

  const fail = (message: string) => ({ ok: false as const, message })

  async function importProject(payload: {
    sourcePath: string
    scriptId?: string
    activate?: boolean
  }) {
    importing.value = true
    try {
      const res = await MaaFwService.importManagedMaafwProjectApiScriptsMaafwManagedImportPost({
        sourcePath: payload.sourcePath,
        scriptId: payload.scriptId ?? null,
        activate: payload.activate ?? true,
      })
      if (res.code !== 200 || !res.data) return fail(res.message ?? '')
      return {
        ok: true as const,
        data: res.data as MaaFWManagedImportData,
        message: res.message ?? '',
      }
    } catch (error) {
      return fail(error instanceof Error ? error.message : String(error))
    } finally {
      importing.value = false
    }
  }

  async function listVersions(projectId: string) {
    loadingVersions.value = true
    try {
      const res = await MaaFwService.listManagedMaafwVersionsApiScriptsMaafwManagedVersionsPost({
        projectId,
      })
      if (res.code !== 200 || !res.data) return fail(res.message ?? '')
      return {
        ok: true as const,
        current: res.data.current ?? null,
        versions: (res.data.versions ?? []) as MaaFWManagedVersionItem[],
      }
    } catch (error) {
      return fail(error instanceof Error ? error.message : String(error))
    } finally {
      loadingVersions.value = false
    }
  }

  async function switchVersion(payload: {
    projectId: string
    version: string
    scriptId?: string
  }) {
    busy.value = true
    try {
      const res = await MaaFwService.switchManagedMaafwVersionApiScriptsMaafwManagedSwitchPost({
        projectId: payload.projectId,
        version: payload.version,
        scriptId: payload.scriptId ?? null,
      })
      return res.code === 200
        ? { ok: true as const, message: res.message ?? '' }
        : fail(res.message ?? '')
    } catch (error) {
      return fail(error instanceof Error ? error.message : String(error))
    } finally {
      busy.value = false
    }
  }

  async function deleteVersion(projectId: string, version: string) {
    busy.value = true
    try {
      const res =
        await MaaFwService.deleteManagedMaafwVersionApiScriptsMaafwManagedVersionDeletePost({
          projectId,
          version,
        })
      // 被 current / pinned / references / lease 阻断时，原因就在 message 里。
      return res.code === 200
        ? { ok: true as const, message: res.message ?? '' }
        : fail(res.message ?? '')
    } catch (error) {
      return fail(error instanceof Error ? error.message : String(error))
    } finally {
      busy.value = false
    }
  }

  /** 把 manifest 里现成的脱壳统计取出来；后端已经算好，前端不重算。 */
  function readProjection(manifest: unknown): MaaFWManagedProjection | null {
    if (!manifest || typeof manifest !== 'object') return null
    const raw = manifest as Record<string, unknown>
    const projection = (raw.projection ?? {}) as Record<string, unknown>
    const shells = (raw.shells ?? {}) as Record<string, unknown>
    if (projection.savedBytes === undefined && projection.payloadSizeBytes === undefined) {
      return null
    }
    return {
      sourceSizeBytes: Number(projection.sourceSizeBytes ?? 0),
      payloadSizeBytes: Number(projection.payloadSizeBytes ?? 0),
      savedBytes: Number(projection.savedBytes ?? 0),
      savedPercent: Number(projection.savedPercent ?? 0),
      excludedCount: Array.isArray(projection.excluded) ? projection.excluded.length : 0,
      shellFamilies: Array.isArray(shells.families) ? (shells.families as string[]) : [],
      excludedReasons: (projection.excludedReasons ?? {}) as Record<string, string>,
    }
  }

  return {
    importing,
    loadingVersions,
    busy,
    importProject,
    listVersions,
    switchVersion,
    deleteVersion,
    readProjection,
  }
}
