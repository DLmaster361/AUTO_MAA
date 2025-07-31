"use strict";
const electron = require("electron");
let mainWindow = null;
function createWindow() {
  mainWindow = new electron.BrowserWindow({
    width: 1200,
    height: 800,
    frame: false,
    // 隐藏默认标题栏
    titleBarStyle: "hidden",
    // 隐藏标题栏
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true,
      preload: __dirname + "/preload.js"
    }
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile("dist/index.html");
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
electron.ipcMain.handle("window-minimize", () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});
electron.ipcMain.handle("window-maximize", () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.restore();
    } else {
      mainWindow.maximize();
    }
  }
});
electron.ipcMain.handle("window-close", () => {
  if (mainWindow) {
    mainWindow.close();
  }
});
electron.app.whenReady().then(createWindow);
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
//# sourceMappingURL=main.js.map
