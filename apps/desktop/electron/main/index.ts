import path from "path";
import { app, ipcMain, safeStorage } from "electron";
import {
  IPC,
  parseBrowser,
  parseHookToggle,
  parseResume,
  parseSessionsScan,
} from "./ipcAllowlist";
import {
  buildResumeArgs,
  defaultRoots,
  importBrowser,
  previewBrowser,
  resolveProfile,
  scanSessions,
} from "./localReader";
import { OwnerHook, TokenStore } from "./ownerHook";
import { createMainWindow } from "./window";

const roots = defaultRoots();
const hookLog = { info: (line: string) => console.info(line) };
const hook = new OwnerHook(hookLog);
const tokens = new TokenStore(safeStorage, hookLog);

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
    const profile = resolveProfile(body.browser, body.profileName, roots);
    return importBrowser(profile, roots.browsers[body.browser], "karim");
  });

  ipcMain.handle(IPC.hookStatus, async () => hook.status());

  ipcMain.handle(IPC.hookToggle, async (_event, payload: unknown) => {
    const body = parseHookToggle(payload);
    if (!body.enabled) return hook.stop();
    if (!body.model) throw new Error("model is required to start the owner hook");
    return tokens.withToken((token) =>
      hook.start({
        model: body.model as string,
        token,
        url: body.url ?? "http://127.0.0.1:8000/mcp",
        owner: body.owner ?? "karim",
      }),
    );
  });

  ipcMain.handle(IPC.tokenStatus, async () => tokens.status());
}

export function boot(): void {
  registerIpc();
  createMainWindow(path.join(__dirname, "../preload/index.js"));
}

if (process.env.DUBAI_DESKTOP_BOOT === "1") {
  void app.whenReady().then(boot);
}
