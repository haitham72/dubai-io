import { BrowserWindow } from "electron";
import { webPreferencesBase } from "./security";

export function createMainWindow(preloadPath: string): BrowserWindow {
  return new BrowserWindow({
    width: 1280,
    height: 840,
    show: false,
    backgroundColor: "#FFFFFF",
    webPreferences: {
      ...webPreferencesBase,
      preload: preloadPath,
    },
  });
}
