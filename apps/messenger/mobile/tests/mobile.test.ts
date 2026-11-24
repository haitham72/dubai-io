import { describe, expect, it } from "vitest";
import {
  DEFAULT_MESSENGER_URL,
  deriveMessengerOrigin,
  deriveWsUrl,
  getConfiguredMessengerUrl,
  isAllowedMessengerNavigation,
  normalizeMessengerUrl,
  shouldOpenExternally,
} from "../src/config";
import {
  buildWebViewBridgeScript,
  parseBridgeRequest,
  serializeBridgeEventToJs,
} from "../src/bridge";

describe("mobile URL & WS derivation", () => {
  it("falls back to default localhost URL when env and override are unset", () => {
    expect(getConfiguredMessengerUrl({})).toBe(DEFAULT_MESSENGER_URL);
    expect(deriveMessengerOrigin(DEFAULT_MESSENGER_URL)).toBe("http://localhost:5173");
    expect(deriveWsUrl(DEFAULT_MESSENGER_URL)).toBe("ws://localhost:5173/api/messenger/ws");
  });

  it("derives LAN origin and ws:// URL from EXPO_PUBLIC_MESSENGER_URL", () => {
    const url = getConfiguredMessengerUrl({
      EXPO_PUBLIC_MESSENGER_URL: "http://192.168.1.42:5173/",
    });
    expect(url).toBe("http://192.168.1.42:5173");
    expect(deriveMessengerOrigin(url)).toBe("http://192.168.1.42:5173");
    expect(deriveWsUrl(url)).toBe("ws://192.168.1.42:5173/api/messenger/ws");
  });

  it("derives wss:// URL for HTTPS tunnel hosts and rejects non-HTTP schemes", () => {
    const tunnel = normalizeMessengerUrl("https://demo-chat.trycloudflare.com/");
    expect(tunnel).toBe("https://demo-chat.trycloudflare.com");
    expect(deriveWsUrl(tunnel)).toBe("wss://demo-chat.trycloudflare.com/api/messenger/ws");
    expect(() => normalizeMessengerUrl("javascript:alert(1)")).toThrow();
    expect(() => normalizeMessengerUrl("file:///etc/passwd")).toThrow();
  });
});

describe("mobile WebView origin allowlist", () => {
  const origin = "http://192.168.1.42:5173";

  it("allows same-origin paths and about:blank inside WebView", () => {
    expect(isAllowedMessengerNavigation("http://192.168.1.42:5173/chats", origin)).toBe(true);
    expect(isAllowedMessengerNavigation("about:blank", origin)).toBe(true);
  });

  it("blocks off-origin navigations and delegates external links", () => {
    expect(isAllowedMessengerNavigation("https://example.com", origin)).toBe(false);
    expect(isAllowedMessengerNavigation("http://192.168.1.42:8070", origin)).toBe(false);
    expect(isAllowedMessengerNavigation("javascript:alert(1)", origin)).toBe(false);

    expect(shouldOpenExternally("https://example.com/docs", origin)).toBe(true);
    expect(shouldOpenExternally("mailto:team@example.com", origin)).toBe(true);
    expect(shouldOpenExternally("javascript:alert(1)", origin)).toBe(false);
    expect(shouldOpenExternally("http://192.168.1.42:5173/chats", origin)).toBe(false);
  });
});

describe("mobile WebView JS bridge validation & serialization", () => {
  it("parses valid mic, voice recording, media, and sticker bridge requests", () => {
    expect(parseBridgeRequest(JSON.stringify({ type: "REQUEST_MIC", requestId: "r1" }))).toEqual({
      type: "REQUEST_MIC",
      requestId: "r1",
    });
    expect(
      parseBridgeRequest(
        JSON.stringify({
          type: "PICK_MEDIA",
          requestId: "r2",
          allowsEditing: true,
          mediaTypes: "images",
        }),
      ),
    ).toEqual({
      type: "PICK_MEDIA",
      requestId: "r2",
      allowsEditing: true,
      mediaTypes: "images",
    });
    expect(parseBridgeRequest(JSON.stringify({ type: "PICK_STICKER", requestId: "r3" }))).toEqual({
      type: "PICK_STICKER",
      requestId: "r3",
    });
    expect(parseBridgeRequest(JSON.stringify({ type: "START_VOICE_RECORDING" }))).toEqual({
      type: "START_VOICE_RECORDING",
    });
    expect(parseBridgeRequest(JSON.stringify({ type: "STOP_VOICE_RECORDING" }))).toEqual({
      type: "STOP_VOICE_RECORDING",
    });
  });

  it("rejects malformed, oversized, or unknown bridge payloads", () => {
    expect(parseBridgeRequest("")).toBeNull();
    expect(parseBridgeRequest("not json")).toBeNull();
    expect(parseBridgeRequest("[]")).toBeNull();
    expect(parseBridgeRequest(JSON.stringify({ type: "EXEC_SHELL" }))).toBeNull();
    expect(parseBridgeRequest("x".repeat(20 * 1024))).toBeNull();
    expect(
      parseBridgeRequest(
        JSON.stringify({ type: "PICK_MEDIA", mediaTypes: "invalid", allowsEditing: "yes" }),
      ),
    ).toEqual({ type: "PICK_MEDIA" });
  });

  it("serializes bridge events safely for injectJavaScript and provides the global helper", () => {
    const js = serializeBridgeEventToJs({
      type: "MIC_PERMISSION_RESULT",
      requestId: "r1",
      granted: true,
      status: "granted",
    });
    expect(js).toContain("messenger:native");
    expect(js.endsWith("true;")).toBe(true);

    const xssSafe = serializeBridgeEventToJs({
      type: "MEDIA_PICKED",
      mode: "sticker",
      canceled: false,
      assets: [{ uri: "file:///tmp/a.png", fileName: "</script><script>alert(1)" }],
    });
    expect(xssSafe).not.toContain("</script>");
    expect(xssSafe).toContain("\\u003c/script\\u003e");

    const initScript = buildWebViewBridgeScript();
    expect(initScript).toContain("__messengerMobileBridge");
    expect(initScript).toContain("pickSticker");
    expect(initScript).toContain("requestMic");
  });
});
