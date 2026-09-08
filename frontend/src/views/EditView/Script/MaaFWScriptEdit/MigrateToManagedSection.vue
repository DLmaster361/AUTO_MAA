<template>
  <div class="form-section">
    <div class="section-header">
      <h3>{{ t('edit.migrate.title') }}</h3>
    </div>

    <a-alert type="info" show-icon :message="t('edit.migrate.pitch')">
      <template #description>
        <div>{{ t('edit.migrate.desc') }}</div>
        <a-button
          type="primary"
          class="migrate-button"
          :disabled="!sourcePath"
          @click="open = true"
        >
          {{ t('edit.migrate.action') }}
        </a-button>
        <div v-if="!sourcePath" class="form-hint">{{ t('edit.migrate.needPath') }}</div>
      </template>
    </a-alert>

    <a-modal
      v-model:open="open"
      :title="t('edit.migrate.confirmTitle')"
      :confirm-loading="migrating"
      :ok-text="t('edit.migrate.action')"
      @ok="handleMigrate"
    >
      <p>{{ t('edit.migrate.confirmBody', { path: sourcePath }) }}</p>
      <a-checkbox v-model:checked="deleteSource">
        {{ t('edit.migrate.deleteSource') }}
      </a-checkbox>
      <!-- 删原目录不可撤销，所以勾上之后必须再说一次它到底会做什么。 -->
      <a-alert
        v-if="deleteSource"
        class="migrate-warning"
        type="warning"
        show-icon
        :message="t('edit.migrate.deleteWarning', { path: sourcePath })"
      />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { Modal, message } from 'ant-design-vue'
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useMaaFWManagedApi } from '@/composables/useMaaFWManagedApi'

const { t } = useI18n()

const props = defineProps<{
  scriptId: string
  /** 当前的 Info.Path；为空时无从迁移 */
  sourcePath: string
}>()

const emit = defineEmits<{ migrated: [] }>()

const { migrating, migrateToManaged } = useMaaFWManagedApi()

const open = ref(false)
const deleteSource = ref(false)

async function handleMigrate() {
  const result = await migrateToManaged({
    scriptId: props.scriptId,
    deleteSource: deleteSource.value,
  })
  if (!result.ok) {
    // 导入闸门的拒绝理由就是用户要看的东西：迁移不成多半是项目本身不合规。
    Modal.error({ title: t('edit.migrate.failed'), content: result.message, width: 560 })
    return
  }
  open.value = false
  // 迁移成了但原目录没删掉是「部分成功」，用警告说清楚，不能吞成一句成功。
  if (result.data?.sourceDeleteError) {
    Modal.warning({ title: t('edit.migrate.partial'), content: result.message, width: 560 })
  } else {
    message.success(result.message)
  }
  emit('migrated')
}
</script>

<style scoped>
.migrate-button {
  margin-top: 12px;
}

.migrate-warning {
  margin-top: 12px;
}
</style>
