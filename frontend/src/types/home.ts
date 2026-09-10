export type HomeModuleKey =
  | 'command'
  | 'quick'
  | 'satellite'
  | 'proxy'
  | 'activities'
  | 'endfield'
  | 'starrail'
  | 'genshin'
  | 'zenless'
  | 'wutheringwaves'
  | 'nte'
  | 'reverse1999'
  | 'arknights'

export interface HomeLayoutConfig {
  moduleOrder: HomeModuleKey[]
  hiddenModules: HomeModuleKey[]
  hideScrollHint?: boolean
  /** 活动轮播是否自动播放；未设置按开启处理 */
  carouselAutoplay?: boolean
}

export interface HomeModuleDescriptor {
  key: HomeModuleKey
  title: string
  visible: boolean
}

export interface ActivityInfo {
  Tip: string
  StageName: string
  UtcStartTime: string
  UtcExpireTime: string
  TimeZone: number
}

export interface ActivityItem {
  Display: string
  Value: string
  Drop: string
  DropName: string
  Activity: ActivityInfo
}

export interface ResourceItem {
  Display: string
  Value: string
  Drop: string
  DropName: string
  Activity: Pick<ActivityInfo, 'Tip' | 'StageName'>
}

export interface StageOption {
  label: string
  value: string | null
}

export interface StageOverview {
  Activity: ActivityItem[]
  Resource: ResourceItem[]
  Options: StageOption[]
}

export interface ProxyInfo {
  LastProxyDate: string
  ProxyTimes: number
  ErrorTimes: number
  ErrorInfo: Record<string, unknown>
}

export interface EndfieldActivityItem {
  Id: string
  Name: string
  StartTime: string
  EndTime: string
  ImageUrl: string
  Tags: string[]
}

export interface EndfieldPoolItem {
  Id: string
  Name: string
  Type: string
  StartTime: string
  EndTime: string
  ImageUrl: string
  UpCharacters: string[]
}

export interface EndfieldActivityOverview {
  Available: boolean
  Stale: boolean
  Message: string
  Version: string
  UpdatedAt: string
  SourceName: string
  SourceUrl: string
  Pools: EndfieldPoolItem[]
  Activities: EndfieldActivityItem[]
}

export const createEmptyEndfieldActivityOverview = (): EndfieldActivityOverview => ({
  Available: false,
  Stale: false,
  Message: '',
  Version: '',
  UpdatedAt: '',
  SourceName: 'AKEData',
  SourceUrl: 'https://www.akedata.wiki',
  Pools: [],
  Activities: [],
})

export interface SraActivityItem {
  name: string
  description: string
  startTime: string
  endTime: string
  cover?: string
}

export interface SraActivityOverview {
  Available: boolean
  Stale: boolean
  Message: string
  version: string
  versionName: string
  cover?: string
  startTime: string
  endTime: string
  activities: SraActivityItem[]
}

export type StarRailActivityOverview = SraActivityOverview
export type GenshinActivityOverview = SraActivityOverview
export type ZenlessZoneZeroActivityOverview = SraActivityOverview
export type WutheringWavesActivityOverview = SraActivityOverview
export type NevernessToEvernessActivityOverview = SraActivityOverview
export type Reverse1999ActivityOverview = SraActivityOverview

export const createEmptySraActivityOverview = (): SraActivityOverview => ({
  Available: false,
  Stale: false,
  Message: '',
  version: '',
  versionName: '',
  cover: '',
  startTime: '',
  endTime: '',
  activities: [],
})

/** @deprecated 请改用 createEmptySraActivityOverview */
export const createEmptyStarRailActivityOverview = createEmptySraActivityOverview

export interface HomeOverviewResponse {
  Stage: StageOverview
  StageByServer: Record<string, StageOverview>
  Proxy: Record<string, ProxyInfo>
}

/** 首页活动轮播里单张 banner 的统一形状，屏蔽各游戏数据源的差异 */
export interface ActivityBannerItem {
  key: HomeModuleKey
  /** 游戏短名，用于 banner 标题与切换条 */
  title: string
  /** 主题色，无封面时用来生成底纹 */
  accent: string
  /** 封面图地址，取不到时为空串 */
  cover: string
  /** 版本名或当期活动名 */
  subtitle: string
  /** 倒计时终点，取不到时为空串 */
  endTime: string
  loading: boolean
  available: boolean
  stale: boolean
}
