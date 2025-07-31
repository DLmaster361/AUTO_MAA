// Electron API 类型声明
declare global {
    interface Window {
        electronAPI: {
            minimize: () => Promise<void>
            maximize: () => Promise<void>
            close: () => Promise<void>
        }
    }
}

export {}