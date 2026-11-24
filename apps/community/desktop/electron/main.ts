import path from "node:path";
import {
  app,
  BrowserWindow,
  ipcMain,
  Menu,
  session,
  shell,
  type MenuItemConstructorOptions,
} from "electron";
import {
  attachNavigationGuards,
  buildFallbackHtml,
  resolveCommunityUrl,
  webPreferencesBase,
} from "./security";
import { loadWindowState, saveWindowState } from "./windowState";

const APP_TITLE = "Dubai-io Community";
const communityUrl = resolveCommunityUrl();

let mainWindow: BrowserWindow | null = null;
let showingFallback = false;

function resolveIconPath(): string {
  return path.join(__dirname, "..", "assets", "icon.png");
}

function loadCommunity(): void {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }
  showingFallback = false;
  void mainWindow.loadURL(communityUrl);
}

function showOfflineFallback(reason: string): void {
  if (!mainWindow || mainWindow.isDestroyed() || showingFallback) {
    return;
  }
  showingFallback = true;
  const html = buildFallbackHtml(communityUrl, reason);
  void mainWindow.loadURL(
    `data:text/html;charset=utf-8,${encodeURIComponent(html)}`,
  );
}

function buildAppMenu(): Menu {
  const template: MenuItemConstructorOptions[] = [
    {
      label: "Community",
      submenu: [
        {
          label: "Reload",
          accelerator: "CmdOrCtrl+R",
          click: () => loadCommunity(),
        },
        {
          label: "Open in Browser",
          click: () => {
            void shell.openExternal(communityUrl);
          },
        },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
        { role: "toggleDevTools" },
      ],
    },
    {
      label: "Window",
      submenu: [{ role: "minimize" }, { role: "close" }],
    },
  ];
  return Menu.buildFromTemplate(template);
}

export function createCommunityWindow(): BrowserWindow {
  const userDataDir = app.getPath("userData");
  const savedBounds = loadWindowState(userDataDir);

  const win = new BrowserWindow({
    width: savedBounds.width,
    height: savedBounds.height,
    x: savedBounds.x,
    y: savedBounds.y,
    minWidth: 640,
    minHeight: 480,
    title: APP_TITLE,
    backgroundColor: "#f3f6f8",
    icon: resolveIconPath(),
    show: false,
    webPreferences: {
      ...webPreferencesBase,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  if (savedBounds.isMaximized) {
    win.maximize();
  }

  attachNavigationGuards(win.webContents, {
    allowedOriginUrl: communityUrl,
    openExternal: (url) => shell.openExternal(url),
    loadUrl: (url) => {
      showingFallback = false;
      void win.loadURL(url);
    },
  });

  win.webContents.on(
    "did-fail-load",
    (_event, errorCode, errorDescription, _validatedUrl, isMainFrame) => {
      // -3 is ERR_ABORTED (normal when a load is superseded or redirected).
      if (!isMainFrame || errorCode === -3) {
        return;
      }
      showOfflineFallback(`${errorDescription} (${errorCode})`);
    },
  );

  win.once("ready-to-show", () => {
    win.show();
  });

  const persistBounds = (): void => {
    if (win.isDestroyed()) {
      return;
    }
    const isMaximized = win.isMaximized();
    const bounds = isMaximized ? win.getNormalBounds() : win.getBounds();
    saveWindowState(userDataDir, {
      width: bounds.width,
      height: bounds.height,
      x: bounds.x,
      y: bounds.y,
      isMaximized,
    });
  };

  win.on("close", persistBounds);
  win.on("closed", () => {
    mainWindow = null;
  });

  mainWindow = win;
  loadCommunity();
  return win;
}

if (process.env.COMMUNITY_DESKTOP_NO_BOOT !== "1") {
  app.setName(APP_TITLE);

  app.whenReady().then(() => {
    session.defaultSession.setPermissionRequestHandler(
      (_webContents, _permission, callback) => {
        callback(false);
      },
    );

    Menu.setApplicationMenu(buildAppMenu());

    ipcMain.on("community:retry", () => {
      loadCommunity();
    });

    createCommunityWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        createCommunityWindow();
      }
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
