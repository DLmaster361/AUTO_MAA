/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type ZzzOdBackupRestoreOut = {
    /**
     * 状态码
     */
    code?: number;
    /**
     * 操作状态
     */
    status?: string;
    /**
     * 操作消息
     */
    message?: string;
    /**
     * 关联槽 idx（onedragon 恢复为 -1，失败为 -1）
     */
    slot: number;
    /**
     * 实际执行的恢复目标
     */
    target?: ZzzOdBackupRestoreOut.target;
};
export namespace ZzzOdBackupRestoreOut {
    /**
     * 实际执行的恢复目标
     */
    export enum target {
        ONEDRAGON = 'onedragon',
        MAS = 'mas',
    }
}

