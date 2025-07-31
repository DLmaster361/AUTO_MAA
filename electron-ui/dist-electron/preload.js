"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  minimize: () => electron.ipcRenderer.invoke("window-minimize"),
  maximize: () => electron.ipcRenderer.invoke("window-maximize"),
  close: () => electron.ipcRenderer.invoke("window-close")
});
//# sourceMappingURL=preload.js.map
