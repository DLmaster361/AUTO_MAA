/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 直控前置备份结果
 */
export type ZzzOdDirectBackupOut = {
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
     * 本次是否新建备份（指纹对比后内容与最近备份一致时为 False）
     */
    created: boolean;
    /**
     * 最新一条龙原生配置备份时间戳（无备份时为空）
     */
    time: string;
};

