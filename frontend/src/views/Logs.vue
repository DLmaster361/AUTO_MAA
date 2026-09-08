<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { SyncOutlined } from '@ant-design/icons-vue'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { useLogHighlight } from '@/composables/useLogHighlight'
const logger = window.electronAPI.getLogger('日志查看')
const route = useRoute()
const { registerLogLanguage, editorTheme } = useLogHighlight()

defineOptions({ name: 'LogViewer' })

// 日志显示模式类型
type LogMode = 'follow' | 'browse'

const logs = ref<string>('')
// 首次 loadLogs 之前就先算加载中，否则空日志的提示会在挂载那一帧闪一下
const loading = ref(true)
const logMode = ref<LogMode>('follow')
// 主进程用 `#/logs?file=frontend` 指定落地时选中哪一份；启动路径要的是前端日志，
// 那时后端还没起来，app.log 打开就是空的。没带参数时维持原来的默认。
const selectedLogFile = ref<'app' | 'frontend'>(
  route.query.file === 'frontend' ? 'frontend' : 'app'
)
const realTimeEnabled = ref(true)
let editorInstance: any = null
let refreshInterval: ReturnType<typeof setInterval> | null = null

// 文件不存在时主进程返回空串。直接把空串塞进编辑器只会得到一片白，说一句人话。
const emptyHint = computed(() =>
  selectedLogFile.value === 'app'
    ? '后端日志还是空的。后端这一程可能还没启动起来，先看「前端日志」。'
    : '前端日志还是空的。'
)

// Monaco Editor 配置
const editorOptions = {
  readOnly: true,
  fontSize: 13,
  lineNumbers: 'on',
  minimap: { enabled: false },
  scrollBeyondLastLine: false,
  automaticLayout: true,
  wordWrap: 'on',
  wrappingIndent: 'same',
  scrollbar: {
    vertical: 'auto',
    horizontal: 'auto',
    useShadows: false,
  },
} as const

// 处理编辑器挂载
const handleEditorMount = (editor: any) => {
  editorInstance = editor
  // 初始滚动到底部
  if (logMode.value === 'follow' && logs.value) {
    nextTick(() => scrollToBottom())
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (editorInstance) {
    const lineCount = editorInstance.getModel()?.getLineCount()
    if (lineCount) {
      editorInstance.revealLine(lineCount)
      editorInstance.setScrollTop(editorInstance.getScrollHeight())
    }
  }
}

// 切换日志模式
const toggleLogMode = () => {
  if (logMode.value === 'follow') {
    // 从保持最新切换到自由浏览
    logMode.value = 'browse'
  } else {
    // 从自由浏览切换到保持最新
    logMode.value = 'follow'
    setTimeout(scrollToBottom, 10)
  }
}

// 加载日志
const loadLogs = async (silent = false) => {
  if (!silent) {
    loading.value = true
  }
  try {
    const fileName = selectedLogFile.value === 'app' ? 'app.log' : 'frontend.log'
    const logContent = await (window as any).electronAPI?.getLogs?.(0, fileName)
    if (logContent) {
      logs.value = logContent
      // 只在保持最新模式下自动滚动
      if (logMode.value === 'follow') {
        nextTick(() => scrollToBottom())
      }
    } else {
      logs.value = ''
    }
  } catch (error) {
    if (!silent) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      logger.error(`加载日志失败: ${errorMsg}`)
      message.error('加载日志失败')
    }
  } finally {
    if (!silent) {
      loading.value = false
    }
  }
}

// 开始实时刷新
const startRealTimeRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  refreshInterval = setInterval(() => {
    loadLogs(true) // 静默刷新
  }, 2000) // 每2秒刷新一次
}

// 停止实时刷新
const stopRealTimeRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}

// 切换实时刷新
const toggleRealTime = () => {
  realTimeEnabled.value = !realTimeEnabled.value
  if (realTimeEnabled.value) {
    startRealTimeRefresh()
    message.success('已启用自动更新')
  } else {
    stopRealTimeRefresh()
    message.info('已停止自动更新')
  }
}

// 切换日志文件
const onLogFileChange = () => {
  loadLogs()
}

// 监听日志内容变化
watch(logs, value => {
  // 内容清空时编辑器整个被 v-else 卸载，留着旧实例会拿到已 dispose 的 model
  if (!value) {
    editorInstance = null
    return
  }
  if (logMode.value === 'follow') {
    nextTick(() => scrollToBottom())
  }
})

onMounted(() => {
  loadLogs()
  if (realTimeEnabled.value) {
    startRealTimeRefresh()
  }
  // 窗口已经开着时主进程不会重新载入，靠这条推送换文件
  window.electronAPI.onLogSelectFile?.(file => {
    selectedLogFile.value = file
    void loadLogs()
  })
})

onUnmounted(() => {
  stopRealTimeRefresh()
  window.electronAPI.removeLogSelectFileListener?.()
})
</script>

<template>
  <div class="logs-container">
    <div class="logs-header">
      <h1 class="page-title">日志查看</h1>
      <div class="header-actions">
        <a-space :size="12">
          <a-radio-group
            v-model:value="selectedLogFile"
            button-style="solid"
            @change="onLogFileChange"
          >
            <a-radio-button value="app">后端日志</a-radio-button>
            <a-radio-button value="frontend">前端日志</a-radio-button>
          </a-radio-group>

          <a-button :type="logMode === 'follow' ? 'primary' : 'default'" @click="toggleLogMode">
            {{ logMode === 'follow' ? '保持最新' : '自由浏览' }}
          </a-button>

          <a-button :type="realTimeEnabled ? 'primary' : 'default'" @click="toggleRealTime">
            <template #icon>
              <SyncOutlined :spin="realTimeEnabled" />
            </template>
            {{ realTimeEnabled ? '自动更新' : '停止更新' }}
          </a-button>
        </a-space>
      </div>
    </div>

    <div class="logs-content">
      <a-spin :spinning="loading" tip="加载日志中...">
        <div class="editor-container" :class="{ 'log-locked': logMode === 'follow' }">
          <p v-if="!loading && !logs" class="log-empty">{{ emptyHint }}</p>
          <vue-monaco-editor
            v-else
            v-model:value="logs"
            language="logfile"
            :theme="editorTheme"
            :options="editorOptions"
            class="log-editor"
            @before-mount="registerLogLanguage"
            @mount="handleEditorMount"
          />
        </div>
      </a-spin>
    </div>
  </div>
</template>

<style scoped>
.logs-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-shrink: 0;
}

.page-title {
  margin: 0;
  font-size: 32px;
  font-weight: 700;
  background: linear-gradient(135deg, var(--ant-color-primary), var(--ant-color-primary-hover));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.logs-content {
  flex: 1;
  background: var(--ant-color-bg-container);
  border-radius: 12px;
  padding: 20px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.editor-container {
  flex: 1;
  border: 1px solid var(--ant-color-border);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s ease;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 保持最新模式：添加视觉提示 */
.log-locked {
  border-color: var(--ant-color-primary);
  box-shadow: 0 0 0 2px var(--ant-color-primary-bg);
}

.log-editor {
  flex: 1;
  min-height: 0;
}

.log-empty {
  flex: 1;
  display: grid;
  place-items: center;
  margin: 0;
  padding: 24px;
  color: var(--ant-color-text-tertiary);
  text-align: center;
}

:deep(.monaco-editor) {
  border-radius: 8px;
}

:deep(.ant-spin-nested-loading),
:deep(.ant-spin-container) {
  height: 100%;
  display: flex;
  flex-direction: column;
}
</style>
