<template>
  <div class="user-edit-container">
    <div class="user-edit-header">
      <div class="header-nav">
        <a-breadcrumb class="breadcrumb">
          <a-breadcrumb-item>
            <router-link to="/scripts">{{ t('edit.scripts') }}</router-link>
          </a-breadcrumb-item>
          <a-breadcrumb-item>
            <router-link :to="`/scripts/${scriptId}/edit/zzzod`" class="breadcrumb-link">
              {{ scriptName }}
            </router-link>
          </a-breadcrumb-item>
          <a-breadcrumb-item>
            {{ isEdit ? t('comp.editUser') : t('comp.addUser2') }}
          </a-breadcrumb-item>
        </a-breadcrumb>
      </div>

      <a-space size="middle">
        <a-tooltip :title="t('edit.zzzodOpenNativeConfigHint')">
          <a-button
            v-if="!showZzzodConfigMask && !showZzzodViewMask"
            type="primary"
            ghost
            size="large"
            :loading="zzzodConfigLoading"
            :disabled="pageLoading || !userId"
            @click="handleZzzodConfig"
          >
            <template #icon>
              <SettingOutlined />
            </template>
            {{ t('edit.zzzodOpenNativeConfig') }}
          </a-button>
        </a-tooltip>
        <a-button
          v-if="showZzzodConfigMask"
          type="default"
          size="large"
          disabled
          class="configuring-button"
        >
          <template #icon>
            <SettingOutlined />
          </template>
          {{ t('edit.configuring') }}
        </a-button>
        <a-button size="large" class="cancel-button" @click="handleCancel">
          <template #icon>
            <ArrowLeftOutlined />
          </template>
          {{ t('edit.back') }}
        </a-button>
      </a-space>
    </div>

    <teleport to="body">
      <div v-if="showZzzodConfigMask" class="zzzod-config-mask">
        <div class="mask-content">
          <div class="mask-icon">
            <SettingOutlined :style="{ fontSize: '48px', color: 'var(--ant-color-primary)' }" />
          </div>
          <h2 class="mask-title">{{ t('edit.zzzodConfiguringTitle') }}</h2>
          <p class="mask-description">
            {{ t('edit.zzzodConfiguringDesc') }}
            <br />
            {{ t('edit.zzzodConfiguringDesc2') }}
          </p>
          <div class="mask-actions">
            <a-button
              v-if="zzzodWebsocketId"
              type="primary"
              size="large"
              @click="handleSaveZzzodConfig"
            >
              {{ t('edit.saveSettings') }}
            </a-button>
          </div>
        </div>
      </div>
      <div v-if="showZzzodViewMask" class="zzzod-config-mask">
        <div class="mask-content">
          <div class="mask-icon">
            <EyeOutlined :style="{ fontSize: '48px', color: 'var(--ant-color-primary)' }" />
          </div>
          <h2 class="mask-title">{{ t('edit.zzzodViewingTitle') }}</h2>
          <p class="mask-description">
            {{ t('edit.zzzodViewingDesc') }}
            <br />
            {{ t('edit.zzzodViewingDesc2') }}
          </p>
          <div class="mask-actions">
            <a-button
              v-if="zzzodWebsocketId"
              type="primary"
              size="large"
              :loading="stoppingZzzodConfig"
              @click="handleCloseZzzodView"
            >
              {{ t('edit.zzzodViewClose') }}
            </a-button>
          </div>
        </div>
      </div>
    </teleport>

    <div class="user-edit-content">
      <a-card class="config-card" :loading="pageLoading">
        <a-form :model="formData" layout="vertical" class="config-form">
          <div class="form-section">
            <div class="section-header">
              <h3>{{ t('edit.basicInfo') }}</h3>
            </div>

            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item>
                  <template #label>
                    <span class="form-label">
                      {{ t('edit.username') }}
                      <a-tooltip :title="t('edit.zzzodUserNameHint')">
                        <QuestionCircleOutlined class="help-icon" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input
                    v-model:value="formData.userName"
                    :placeholder="t('edit.enterUsername')"
                    size="large"
                    class="modern-input"
                    @blur="handleNameBlur"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item>
                  <template #label>
                    <span class="form-label">
                      {{ t('edit.enabled') }}
                      <a-tooltip :title="t('edit.whetherThisUserEnabled')">
                        <QuestionCircleOutlined class="help-icon" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-select
                    v-model:value="formData.Info.Status"
                    size="large"
                    class="modern-select"
                    @change="saveField('Info.Status', formData.Info.Status)"
                  >
                    <a-select-option :value="true">{{ t('edit.yes') }}</a-select-option>
                    <a-select-option :value="false">{{ t('edit.no') }}</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24">
              <a-col :span="24">
                <GeneralConfigModeSelector
                  :model-value="formData.Info.Mode"
                  :options="configModeOptions"
                  :disabled="pageLoading"
                  :alert-message="configModeAlert"
                  @change="handleConfigModeChange"
                />
              </a-col>
            </a-row>

            <!-- 直控：选择要直接编辑的一条龙实例（强绑定原生配置） -->
            <template v-if="formData.Info.Mode === '直控'">
              <a-row :gutter="24">
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodDirectInstance') }}
                        <a-tooltip :title="t('edit.zzzodDirectInstanceHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-select
                      v-model:value="nativeInstanceIdx"
                      :options="instanceOptions"
                      :placeholder="t('edit.zzzodDirectPickInstance')"
                      :loading="instancesLoading"
                      size="large"
                      class="modern-select"
                      @change="handleNativeInstanceChange"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodDirectInstanceRun') }}
                        <a-tooltip :title="t('edit.zzzodDirectInstanceRunHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-select
                      v-model:value="nativeInstanceRun"
                      :options="instanceRunOptions"
                      :disabled="!instancesLoading && nativeInstanceIdx === null"
                      size="large"
                      class="modern-select"
                      @change="handleNativeInstanceRunChange"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-alert
                type="info"
                show-icon
                class="native-bind-alert"
                :message="t('edit.zzzodDirectBindAlert')"
              />

              <!-- 直控：所选实例的原生账号字段（保存即写回一条龙 game_account.yml） -->
              <a-spin :spinning="nativeLoading">
                <template v-if="nativeInstanceIdx !== null">
                  <a-row :gutter="24">
                    <a-col
                      v-for="f in nativeAccountFields"
                      :key="f.key"
                      :span="12"
                    >
                      <a-form-item>
                        <template #label>
                          <span class="form-label">{{ f.title }}</span>
                        </template>
                        <a-input-group
                          v-if="f.key === 'game_path'"
                          compact
                          class="path-input-group"
                        >
                          <a-input
                            v-model:value="nativeAccountValues[f.key]"
                            :placeholder="t('edit.zzzodGamePathPlaceholder')"
                            size="large"
                            class="path-input"
                            readonly
                          />
                          <a-button
                            size="large"
                            class="path-button"
                            @click="selectDirectGamePath"
                          >
                            <template #icon>
                              <FolderOpenOutlined />
                            </template>
                            {{ t('edit.pickFile') }}
                          </a-button>
                        </a-input-group>
                        <a-input-password
                          v-else-if="f.key === 'password'"
                          v-model:value="nativeAccountValues[f.key]"
                          :placeholder="t('edit.zzzodEnterPasswordPlaceholder')"
                          size="large"
                          class="modern-input"
                        />
                        <a-select
                          v-else-if="(f.options?.length ?? 0) > 0"
                          v-model:value="nativeAccountValues[f.key]"
                          :options="f.options"
                          size="large"
                          class="modern-select"
                        />
                        <a-input
                          v-else
                          v-model:value="nativeAccountValues[f.key]"
                          size="large"
                          class="modern-input"
                        />
                      </a-form-item>
                    </a-col>
                  </a-row>
                  <a-button
                    type="primary"
                    size="large"
                    :loading="nativeSaving"
                    @click="saveNativeAccount"
                  >
                    {{ t('edit.saveSettings') }}
                  </a-button>
                </template>
                <a-empty
                  v-else
                  :description="t('edit.zzzodDirectPickInstanceFirst')"
                />
              </a-spin>
            </template>

            <!-- 账号配置（用户模式：MAS 字段化配置） -->
            <template v-else>
              <a-row :gutter="24">
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodGameRegion') }}
                        <a-tooltip :title="t('edit.zzzodGameRegionHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-select
                      v-model:value="formData.Game.GameRegion"
                      :options="gameRegionOptions"
                      size="large"
                      class="modern-select"
                      @change="saveField('Game.GameRegion', formData.Game.GameRegion)"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodGameLanguage') }}
                        <a-tooltip :title="t('edit.zzzodGameLanguageHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-select
                      v-model:value="formData.Game.GameLanguage"
                      :options="gameLanguageOptions"
                      size="large"
                      class="modern-select"
                      @change="saveField('Game.GameLanguage', formData.Game.GameLanguage)"
                    />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="24">
                <a-col :span="24">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodGamePath') }}
                        <a-tooltip :title="t('edit.zzzodGamePathHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-input-group compact class="path-input-group">
                      <a-input
                        v-model:value="formData.Game.GamePath"
                        :placeholder="t('edit.zzzodGamePathPlaceholder')"
                        size="large"
                        class="path-input"
                        readonly
                      />
                      <a-button size="large" class="path-button" @click="selectGamePath">
                        <template #icon>
                          <FolderOpenOutlined />
                        </template>
                        {{ t('edit.pickFile') }}
                      </a-button>
                    </a-input-group>
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row :gutter="24">
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodAccount') }}
                        <a-tooltip :title="t('edit.zzzodAccountHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-input
                      v-model:value="formData.Game.Account"
                      :placeholder="t('edit.zzzodEnterAccount')"
                      size="large"
                      class="modern-input"
                      @blur="saveField('Game.Account', formData.Game.Account)"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.password') }}
                        <a-tooltip :title="t('edit.zzzodPasswordHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-input-password
                      v-model:value="formData.Game.Password"
                      :placeholder="t('edit.zzzodEnterPasswordPlaceholder')"
                      size="large"
                      class="modern-input"
                      @blur="saveField('Game.Password', formData.Game.Password)"
                    />
                  </a-form-item>
                </a-col>
              </a-row>

              <a-row v-if="formData.Game.GameRegion === 'cn_b'" :gutter="24">
                <a-col :span="12">
                  <a-form-item>
                    <template #label>
                      <span class="form-label">
                        {{ t('edit.zzzodBilibiliAccount') }}
                        <a-tooltip :title="t('edit.zzzodBilibiliAccountHint')">
                          <QuestionCircleOutlined class="help-icon" />
                        </a-tooltip>
                      </span>
                    </template>
                    <a-input
                      v-model:value="formData.Game.BilibiliAccountName"
                      :placeholder="t('edit.zzzodEnterBilibiliAccount')"
                      size="large"
                      class="modern-input"
                      @blur="saveField('Game.BilibiliAccountName', formData.Game.BilibiliAccountName)"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
            </template>

            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item>
                  <template #label>
                    <span class="form-label">
                      {{ t('edit.daysLeft') }}
                      <a-tooltip :title="t('edit.daysLeftAccount1')">
                        <QuestionCircleOutlined class="help-icon" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input-number
                    v-model:value="formData.Info.RemainedDay"
                    :min="-1"
                    :max="9999"
                    size="large"
                    style="width: 100%"
                    @blur="saveField('Info.RemainedDay', formData.Info.RemainedDay)"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item>
                  <template #label>
                    <span class="form-label">
                      {{ t('edit.note') }}
                      <a-tooltip :title="t('edit.addNoteAboutThis')">
                        <QuestionCircleOutlined class="help-icon" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-input
                    v-model:value="formData.Info.Notes"
                    :placeholder="t('edit.enterNote')"
                    size="large"
                    class="modern-input"
                    @blur="saveField('Info.Notes', formData.Info.Notes)"
                  />
                </a-form-item>
              </a-col>
            </a-row>

            <a-row :gutter="24">
              <a-col :span="12">
                <a-form-item>
                  <template #label>
                    <span class="form-label">
                      {{ t('edit.collectNodeDetails') }}
                      <a-tooltip :title="t('edit.zzzodPushLogModeHint')">
                        <QuestionCircleOutlined class="help-icon" />
                      </a-tooltip>
                    </span>
                  </template>
                  <a-select
                    v-model:value="formData.Notify.PushLogMode"
                    :options="pushLogModeOptions"
                    :disabled="!formData.Notify.Enabled"
                    size="large"
                    class="modern-select"
                    @change="saveField('Notify.PushLogMode', formData.Notify.PushLogMode)"
                  />
                </a-form-item>
              </a-col>
            </a-row>
          </div>
        </a-form>
      </a-card>

      <!-- ══ 任务配置（一条龙编排，紧跟基本信息）══ -->
      <a-card class="config-card" style="margin-top: 24px">
        <a-form :model="formData" layout="vertical" class="config-form">
          <div class="form-section">
            <div class="section-header">
              <h3>
                {{ t('edit.zzzodOneDragonConfig') }}
                <a-tooltip :title="t('edit.zzzodOneDragonConfigHint')">
                  <QuestionCircleOutlined class="help-icon" />
                </a-tooltip>
              </h3>
              <a-button size="small" class="restore-entry" @click="openRestoreModal">
                <template #icon><HistoryOutlined /></template>
                {{ t('edit.zzzodRestoreTitle') }}
              </a-button>
            </div>

            <p class="section-desc">
              {{
                formData.Info.Mode === '直控'
                  ? t('edit.zzzodDirectTasksDesc')
                  : t('edit.zzzodOneDragonDesc')
              }}
            </p>

            <div class="task-grid">
              <div
                v-for="card in activeTaskCards"
                :key="card.app_id"
                class="task-card"
                :class="{ inactive: !card.enabled }"
              >
                <div class="task-card-main">
                  <span class="task-name" :title="card.app_name">{{ card.app_name }}</span>
                  <div
                    class="config-group-item-capsule"
                    :class="{ active: card.enabled }"
                    @click="toggleTask(card)"
                  >
                    <span class="config-group-item-dot"></span>
                  </div>
                </div>
                <div class="task-card-actions">
                  <template v-if="card.enabled">
                    <a-popover
                      v-if="card.configurable"
                      trigger="click"
                      placement="top"
                      @open-change="(o: boolean) => o && openTaskConfig(card)"
                    >
                      <template #content>
                        <div
                          v-if="taskConfigLoading[card.app_id]"
                          class="task-config-loading"
                        >
                          <a-spin size="small" />
                        </div>
                        <template v-else>
                          <div
                            v-for="f in taskConfigData[card.app_id] ?? []"
                            :key="f.field"
                            class="task-config-field"
                          >
                            <span class="task-config-field-title">{{ f.title }}</span>
                            <a-select
                              :value="f.value ?? undefined"
                              size="small"
                              style="min-width: 150px"
                              @change="(v: any) => saveTaskConfigField(card, f, v)"
                            >
                              <a-select-option
                                v-for="o in f.options"
                                :key="o.value"
                                :value="o.value"
                              >
                                {{ o.label }}
                              </a-select-option>
                            </a-select>
                          </div>
                        </template>
                      </template>
                      <a-tooltip :title="t('edit.zzzodTaskConfigHint')">
                        <a-button size="small" type="text" class="task-config-gear">
                          <template #icon><SettingOutlined /></template>
                        </a-button>
                      </a-tooltip>
                    </a-popover>
                    <a-button
                      size="small"
                      type="text"
                      @click="moveTask(card, -1)"
                    >
                      <template #icon><ArrowUpOutlined /></template>
                    </a-button>
                    <a-button
                      size="small"
                      type="text"
                      @click="moveTask(card, 1)"
                    >
                      <template #icon><ArrowDownOutlined /></template>
                    </a-button>
                  </template>
                </div>
              </div>
            </div>
          </div>
        </a-form>
      </a-card>

      <a-card class="config-card" style="margin-top: 24px">
        <a-form :model="formData" layout="vertical" class="config-form">
          <ExtraScriptSection :form-data="formData" :loading="pageLoading" @save="saveField" />
        </a-form>
      </a-card>

      <a-card class="config-card" style="margin-top: 24px">
        <a-form :model="formData" layout="vertical" class="config-form">
          <UserNotifyConfig
            v-model="formData.Notify"
            :loading="pageLoading"
            :script-id="scriptId"
            :user-id="userId"
            @save="saveField"
          />
        </a-form>
      </a-card>

      <!-- ══ 配置恢复（历史备份浏览 / 查看 / 一键恢复；目标可切换）══ -->
      <a-modal
        v-model:open="restoreOpen"
        :title="t('edit.zzzodRestoreTitle')"
        :footer="null"
        width="520px"
      >
        <a-segmented
          v-model:value="restoreTarget"
          block
          class="restore-target-switch"
          :options="[
            { label: t('edit.zzzodRestoreTargetOd'), value: 'onedragon' },
            { label: t('edit.zzzodRestoreTargetMas'), value: 'mas' },
          ]"
        />
        <p class="restore-desc">
          {{
            restoreTarget === 'mas'
              ? t('edit.zzzodRestoreMasDesc')
              : t('edit.zzzodRestoreDesc')
          }}
        </p>
        <a-spin :spinning="backupsLoading">
          <a-empty
            v-if="!backups.length"
            :description="t('edit.zzzodRestoreEmpty')"
          />
          <a-list v-else :data-source="backups" size="small" row-key="time">
            <template #renderItem="{ item }">
              <a-list-item>
                <span class="backup-time">{{ formatBackupTime(item.time) }}</span>
                <a-space>
                  <a-tooltip
                    :title="
                      restoreTarget === 'mas'
                        ? t('edit.zzzodRestoreViewHintMas')
                        : t('edit.zzzodRestoreViewHintOd')
                    "
                  >
                    <a-button size="small" @click="handleRestoreView(item)">
                      {{ t('edit.zzzodRestoreView') }}
                    </a-button>
                  </a-tooltip>
                  <a-button size="small" danger @click="confirmRestore(item)">
                    {{ t('edit.zzzodRestoreAction') }}
                  </a-button>
                </a-space>
              </a-list-item>
            </template>
          </a-list>
        </a-spin>
      </a-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { message, Modal } from 'ant-design-vue'
import {
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowUpOutlined,
  EyeOutlined,
  FolderOpenOutlined,
  HistoryOutlined,
  QuestionCircleOutlined,
  SettingOutlined,
} from '@ant-design/icons-vue'
import {
  Service,
  ZzzOdBackupRestoreIn,
  type ZzzOdInstanceOut,
  type ZzzOdNativeAccountField,
  type ZzzOdNativeConfigOut,
  type ZzzOdUserConfig,
} from '@/api'
import { useUserApi } from '@/composables/useUserApi'
import { useScriptApi } from '@/composables/useScriptApi'
import { useZzzodGuiSession } from '@/composables/useZzzodGuiSession'
import GeneralConfigModeSelector from '@/views/EditView/User/GeneralConfigModeSelector.vue'
import UserNotifyConfig from '@/components/UserNotifyConfig.vue'
import ExtraScriptSection from '@/components/ExtraScriptSection.vue'

const { t } = useI18n()
const logger = window.electronAPI.getLogger('ZZZ-OD用户编辑')
const route = useRoute()
const router = useRouter()
const { addUser, getUsers, updateUser, error: userApiError } = useUserApi()
const { getScript } = useScriptApi()

const scriptId = route.params.scriptId as string
const userId = ref((route.params.userId as string) || '')
const isEdit = ref(!!userId.value)
const scriptName = ref(t('edit.zzzodScriptFallbackName'))

const pageLoading = ref(true)
const isInitializing = ref(true)

type FormSection<T> = { [K in keyof T]-?: NonNullable<T[K]> }

type ZzzOdUserFormData = {
  userName: string
  Info: FormSection<NonNullable<ZzzOdUserConfig['Info']>>
  Game: FormSection<NonNullable<ZzzOdUserConfig['Game']>>
  OneDragon: FormSection<NonNullable<ZzzOdUserConfig['OneDragon']>>
  Notify: FormSection<NonNullable<ZzzOdUserConfig['Notify']>>
}

const getDefaultUserData = (): Omit<ZzzOdUserFormData, 'userName'> => ({
  Info: {
    Name: '',
    Status: true,
    Mode: '用户',
    SlotIdx: -1,
    RemainedDay: -1,
    IfScriptBeforeTask: false,
    ScriptBeforeTask: '',
    IfScriptAfterTask: false,
    ScriptAfterTask: '',
    Notes: '',
    Tag: '',
  },
  Game: {
    GameRegion: 'cn',
    GamePath: '',
    GameLanguage: 'cn',
    Account: '',
    Password: '',
    BilibiliAccountName: '',
  },
  OneDragon: {
    AppList: '[]',
  },
  Notify: {
    Enabled: false,
    PushLogMode: '汇总',
    IfSendStatistic: false,
    IfSendMail: false,
    ToAddress: '',
    IfServerChan: false,
    ServerChanKey: '',
  },
})

const formData = reactive<ZzzOdUserFormData>({
  userName: '',
  ...getDefaultUserData(),
})

// 节点详情推送模式（value 为后端 Notify.PushLogMode 取值，驱动逻辑需保持原样；label 走词表）
const pushLogModeOptions = [
  { label: t('edit.pushLogModeOff'), value: '关闭' },
  { label: t('edit.pushLogModeList'), value: '逐条' },
  { label: t('edit.pushLogModeSummary'), value: '汇总' },
]

// 配置来源两态卡片（value 为后端 Info.Mode 取值，驱动逻辑需保持原样；文案走词表）
const configModeOptions: Array<{
  label: string
  value: '用户' | '直控'
  title: string
  description: string
  icon: 'database' | 'setting'
}> = [
  {
    label: t('edit.zzzodModeUser'),
    value: '用户',
    title: t('edit.zzzodModeUser'),
    description: t('edit.zzzodModeUserDesc'),
    icon: 'database',
  },
  {
    label: t('edit.directControl'),
    value: '直控',
    title: t('edit.directControl'),
    description: t('edit.zzzodModeDirectDesc'),
    icon: 'setting',
  },
]

// 蓝色说明框随所选模式动态切换（只显示当前模式的行为，减少固定长文案）
const configModeAlert = computed(() =>
  formData.Info.Mode === '直控'
    ? t('edit.zzzodConfigSourceDirectAlert')
    : t('edit.zzzodConfigSourceUserAlert')
)

// ══ 区服 / 语言选项（value 为 zzz-od YAML 原生取值，驱动逻辑需保持原样）══
const gameRegionOptions = [
  { label: t('edit.zzzodRegionCn'), value: 'cn' },
  { label: t('edit.zzzodRegionCnB'), value: 'cn_b' },
  { label: t('edit.zzzodRegionUs'), value: 'us' },
  { label: t('edit.zzzodRegionEu'), value: 'eu' },
  { label: t('edit.zzzodRegionAsia'), value: 'asia' },
  { label: t('edit.zzzodRegionTwHkMo'), value: 'twhkmo' },
]
const gameLanguageOptions = [
  { label: t('edit.zzzodLanguageCn'), value: 'cn' },
  { label: t('edit.zzzodLanguageEn'), value: 'en' },
]

// 用户名失焦：同脚本内禁止重名（绑定槽名与统计都依赖名字区分）
const handleNameBlur = async () => {
  const name = formData.userName.trim()
  if (!name) return
  try {
    const resp = await getUsers(scriptId)
    const duplicate = Object.entries(resp?.data ?? {}).some(
      ([uid, user]) =>
        uid !== userId.value &&
        String((user as { Info?: { Name?: string } })?.Info?.Name ?? '').trim() ===
          name
    )
    if (duplicate) {
      message.error(t('edit.zzzodDuplicateUserName'))
      return
    }
  } catch (e) {
    logger.warn(e instanceof Error ? e.message : String(e))
  }
  await saveField('Info.Name', formData.userName)
}

const createUserImmediately = async (): Promise<boolean> => {
  const resp = await addUser(scriptId, { showError: false })
  if (!resp?.userId) {
    message.error(userApiError.value || t('edit.couldNotCreateUser'))
    handleCancel()
    return false
  }
  userId.value = resp.userId
  isEdit.value = true
  await router.replace({
    name: 'ZzzOdUserEdit',
    params: { scriptId, userId: userId.value },
  })
  return true
}

// 保存串行化队列：以 promise 链取代布尔互斥，连续保存按序写回不丢
let saveChain: Promise<boolean> = Promise.resolve(true)

const saveField = (key: string, value: unknown): Promise<boolean> => {
  if (isInitializing.value || !userId.value) return Promise.resolve(false)

  const parts = key.split('.')
  const patch: Record<string, any> = {}
  let current = patch
  for (let i = 0; i < parts.length - 1; i += 1) {
    current[parts[i]] = {}
    current = current[parts[i]]
  }
  current[parts[parts.length - 1]] = value

  if (key === 'Info.Name') {
    formData.userName = String(value || '')
  }

  const persist = async (): Promise<boolean> => {
    try {
      const ok = await updateUser(scriptId, userId.value, patch)
      if (!ok) {
        logger.error(`保存字段「${key}」失败: ${userApiError.value || '未知错误'}`)
      }
      return ok
    } catch (e) {
      logger.error(e instanceof Error ? e.message : String(e))
      return false
    }
  }

  const run = saveChain.then(persist, persist)
  saveChain = run
  return run
}

const handleConfigModeChange = async (value: boolean | string) => {
  if (typeof value !== 'string' || !['用户', '直控'].includes(value)) return
  const prev = formData.Info.Mode
  formData.Info.Mode = value as '用户' | '直控'
  await saveField('Info.Mode', formData.Info.Mode)
  if (value === '直控') {
    // 进入直控：先确保一条龙原生配置已有「改动前」备份（指纹去重，防误操作改坏后无法找回）
    await ensureDirectBackup()
    // 尚未选实例时默认选中第一个直接进入原生编辑
    if (nativeInstanceIdx.value === null && instances.value.length) {
      nativeInstanceIdx.value = instances.value[0].idx
      await loadNativeConfig(instances.value[0].idx)
    }
  } else if (prev === '直控') {
    // 离开直控（切回用户）：补一份「配置完成时」的备份
    await ensureDirectBackup()
  }
}

/** 直控前置保护：指纹对比后若无最新备份立即归档，返回最新备份时间戳 */
const ensureDirectBackup = async (): Promise<void> => {
  try {
    const resp = await Service.ensureZzzodDirectBackupApiApiScriptsZzzodDirectBackupEnsurePost({
      scriptId,
    })
    if (resp.code !== 200) throw new Error(resp.message || t('edit.zzzodBackupFailed'))
  } catch (e) {
    // 备份失败不阻断使用，但向用户提示（防止误以为有恢复点）
    logger.warn(e instanceof Error ? e.message : String(e))
    message.warning(t('edit.zzzodBackupFailed'))
  }
}

// ══ 实例列表（直控「选择实例」来源）══
const instances = ref<ZzzOdInstanceOut[]>([])
const instancesLoading = ref(false)

const instanceOptions = computed(() =>
  instances.value.map(item => ({
    label: `${String(item.idx).padStart(2, '0')} - ${item.name}`,
    value: item.idx,
  }))
)

const loadInstances = async () => {
  instancesLoading.value = true
  try {
    const resp = await Service.getZzzodInstancesApiApiScriptsZzzodInstancesGet(scriptId)
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodLoadInstancesFailed'))
    }
    instances.value = resp.data || []
  } catch (e) {
    logger.error(e instanceof Error ? e.message : String(e))
  } finally {
    instancesLoading.value = false
  }
}

// ══ 直控：所选实例的原生配置（强绑定一条龙原始 YAML，页面即改原生）══
const nativeInstanceIdx = ref<number | null>(null)
// 运行实例（value 为一条龙原生中文取值，label 走词表）
const nativeInstanceRun = ref('仅运行当前')
const instanceRunOptions = [
  { label: t('edit.zzzodInstanceRunCurrent'), value: '仅运行当前' },
  { label: t('edit.zzzodInstanceRunAll'), value: '全部实例' },
]
const nativeLoading = ref(false)
const nativeSaving = ref(false)
const nativeAccountFields = ref<ZzzOdNativeAccountField[]>([])
const nativeAccountValues = reactive<Record<string, string>>({})
const nativeTasks = ref<TaskCard[]>([])

const applyNativeConfig = (data: ZzzOdNativeConfigOut) => {
  nativeAccountFields.value = data.account ?? []
  const values: Record<string, string> = {}
  for (const f of data.account ?? []) {
    if (f.value != null) values[f.key] = String(f.value)
  }
  Object.keys(nativeAccountValues).forEach(k => delete nativeAccountValues[k])
  Object.assign(nativeAccountValues, values)
  nativeInstanceRun.value = data.instanceRun || '仅运行当前'
  nativeTasks.value = (data.tasks ?? []).map(
    t =>
      ({
        app_id: t.app_id,
        app_name: t.app_name,
        enabled: !!t.enabled,
        configurable: t.configurable,
      }) as TaskCard
  )
}

const loadNativeConfig = async (instanceIdx: number) => {
  nativeLoading.value = true
  try {
    const resp = await Service.getZzzodNativeConfigApiApiScriptsZzzodNativeConfigGet(
      scriptId,
      instanceIdx
    )
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodNativeLoadFailed'))
    }
    applyNativeConfig(resp)
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('edit.zzzodNativeLoadFailed'))
    nativeAccountFields.value = []
    nativeTasks.value = []
  } finally {
    nativeLoading.value = false
  }
}

const handleNativeInstanceChange = async (instanceIdx: number) => {
  if (instanceIdx == null) {
    nativeAccountFields.value = []
    nativeTasks.value = []
    return
  }
  await loadNativeConfig(instanceIdx)
}

/** 运行实例（仅运行当前/全部实例）改动即写回一条龙原生 instance_run */
const handleNativeInstanceRunChange = async () => {
  if (nativeInstanceIdx.value === null) return
  await saveNativeConfig({ instanceRun: nativeInstanceRun.value }, 'instanceRun')
}

/** 直控按需保存：只提交指定区块并只回读该区块。
 *
 *  - 账号字段（「保存设置」按钮）：全量提交 account + tasks + instanceRun；
 *  - 任务开关/排序、运行实例：即时增量提交对应字段——不把未保存的账号
 *    草稿一并落盘或覆盖。
 */
type NativeSaveSection = 'all' | 'tasks' | 'instanceRun'
/** 提交给后端的任务条目（后端只认 app_id/enabled） */
const toNativeTaskIn = (list: TaskCard[]): { app_id: string; enabled: boolean }[] =>
  list.map(t => ({ app_id: t.app_id, enabled: !!t.enabled }))
const saveNativeConfig = async (
  payload: {
    account?: Record<string, string>
    tasks?: { app_id: string; enabled: boolean }[]
    instanceRun?: string
  },
  section: NativeSaveSection = 'all',
  silent = false
): Promise<boolean> => {
  if (nativeInstanceIdx.value === null) return false
  nativeSaving.value = true
  try {
    const resp = await Service.saveZzzodNativeConfigApiApiScriptsZzzodNativeConfigSavePost({
      scriptId,
      instanceIdx: nativeInstanceIdx.value,
      ...payload,
    })
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodNativeSaveFailed'))
    }
    if (section === 'tasks') {
      nativeTasks.value = (resp.tasks ?? []).map(
        t =>
          ({
            app_id: t.app_id,
            app_name: t.app_name,
            enabled: !!t.enabled,
            configurable: t.configurable,
          }) as TaskCard
      )
    } else if (section === 'instanceRun') {
      nativeInstanceRun.value = resp.instanceRun || '仅运行当前'
    } else {
      applyNativeConfig(resp)
    }
    if (!silent) message.success(t('edit.zzzodNativeSaved'))
    return true
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('edit.zzzodNativeSaveFailed'))
    return false
  } finally {
    nativeSaving.value = false
  }
}

/** 「保存设置」：账号字段全量写回（连同当前任务编排与运行实例，保持表单一致） */
const saveNativeAccount = () =>
  saveNativeConfig(
    {
      account: { ...nativeAccountValues },
      tasks: toNativeTaskIn(nativeTasks.value),
      instanceRun: nativeInstanceRun.value,
    },
    'all'
  )

const selectDirectGamePath = async () => {
  const paths = await window.electronAPI?.selectFile([
    {
      name: 'ZenlessZoneZero.exe',
      extensions: ['exe'],
    },
  ])
  const path = paths?.[0]
  if (!path) return
  const fileName = path.split(/[\\/]/).pop()
  if (fileName?.toLowerCase() !== 'zenlesszonezero.exe') {
    message.error(t('edit.zzzodPickGameExe'))
    return
  }
  nativeAccountValues.game_path = path
}

// ══ 任务目录（中文名渲染；一条龙系列 = zzz-od 默认编组应用）══
interface ZzzOdCatalogItem {
  app_id: string
  app_name: string
  default_group: boolean
  configurable?: boolean
  priority: number
}

const catalog = ref<ZzzOdCatalogItem[]>([])

const loadCatalog = async () => {
  try {
    const resp = await Service.getZzzodCatalogApiApiScriptsZzzodCatalogGet(scriptId)
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodLoadOneDragonFailed'))
    }
    catalog.value = resp.data || []
  } catch (e) {
    logger.error(e instanceof Error ? e.message : String(e))
  }
}

// ══ 任务卡片 ⚙：可配置任务弹出选项编辑（数据驱动元数据表）══
interface TaskConfigField {
  field: string
  title: string
  value: string | null
  options: { label: string; value: string }[]
}

const taskConfigData = ref<Record<string, TaskConfigField[]>>({})
const taskConfigLoading = ref<Record<string, boolean>>({})

const openTaskConfig = async (card: TaskCard) => {
  taskConfigLoading.value = { ...taskConfigLoading.value, [card.app_id]: true }
  try {
    // 直控：读所选实例的原生 per-app YAML；用户：读绑定槽
    const instanceIdx = formData.Info.Mode === '直控' ? nativeInstanceIdx.value : null
    const resp = await Service.getZzzodAppConfigApiApiScriptsZzzodAppConfigGet(
      scriptId,
      userId.value,
      card.app_id,
      instanceIdx
    )
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodTaskConfigLoadFailed'))
    }
    taskConfigData.value = {
      ...taskConfigData.value,
      [card.app_id]: (resp.fields ?? []) as TaskConfigField[],
    }
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('edit.zzzodTaskConfigLoadFailed'))
  } finally {
    taskConfigLoading.value = { ...taskConfigLoading.value, [card.app_id]: false }
  }
}

const saveTaskConfigField = async (
  card: TaskCard,
  field: TaskConfigField,
  value: string
) => {
  try {
    const resp = await Service.saveZzzodAppConfigApiApiScriptsZzzodAppConfigSavePost({
      scriptId,
      userId: userId.value,
      appId: card.app_id,
      values: { [field.field]: value },
      instanceIdx: formData.Info.Mode === '直控' ? nativeInstanceIdx.value : undefined,
    })
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodTaskConfigSaveFailed'))
    }
    field.value = value
    message.success(t('edit.zzzodTaskConfigSaved'))
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('edit.zzzodTaskConfigSaveFailed'))
  }
}

// ══ 配置恢复（历史备份浏览 / 查看 / 一键恢复）══
interface BackupItem {
  time: string
}

const restoreOpen = ref(false)
const restoreTarget = ref<'onedragon' | 'mas'>('onedragon')
const backups = ref<BackupItem[]>([])
const backupsLoading = ref(false)

const formatBackupTime = (ts: string) =>
  `${ts.slice(0, 4)}-${ts.slice(4, 6)}-${ts.slice(6, 8)} ${ts.slice(9, 11)}:${ts.slice(11, 13)}:${ts.slice(13, 15)}`

const loadBackups = async () => {
  backupsLoading.value = true
  try {
    const resp = await Service.listZzzodBackupsApiApiScriptsZzzodBackupsGet(
      scriptId,
      userId.value,
      restoreTarget.value
    )
    if (resp.code !== 200) {
      throw new Error(resp.message || t('edit.zzzodBackupListFailed'))
    }
    backups.value = (resp.data ?? []) as BackupItem[]
  } catch (e) {
    message.error(e instanceof Error ? e.message : t('edit.zzzodBackupListFailed'))
  } finally {
    backupsLoading.value = false
  }
}

const openRestoreModal = async () => {
  restoreOpen.value = true
  await loadBackups()
}

// 切换恢复目标时按对应类别重新拉取备份列表（两类备份独立归档）
watch(restoreTarget, () => {
  if (restoreOpen.value) void loadBackups()
})

const doRestore = async (
  item: BackupItem,
  target: ZzzOdBackupRestoreIn['target'] = ZzzOdBackupRestoreIn.target.ONEDRAGON
) => {
  const resp = await Service.restoreZzzodBackupApiApiScriptsZzzodBackupRestorePost({
    scriptId,
    userId: userId.value,
    time: item.time,
    target,
  })
  if (resp.code !== 200) {
    throw new Error(resp.message || t('edit.zzzodRestoreFailed'))
  }
  message.success(
    target === ZzzOdBackupRestoreIn.target.MAS
      ? t('edit.zzzodRestoreMasSuccess')
      : t('edit.zzzodRestoreSuccess')
  )
}

const handleRestoreView = (item: BackupItem) => {
  const isMas = restoreTarget.value === 'mas'
  Modal.confirm({
    title: t('edit.zzzodRestoreView'),
    content: isMas
      ? t('edit.zzzodRestoreViewNoteMas')
      : t('edit.zzzodRestoreViewNoteOd'),
    onOk: async () => {
      try {
        await doRestore(
          item,
          isMas
            ? ZzzOdBackupRestoreIn.target.MAS
            : ZzzOdBackupRestoreIn.target.ONEDRAGON
        )
        restoreOpen.value = false
        if (isMas) {
          // MAS 备份预览：只读会话打开一条龙，合成视图下看到的是 MAS 实例
          // （槽内容即恢复的备份，不注入基线、不回读字段）
          await startSession(userId.value, true)
        } else {
          // 一条龙备份预览：脚本级原生会话，看到的是一条龙自己的原生实例，
          // 与 MAS 侧完全无关
          await startSession(scriptId, true)
        }
      } catch (e) {
        message.error(e instanceof Error ? e.message : t('edit.zzzodRestoreFailed'))
      }
    },
  })
}

const confirmRestore = (item: BackupItem) => {
  const isMas = restoreTarget.value === 'mas'
  Modal.confirm({
    title: isMas
      ? t('edit.zzzodRestoreMasConfirmTitle')
      : t('edit.zzzodRestoreConfirmTitle'),
    content: isMas
      ? t('edit.zzzodRestoreMasConfirmDesc')
      : t('edit.zzzodRestoreConfirmDesc'),
    okText: t('edit.zzzodRestoreAction'),
    okType: 'danger',
    onOk: async () => {
      try {
        await doRestore(
          item,
          isMas
            ? ZzzOdBackupRestoreIn.target.MAS
            : ZzzOdBackupRestoreIn.target.ONEDRAGON
        )
        if (isMas) {
          // MAS 恢复含字段回填，刷新表单
          restoreOpen.value = false
          await loadUserData()
        } else {
          await loadBackups()
        }
      } catch (e) {
        message.error(e instanceof Error ? e.message : t('edit.zzzodRestoreFailed'))
      }
    },
  })
}

// ══ 一条龙任务（OneDragon.AppList JSON 字段，打开页面即可开关）══
interface TaskCard {
  app_id: string
  app_name: string
  enabled: boolean
  configurable?: boolean
}

const savedApps = computed<{ app_id: string; enabled: boolean }[]>(() => {
  try {
    const parsed = JSON.parse(formData.OneDragon.AppList || '[]')
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})

const taskCards = computed<TaskCard[]>(() => {
  const nameBook = new Map(
    catalog.value.map(item => [item.app_id, { name: item.app_name, configurable: item.configurable }])
  )
  const cards: TaskCard[] = savedApps.value
    .filter(item => item && typeof item.app_id === 'string')
    .map(item => ({
      app_id: item.app_id,
      app_name: nameBook.get(item.app_id)?.name ?? item.app_id,
      enabled: !!item.enabled,
      configurable: nameBook.get(item.app_id)?.configurable,
    }))
  // 只把一条龙系列（zzz-od 默认编组）任务作为可选项；独立工具应用不入列
  const known = new Set(cards.map(card => card.app_id))
  for (const item of catalog.value) {
    if (item.default_group && !known.has(item.app_id)) {
      cards.push({
        app_id: item.app_id,
        app_name: item.app_name,
        enabled: false,
        configurable: item.configurable,
      })
    }
  }
  return cards
})

/** 当前模式展示的任务卡片：用户=MAS 字段编排；直控=所选实例的原生编排 */
const activeTaskCards = computed<TaskCard[]>(() =>
  formData.Info.Mode === '直控' ? nativeTasks.value : taskCards.value
)

const persistAppList = (list: { app_id: string; enabled: boolean }[]) => {
  formData.OneDragon.AppList = JSON.stringify(list)
  void saveField('OneDragon.AppList', formData.OneDragon.AppList)
}

/** 开关即配置：开=加入编排末尾；关=移出编排（直控直接写回实例原生 YAML） */
const toggleTask = (card: TaskCard) => {
  if (formData.Info.Mode === '直控') {
    const list = [...nativeTasks.value]
    const idx = list.findIndex(item => item.app_id === card.app_id)
    if (idx >= 0) {
      list[idx] = { ...list[idx], enabled: !list[idx].enabled }
    } else {
      list.push({ app_id: card.app_id, app_name: card.app_name, enabled: true, configurable: card.configurable })
    }
    nativeTasks.value = list
    void saveNativeConfig({ tasks: toNativeTaskIn(list) }, 'tasks', true)
    return
  }
  const list = [...savedApps.value]
  const idx = list.findIndex(item => item.app_id === card.app_id)
  if (idx >= 0) {
    if (list[idx].enabled) {
      list.splice(idx, 1)
    } else {
      list[idx] = { ...list[idx], enabled: true }
    }
  } else {
    list.push({ app_id: card.app_id, enabled: true })
  }
  persistAppList(list)
}

/** 调整任务执行顺序（仅在编排内的任务可移动；直控直接写回实例原生 YAML） */
const moveTask = (card: TaskCard, offset: number) => {
  if (formData.Info.Mode === '直控') {
    const list = [...nativeTasks.value]
    const idx = list.findIndex(item => item.app_id === card.app_id)
    const target = idx + offset
    if (idx < 0 || target < 0 || target >= list.length) return
    const [item] = list.splice(idx, 1)
    list.splice(target, 0, item)
    nativeTasks.value = list
    void saveNativeConfig({ tasks: toNativeTaskIn(list) }, 'tasks', true)
    return
  }
  const list = [...savedApps.value]
  const idx = list.findIndex(item => item.app_id === card.app_id)
  const target = idx + offset
  if (idx < 0 || target < 0 || target >= list.length) return
  const [item] = list.splice(idx, 1)
  list.splice(target, 0, item)
  persistAppList(list)
}

// ══ 原生 GUI 设置会话（直控模式专用；viewOnly 为只读查看会话）══
const {
  zzzodConfigLoading,
  zzzodWebsocketId,
  showZzzodConfigMask,
  showZzzodViewMask,
  stoppingZzzodConfig,
  startSession,
  saveSession,
  stopSession,
  dispose: disposeGuiSession,
} = useZzzodGuiSession()

const handleZzzodConfig = () => {
  if (!userId.value) return
  void startSession(userId.value)
}

const handleSaveZzzodConfig = () => {
  void saveSession()
}

const handleCloseZzzodView = () => {
  void stopSession()
}

const handleCancel = async () => {
  await stopSession()
  await router.push('/scripts')
}

const selectGamePath = async () => {
  const paths = await window.electronAPI?.selectFile([
    {
      name: 'ZenlessZoneZero.exe',
      extensions: ['exe'],
    },
  ])
  const path = paths?.[0]
  if (!path) return
  const fileName = path.split(/[\\/]/).pop()
  if (fileName?.toLowerCase() !== 'zenlesszonezero.exe') {
    message.error(t('edit.zzzodPickGameExe'))
    return
  }
  formData.Game.GamePath = path
  void saveField('Game.GamePath', path)
}

const loadScriptInfo = async (): Promise<boolean> => {
  const detail = await getScript(scriptId)
  if (!detail || detail.type !== 'ZzzOd') {
    message.error(t('edit.zzzodScriptNotFound'))
    handleCancel()
    return false
  }

  scriptName.value = detail.name
  return true
}

const applyUserData = (userData: ZzzOdUserConfig) => {
  Object.assign(formData, {
    Info: { ...getDefaultUserData().Info, ...(userData.Info || {}) },
    Game: { ...getDefaultUserData().Game, ...(userData.Game || {}) },
    OneDragon: { ...getDefaultUserData().OneDragon, ...(userData.OneDragon || {}) },
    Notify: { ...getDefaultUserData().Notify, ...(userData.Notify || {}) },
  })
}

const loadUserData = async () => {
  const resp = await getUsers(scriptId, userId.value)
  const userIndex = resp?.index?.find(i => i.uid === userId.value)
  const data = resp?.data?.[userId.value]
  if (!userIndex || !data) {
    throw new Error('用户不存在或加载失败')
  }
  applyUserData(data as ZzzOdUserConfig)
  await nextTick()
  formData.userName = formData.Info.Name || ''
}

const loadUser = async () => {
  pageLoading.value = true
  try {
    if (!userId.value) {
      if (!(await createUserImmediately())) return
    }
    await loadUserData()
  } catch (e) {
    logger.error(e instanceof Error ? e.message : String(e))
    message.error(t('edit.couldNotLoadUser'))
    handleCancel()
  } finally {
    isInitializing.value = false
    pageLoading.value = false
  }
}

onMounted(async () => {
  if (await loadScriptInfo()) {
    await loadUser()
    await loadInstances()
    await loadCatalog()
    // 已是直控模式的用户：同样确保原生配置已有最新备份（指纹去重，幂等）
    if (formData.Info.Mode === '直控') {
      await ensureDirectBackup()
    }
  }
})

// 「在一条龙内配置」会话结束后回读会刷新后端字段，重新拉取保持表单同步
// （查看会话只读不回读，无需刷新）。直控时以所选实例的原生配置为准。
watch(showZzzodConfigMask, (now, before) => {
  if (before && !now && !showZzzodViewMask.value && userId.value) {
    if (formData.Info.Mode === '直控') {
      if (nativeInstanceIdx.value !== null) {
        void loadNativeConfig(nativeInstanceIdx.value).catch(e => {
          logger.error(e instanceof Error ? e.message : String(e))
        })
      }
    } else {
      void loadUserData().catch(e => {
        logger.error(e instanceof Error ? e.message : String(e))
      })
    }
  }
})

onUnmounted(() => {
  // 直控页面关闭：补一份「配置完成时」的备份（指纹去重；与进入时的「改动前」备份配对）
  if (formData.Info.Mode === '直控') {
    void ensureDirectBackup()
  }
  void stopSession()
  disposeGuiSession()
})
</script>

<style scoped>
.user-edit-container {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.user-edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
  padding: 0 8px;
}

.header-nav {
  flex: 1;
}

.breadcrumb {
  margin: 0;
}

.breadcrumb-link {
  align-items: center;
  gap: 8px;
  color: var(--ant-color-text-secondary);
  text-decoration: none;
}

.user-edit-content {
  display: flex;
  flex-direction: column;
  gap: 0;
  flex: 1;
  min-height: 0;
  padding-bottom: 24px;
}

.config-card {
  overflow: hidden;
}

.config-card :deep(.ant-card-head) {
  background: var(--ant-color-bg-container);
  padding: 24px 32px;
}

.config-card :deep(.ant-card-body) {
  padding: 32px;
}

.form-section {
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ant-color-border-secondary);
}

.section-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-desc {
  color: var(--ant-color-text-tertiary);
  margin: 8px 0 16px;
  font-size: 14px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.help-icon {
  color: var(--ant-color-text-tertiary);
  cursor: help;
}

/* 直控绑定提示与原生配置保存按钮间距 */
.native-bind-alert {
  margin-bottom: 8px;
}

.native-bind-alert + .ant-spin-nested-loading {
  margin-top: 8px;
}

.path-input-group {
  display: flex;
  overflow: hidden;
  border: 1px solid var(--ant-color-border);
}

.path-input {
  flex: 1;
  min-width: 0;
  border: none !important;
  border-radius: 0 !important;
}

.path-button {
  flex-shrink: 0;
  border: none;
  border-radius: 0;
  background: var(--ant-color-primary-bg);
  color: var(--ant-color-primary);
  font-weight: 600;
  padding: 0 20px;
  border-left: 1px solid var(--ant-color-border-secondary);
}

.config-form :deep(.ant-form-item) {
  margin-bottom: 24px;
}

/* 一条龙任务卡片网格（对齐任务配置区的卡片 + 开关交互语言） */
.task-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.task-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 16px;
  border: 1px solid var(--ant-color-border-secondary);
  border-radius: 8px;
  background: var(--ant-color-fill-quaternary);
  transition:
    background 0.2s,
    border-color 0.2s;
}

.task-card:hover {
  background: var(--ant-color-fill-tertiary);
}

.task-card.inactive {
  opacity: 0.6;
}

.task-card-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.task-name {
  font-weight: 600;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.task-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-height: 24px;
}

/* 任务卡片 ⚙：可配置任务高亮 */
.task-config-gear {
  color: var(--ant-color-primary);
}

.task-config-loading {
  display: flex;
  justify-content: center;
  padding: 8px 0;
}

.task-config-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 260px;
  padding: 4px 0;
}

.task-config-field-title {
  color: var(--ant-color-text);
  font-size: 13px;
}

.restore-entry {
  flex-shrink: 0;
}

.restore-target-switch {
  margin-bottom: 12px;
}

.restore-desc {
  margin: 0 0 12px;
  color: var(--ant-color-text-secondary);
  font-size: 13px;
}

.backup-time {
  color: var(--ant-color-text);
  font-variant-numeric: tabular-nums;
}

/* 开关胶囊 */
.config-group-item-capsule {
  width: 40px;
  height: 22px;
  border-radius: 11px;
  border: 1px solid var(--ant-color-border);
  background: var(--ant-color-bg-container);
  position: relative;
  cursor: pointer;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.config-group-item-capsule .config-group-item-dot {
  position: absolute;
  top: 2px;
  left: 2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ant-color-text-quaternary);
  transition: all 0.2s ease;
}

.config-group-item-capsule.active {
  border-color: var(--ant-color-primary);
  background: var(--ant-color-primary);
}

.config-group-item-capsule.active .config-group-item-dot {
  left: 20px;
  background: #fff;
}

/* 遮罩 */
.zzzod-config-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.mask-content {
  text-align: center;
  color: #fff;
  max-width: 420px;
  padding: 0 24px;
}

.mask-icon {
  margin-bottom: 24px;
}

.mask-title {
  color: #fff;
  font-size: 24px;
  margin-bottom: 16px;
}

.mask-description {
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  line-height: 1.8;
  margin-bottom: 32px;
}

@media (max-width: 768px) {
  .user-edit-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .config-card :deep(.ant-card-body) {
    padding: 20px;
  }
}
</style>
