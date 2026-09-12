<template>
  <div class="form-section">
    <div class="section-header">
      <h3>{{ t('edit.managed.title') }}</h3>
    </div>

    <a-alert
      v-if="!boundProjectId"
      class="managed-alert"
      type="info"
      show-icon
      :message="t('edit.managed.notImportedTitle')"
      :description="t('edit.managed.notImportedDesc')"
    />

    <a-descriptions v-else :column="3" size="small" class="managed-summary">
      <a-descriptions-item :label="t('edit.managed.project')">
        {{ boundProjectId }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('edit.managed.version')">
        {{ boundVersion || '-' }}
      </a-descriptions-item>
      <a-descriptions-item :label="t('edit.managed.payloadSize')">
        {{ formatBytes(projection?.payloadSizeBytes ?? 0) }}
      </a-descriptions-item>
    </a-descriptions>

    <a-alert
      v-if="projection"
      class="managed-alert"
      type="success"
      show-icon
      :message="
        t('edit.managed.strippedTitle', {
          saved: formatBytes(projection.savedBytes ?? 0),
          percent: (projection.savedPercent ?? 0).toFixed(2),
        })
      "
    >
      <template #description>
        <div>
          {{
            t('edit.managed.strippedDesc', {
              shells: (projection.shellFamilies ?? []).join(' / ') || '-',
              count: projection.excludedCount,
            })
          }}
        </div>
        <a-typography-link v-if="excludedRows.length" @click="excludedOpen = true">
          {{ t('edit.managed.viewExcluded') }}
        </a-typography-link>
      </template>
    </a-alert>

    <a-row v-if="managedPreviewEnabled" :gutter="16" class="managed-import-row">
      <a-col :span="16">
        <a-form-item :label="t('edit.managed.sourcePath')">
          <a-input
            :value="sourcePath"
            :placeholder="t('edit.managed.sourcePlaceholder')"
            allow-clear
            @update:value="(value: string) => (sourcePath = value)"
          />
        </a-form-item>
      </a-col>
      <a-col :span="8">
        <a-form-item :label="' '">
          <a-button
            type="primary"
            :loading="importing"
            :disabled="!sourcePath.trim()"
            @click="handleImport"
          >
            {{ t('edit.managed.import') }}
          </a-button>
        </a-form-item>
      </a-col>
    </a-row>

    <div v-if="boundProjectId" class="managed-versions">
      <div class="versions-header">
        <span class="versions-title">{{ t('edit.managed.versions') }}</span>
        <a-button size="small" :loading="loadingVersions" @click="refreshVersions">
          {{ t('edit.managed.refresh') }}
        </a-button>
      </div>
      <a-table
        :columns="versionColumns"
        :data-source="versions"
        :pagination="false"
        :loading="loadingVersions"
        size="small"
        row-key="version"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'version'">
            <span>{{ record.version }}</span>
            <a-tag v-if="record.current" color="green" class="version-tag">
              {{ t('edit.managed.current') }}
            </a-tag>
            <a-tag v-if="record.pinned" color="orange" class="version-tag">
              {{ t('edit.managed.pinned') }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'sizeBytes'">
            {{ formatBytes(record.sizeBytes ?? 0) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button
              type="link"
              size="small"
              :disabled="record.current || busy"
              @click="handleSwitch(record.version)"
            >
              {{ t('edit.managed.switchTo') }}
            </a-button>
            <a-button
              type="link"
              size="small"
              danger
              :disabled="record.current || busy"
              @click="handleDelete(record.version)"
            >
              {{ t('edit.managed.delete') }}
            </a-button>
          </template>
        </template>
      </a-table>
    </div>

    <a-modal
      v-model:open="excludedOpen"
      :title="t('edit.managed.excludedTitle')"
      :footer="null"
      width="640px"
    >
      <a-table
        :columns="excludedColumns"
        :data-source="excludedRows"
        :pagination="{ pageSize: 12 }"
        size="small"
        row-key="path"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { Modal, message } from 'ant-design-vue'
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import type { MaaFWManagedVersionItem } from '@/api'
import { useMaaFWManagedApi } from '@/composables/useMaaFWManagedApi'
import { useMaaFWManagedPreview } from '@/composables/useMaaFWManagedPreview'

const { t } = useI18n()

const props = defineProps<{
  scriptId: string
  /** 脚本配置的 Managed 段；ProjectManifest 是 JSON 字符串或已解析的对象 */
  managed: Record<string, unknown> | null | undefined
}>()

const emit = defineEmits<{ imported: [] }>()

const {
  importing,
  loadingVersions,
  busy,
  importProject,
  listVersions,
  switchVersion,
  deleteVersion,
  readProjection,
} = useMaaFWManagedApi()

// 导入是「进门」，版本表是「房间」：开关只管前者。
const { enabled: managedPreviewEnabled, load: loadManagedPreview } = useMaaFWManagedPreview()
const sourcePath = ref('')
const versions = ref<MaaFWManagedVersionItem[]>([])
const excludedOpen = ref(false)

const boundProjectId = computed(() => String(props.managed?.ProjectId ?? '').trim())
const boundVersion = computed(() => String(props.managed?.Version ?? '').trim())

const manifest = computed<unknown>(() => {
  const raw = props.managed?.ProjectManifest
  if (typeof raw !== 'string') return raw ?? null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
})
const projection = computed(() => readProjection(manifest.value))

const excludedRows = computed(() =>
  Object.entries(projection.value?.excludedReasons ?? {}).map(([path, reason]) => ({
    path,
    reason,
  }))
)

const versionColumns = computed(() => [
  { title: t('edit.managed.version'), key: 'version', dataIndex: 'version' },
  { title: t('edit.managed.size'), key: 'sizeBytes', dataIndex: 'sizeBytes', width: 120 },
  { title: t('edit.managed.lastUsed'), key: 'lastUsedAt', dataIndex: 'lastUsedAt', width: 180 },
  { title: t('edit.managed.action'), key: 'action', width: 160 },
])

const excludedColumns = computed(() => [
  { title: t('edit.managed.excludedPath'), dataIndex: 'path', key: 'path', ellipsis: true },
  { title: t('edit.managed.excludedReason'), dataIndex: 'reason', key: 'reason', width: 200 },
])

function formatBytes(bytes: number): string {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = bytes
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`
}

async function refreshVersions() {
  if (!boundProjectId.value) return
  const result = await listVersions(boundProjectId.value)
  if (!result.ok) {
    message.error(result.message)
    return
  }
  versions.value = result.versions
}

async function handleImport() {
  const result = await importProject({
    sourcePath: sourcePath.value.trim(),
    scriptId: props.scriptId,
  })
  if (!result.ok) {
    // 闸门拒绝的理由（依赖不合规、ABI 未知……）就是用户要看的东西，别缩成一句失败。
    Modal.error({ title: t('edit.managed.importFailed'), content: result.message, width: 560 })
    return
  }
  message.success(result.message)
  sourcePath.value = ''
  emit('imported')
  await refreshVersions()
}

async function handleSwitch(version: string) {
  const result = await switchVersion({
    projectId: boundProjectId.value,
    version,
    scriptId: props.scriptId,
  })
  if (!result.ok) {
    message.error(result.message)
    return
  }
  message.success(result.message)
  emit('imported')
  await refreshVersions()
}

function handleDelete(version: string) {
  Modal.confirm({
    title: t('edit.managed.deleteTitle', { version }),
    content: t('edit.managed.deleteContent'),
    okType: 'danger',
    onOk: async () => {
      const result = await deleteVersion(boundProjectId.value, version)
      if (!result.ok) {
        // current / pinned / references / lease 的阻断理由原样展示。
        Modal.error({ title: t('edit.managed.deleteBlocked'), content: result.message })
        return
      }
      message.success(result.message)
      await refreshVersions()
    },
  })
}

watch(boundProjectId, value => {
  if (value) void refreshVersions()
  else versions.value = []
})

onMounted(() => {
  void loadManagedPreview()
  if (boundProjectId.value) void refreshVersions()
})
</script>

<style scoped>
.managed-alert {
  margin-bottom: 16px;
}

.managed-summary {
  margin-bottom: 16px;
}

.managed-import-row {
  margin-top: 4px;
}

.managed-versions {
  margin-top: 8px;
}

.versions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.versions-title {
  font-weight: 600;
}

.version-tag {
  margin-left: 8px;
}
</style>
