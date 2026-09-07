/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type GlobalConfig_Display = {
    /**
     * 无人值守时，桌面上没有一块屏够用则挂载虚拟显示器（需自行安装 Parsec 虚拟显示驱动）
     */
    IfEnableVirtualDisplay?: (boolean | null);
    /**
     * 虚拟显示器的分辨率与刷新率，形如 1920x1080@60
     */
    VirtualDisplayMode?: (string | null);
};

