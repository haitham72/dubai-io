import { BrowserWindow, shell } from "electron";
import { attachNavigationGuards, buildFallbackHtml, webPreferencesBase } from "./security";

export type AppWindow = BrowserWindow & { reloadApp: () => void };

/**
 * Main window: the Dubai-io app (the Expo web build). It is remote web content, so it gets no bridge script and
 * therefore no `window.dubaiDesktop` bridge. Settings and sign-in live in their own window (createSettingsWindow).
 */
export function createMainWindow(appUrl: string): AppWindow {
  const win = new BrowserWindow({
    width: 1280,
    height: 840,
    show: false,
    title: "Dubai-io",
    backgroundColor: "#FFFFFF",
    webPreferences: { ...webPreferencesBase },
  }) as AppWindow;
  let showingFallback = false;
  win.reloadApp = () => {
    showingFallback = false;
    void win.loadURL(appUrl);
  };
  attachNavigationGuards(win.webContents, {
    allowedOriginUrl: appUrl,
    openExternal: (url) => shell.openExternal(url),
    loadUrl: (url) => void win.loadURL(url),
  });
  win.webContents.on("did-fail-load", (_event, errorCode, errorDescription, _url, isMainFrame) => {
    if (!isMainFrame || errorCode === -3 || showingFallback) return; // -3 = ERR_ABORTED
    showingFallback = true;
    const html = buildFallbackHtml(appUrl, `${errorDescription} (${errorCode})`);
    void win.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`);
  });
  win.once("ready-to-show", () => win.show());
  win.reloadApp();
  return win;
}

/** Settings window: the local renderer (file://) with the allowlisted preload bridge. Navigation is denied. */
export function createSettingsWindow(preloadPath: string, rendererIndex: string): BrowserWindow {
  const win = new BrowserWindow({
    width: 1100,
    height: 800,
    show: false,
    title: "Dubai-io Settings",
    backgroundColor: "#FFFFFF",
    webPreferences: { ...webPreferencesBase, preload: preloadPath },
  });
  // No origin is allowed to navigate to: links open in the OS browser, everything else is blocked.
  attachNavigationGuards(win.webContents, {
    allowedOriginUrl: "about:blank",
    openExternal: (url) => shell.openExternal(url),
  });
  win.once("ready-to-show", () => win.show());
  void win.loadFile(rendererIndex);
  return win;
}
