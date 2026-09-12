/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWManagedProjection } from './MaaFWManagedProjection';
export type MaaFWManagedMigrateData = {
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
     * 迁移前的原项目目录；AUTO-MAS 不会动它，由用户自行决定是否删除
     */
    sourcePath: string;
    /**
     * 脱壳报告
     */
    projection: MaaFWManagedProjection;
};

