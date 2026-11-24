import fs from "node:fs";
import path from "node:path";
import { describe, expect, it, vi } from "vitest";
import { IPC } from "../../electron/main/ipcAllowlist";
import {
  DEFAULT_APP_URL,
  attachNavigationGuards,
  buildFallbackHtml,
  classifyDesktopNavigation,
  resolveAppUrl,
  resolveRendererIndex,
  webPreferencesBase,
  type GuardedWebContents,
} from "../../electron/main/security";

describe("resolveAppUrl", () => {
  it("defaults to the Expo web URL and honours DUBAI_APP_URL", () => {
    expect(DEFAULT_APP_URL).toBe("http://localhost:8081");
    expect(resolveAppUrl({})).toBe("http://localhost:8081");
    expect(resolveAppUrl({ DUBAI_APP_URL: "http://192.168.1.5:8081/" })).toBe("http://192.168.1.5:8081");
  });
  it("rejects non-http(s) and malformed values", () => {
    for (const bad of ["file:///C:/x", "javascript:alert(1)", "not a url", "  "]) {
      expect(resolveAppUrl({ DUBAI_APP_URL: bad })).toBe(DEFAULT_APP_URL);
    }
  });
});

describe("window hardening and navigation classification", () => {
  it("keeps the hardened webPreferences", () => {
    expect(webPreferencesBase).toMatchObject({
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      webviewTag: false,
    });
  });
  it("classifies same origin, external and blocked targets", () => {
    const base = "http://localhost:8081";
    expect(classifyDesktopNavigation("http://localhost:8081/connect", base)).toBe("allow");
    expect(classifyDesktopNavigation("http://localhost:8082/", base)).toBe("external");
    expect(classifyDesktopNavigation("https://evil.example/", base)).toBe("external");
    expect(classifyDesktopNavigation("file:///C:/secret.txt", base)).toBe("block");
    expect(classifyDesktopNavigation("javascript:alert(1)", base)).toBe("block");
  });
});

function mockContents() {
  let onNavigate: ((e: { preventDefault: () => void }, url: string) => void) | undefined;
  let onWebview: ((e: { preventDefault: () => void }) => void) | undefined;
  let openHandler: ((d: { url: string }) => { action: "allow" | "deny" }) | undefined;
  const contents: GuardedWebContents = {
    on(event: string, listener: (...a: never[]) => void) {
      if (event === "will-navigate") onNavigate = listener as typeof onNavigate;
      else if (event === "will-attach-webview") onWebview = listener as typeof onWebview;
      return contents;
    },
    setWindowOpenHandler(h) {
      openHandler = h;
    },
  };
  return {
    contents,
    navigate(url: string) {
      const preventDefault = vi.fn();
      onNavigate?.({ preventDefault }, url);
      return preventDefault;
    },
    open: (url: string) => openHandler?.({ url }),
    webview() {
      const preventDefault = vi.fn();
      onWebview?.({ preventDefault });
      return preventDefault;
    },
  };
}

describe("attachNavigationGuards (same pattern as the Community and Messenger shells)", () => {
  it("allows app-origin navigation, sends safe off-origin links to the OS, blocks the rest, denies window.open", () => {
    const m = mockContents();
    const openExternal = vi.fn();
    const loadUrl = vi.fn();
    const onBlocked = vi.fn();
    attachNavigationGuards(m.contents, { allowedOriginUrl: "http://localhost:8081", openExternal, loadUrl, onBlocked });

    expect(m.navigate("http://localhost:8081/memory")).not.toHaveBeenCalled();

    expect(m.navigate("https://example.org/x")).toHaveBeenCalledTimes(1);
    expect(openExternal).toHaveBeenCalledWith("https://example.org/x");

    expect(m.navigate("file:///C:/Windows/win.ini")).toHaveBeenCalledTimes(1);
    expect(onBlocked).toHaveBeenCalledWith("file:///C:/Windows/win.ini");
    expect(openExternal).toHaveBeenCalledTimes(1);

    expect(m.open("https://docs.example.com")).toEqual({ action: "deny" });
    expect(openExternal).toHaveBeenCalledWith("https://docs.example.com");
    expect(m.open("javascript:alert(1)")).toEqual({ action: "deny" });
    expect(m.open("http://localhost:8081/chat")).toEqual({ action: "deny" });
    expect(loadUrl).toHaveBeenCalledWith("http://localhost:8081/chat");

    expect(m.webview()).toHaveBeenCalledTimes(1);
  });

  it("the Settings window (about:blank origin) opens every link outside and blocks file:", () => {
    const m = mockContents();
    const openExternal = vi.fn();
    attachNavigationGuards(m.contents, { allowedOriginUrl: "about:blank", openExternal });
    expect(m.navigate("http://localhost:8081/")).toHaveBeenCalledTimes(1);
    expect(openExternal).toHaveBeenCalledWith("http://localhost:8081/");
    expect(m.navigate("file:///C:/x")).toHaveBeenCalledTimes(1);
    expect(m.open("https://a.example")).toEqual({ action: "deny" });
  });
});

describe("fallback page and renderer lookup", () => {
  it("escapes the reason and URL, so an unreachable app is explained, never blank", () => {
    const html = buildFallbackHtml("http://localhost:8081", "<script>alert(1)</script>");
    expect(html).toContain("Dubai-io is not running");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).not.toContain("<script>alert(1)</script>");
  });
  it("finds the built renderer: env first, then relative to the compiled main", () => {
    const join = path.join;
    const hit = join("D:", "dist", "index.html");
    expect(resolveRendererIndex({ DUBAI_DESKTOP_RENDERER_DIST: join("D:", "dist") }, "X", (p) => p === hit, join)).toBe(hit);
    expect(resolveRendererIndex({}, "X", () => false, join)).toBeNull();
    const rel = join("M", "..", "..", "renderer", "dist", "index.html");
    expect(resolveRendererIndex({}, "M", (p) => p === rel, join)).toBe(rel);
  });
});

describe("window and boot wiring (source checks)", () => {
  const read = (rel: string) => fs.readFileSync(path.join(__dirname, "..", "..", rel), "utf8");
  it("the main window loads the app URL, has no preload, and has the guards", () => {
    const win = read("electron/main/window.ts");
    expect(win).toMatch(/loadURL\(appUrl\)/);
    expect(win).toMatch(/attachNavigationGuards\(win\.webContents/);
    const mainBlock = win.slice(win.indexOf("export function createMainWindow"), win.indexOf("/** Settings window"));
    expect(mainBlock).not.toMatch(/preload/);
    const settings = win.slice(win.indexOf("/** Settings window"));
    expect(settings).toMatch(/preload: preloadPath/);
    expect(settings).toMatch(/attachNavigationGuards/);
  });
  it("boot builds a menu with Settings and Sign in, and the preload table equals the IPC allowlist", () => {
    expect(read("electron/main/index.ts")).toMatch(/Settings and Sign in/);
    const preload = read("electron/preload/index.ts");
    expect(preload).not.toMatch(/from "\.\.\/main/);
    const table = Object.fromEntries([...preload.matchAll(/^\s+(\w+): "([^"]+)",$/gm)].map((m) => [m[1], m[2]]));
    expect(table).toEqual(IPC);
  });
});
