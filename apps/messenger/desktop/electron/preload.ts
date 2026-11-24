import { contextBridge, ipcRenderer } from "electron";

/** Minimal, allowlisted preload bridge exposed to the sandboxed Messenger renderer. */
contextBridge.exposeInMainWorld("messengerDesktop", {
  platform: process.platform,
  retry: (): Promise<void> => ipcRenderer.invoke("messenger:retry"),
  notify: (title: string, body: string): Promise<boolean> =>
    ipcRenderer.invoke("messenger:notify", { title, body }),
});
