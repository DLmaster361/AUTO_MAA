import type {
  ActivityItem,
  EndfieldActivityOverview,
  HomeModuleKey,
  SraActivityOverview,
} from '@/types/home'

/** 各游戏 banner 的主题色，无封面时用来生成底纹；与原卡片上的 accent 保持一致 */
export const HOME_ACTIVITY_ACCENTS: Record<string, string> = {
  endfield: '#ffb45a',
  starrail: '#62c4e7',
  genshin: '#8fe3b0',
  zenless: '#ffd24a',
  wutheringwaves: '#7aa2ff',
  nte: '#c9a7ff',
  reverse1999: '#f2a0c0',
  arknights: '#9fb4cc',
}

export const getActivityAccent = (key: HomeModuleKey): string => {
  return HOME_ACTIVITY_ACCENTS[key] ?? '#7aa2ff'
}

/** 从各游戏数据源里抽出 banner 需要的四项，屏蔽字段命名差异 */
export interface ActivityBannerSource {
  cover: string
  subtitle: string
  endTime: string
  available: boolean
  stale: boolean
}

export const sraActivityBanner = (overview: SraActivityOverview): ActivityBannerSource => {
  const activity = overview.activities[0]
  return {
    // 版本封面优先；部分游戏没有版本封面，退回第一张有图的活动
    cover: overview.cover || overview.activities.find(item => item.cover)?.cover || '',
    subtitle: overview.versionName || activity?.name || '',
    endTime: overview.endTime || activity?.endTime || '',
    available: overview.Available,
    stale: overview.Stale,
  }
}

export const endfieldActivityBanner = (
  overview: EndfieldActivityOverview
): ActivityBannerSource => {
  // 标题与倒计时取自同一个卡池，避免拼出一条对不上的信息
  const pool = overview.Pools.find(item => item.ImageUrl) ?? overview.Pools[0]
  const activity = overview.Activities[0]
  const fallback = pool ? undefined : activity
  return {
    cover: pool?.ImageUrl || fallback?.ImageUrl || '',
    subtitle: pool?.Name || fallback?.Name || overview.Version || '',
    endTime: pool?.EndTime || fallback?.EndTime || '',
    available: overview.Available,
    stale: overview.Stale,
  }
}

export const arknightsActivityBanner = (activityData: ActivityItem[]): ActivityBannerSource => {
  const activity = activityData[0]?.Activity
  return {
    // 明日方舟的数据源里没有活动图，靠主题色底纹兜底
    cover: '',
    subtitle: activity?.Tip ?? '',
    endTime: activity?.UtcExpireTime ?? '',
    available: activityData.length > 0,
    stale: false,
  }
}
