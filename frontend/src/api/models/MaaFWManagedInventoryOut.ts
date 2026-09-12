/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { MaaFWManagedInventoryData } from './MaaFWManagedInventoryData';
export type MaaFWManagedInventoryOut = {
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
     * Store 库存
     */
    data?: (MaaFWManagedInventoryData | null);
};

