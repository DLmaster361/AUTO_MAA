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

// 执行层步骤命名约定：同一战斗类型可配多个独立实例，名字形如 "自动秘境-副本A"
// （基名 + "-" 后缀）。归一到基名以复用分发 / 每周逻辑。基名本身不含 "-"。
function baseStepName(name) {
  if (COMBAT_STEPS.includes(name) || DAILY_STEPS.includes(name)) return name;
  const idx = name.indexOf("-");
  return idx > 0 ? name.slice(0, idx) : name;
}

// 日志：优先 BGI 注入的 log（写入 BGI 日志文件，供 MAS 监控解析 MAS_STEP_* 标记），
// console.log 仅作兜底（不进日志文件）。不可命名回 log，避免遮蔽注入对象。
function masLog(line) {
  try {
    if (typeof log !== "undefined" && log && typeof log.info === "function") {
      log.info(line);
      return;
    }
  } catch (e) {
    /* 忽略注入缺失 */
  }
  console.log(line);
}

// 统一封装：每次 new 一个新 Param；必须 await；try/finally 复位主界面；
// 策略用 setCombatStrategyPath 的返回值回填（遵循 AutoPlan 六条纪律）。
// new Date().getDay() 的顺序：0=周日..6=周六
const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

// 星期执行标记：地脉花的「执行」勾选由 MAS 托管在 weeklyLeyLine[day].run；
// 其余任务读扁平的 run{Day}。全部未勾选视为不限制（每天执行）。
function weekdayRunFlags(step) {
  const s = step.settings || {};
  const weekly = s.weeklyLeyLine;
  if (weekly && typeof weekly === "object") {
    const flags = DAY_NAMES.map((d) => !!(weekly[d] && weekly[d].run === true));
    if (flags.some(Boolean)) return flags;
  }
  return DAY_NAMES.map((d) => s["run" + d] === true);
}

// 星期编排：仅当勾选的星期包含今天才执行；全部未勾选视为不限制（每天执行）。
// 由 MAS 自行管理，不依赖被过滤掉的原生一条龙「每周刷取」配置表。
function shouldRunToday(step) {
  const s = step.settings || {};
  // 秘境特殊处理：每周秘境开启时按当天的「执行」开关（开启才执行）；全关=不执行。
  // 每日秘境（关闭每周）不受星期限制，每天都跑。
  if (baseStepName(step.name) === "自动秘境") {
    const useWeekly = s.weeklyDomainEnabled !== false;
    if (useWeekly) {
      const wd = s.weeklyDomain || {};
      const wdName = DAY_NAMES[new Date().getDay()];
      return !!(wd[wdName] && wd[wdName].run === true);
    }
    return true;
  }
  const flags = weekdayRunFlags(step);
  if (!flags.some(Boolean)) return true;
  return flags[new Date().getDay()];
}

async function dispatchCombat(step) {
  const s = step.settings || {};
  switch (baseStepName(step.name)) {
    case "自动秘境": {
      // 每周配置由 MAS 托管：按今天星期从 settings.weeklyDomain 取对应行（回退 default）。
      // 关闭「每周秘境」时只走每日行；奖励档位同理，每周走 default.reward（每周表默认行），
      // 走每日则用 sundaySelectedValue（每日行），两者不可混用。
      const wdName = DAY_NAMES[new Date().getDay()];
      const wd = s.weeklyDomain || {};
      const defaultRow = wd.default || {};
      const useWeekly = s.weeklyDomainEnabled !== false;
      const todayRow = (useWeekly && wd[wdName]) || {};
      const partyName = todayRow.partyName || defaultRow.partyName || s.partyName;
      const domainName = todayRow.domainName || defaultRow.domainName || s.domainName;
      const reward = useWeekly
        ? todayRow.reward != null
          ? todayRow.reward
          : defaultRow.reward != null
            ? defaultRow.reward
            : s.sundaySelectedValue
        : s.sundaySelectedValue;
      // 战斗策略：优先当天行，其次每周默认行，最后才是步骤级 combatStrategyPath（全局兜底）。
      // 留空则完全不设置，由 BGI 沿用 autoFightConfig 的全局策略。
      const strategyName = todayRow.strategy || defaultRow.strategy || s.combatStrategyPath;
      // 今天无对应秘境配置则跳过（不执行）
      if (!domainName) {
        masLog("MAS_STEP_SKIP_WEEKDAY: " + step.uid + " " + step.name);
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
      if (strategyName) p.combatStrategyPath = p.setCombatStrategyPath(strategyName);
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
      // 每日地脉花（leyLineDailyEnabled）优先于每周地脉花：开启时走每日统一配置，直接执行；
      // 否则走每周地脉花：按今天星期取对应行，仅当该行执行开关开启才刷取，
      // 当天某字段为空时按「默认」行兜底（默认行无执行开关）。
      const wdName = DAY_NAMES[new Date().getDay()];
      // 未配置（新用户）默认走每日模式，与右栏「开启每日地脉花」默认开启一致；
      // 仅显式 false（用户选了每周地脉花）才走每周分支。
      const daily = s.leyLineDailyEnabled !== false;
      let country, leyLineOutcropType, team, strategy;
      if (daily) {
        country = s.country;
        leyLineOutcropType = s.leyLineOutcropType;
        team = s.team;
        strategy = s.combatStrategyPath;
      } else {
        const weeklyLeyLine = s.weeklyLeyLine || {};
        const wdRow = weeklyLeyLine[wdName] || {};
        // 执行开关全部关闭（今天的行未勾选）即不执行
        if (wdRow.run !== true) {
          masLog("MAS_STEP_SKIP_WEEKDAY: " + step.uid + " " + step.name);
          break;
        }
        const def = weeklyLeyLine.default || {};
        country = wdRow.country != null ? wdRow.country : (def.country != null ? def.country : s.country);
        leyLineOutcropType = wdRow.type != null ? wdRow.type : (def.type != null ? def.type : s.leyLineOutcropType);
        team = wdRow.team || def.team || s.team;
        strategy = wdRow.strategy || def.strategy || s.combatStrategyPath;
      }
      const p = new AutoLeyLineOutcropParam(
        s.count != null ? s.count : 3,
        country || "",
        leyLineOutcropType || ""
      );
      if (s.isResinExhaustionMode != null) p.isResinExhaustionMode = !!s.isResinExhaustionMode;
      if (s.openModeCountMin != null) p.openModeCountMin = !!s.openModeCountMin;
      // 前端「不使用冒险之证寻路」勾选=true 表示不通过冒险之证，与 BGI Param 的
      // useAdventurerHandbook 语义相反，此处取反后透传（原 TODO(#4) 已据 UI 语义落地）。
      if (s.useAdventurerHandbook != null) p.useAdventurerHandbook = !s.useAdventurerHandbook;
      // 「跳过准备流程」(LeyLineOneDragonMode)：经查证（bettergi.d.ts + BGI main 分支源码）
      // AutoLeyLineOutcropParam 无此字段、dispatcher.runAutoLeyLineOutcropTask 无附加参数，
      // oneDragonMode 是 AutoLeyLineOutcropTask 构造参数（由 BGI 一条龙调度器注入，JS 不可达）；
      // SoloTask 工厂也不会读取该任务键，故 MAS 接管路径暂无法透传，开关仅在
      // BGI 原生一条龙（未被 Plan 接管）路径生效（原生副本已双写该键）。
      // 地脉花无原生超时，不兜底（前端默认 0=不限制）；仅当显式 >0 时透传。
      if (s.timeout != null && s.timeout > 0) p.timeout = s.timeout;
      if (s.useFragileResin != null) p.useFragileResin = !!s.useFragileResin;
      if (s.useTransientResin != null) p.useTransientResin = !!s.useTransientResin;
      // 好感队仅在战斗队伍填写后才透传（冻结态视为空）
      if (team) p.team = team;
      if (team && s.friendshipTeam) p.friendshipTeam = s.friendshipTeam;
      // 地脉花 Param 在部分 BGI 版本无 setCombatStrategyPath（d.ts 未声明），做存在性守卫防 TypeError
      if (strategy) {
        if (typeof p.setCombatStrategyPath === "function") {
          p.combatStrategyPath = p.setCombatStrategyPath(strategy);
        } else {
          masLog("MAS_LEYLINE_STRATEGY_UNSUPPORTED: " + strategy);
        }
      }
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
      // maxArtifactStar 来自秘境面板（globalDomain），由 _route_combat_to_plan 同步进本 step
      if (s.maxArtifactStar != null) p.maxArtifactStar = String(s.maxArtifactStar);
      if (s.specifyResinUse != null) p.specifyResinUse = !!s.specifyResinUse;
      if (s.originalResinUseCount != null) p.originalResinUseCount = s.originalResinUseCount;
      if (s.condensedResinUseCount != null) p.condensedResinUseCount = s.condensedResinUseCount;
      if (s.transientResinUseCount != null) p.transientResinUseCount = s.transientResinUseCount;
      if (s.fragileResinUseCount != null) p.fragileResinUseCount = s.fragileResinUseCount;
      // 右栏幽境面板的战斗队伍/策略优先（fightTeamName/strategyName 来自 globalStygian），
      // 留空时 Param 不设置，BGI 回退全局 config.json 段（顶部通用队伍/策略兜底）。
      if (s.fightTeamName) p.fightTeamName = s.fightTeamName;
      const stygianStrategy = s.strategyName || s.combatStrategyPath;
      if (stygianStrategy) p.combatStrategyPath = p.setCombatStrategyPath(stygianStrategy);
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

function safeParsePlan(raw) {
  if (typeof raw === "string" && raw.trim()) {
    try {
      return JSON.parse(raw);
    } catch (e) {
      return { version: 1, steps: [] };
    }
  }
  return raw;
}

async function main() {
  masLog(
    "MAS_SETTINGS_KEYS " +
      (typeof settings !== "undefined" && settings
        ? Object.keys(settings).join(",")
        : "(no settings)")
  );
  const rawPlan =
    typeof settings !== "undefined" && settings ? settings.plan : undefined;
  const plan = safeParsePlan(rawPlan) || {
    version: 1,
    steps: [],
  };
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  masLog("MAS_PLAN_BEGIN " + steps.length);
  for (const step of steps) {
    if (!step || !step.enabled) {
      masLog("MAS_STEP_SKIP: " + (step ? step.uid : "?"));
      continue;
    }
    if (DAILY_STEPS.includes(baseStepName(step.name))) {
      masLog("MAS_STEP_DAILY: " + step.uid + " " + step.name); // 由随后的一条龙承接
      continue;
    }
    if (!COMBAT_STEPS.includes(baseStepName(step.name))) {
      masLog("MAS_STEP_UNKNOWN: " + step.uid + " " + step.name);
      continue;
    }
    if (!shouldRunToday(step)) {
      masLog("MAS_STEP_SKIP_WEEKDAY: " + step.uid + " " + step.name);
      continue;
    }
    masLog("MAS_STEP_BEGIN: " + step.uid + " " + step.name);
    try {
      await dispatchCombat(step);
      masLog("MAS_STEP_DONE: " + step.uid + " " + step.name);
    } catch (e) {
      const msg = (e && (e.message || e.toString())) || String(e);
      masLog("MAS_STEP_FAIL: " + step.uid + " " + step.name + " " + msg);
      throw e; // 单配置组场景下异常即失败，与 AutoProxy 判定一致
    }
  }
  masLog("MAS_PLAN_DONE");
}

main().catch((e) => {
  const msg = (e && (e.message || e.toString())) || String(e);
  masLog("MAS_PLAN_FAIL " + msg);
  throw e;
});
