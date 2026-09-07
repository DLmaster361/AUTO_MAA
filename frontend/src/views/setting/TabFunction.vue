<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons-vue'
import { message } from 'ant-design-vue'
import type { GlobalConfig, VirtualDisplayCheckOut } from '@/api'
import { GetService } from '@/api'
import { handleExternalLink, openExternalUrl } from '@/utils/openExternal'

const { t } = useI18n()

const VDD_DOWNLOAD_URL =
  'https://github.com/nomi-san/parsec-vdd/releases/download/v0.45.1/ParsecVDisplay-v0.45-setup.exe'

// 分辨率固定 1920x1080：实测只有它 Windows 给 100% 缩放，再高会被自动上缩放，
// 游戏窗口又要面对 DPI 虚拟化——而虚拟屏本来就是为了绕开这类问题。所以这里只让用户
// 选刷新率。驱动的刷新率表是 24/30/60/144/240，写 120 会被 BADMODE 拒绝。
// 选项放在 computed 里，t() 是响应式的。
const virtualDisplayModeOptions = computed(() => [
  { label: `60 Hz（${t('setting.display.refreshDefault')}）`, value: '1920x1080@60' },
  { label: `30 Hz（${t('setting.display.refreshLowPower')}）`, value: '1920x1080@30' },
])

const vddChecking = ref(false)
const vddResult = ref<VirtualDisplayCheckOut | null>(null)

async function runVirtualDisplayCheck() {
  vddChecking.value = true
  try {
    vddResult.value = await GetService.checkVirtualDisplayApiSettingVirtualDisplayCheckPost()
  } catch (error) {
    vddResult.value = null
    message.error(t('setting.display.checkFailed'))
  } finally {
    vddChecking.value = false
  }
}

function openVddDownload() {
  openExternalUrl(VDD_DOWNLOAD_URL)
}

const { settings, historyRetentionOptions, voiceTypeOptions, handleSettingChange } = defineProps<{
  settings: GlobalConfig
  historyRetentionOptions: { label: string; value: number }[]
  voiceTypeOptions: { label: string; value: string }[]
  handleSettingChange: (category: keyof GlobalConfig, key: string, value: any) => Promise<void>
}>()
</script>
<template>
  <div class="tab-content">
    <div class="form-section">
      <div class="section-header">
        <h3>{{ t('setting.func.startupSection') }}</h3>
      </div>
      <a-row :gutter="24">
        <a-col :span="12">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.autoStart') }}</span>
              <a-tooltip :title="t('setting.func.autoStartTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Start?.IfSelfStart"
              size="large"
              style="width: 100%"
              @change="(checked: any) => handleSettingChange('Start', 'IfSelfStart', checked)"
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="12">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.startMinimized') }}</span>
              <a-tooltip :title="t('setting.func.startMinimizedTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Start?.IfMinimizeDirectly"
              size="large"
              style="width: 100%"
              @change="
                (checked: any) => handleSettingChange('Start', 'IfMinimizeDirectly', checked)
              "
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
      </a-row>
    </div>

    <div class="form-section">
      <div class="section-header">
        <h3>{{ t('setting.func.featureSection') }}</h3>
      </div>
      <a-row :gutter="24">
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.retention') }}</span>
              <a-tooltip :title="t('setting.func.retentionTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.HistoryRetentionTime"
              :options="historyRetentionOptions"
              size="large"
              style="width: 100%"
              @change="
                (value: any) => handleSettingChange('Function', 'HistoryRetentionTime', value)
              "
            />
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.silent') }}</span>
              <a-tooltip :title="t('setting.func.silentTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.IfSilence"
              size="large"
              style="width: 100%"
              @change="(checked: any) => handleSettingChange('Function', 'IfSilence', checked)"
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.preventSleep') }}</span>
              <a-tooltip :title="t('setting.func.preventSleepTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.IfAllowSleep"
              size="large"
              style="width: 100%"
              @change="(checked: any) => handleSettingChange('Function', 'IfAllowSleep', checked)"
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
      </a-row>
      <a-row :gutter="24">
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.telemetry') }}</span>
              <a-tooltip :title="t('setting.func.telemetryTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.IfEnableTelemetry !== false"
              size="large"
              style="width: 100%"
              @change="
                (checked: any) => handleSettingChange('Function', 'IfEnableTelemetry', checked)
              "
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.biliPolicy') }}</span>
              <a-tooltip>
                <template #title>
                  <div style="max-width: 300px">
                    <p>{{ t('setting.func.biliIntro') }}</p>
                    <ul style="margin: 8px 0; padding-left: 16px">
                      <li>
                        <a
                          href="https://www.bilibili.com/protocal/licence.html"
                          class="tooltip-link"
                          @click="handleExternalLink"
                          >{{ t('setting.func.biliTerms') }}</a
                        >
                      </li>
                      <li>
                        <a
                          href="https://www.bilibili.com/blackboard/privacy-pc.html"
                          class="tooltip-link"
                          @click="handleExternalLink"
                          >{{ t('setting.func.biliPrivacy') }}</a
                        >
                      </li>
                      <li>
                        <a
                          href="https://game.bilibili.com/yhxy"
                          class="tooltip-link"
                          @click="handleExternalLink"
                          >{{ t('setting.func.biliGame') }}</a
                        >
                      </li>
                    </ul>
                  </div>
                </template>
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.IfAgreeBilibili"
              size="large"
              style="width: 100%"
              @change="
                (checked: any) => handleSettingChange('Function', 'IfAgreeBilibili', checked)
              "
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.blockAds') }}</span>
              <a-tooltip>
                <template #title>
                  <div style="max-width: 300px">
                    <p>{{ t('setting.func.blockAdsIntro') }}</p>
                    <ul style="margin: 8px 0; padding-left: 16px">
                      <li>
                        <strong>{{ t('emulator.type.mumu') }}</strong
                        >: {{ t('setting.func.blockAdsMumu') }}
                      </li>
                      <li>
                        <strong>{{ t('emulator.type.ldplayer') }}</strong
                        >: {{ t('setting.func.blockAdsLd') }}
                      </li>
                    </ul>
                  </div>
                </template>
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Function?.IfBlockAd"
              size="large"
              style="width: 100%"
              @change="(checked: any) => handleSettingChange('Function', 'IfBlockAd', checked)"
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
      </a-row>
    </div>

    <div class="form-section">
      <div class="section-header">
        <h3>{{ t('setting.func.voiceSection') }}</h3>
      </div>
      <a-row :gutter="24">
        <a-col :span="12">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.voiceEnable') }}</span>
              <a-tooltip :title="t('setting.func.voiceEnableTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Voice?.Enabled"
              size="large"
              style="width: 100%"
              @change="(checked: any) => handleSettingChange('Voice', 'Enabled', checked)"
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="12">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.func.voiceType') }}</span>
              <a-tooltip :title="t('setting.func.voiceTypeTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Voice?.Type"
              :options="voiceTypeOptions"
              :disabled="!settings.Voice?.Enabled"
              size="large"
              style="width: 100%"
              @change="(value: any) => handleSettingChange('Voice', 'Type', value)"
            />
          </div>
        </a-col>
      </a-row>
    </div>

    <div class="form-section">
      <div class="section-header">
        <h3>{{ t('setting.display.section') }}</h3>
      </div>
      <a-alert type="info" show-icon class="vdd-alert">
        <template #message>{{ t('setting.display.intro') }}</template>
      </a-alert>
      <a-row :gutter="24">
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.display.enable') }}</span>
              <a-tooltip :title="t('setting.display.enableTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Display?.IfEnableVirtualDisplay"
              size="large"
              style="width: 100%"
              @change="
                (checked: any) =>
                  handleSettingChange('Display', 'IfEnableVirtualDisplay', checked)
              "
            >
              <a-select-option :value="true">{{ t('common.yes') }}</a-select-option>
              <a-select-option :value="false">{{ t('common.no') }}</a-select-option>
            </a-select>
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.display.mode') }}</span>
              <a-tooltip :title="t('setting.display.modeTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-select
              :value="settings.Display?.VirtualDisplayMode"
              :options="virtualDisplayModeOptions"
              :disabled="!settings.Display?.IfEnableVirtualDisplay"
              size="large"
              style="width: 100%"
              @change="
                (value: any) => handleSettingChange('Display', 'VirtualDisplayMode', value)
              "
            />
          </div>
        </a-col>
        <a-col :span="8">
          <div class="form-item-vertical">
            <div class="form-label-wrapper">
              <span class="form-label">{{ t('setting.display.check') }}</span>
              <a-tooltip :title="t('setting.display.checkTip')">
                <QuestionCircleOutlined class="help-icon" />
              </a-tooltip>
            </div>
            <a-button
              size="large"
              style="width: 100%"
              :loading="vddChecking"
              @click="runVirtualDisplayCheck"
            >
              {{ t('setting.display.checkAction') }}
            </a-button>
          </div>
        </a-col>
      </a-row>
      <a-row v-if="vddResult" :gutter="24" class="vdd-result-row">
        <a-col :span="24">
          <a-alert
            :type="(vddResult.results ?? []).every((item) => item.passed) ? 'success' : 'warning'"
            show-icon
          >
            <template #message>{{ vddResult.message }}</template>
            <template #description>
              <ul class="vdd-result-list">
                <li v-for="item in vddResult.results ?? []" :key="item.stage">
                  <CheckCircleOutlined v-if="item.passed" class="vdd-ok" />
                  <CloseCircleOutlined v-else class="vdd-fail" />
                  {{ t(`setting.display.stage.${item.stage}`) }} — {{ item.message }}
                </li>
              </ul>
              <p v-if="vddResult.monitors" class="vdd-monitors">
                {{ t('setting.display.monitors') }}: {{ vddResult.monitors }}
              </p>
              <p v-if="!(vddResult.results ?? []).some((item) => item.stage === 'openable')">
                <a href="#" @click.prevent="openVddDownload">
                  {{ t('setting.display.download') }}
                </a>
              </p>
            </template>
          </a-alert>
        </a-col>
      </a-row>
    </div>
  </div>
</template>

<style scoped>
.vdd-alert {
  margin-bottom: 16px;
}

.vdd-result-row {
  margin-top: 16px;
}

.vdd-result-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.vdd-result-list li {
  margin: 4px 0;
}

.vdd-ok {
  color: var(--ant-color-success);
}

.vdd-fail {
  color: var(--ant-color-warning);
}

.vdd-monitors {
  margin: 8px 0 0;
  word-break: break-all;
  color: var(--ant-color-text-secondary);
}
</style>
