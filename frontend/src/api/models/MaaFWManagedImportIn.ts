/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type MaaFWManagedImportIn = {
    /**
     * 本地项目目录或 ZIP 发行包路径
     */
    sourcePath: string;
    /**
     * 导入后绑定到该托管脚本；留空则只入库不绑定
     */
    scriptId?: (string | null);
    /**
     * 导入后设为该项目的当前版本
     */
    activate?: boolean;
};

