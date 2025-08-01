"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  openDevTools: () => electron.ipcRenderer.invoke("open-dev-tools"),
  selectDirectory: () => electron.ipcRenderer.invoke("select-directory"),
  selectFile: (filters) => electron.ipcRenderer.invoke("select-file", filters)
});
//# sourceMappingURL=preload.js.map
