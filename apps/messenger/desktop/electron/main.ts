import fs from "node:fs";
import path from "node:path";
import { app, BrowserWindow, ipcMain, Notification, session, shell } from "electron";
import {
  getAllowedOrigin,
  isAllowedNavigation,
  isOriginPermissionAllowed,
  resolveMessengerUrl,
  sanitizeNotificationPayload,
  shouldOpenExternally,
  webPreferencesBase,
} from "./security";

interface WindowState {
  width: number;
  height: number;
  x?: number;
  y?: number;
  isMaximized?: boolean;
}

const DEFAULT_WINDOW_STATE: WindowState = { width: 1280, height: 840 };
const APP_USER_MODEL_ID = "app.messenger.desktop";

let mainWindow: BrowserWindow | null = null;
let targetUrl = resolveMessengerUrl();
let allowedOrigin = getAllowedOrigin(targetUrl);

function getWindowStatePath(): string {
  return path.join(app.getPath("userData"), "window-state.json");
}

function loadWindowState(): WindowState {
  try {
    const raw = fs.readFileSync(getWindowStatePath(), "utf8");
    const parsed = JSON.parse(raw) as Partial<WindowState>;
    const width = typeof parsed.width === "number" && parsed.width >= 480 ? parsed.width : DEFAULT_WINDOW_STATE.width;
    const height = typeof parsed.height === "number" && parsed.height >= 480 ? parsed.height : DEFAULT_WINDOW_STATE.height;
    return {
      width,
      height,
      x: typeof parsed.x === "number" ? parsed.x : undefined,
      y: typeof parsed.y === "number" ? parsed.y : undefined,
      isMaximized: Boolean(parsed.isMaximized),
    };
  } catch {
    return { ...DEFAULT_WINDOW_STATE };
  }
}

function saveWindowState(win: BrowserWindow): void {
  try {
    const bounds = win.getNormalBounds();
    const state: WindowState = {
      width: bounds.width,
      height: bounds.height,
      x: bounds.x,
      y: bounds.y,
      isMaximized: win.isMaximized(),
    };
    fs.mkdirSync(app.getPath("userData"), { recursive: true });
    fs.writeFileSync(getWindowStatePath(), JSON.stringify(state), "utf8");
  } catch {
    // Non-fatal if userData is read-only.
  }
}

function configureOriginPermissions(origin: string): void {
  const defaultSession = session.defaultSession;
  defaultSession.setPermissionCheckHandler((_webContents, permission, requestingOrigin) =>
    isOriginPermissionAllowed(permission, requestingOrigin, origin),
  );
  defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const requester = details.requestingUrl || webContents.getURL();
    callback(isOriginPermissionAllowed(permission, requester, origin));
  });
}

function registerIpc(): void {
  ipcMain.handle("messenger:retry", async () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      await mainWindow.loadURL(targetUrl);
    }
  });

  ipcMain.handle("messenger:notify", (_event, payload: unknown) => {
    const sanitized = sanitizeNotificationPayload(payload);
    if (!sanitized || !Notification.isSupported()) {
      return false;
    }
    const toast = new Notification({
      title: sanitized.title,
      body: sanitized.body,
      icon: path.join(__dirname, "../../assets/icon.png"),
    });
    toast.on("click", () => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
      }
    });
    toast.show();
    return true;
  });
}

function createWindow(): BrowserWindow {
  const saved = loadWindowState();
  const win = new BrowserWindow({
    width: saved.width,
    height: saved.height,
    x: saved.x,
    y: saved.y,
    minWidth: 420,
    minHeight: 540,
    show: false,
    title: "Messenger",
    backgroundColor: "#eef3fa",
    icon: path.join(__dirname, "../../assets/icon.png"),
    webPreferences: {
      ...webPreferencesBase,
      preload: path.join(__dirname, "preload.js"),
    },
  });

  if (saved.isMaximized) {
    win.maximize();
  }

  win.once("ready-to-show", () => {
    win.show();
  });

  win.on("close", () => saveWindowState(win));

  win.webContents.setWindowOpenHandler(({ url }) => {
    if (shouldOpenExternally(url, allowedOrigin)) {
      void shell.openExternal(url);
    }
    return { action: "deny" };
  });

  win.webContents.on("will-navigate", (event, url) => {
    if (isAllowedNavigation(url, allowedOrigin)) {
      return;
    }
    event.preventDefault();
    if (shouldOpenExternally(url, allowedOrigin)) {
      void shell.openExternal(url);
    }
  });

  win.webContents.on("did-fail-load", (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (!isMainFrame || errorCode === -3) return;
    if (validatedURL.startsWith("file://")) return;
    const offlinePath = path.join(__dirname, "../../electron/offline.html");
    void win.loadFile(offlinePath, {
      query: {
        target: targetUrl,
        reason: errorDescription || `Connection failed (${errorCode})`,
      },
    });
  });

  void win.loadURL(targetUrl);
  return win;
}

const gotSingleInstanceLock = app.requestSingleInstanceLock();
if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  void app.whenReady().then(() => {
    app.setAppUserModelId(APP_USER_MODEL_ID);
    targetUrl = resolveMessengerUrl();
    allowedOrigin = getAllowedOrigin(targetUrl);
    configureOriginPermissions(allowedOrigin);
    registerIpc();
    mainWindow = createWindow();

    app.on("activate", () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        mainWindow = createWindow();
      }
    });
  });

  app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
      app.quit();
    }
  });
}
