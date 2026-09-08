/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type MaaFWManagedMigrateIn = {
    /**
     * 要迁移的 MFW 脚本 ID
     */
    scriptId: string;
    /**
     * 迁移成功后删除原项目目录；不可撤销，必须由用户显式确认
     */
    deleteSource?: boolean;
};

