import { contextBridge, ipcRenderer } from "electron";
import { IPC } from "../main/ipcAllowlist";

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
};

contextBridge.exposeInMainWorld("dubaiDesktop", dubaiDesktop);

export type DubaiDesktopBridge = typeof dubaiDesktop;
