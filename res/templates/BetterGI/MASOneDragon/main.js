// MASOneDragon/main.js
// 路径 B「MAS 自编排执行层」：读取 settings.plan.steps，按顺序把战斗 4 项直连
// BetterGI 原生任务（dispatcher.runAutoXxxTask）；日常 4 项不在此处理（由随后启动的
// 一条龙承接，其副本已过滤掉战斗 4 项，避免重复）。每步打印 MAS_STEP_* 标记行，
// 供 MAS 的 one_dragon_report 解析步骤级成败。
//
// ⚠️ 待实机复核（技术路径文档 #4/#5/#7）：
//   - settings 注入方式（全局 `settings` 还是脚本参数）、脚本入口约定；
//   - 地脉花 useAdventurerHandbook 语义反转（AutoPlan 记录需取反）；
//   - 秘境 domainRoundNum 轮数 ↔ 树脂次数的换算；
//   - 字段名以目标版本 bettergi.d.ts 复核（本文件依据 bettergi-scripts-list 0.64 附近 d.ts）。

const COMBAT_STEPS = ["自动秘境", "自动地脉花", "自动幽境危战", "自动首领讨伐"];
const DAILY_STEPS = ["领取邮件", "合成树脂", "领取每日奖励", "领取尘歌壶奖励"];

function log(line) {
  console.log(line);
}

// 统一封装：每次 new 一个新 Param；必须 await；try/finally 复位主界面；
// 策略用 setCombatStrategyPath 的返回值回填（遵循 AutoPlan 六条纪律）。
// 星期编排：仅当 settings 中勾选的星期包含今天才执行；全部未勾选视为不限制（每天执行）。
// 由 MAS 自行管理，不依赖被过滤掉的原生一条龙「每周刷取」配置表。
function shouldRunToday(step) {
  const s = step.settings || {};
  const days = ["runSunday", "runMonday", "runTuesday", "runWednesday", "runThursday", "runFriday", "runSaturday"];
  const anyChecked = days.some((k) => s[k] === true);
  if (!anyChecked) return true;
  const todayKey = days[new Date().getDay()]; // getDay(): 0=Sun..6=Sat
  return s[todayKey] === true;
}

async function dispatchCombat(step) {
  const s = step.settings || {};
  switch (step.name) {
    case "自动秘境": {
      // 每周配置由 MAS 托管：按今天星期从 settings.weeklyDomain 取对应行（回退 default）
      const wdName = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][new Date().getDay()];
      const wdRow = (s.weeklyDomain && (s.weeklyDomain[wdName] || s.weeklyDomain.default)) || {};
      const partyName = wdRow.partyName != null ? wdRow.partyName : s.partyName;
      const domainName = wdRow.domainName != null ? wdRow.domainName : s.domainName;
      const reward = wdRow.reward != null ? wdRow.reward : s.sundaySelectedValue;
      // 今天无对应秘境配置则跳过（不执行）
      if (!domainName) {
        log("MAS_STEP_SKIP_WEEKDAY: " + step.uid + " " + step.name);
        return;
      }
      const p = new AutoDomainParam(s.domainRoundNum != null ? s.domainRoundNum : 1);
      if (partyName) p.partyName = partyName;
      if (domainName) p.domainName = domainName;
      if (reward != null) p.sundaySelectedValue = String(reward);
      if (s.autoArtifactSalvage != null) p.autoArtifactSalvage = !!s.autoArtifactSalvage;
      if (s.maxArtifactStar != null) p.maxArtifactStar = String(s.maxArtifactStar);
      if (s.specifyResinUse != null) p.specifyResinUse = !!s.specifyResinUse;
      if (s.originalResinUseCount != null) p.originalResinUseCount = s.originalResinUseCount;
      if (s.condensedResinUseCount != null) p.condensedResinUseCount = s.condensedResinUseCount;
      if (s.transientResinUseCount != null) p.transientResinUseCount = s.transientResinUseCount;
      if (s.fragileResinUseCount != null) p.fragileResinUseCount = s.fragileResinUseCount;
      if (s.combatStrategyPath) p.combatStrategyPath = p.setCombatStrategyPath(s.combatStrategyPath);
      if (Array.isArray(s.resinPriorityList)) p.setResinPriorityList(...s.resinPriorityList);
      await genshin.returnMainUi();
      try {
        await dispatcher.runAutoDomainTask(p);
      } finally {
        await genshin.returnMainUi();
      }
      break;
    }
    case "自动地脉花": {
      // 每周配置由 MAS 托管：按今天星期从 settings.weeklyLeyLine 取对应行的地区/类型
      const wdName = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"][new Date().getDay()];
      const wdRow = (s.weeklyLeyLine && s.weeklyLeyLine[wdName]) || {};
      const country = wdRow.country != null ? wdRow.country : s.country;
      const leyLineOutcropType = wdRow.type != null ? wdRow.type : s.leyLineOutcropType;
      const p = new AutoLeyLineOutcropParam(
        s.count != null ? s.count : 3,
        country || "",
        leyLineOutcropType || ""
      );
      if (s.isResinExhaustionMode != null) p.isResinExhaustionMode = !!s.isResinExhaustionMode;
      if (s.openModeCountMin != null) p.openModeCountMin = !!s.openModeCountMin;
      // TODO(#4): AutoPlan 记录 useAdventurerHandbook 需取反，实机确认后改为 !s.useAdventurerHandbook
      if (s.useAdventurerHandbook != null) p.useAdventurerHandbook = !!s.useAdventurerHandbook;
      if (s.team) p.team = s.team;
      // 「跳过准备流程」(LeyLineOneDragonMode) 为 BGI 地脉花 Task 级开关（已确认层级），
      // 非 AutoLeyLineOutcropParam 字段，需改用 SoloTask("AutoLeyLineOutcrop", cfg) 包裹传入；
      // 数据已在 settings.leyLineOneDragonMode，待后续接入，此处不塞进 Param。
      // 地脉花无原生超时，不兜底（前端默认 0=不限制）；仅当显式 >0 时透传。
      if (s.timeout != null && s.timeout > 0) p.timeout = s.timeout;
      if (s.useFragileResin != null) p.useFragileResin = !!s.useFragileResin;
      if (s.useTransientResin != null) p.useTransientResin = !!s.useTransientResin;
      await genshin.returnMainUi();
      try {
        await dispatcher.runAutoLeyLineOutcropTask(p);
      } finally {
        await genshin.returnMainUi();
      }
      break;
    }
    case "自动幽境危战": {
      const p = new AutoStygianOnslaughtParam("");
      if (s.bossNum != null) p.bossNum = s.bossNum;
      if (s.autoArtifactSalvage != null) p.autoArtifactSalvage = !!s.autoArtifactSalvage;
      if (s.specifyResinUse != null) p.specifyResinUse = !!s.specifyResinUse;
      if (s.originalResinUseCount != null) p.originalResinUseCount = s.originalResinUseCount;
      if (s.condensedResinUseCount != null) p.condensedResinUseCount = s.condensedResinUseCount;
      if (s.transientResinUseCount != null) p.transientResinUseCount = s.transientResinUseCount;
      if (s.fragileResinUseCount != null) p.fragileResinUseCount = s.fragileResinUseCount;
      if (s.fightTeamName) p.fightTeamName = s.fightTeamName;
      if (s.combatStrategyPath) p.combatStrategyPath = p.setCombatStrategyPath(s.combatStrategyPath);
      if (Array.isArray(s.resinPriorityList)) p.setResinPriorityList(...s.resinPriorityList);
      await genshin.returnMainUi();
      try {
        await dispatcher.runAutoStygianOnslaughtTask(p);
      } finally {
        await genshin.returnMainUi();
      }
      break;
    }
    case "自动首领讨伐": {
      // TODO(#3/#7): AutoBoss 超时经通道 B（SoloTask 配置覆盖键 AutoBossTimeout，键名已实机命中 exe）
      const timeout = s.timeout != null ? s.timeout : 240;
      const cfg = Object.assign(
        {
          AutoBossTimeout: timeout,
          bossName: s.bossName || "",
          teamName: s.teamName || "",
          specifyRunCount: !!s.specifyRunCount,
          runCount: s.runCount != null ? s.runCount : 1,
          useTransientResin: !!s.useTransientResin,
          useFragileResin: !!s.useFragileResin,
          rviveRetryCount: s.rviveRetryCount != null ? s.rviveRetryCount : 3,
          returnToStatueAfterEachRound: !!s.returnToStatueAfterEachRound,
          rewardRecognitionEnabled: !!s.rewardRecognitionEnabled,
        },
        s.combatStrategyPath ? { strategyName: s.combatStrategyPath } : {}
      );
      await genshin.returnMainUi();
      try {
        await dispatcher.runTask(new SoloTask("AutoBoss", cfg));
      } finally {
        await genshin.returnMainUi();
      }
      break;
    }
  }
}

async function main() {
  const plan = (typeof settings !== "undefined" && settings && settings.plan) || {
    version: 1,
    steps: [],
  };
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  log("MAS_PLAN_BEGIN " + steps.length);
  for (const step of steps) {
    if (!step || !step.enabled) {
      log("MAS_STEP_SKIP: " + (step ? step.uid : "?"));
      continue;
    }
    if (DAILY_STEPS.includes(step.name)) {
      log("MAS_STEP_DAILY: " + step.uid + " " + step.name); // 由随后的一条龙承接
      continue;
    }
    if (!COMBAT_STEPS.includes(step.name)) {
      log("MAS_STEP_UNKNOWN: " + step.uid + " " + step.name);
      continue;
    }
    if (!shouldRunToday(step)) {
      log("MAS_STEP_SKIP_WEEKDAY: " + step.uid + " " + step.name);
      continue;
    }
    log("MAS_STEP_BEGIN: " + step.uid + " " + step.name);
    try {
      await dispatchCombat(step);
      log("MAS_STEP_DONE: " + step.uid + " " + step.name);
    } catch (e) {
      const msg = (e && (e.message || e.toString())) || String(e);
      log("MAS_STEP_FAIL: " + step.uid + " " + step.name + " " + msg);
      throw e; // 单配置组场景下异常即失败，与 AutoProxy 判定一致
    }
  }
  log("MAS_PLAN_DONE");
}

main().catch((e) => {
  const msg = (e && (e.message || e.toString())) || String(e);
  log("MAS_PLAN_FAIL " + msg);
  throw e;
});
