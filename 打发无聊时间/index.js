// 导入所需的 Electron 组件
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

// 保持对窗口对象的全局引用，避免垃圾回收导致窗口关闭
let mainWindow;

function createWindow() {
  // 创建浏览器窗口
  // 获取屏幕尺寸
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

  mainWindow = new BrowserWindow({
    width: 400,
    height: 300,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    hasShadow: true,
    // 关键设置：确保窗口可以自由移动
    movable: true,
    // 避免系统拖动限制
    fullscreenable: false,
    skipTaskbar: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      enableRemoteModule: true,
      // 允许窗口内容超出边界（确保拖动功能正常）
      backgroundThrottling: false
    }
  });
  
  // 设置可移动范围为整个屏幕
  // 移除所有限制
  mainWindow.setMovable(true);
  console.log(`屏幕尺寸: ${screenWidth}x${screenHeight}`);
  console.log(`窗口可在整个屏幕范围内拖动`);
  
  // 监听窗口移动事件，确保不会限制拖动范围
  mainWindow.on('will-move', (event, newBounds) => {
    // 不阻止任何移动 - 注释掉任何阻止事件的代码
    // event.preventDefault();
  });

  // 加载 HTML 文件，使用 path.join 处理路径问题
  const indexPath = path.join(__dirname, 'index.html');
  mainWindow.loadFile(indexPath);
  
  // 输出加载的路径以便于调试
  console.log('Loading file from path:', indexPath);

  // 窗口关闭时触发的事件
  mainWindow.on('closed', function() {
    mainWindow = null;
  });
}

// 当 Electron 完成初始化并准备创建浏览器窗口时调用此方法
app.whenReady().then(createWindow);

// 所有窗口关闭时退出应用
app.on('window-all-closed', function() {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', function() {
  if (mainWindow === null) createWindow();
});

// 监听关闭应用的消息
ipcMain.on('close-app', () => {
  app.quit();
});

// 不再需要自定义拖动事件处理
// 使用Electron原生的-webkit-app-region: drag支持
