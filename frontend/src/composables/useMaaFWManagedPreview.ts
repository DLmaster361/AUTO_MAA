import { ref } from 'vue'

import { useSettingsApi } from '@/composables/useSettingsApi'

/**
 * MFW 托管的小范围试用开关（`Function.MaaFWManagedPreview`）。
 *
 * 开关不在设置界面里，由维护者逐个告知怎么打开；前端只负责按它藏起三个「进门」的
 * 入口：建项向导里的托管类型、编辑页的「转为托管」、托管区块里的导入。已经建好的
 * 托管脚本不受影响——后端也只锁门不锁房间。
 *
 * 模块级缓存：几个页面都要问，一次会话里问一遍就够，后端没开时也不必反复打。
 */
const enabled = ref(false)
let loaded: Promise<void> | null = null

export function useMaaFWManagedPreview() {
  const { getSettings } = useSettingsApi()

  const load = async () => {
    if (!loaded) {
      loaded = getSettings()
        .then(settings => {
          enabled.value = settings?.Function?.MaaFWManagedPreview === true
        })
        .catch(() => {
          // 读不到就当没开：宁可少露一个入口，也不把未验证的功能亮给不该看的人。
          enabled.value = false
        })
    }
    await loaded
  }

  return { enabled, load }
}
