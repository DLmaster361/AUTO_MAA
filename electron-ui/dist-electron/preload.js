"use strict";
const electron = require("electron");
electron.contextBridge.exposeInMainWorld("electronAPI", {
  openDevTools: () => electron.ipcRenderer.invoke("open-dev-tools")
});
//# sourceMappingURL=preload.js.map
