import { contextBridge, ipcRenderer } from 'electron'

// 暴露安全的API给渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  openDevTools: () => ipcRenderer.invoke('open-dev-tools'),
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  selectFile: (filters?: any[]) => ipcRenderer.invoke('select-file', filters),
})

// 类型声明
declare global {
  interface Window {
    electronAPI: {
      openDevTools: () => Promise<void>
      selectDirectory: () => Promise<string | null>
      selectFile: (filters?: any[]) => Promise<string | null>
    }
  }
}