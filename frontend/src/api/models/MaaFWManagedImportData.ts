/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWManagedProjection } from './MaaFWManagedProjection';
export type MaaFWManagedImportData = {
    /**
     * 项目 ID
     */
    projectId: string;
    /**
     * 版本号
     */
    version: string;
    /**
     * Project Store 实例身份
     */
    storeId: string;
    /**
     * 不可变版本载荷目录
     */
    dataPath: string;
    /**
     * 是否已绑定到脚本
     */
    bound?: boolean;
    /**
     * 脱壳报告
     */
    projection: MaaFWManagedProjection;
};

