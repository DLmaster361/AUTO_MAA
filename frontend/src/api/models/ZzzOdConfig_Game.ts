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
     * 多用户账号切换方式：一条龙内置=全部用户注入实例槽由一条龙多账号运行；MAS账号切换=逐用户循环运行（MAS侧主动切换后续接入）
     */
    AccountSwitch?: ('一条龙内置' | 'MAS账号切换' | null);
};

