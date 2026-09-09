/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * ZZZ-OD 用户游戏账号配置（运行时生成 game_account.yml 注入）
 */
export type ZzzOdUserConfig_Game = {
    /**
     * 游戏区服
     */
    GameRegion?: ('cn' | 'cn_b' | 'us' | 'eu' | 'asia' | 'twhkmo' | null);
    /**
     * 游戏 exe 完整路径（ZenlessZoneZero.exe）
     */
    GamePath?: (string | null);
    /**
     * 游戏界面语言
     */
    GameLanguage?: ('cn' | 'en' | null);
    /**
     * 登录账号（留空沿用 zzz-od 已保存的登录态）
     */
    Account?: (string | null);
    /**
     * 登录密码（与 zzz-od 一致明文存储）
     */
    Password?: (string | null);
    /**
     * B服登录账号名
     */
    BilibiliAccountName?: (string | null);
    /**
     * 游戏平台（上游 GamePlatformEnum.PC 真实值为大写）
     */
    Platform?: (string | null);
    /**
     * 是否使用自定义窗口标题
     */
    UseCustomWinTitle?: (boolean | null);
    /**
     * 自定义窗口标题
     */
    CustomWinTitle?: (string | null);
};

