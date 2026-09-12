/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWManagedProjectItem } from './MaaFWManagedProjectItem';
export type MaaFWManagedInventoryData = {
    /**
     * Project Store 实例身份
     */
    storeId: string;
    /**
     * Store 根目录
     */
    root: string;
    /**
     * 脚本 checkout 根目录
     */
    runRoot: string;
    /**
     * Store 占用合计
     */
    totalBytes?: number;
    /**
     * 项目列表
     */
    projects?: Array<MaaFWManagedProjectItem>;
};

