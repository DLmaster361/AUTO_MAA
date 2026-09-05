/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { ZzzOdPreviewField } from './ZzzOdPreviewField';
import type { ZzzOdPreviewInstance } from './ZzzOdPreviewInstance';
import type { ZzzOdPreviewTask } from './ZzzOdPreviewTask';
/**
 * 备份配置摘要（预览用，纯读不恢复）
 */
export type ZzzOdBackupPreviewOut = {
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
     * 备份时间戳
     */
    time: string;
    /**
     * 备份类别
     */
    target: ZzzOdBackupPreviewOut.target;
    /**
     * 基本信息卡信息字段（mas 类备份；旧备份或 onedragon 为空）
     */
    info: Array<ZzzOdPreviewField>;
    /**
     * 账号字段（mas 类备份；onedragon 为空）
     */
    account: Array<ZzzOdPreviewField>;
    /**
     * 任务编排（mas 类备份；onedragon 为空）
     */
    tasks: Array<ZzzOdPreviewTask>;
    /**
     * 实例列表（onedragon 类备份，带可展开明细；mas 为空）
     */
    instances: Array<ZzzOdPreviewInstance>;
};
export namespace ZzzOdBackupPreviewOut {
    /**
     * 备份类别
     */
    export enum target {
        ONEDRAGON = 'onedragon',
        MAS = 'mas',
    }
}

