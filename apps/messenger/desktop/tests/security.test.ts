import { describe, expect, it } from "vitest";
import {
  DEFAULT_MESSENGER_URL,
  ORIGIN_SCOPED_PERMISSIONS,
  getAllowedOrigin,
  isAllowedNavigation,
  isOriginPermissionAllowed,
  resolveMessengerUrl,
  sanitizeNotificationPayload,
  shouldOpenExternally,
  webPreferencesBase,
} from "../electron/security";

describe("desktop webPreferences invariants", () => {
  it("enforces hardened Electron sandbox & isolation defaults", () => {
    expect(webPreferencesBase.contextIsolation).toBe(true);
    expect(webPreferencesBase.nodeIntegration).toBe(false);
    expect(webPreferencesBase.sandbox).toBe(true);
    expect(webPreferencesBase.webSecurity).toBe(true);
    expect(webPreferencesBase.allowRunningInsecureContent).toBe(false);
    expect(webPreferencesBase.webviewTag).toBe(false);
  });
});

describe("desktop URL, navigation allowlist & external links", () => {
  it("resolves default and custom MESSENGER_URL values cleanly", () => {
    expect(resolveMessengerUrl({})).toBe(DEFAULT_MESSENGER_URL);
    expect(resolveMessengerUrl({ MESSENGER_URL: "http://192.168.1.50:5173/" })).toBe(
      "http://192.168.1.50:5173",
    );
    expect(resolveMessengerUrl({ VITE_MESSENGER_URL: "https://chat.example.com/" })).toBe(
      "https://chat.example.com",
    );
    expect(() => resolveMessengerUrl({ MESSENGER_URL: "file:///C:/Windows" })).toThrow();
  });

  it("allows same-origin navigation and blocks/externalizes off-origin links", () => {
    const origin = getAllowedOrigin("http://localhost:5173");
    expect(origin).toBe("http://localhost:5173");

    expect(isAllowedNavigation("http://localhost:5173/", origin)).toBe(true);
    expect(isAllowedNavigation("http://localhost:5173/chats?demo=1", origin)).toBe(true);
    expect(isAllowedNavigation("http://127.0.0.1:5173/", origin)).toBe(false);
    expect(isAllowedNavigation("https://example.com/", origin)).toBe(false);
    expect(isAllowedNavigation("javascript:alert(1)", origin)).toBe(false);

    expect(shouldOpenExternally("https://example.com/help", origin)).toBe(true);
    expect(shouldOpenExternally("mailto:support@example.com", origin)).toBe(true);
    expect(shouldOpenExternally("http://localhost:5173/chats", origin)).toBe(false);
    expect(shouldOpenExternally("javascript:alert(1)", origin)).toBe(false);
    expect(shouldOpenExternally("file:///etc/passwd", origin)).toBe(false);
  });
});

describe("desktop origin-gated Notification & media permissions", () => {
  const allowed = "http://localhost:5173";

  it("allows notifications and media ONLY for the configured Messenger origin", () => {
    expect(ORIGIN_SCOPED_PERMISSIONS.has("notifications")).toBe(true);
    expect(ORIGIN_SCOPED_PERMISSIONS.has("media")).toBe(true);

    expect(isOriginPermissionAllowed("notifications", "http://localhost:5173/chats", allowed)).toBe(true);
    expect(isOriginPermissionAllowed("media", "http://localhost:5173/", allowed)).toBe(true);
  });

  it("denies notifications/media for any other origin and denies non-allowlisted permissions", () => {
    expect(isOriginPermissionAllowed("notifications", "https://evil.example.com", allowed)).toBe(false);
    expect(isOriginPermissionAllowed("media", "http://127.0.0.1:5173", allowed)).toBe(false);
    expect(isOriginPermissionAllowed("notifications", "", allowed)).toBe(false);
    expect(isOriginPermissionAllowed("notifications", "not-a-url", allowed)).toBe(false);
    expect(isOriginPermissionAllowed("geolocation", "http://localhost:5173", allowed)).toBe(false);
    expect(isOriginPermissionAllowed("openExternal", "http://localhost:5173", allowed)).toBe(false);
  });

  it("sanitizes IPC notification payloads cleanly", () => {
    expect(sanitizeNotificationPayload({ title: "New message", body: "Hello!" })).toEqual({
      title: "New message",
      body: "Hello!",
    });
    expect(sanitizeNotificationPayload({ title: "", body: "" })).toBeNull();
    expect(sanitizeNotificationPayload(null)).toBeNull();
    expect(sanitizeNotificationPayload(["bad"])).toBeNull();
  });
});
