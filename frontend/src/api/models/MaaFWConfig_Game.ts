/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
export type MaaFWConfig_Game = {
    /**
     * 游戏启动模式
     */
    LaunchMode?: ('AttachOnly' | 'DirectExe' | null);
    /**
     * DirectExe 模式下 MAS 启动的游戏 exe
     */
    LaunchPath?: (string | null);
    /**
     * 游戏启动参数
     */
    Arguments?: (string | null);
    /**
     * 游戏启动后等待窗口就绪的时间（秒）
     */
    WaitTime?: (number | null);
    /**
     * 任务结束后是否关闭由 MAS 启动的游戏
     */
    CloseOnFinish?: (boolean | null);
    /**
     * Win32 controller 下把游戏窗口客户区调整为指定尺寸；Off 不调整，Fit 取屏幕放得下的最大一档
     */
    WindowSize?: ('Off' | 'Fit' | '1280x720' | '1600x900' | '1920x1080' | null);
};

