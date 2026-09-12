/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type MaaFWManagedVersionItem = {
    /**
     * 版本号
     */
    version: string;
    /**
     * 导入时间
     */
    createdAt?: (string | null);
    /**
     * 最近使用时间
     */
    lastUsedAt?: (string | null);
    /**
     * 是否为当前版本
     */
    current?: boolean;
    /**
     * 是否被钉住
     */
    pinned?: boolean;
    /**
     * 引用者
     */
    references?: Array<string>;
    /**
     * 该版本载荷体积
     */
    sizeBytes?: number;
};

