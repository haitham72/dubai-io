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
};

contextBridge.exposeInMainWorld("dubaiDesktop", dubaiDesktop);

export type DubaiDesktopBridge = typeof dubaiDesktop;
