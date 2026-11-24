import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("communityDesktop", {
  retry: (): void => {
    ipcRenderer.send("community:retry");
  },
});
