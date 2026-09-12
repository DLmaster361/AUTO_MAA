/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
/**
 * 脱壳报告。数值全部取自 Store manifest，界面直接展示，不要另算。
 */
export type MaaFWManagedProjection = {
    /**
     * 导入源的体积
     */
    sourceSizeBytes?: number;
    /**
     * 脱壳后落盘的体积
     */
    payloadSizeBytes?: number;
    /**
     * 脱壳省下的体积
     */
    savedBytes?: number;
    /**
     * 脱壳省下的比例（百分数）
     */
    savedPercent?: number;
    /**
     * 被排除的路径条数
     */
    excludedCount?: number;
    /**
     * 识别到的外壳家族，如 MFAAvalonia / MXU
     */
    shellFamilies?: Array<string>;
    /**
     * 被排除路径 → 原因（截断到前 128 条）
     */
    excludedReasons?: Record<string, string>;
};

