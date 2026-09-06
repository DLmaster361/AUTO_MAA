/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * ZZZ-OD 游戏配置
 */
export type ZzzOdConfig_Game = {
    /**
     * 任务结束后是否由 zzz-od 关闭游戏
     */
    CloseOnFinish?: (boolean | null);
    /**
     * 多用户账号切换方式：单实例切换=逐用户独立会话（默认，推荐）；多实例切换=全部用户合并一轮多账号运行（不推荐）；MAS切换=MAS侧切换账号后交一条龙（暂未开放）
     */
    AccountSwitch?: ('单实例切换' | '多实例切换' | 'MAS切换' | null);
};

