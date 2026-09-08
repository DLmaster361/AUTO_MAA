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
     * 迁移前的原项目目录
     */
    sourcePath: string;
    /**
     * 原目录是否已删除
     */
    sourceDeleted?: boolean;
    /**
     * 删除原目录失败的原因；迁移本身已经完成
     */
    sourceDeleteError?: (string | null);
    /**
     * 脱壳报告
     */
    projection: MaaFWManagedProjection;
};

