import { contextBridge, ipcRenderer } from "electron";
// A sandboxed preload cannot `require` local modules, so the channel names are inlined here.
// tests/main/preload.test.ts asserts this table equals IPC in ../main/ipcAllowlist.
const IPC = {
  sessionsScan: "sessions:scan",
  sessionsResume: "sessions:resumeCommand",
  browserPreview: "browser:preview",
  browserImport: "browser:import",
  hookStatus: "hook:status",
  hookToggle: "hook:toggle",
  tokenStatus: "token:status",
  syncStatus: "sync:status",
  syncConfigure: "sync:configure",
  syncRun: "sync:run",
  authStatus: "auth:status",
  authSignIn: "auth:signIn",
  authSignOut: "auth:signOut",
} as const;

const dubaiDesktop = {
  scanSessions: (payload: unknown) => ipcRenderer.invoke(IPC.sessionsScan, payload),
  resumeCommand: (payload: unknown) => ipcRenderer.invoke(IPC.sessionsResume, payload),
  previewBrowser: (payload: unknown) => ipcRenderer.invoke(IPC.browserPreview, payload),
  importBrowser: (payload: unknown) => ipcRenderer.invoke(IPC.browserImport, payload),
  hookStatus: () => ipcRenderer.invoke(IPC.hookStatus),
  hookToggle: (payload: unknown) => ipcRenderer.invoke(IPC.hookToggle, payload),
  tokenStatus: () => ipcRenderer.invoke(IPC.tokenStatus),
  syncStatus: () => ipcRenderer.invoke(IPC.syncStatus),
  syncConfigure: (payload: unknown) => ipcRenderer.invoke(IPC.syncConfigure, payload),
  syncRun: () => ipcRenderer.invoke(IPC.syncRun),
  authStatus: () => ipcRenderer.invoke(IPC.authStatus),
  authSignIn: (payload?: unknown) => ipcRenderer.invoke(IPC.authSignIn, payload),
  authSignOut: () => ipcRenderer.invoke(IPC.authSignOut),
};

contextBridge.exposeInMainWorld("dubaiDesktop", dubaiDesktop);

export type DubaiDesktopBridge = typeof dubaiDesktop;
