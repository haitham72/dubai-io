import fs from "fs";
import path from "path";
import { app, BrowserWindow, ipcMain, Menu, safeStorage, shell, type MenuItemConstructorOptions } from "electron";
import {
  IPC,
  parseBrowser,
  parseHookToggle,
  parseSignIn,
  parseResume,
  parseSessionsScan,
  parseSyncConfigure,
} from "./ipcAllowlist";
import {
  buildResumeArgs,
  defaultRoots,
  collectBrowserRecords,
  collectSessionRecords,
  previewBrowser,
  resolveProfile,
  scanSessions,
} from "./localReader";
import { DesktopAuthManager } from "./auth";
import { runDesktopSync } from "./desktopSync";
import { OwnerHook, TokenStore } from "./ownerHook";
import { ContinuousSync, filesystemPacketReader, type SyncSource } from "./continuousSync";
import { createMainWindow, createSettingsWindow, type AppWindow } from "./window";
import { resolveAppUrl, resolveRendererIndex } from "./security";

const roots = defaultRoots();
const hookLog = { info: (line: string) => console.info(line) };
const hook = new OwnerHook(hookLog);
const tokens = new TokenStore(safeStorage, hookLog, path.join(app.getPath("userData"), "owner-credentials.bin"));
const auth = new DesktopAuthManager(tokens, hookLog);
const seenRecords = new Set<string>();
const apiBaseUrl = () => process.env.DUBAI_API_URL || "http://127.0.0.1:8000";
const sync = new ContinuousSync(filesystemPacketReader(roots));

export function registerIpc(): void {
  ipcMain.handle(IPC.sessionsScan, async (_event, payload: unknown) => {
    const body = parseSessionsScan(payload ?? {});
    return scanSessions(body.tool, body.since, roots);
  });

  ipcMain.handle(IPC.sessionsResume, async (_event, payload: unknown) => {
    const body = parseResume(payload);
    return buildResumeArgs(body.agentTool, body.sessionId, body.cwd);
  });

  ipcMain.handle(IPC.browserPreview, async (_event, payload: unknown) => {
    const body = parseBrowser(payload, "preview");
    const profile = resolveProfile(body.browser, body.profileName, roots);
    return previewBrowser(profile, roots.browsers[body.browser]);
  });

  ipcMain.handle(IPC.browserImport, async (_event, payload: unknown) => {
    const body = parseBrowser(payload, "import");
    if (body.browser === "brave") throw new Error("brave import is not supported by sync yet");
    const source = body.browser;
    const result = await runDesktopSync({
      tokens,
      apiBaseUrl: apiBaseUrl(),
      enabledSources: [source],
      collect: () => collectBrowserRecords(body.browser, body.profileName, roots),
      seen: seenRecords,
    });
    return result;
  });

  ipcMain.handle(IPC.hookStatus, async () => hook.status());

  ipcMain.handle(IPC.hookToggle, async (_event, payload: unknown) => {
    const body = parseHookToggle(payload);
    if (!body.enabled) return hook.stop();
    if (!body.model) throw new Error("model is required to start the owner hook");
    if (!tokens.authStatus().signedIn) throw new Error("Sign in required");
    return tokens.withToken((token) =>
      hook.start({
        model: body.model as string,
        token,
        url: body.url ?? "http://127.0.0.1:8000/mcp",
        owner: tokens.authStatus().userId as string,
      }),
    );
  });

  ipcMain.handle(IPC.tokenStatus, async () => tokens.status());

  ipcMain.handle(IPC.syncStatus, async () => sync.status());

  ipcMain.handle(IPC.syncConfigure, async (_event, payload: unknown) => {
    const body = parseSyncConfigure(payload);
    return sync.configure(body.enabledSources as SyncSource[], body.syncOnFocus);
  });

  ipcMain.handle(IPC.syncRun, async () => {
    const status = sync.status();
    const result = await runDesktopSync({
      tokens,
      apiBaseUrl: apiBaseUrl(),
      enabledSources: status.enabledSources,
      collect: (source) =>
        source === "chrome" || source === "edge"
          ? collectBrowserRecords(source, "Default", roots)
          : collectSessionRecords(source, roots),
      seen: seenRecords,
    });
    sync.lastSyncAt = new Date().toISOString();
    return { ...sync.status(), uploaded: result.uploaded, errors: result.errors, signedIn: result.signedIn };
  });

  ipcMain.handle(IPC.authStatus, async () => auth.status());
  ipcMain.handle(IPC.authSignIn, async (_event, payload: unknown) => {
    const body = parseSignIn(payload);
    return auth.signIn({ apiBaseUrl: body.apiBaseUrl ?? apiBaseUrl() });
  });
  ipcMain.handle(IPC.authSignOut, async () => auth.signOut({ apiBaseUrl: apiBaseUrl() }));
}

let mainWindow: AppWindow | null = null;
let settingsWindow: BrowserWindow | null = null;

function openSettings(): void {
  if (settingsWindow && !settingsWindow.isDestroyed()) {
    settingsWindow.show();
    settingsWindow.focus();
    return;
  }
  const index = resolveRendererIndex(process.env, __dirname, fs.existsSync, path.join);
  if (!index) {
    console.error("Settings renderer is not built: run `npm run build` in apps/desktop/renderer");
    return;
  }
  settingsWindow = createSettingsWindow(path.join(__dirname, "../preload/index.js"), index);
  settingsWindow.on("closed", () => {
    settingsWindow = null;
  });
}

function buildAppMenu(appUrl: string): Menu {
  const template: MenuItemConstructorOptions[] = [
    {
      label: "Dubai-io",
      submenu: [
        { label: "Settings and Sign in...", accelerator: "CmdOrCtrl+,", click: () => openSettings() },
        { label: "Reload", accelerator: "CmdOrCtrl+R", click: () => mainWindow?.reloadApp() },
        { label: "Open in Browser", click: () => void shell.openExternal(appUrl) },
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
      submenu: [{ role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" }, { type: "separator" }, { role: "togglefullscreen" }],
    },
  ];
  return Menu.buildFromTemplate(template);
}

export function boot(): void {
  tokens.loadFromDisk();
  registerIpc();
  const appUrl = resolveAppUrl();
  Menu.setApplicationMenu(buildAppMenu(appUrl));
  mainWindow = createMainWindow(appUrl);
  mainWindow.on("closed", () => {
    mainWindow = null;
  });
  if (process.env.DUBAI_DESKTOP_OPEN_SETTINGS === "1") openSettings();
}

app.on("window-all-closed", () => {
  if (process.env.DUBAI_DESKTOP_BOOT === "1" && process.platform !== "darwin") app.quit();
});

if (process.env.DUBAI_DESKTOP_BOOT === "1") {
  void app.whenReady().then(boot);
}
