/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWManagedVersionItem } from './MaaFWManagedVersionItem';
export type MaaFWManagedVersionsData = {
    /**
     * 项目 ID
     */
    projectId: string;
    /**
     * 当前版本
     */
    current?: (string | null);
    /**
     * 版本列表，按导入时间倒序
     */
    versions?: Array<MaaFWManagedVersionItem>;
};

