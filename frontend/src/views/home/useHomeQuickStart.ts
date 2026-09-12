import { translate as t } from '@/i18n'
import { ref } from 'vue'
import { message } from 'ant-design-vue'
import { TaskCreateIn } from '@/api/models/TaskCreateIn'
import { Service } from '@/api/services/Service'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import { getConfig, saveConfig } from '@/utils/config'
import { navigateTo } from '@/router'
import {
  launchHomeTasks,
  normalizeHomeQuickStartSelection,
  retainSelectedTaskIds,
  toHomeTaskOptions,
  type HomeTaskOption,
} from '@/views/home/homeQuickStartTasks'
import { useSchedulerLogic } from '@/views/scheduler/useSchedulerLogic'

interface HomeGreetingMessage {
  text: string
  author: string
}

const homeGreetingMessages: HomeGreetingMessage[] = [
  { text: '坐和放宽，脚本正在为你努力运行中。', author: 'AUTO-MAS项目组' },
  {
    text: '启动前请确认脚本路径已正确，否则它将无法找到自己。',
    author: 'AUTO-MAS项目组',
  },
  { text: '请勿™强制关闭AUTO-MAS，正在处理一些事情。', author: 'AUTO-MAS项目组' },
  { text: '好东西就要来了……别来无恙啊！', author: 'AUTO-MAS项目组' },
  { text: 'AUTO-MAS正在为你的设备匹配专属脚本设置。', author: 'AUTO-MAS项目组' },
  { text: '启动AUTO-MAS脚本系统，不要说我们没有警告过你。', author: 'AUTO-MAS项目组' },
  { text: '需要重启脚本是正常现象，请不要惊慌。', author: 'AUTO-MAS项目组' },
  {
    text: '你的设备正在准备就绪，准备好迎接脚本运行了吗？',
    author: 'AUTO-MAS项目组',
  },
  { text: '运行完成后，你的游戏进度可能会发生位移。', author: 'AUTO-MAS项目组' },
  { text: '我们的脚本协议更新了，你只能同意不能不同意。', author: 'AUTO-MAS项目组' },
  { text: '请耐心等待，进度条只是看起来不动而已。', author: 'AUTO-MAS项目组' },
  { text: '感谢你使用AUTO-MAS，你永远可以相信脚本的力量。', author: 'AUTO-MAS项目组' },
  { text: '正在应用最适合当前宇宙版本的脚本设置。', author: 'AUTO-MAS项目组' },
  {
    text: '你的请求很重要，AUTO-MAS正在以看似安静的方式处理它。',
    author: 'AUTO-MAS项目组',
  },
  { text: 'AUTO-MAS检测到一切正常，除非稍后它不正常。', author: 'AUTO-MAS项目组' },
  { text: '请稍候，系统正在把复杂问题包装成一个按钮。', author: 'AUTO-MAS项目组' },
  { text: '欢迎来到大雷主人361的世界……魔↗术↘技↻巧！', author: "T'a1mer" },
  { text: '海内存知己，天涯若比邻', author: '匿名' },
  {
    text: '注意到你已经有一段时间没有使用AUTO-MAS了。现在不启用 | 关闭',
    author: '匿名',
  },
  { text: '喵→喵↓↑喵~喵→喵↓↑喵~', author: 'qsy' },
  { text: '我说SRA是神有没有懂得！', author: "T'a1mer" },
  { text: '主人，欢迎回来喵。', author: "T'a3mer" },
  { text: '↑→↓↓↓', author: "T'a3mer" },
  { text: "我睡觉去了喵，有事请找T'amer喵(´∩｡• ᵕ •｡∩`)", author: "T'a3mer" },
  { text: 'AUTO-MAS即将在114514年32月5日支持maa-meow', author: "T'a1mer" },
  { text: '很不高兴为你服务喵😑', author: "T'a3mer" },
  {
    text: '非常感谢您支持并使用正版软件喵，支持正版打击盗版喵',
    author: "T'a3mer",
  },
  { text: '系统检测到一切正常——除非下一秒它突然觉得正常很无聊', author: '匿名' },
  { text: '喵一下代表启动，再喵一下代表它还在跑', author: '匿名' },
  {
    text: '运行结束后，你的游戏进度可能发生位移——物理意义上的，或精神意义上的',
    author: '匿名',
  },
  {
    text: '进度条看起来不动，是因为它在假装优雅，其实它在后台疯狂翻抽屉',
    author: '匿名',
  },
  {
    text: '你的请求很重要，AUTO-MAS 会用最安静、最漫长、最像卡死的方式处理它',
    author: '匿名',
  },
  { text: '在世界深处寻找你所想要的答案', author: '人' },
  { text: '到下次相遇时再次启程', author: '人' },
  { text: '也许一个切面并不足矣看到事情的全貌', author: '人' },
  { text: '您的请求正在被接受，还剩10...000年进行应答', author: '人' },
  { text: '关注DLmaster_361喵，关注DLmaster_361谢谢喵', author: '匿名' },
  { text: '也许在10086年以后MAS就能管理运行所有脚本', author: '匿名' },
]

const pickHomeGreeting = (): HomeGreetingMessage => {
  const index = Math.floor(Math.random() * homeGreetingMessages.length)
  return homeGreetingMessages[index] ?? homeGreetingMessages[0]
}

export const useHomeQuickStart = () => {
  const logger = window.electronAPI.getLogger('首页')
  const { playSound } = useAudioPlayer()
  const { trackStartedTask } = useSchedulerLogic()

  const homeGreeting = pickHomeGreeting()
  const commandTitle = ref(homeGreeting.text)
  const commandAuthor = ref(homeGreeting.author)
  const schedulerTasksLoading = ref(false)
  // 任务列表拉取失败：下拉里给一句提示，重新展开下拉即重试
  const schedulerTasksUnavailable = ref(false)
  const startingHomeTask = ref(false)

  const schedulerTaskOptions = ref<HomeTaskOption[]>([])
  const selectedHomeTaskIds = ref<string[]>([])
  const selectedHomeMode = ref<TaskCreateIn.mode>(TaskCreateIn.mode.AUTO_PROXY)
  let savedSelectedTaskIds: string[] = []
  let selectionTouched = false
  let selectionSaveQueue = Promise.resolve()

  const sameTaskIds = (left: string[], right: string[]) => {
    return left.length === right.length && left.every((taskId, index) => taskId === right[index])
  }

  const logWarning = (warning: string, error: unknown) => {
    const errorMessage = error instanceof Error ? error.message : String(error)
    logger.warn(`${warning}: ${errorMessage}`)
  }

  const queueSelectionSave = (taskIds: string[]) => {
    const normalizedTaskIds = normalizeHomeQuickStartSelection(taskIds)
    const saveTask = selectionSaveQueue.then(() =>
      saveConfig({ homeQuickStartSelectedTaskIds: normalizedTaskIds })
    )
    selectionSaveQueue = saveTask.catch(error => {
      logWarning('保存首页快速启动选择失败', error)
    })
    return saveTask.catch(() => undefined)
  }

  const restoreSelectedHomeTaskIds = async () => {
    try {
      const config = await getConfig()
      if (selectionTouched) return
      savedSelectedTaskIds = normalizeHomeQuickStartSelection(config.homeQuickStartSelectedTaskIds)
      selectedHomeTaskIds.value = [...savedSelectedTaskIds]
    } catch (error) {
      logWarning('读取首页快速启动选择失败', error)
    }
  }

  const updateSelectedHomeTaskIds = (taskIds: string[]) => {
    const normalizedTaskIds = normalizeHomeQuickStartSelection(taskIds)
    selectionTouched = true
    savedSelectedTaskIds = normalizedTaskIds
    selectedHomeTaskIds.value = [...normalizedTaskIds]
    void queueSelectionSave(normalizedTaskIds)
  }

  const applyRealTaskOptions = (taskOptions: HomeTaskOption[]) => {
    schedulerTaskOptions.value = taskOptions
    const previousSavedTaskIds = savedSelectedTaskIds
    const baseTaskIds = selectionTouched
      ? selectedHomeTaskIds.value
      : selectedHomeTaskIds.value.length
        ? selectedHomeTaskIds.value
        : savedSelectedTaskIds
    const retainedTaskIds = retainSelectedTaskIds(baseTaskIds, taskOptions)
    savedSelectedTaskIds = retainedTaskIds

    if (!sameTaskIds(selectedHomeTaskIds.value, retainedTaskIds)) {
      selectedHomeTaskIds.value = retainedTaskIds
    }
    if (!sameTaskIds(previousSavedTaskIds, retainedTaskIds)) {
      void queueSelectionSave(retainedTaskIds)
    }
  }

  const fetchSchedulerTaskOptions = async (options?: { quiet?: boolean }) => {
    schedulerTasksLoading.value = true

    try {
      const response = await Service.getTaskComboxApiInfoComboxTaskPost()
      if (response.code === 200 && Array.isArray(response.data)) {
        schedulerTasksUnavailable.value = false
        applyRealTaskOptions(toHomeTaskOptions(response.data))
        return
      }

      schedulerTasksUnavailable.value = true
      if (!options?.quiet) {
        message.warning(t('home.quickStart.listUnavailable'))
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      logger.warn(`获取首页任务列表失败: ${errorMsg}`)
      schedulerTasksUnavailable.value = true
      if (!options?.quiet) {
        message.warning(t('home.quickStart.listUnavailable'))
      }
    } finally {
      schedulerTasksLoading.value = false
    }
  }

  const onSchedulerDropdownVisibleChange = (open: boolean) => {
    if (open) {
      fetchSchedulerTaskOptions({ quiet: true })
    }
  }

  const startHomeTask = async () => {
    if (schedulerTasksLoading.value) return

    const taskIds = retainSelectedTaskIds(selectedHomeTaskIds.value, schedulerTaskOptions.value)
    if (!taskIds.length) {
      message.error(t('home.quickStart.selectTask'))
      return
    }

    startingHomeTask.value = true
    try {
      const outcome = await launchHomeTasks({
        taskIds,
        options: schedulerTaskOptions.value,
        fallbackLabel: t('home.quickStart.fallbackLabel'),
        failureReason: t('home.quickStart.startFailed'),
        startTask: taskId =>
          Service.addTaskApiDispatchStartPost({
            taskId,
            mode: selectedHomeMode.value,
          }),
        onTaskStarted: result => {
          trackStartedTask({
            taskId: result.taskId,
            selectedTaskId: result.selectedTaskId,
            selectedMode: selectedHomeMode.value,
            taskLabel: result.taskLabel,
            modeLabel: '自动代理',
          })
        },
      })

      for (const failure of outcome.failed) {
        logger.warn(`首页开始任务失败: ${failure.taskLabel}: ${failure.reason}`)
      }

      if (outcome.started.length) {
        message.success(
          t('home.quickStart.startedCount', {
            p0: outcome.started.length,
            p1: taskIds.length,
          })
        )
      }
      if (outcome.failed.length) {
        const failureSummary = outcome.failed
          .map(failure => `${failure.taskLabel}: ${failure.reason}`)
          .join('; ')
        message.error(t('home.quickStart.startFailedItems', { p0: failureSummary }))
      }
      if (outcome.started.length) {
        await navigateTo('/scheduler')
        void playSound('task_started')
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : String(error)
      logger.error(`首页开始任务失败: ${errorMsg}`)
      message.error(t('home.quickStart.startError'))
    } finally {
      startingHomeTask.value = false
    }
  }

  return {
    commandTitle,
    commandAuthor,
    schedulerTasksLoading,
    schedulerTasksUnavailable,
    startingHomeTask,
    schedulerTaskOptions,
    selectedHomeTaskIds,
    restoreSelectedHomeTaskIds,
    updateSelectedHomeTaskIds,
    fetchSchedulerTaskOptions,
    onSchedulerDropdownVisibleChange,
    startHomeTask,
  }
}
