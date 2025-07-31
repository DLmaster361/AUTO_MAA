import { app, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  // 获取正确的路径
  const isDev = process.env.NODE_ENV === 'development';
  const preloadPath = isDev 
    ? join(__dirname, 'preload.js')
    : join(__dirname, 'preload.js');

  console.log('Preload path:', preloadPath);
  console.log('__dirname:', __dirname);
  console.log('isDev:', isDev);

  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    frame: false, // 隐藏默认标题栏
    titleBarStyle: 'hidden', // 隐藏标题栏
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      webSecurity: true,
      preload: preloadPath
    }
  })

  // 开发模式加载 Vite 服务，生产加载本地 index.html
  const devUrl = process.env.VITE_DEV_SERVER_URL
  if (devUrl) {
    console.log('Loading dev URL:', devUrl);
    mainWindow.loadURL(devUrl)
  } else {
    // 简化路径逻辑
    const indexPath = join(__dirname, '../dist/index.html');
    console.log('Loading file:', indexPath);
    console.log('__dirname:', __dirname);
    console.log('Current working directory:', process.cwd());
    console.log('App path:', app.getAppPath());
    
    mainWindow.loadFile(indexPath).catch((error) => {
      console.error('Failed to load index.html:', error);
      // 如果加载失败，尝试备用路径
      const backupPath = join(app.getAppPath(), 'dist/index.html');
      console.log('Trying backup path:', backupPath);
      mainWindow?.loadFile(backupPath);
    });
  }

  // 添加错误处理
  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription) => {
    console.error('Failed to load:', errorCode, errorDescription);
  });

  // 在生产环境中也打开开发者工具来调试
  if (!isDev) {
    mainWindow.webContents.openDevTools();
  }

  // 窗口关闭时清空引用
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// IPC处理程序
ipcMain.handle('window-minimize', () => {
  if (mainWindow) {
    mainWindow.minimize();
  }
});

ipcMain.handle('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.restore();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.handle('window-close', () => {
  if (mainWindow) {
    mainWindow.close();
  }
});

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
