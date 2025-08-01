"use strict";
const electron = require("electron");
const path = require("path");
let mainWindow = null;
function createWindow() {
  const isDev = process.env.NODE_ENV === "development";
  const preloadPath = isDev ? path.join(__dirname, "preload.js") : path.join(__dirname, "preload.js");
  console.log("Preload path:", preloadPath);
  console.log("__dirname:", __dirname);
  console.log("isDev:", isDev);
  mainWindow = new electron.BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, "../public/AUTO_MAA.ico"),
    // 设置应用图标
    autoHideMenuBar: true,
    // 隐藏菜单栏（file、edit等）
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true,
      preload: preloadPath
    }
  });
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    console.log("Loading dev URL:", devUrl);
    mainWindow.loadURL(devUrl);
  } else {
    const indexPath = path.join(__dirname, "../dist/index.html");
    console.log("Loading file:", indexPath);
    console.log("__dirname:", __dirname);
    console.log("Current working directory:", process.cwd());
    console.log("App path:", electron.app.getAppPath());
    mainWindow.loadFile(indexPath).catch((error) => {
      console.error("Failed to load index.html:", error);
      const backupPath = path.join(electron.app.getAppPath(), "dist/index.html");
      console.log("Trying backup path:", backupPath);
      mainWindow == null ? void 0 : mainWindow.loadFile(backupPath);
    });
  }
  mainWindow.webContents.on("did-fail-load", (event, errorCode, errorDescription) => {
    console.error("Failed to load:", errorCode, errorDescription);
  });
  if (!isDev) {
    mainWindow.webContents.openDevTools();
  }
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}
electron.ipcMain.handle("open-dev-tools", () => {
  if (mainWindow) {
    mainWindow.webContents.openDevTools();
  }
});
electron.ipcMain.handle("select-directory", async () => {
  if (mainWindow) {
    const { dialog } = require("electron");
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openDirectory"],
      title: "选择MAA目录",
      buttonLabel: "选择"
    });
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
  }
  return null;
});
electron.ipcMain.handle("select-file", async (event, filters = []) => {
  if (mainWindow) {
    const { dialog } = require("electron");
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ["openFile"],
      title: "选择文件",
      buttonLabel: "选择",
      filters: filters.length > 0 ? filters : [
        { name: "All Files", extensions: ["*"] }
      ]
    });
    if (!result.canceled && result.filePaths.length > 0) {
      return result.filePaths[0];
    }
  }
  return null;
});
electron.app.whenReady().then(createWindow);
electron.app.on("window-all-closed", () => {
  if (process.platform !== "darwin") electron.app.quit();
});
//# sourceMappingURL=main.js.map
