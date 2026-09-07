/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 按需归档目标池当前配置（编辑界面三时机：进入/退出/运行前）
 */
export type ZzzOdBackupEnsureIn = {
    /**
     * 所属脚本ID
     */
    scriptId: string;
    /**
     * 目标用户ID
     */
    userId: string;
    /**
     * 归档目标：onedragon=一条龙原生配置当前状态（进入编辑界面时捕捉 MAS 操作前原始态）；mas=MAS 用户绑定槽当前状态（退出编辑界面时的用户侧终态）
     */
    target?: ZzzOdBackupEnsureIn.target;
};
export namespace ZzzOdBackupEnsureIn {
    /**
     * 归档目标：onedragon=一条龙原生配置当前状态（进入编辑界面时捕捉 MAS 操作前原始态）；mas=MAS 用户绑定槽当前状态（退出编辑界面时的用户侧终态）
     */
    export enum target {
        ONEDRAGON = 'onedragon',
        MAS = 'mas',
    }
}

