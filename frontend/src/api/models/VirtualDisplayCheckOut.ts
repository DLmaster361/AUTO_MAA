/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { VirtualDisplayCheckResultItem } from './VirtualDisplayCheckResultItem';
export type VirtualDisplayCheckOut = {
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
     * 驱动次版本号
     */
    driverVersion?: (number | null);
    /**
     * 检测时的显示器概况
     */
    monitors?: string;
    results?: Array<VirtualDisplayCheckResultItem>;
};

