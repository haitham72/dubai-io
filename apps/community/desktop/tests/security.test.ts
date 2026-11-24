import { describe, expect, it, vi } from "vitest";
import {
  DEFAULT_COMMUNITY_URL,
  attachNavigationGuards,
  buildFallbackHtml,
  classifyDesktopNavigation,
  isAllowedNavigationOrigin,
  isSafeExternalUrl,
  resolveCommunityUrl,
  webPreferencesBase,
  type GuardedWebContents,
} from "../electron/security";

describe("webPreferencesBase", () => {
  it("enforces hardened Electron defaults", () => {
    expect(webPreferencesBase.contextIsolation).toBe(true);
    expect(webPreferencesBase.nodeIntegration).toBe(false);
    expect(webPreferencesBase.sandbox).toBe(true);
    expect(webPreferencesBase.webSecurity).toBe(true);
    expect(webPreferencesBase.allowRunningInsecureContent).toBe(false);
    expect(webPreferencesBase.webviewTag).toBe(false);
  });
});

describe("resolveCommunityUrl", () => {
  it("defaults to http://localhost:3060 when COMMUNITY_URL is unset", () => {
    expect(resolveCommunityUrl({})).toBe(DEFAULT_COMMUNITY_URL);
    expect(resolveCommunityUrl({ COMMUNITY_URL: "   " })).toBe(
      DEFAULT_COMMUNITY_URL,
    );
  });

  it("accepts valid http and https COMMUNITY_URL values", () => {
    expect(
      resolveCommunityUrl({ COMMUNITY_URL: "http://192.168.1.42:3060/" }),
    ).toBe("http://192.168.1.42:3060");
    expect(
      resolveCommunityUrl({ COMMUNITY_URL: "https://community.dubai.io" }),
    ).toBe("https://community.dubai.io");
  });

  it("rejects non-http(s) schemes and malformed URLs", () => {
    expect(
      resolveCommunityUrl({ COMMUNITY_URL: "file:///C:/Windows/System32" }),
    ).toBe(DEFAULT_COMMUNITY_URL);
    expect(resolveCommunityUrl({ COMMUNITY_URL: "javascript:alert(1)" })).toBe(
      DEFAULT_COMMUNITY_URL,
    );
    expect(resolveCommunityUrl({ COMMUNITY_URL: "not a url" })).toBe(
      DEFAULT_COMMUNITY_URL,
    );
  });
});

describe("origin allowlist and navigation classification", () => {
  const base = "http://localhost:3060";

  it("allows only exact origin matches for in-app navigation", () => {
    expect(isAllowedNavigationOrigin("http://localhost:3060/inbox", base)).toBe(
      true,
    );
    expect(isAllowedNavigationOrigin("http://localhost:3060/", base)).toBe(
      true,
    );
    expect(isAllowedNavigationOrigin("http://localhost:3061/", base)).toBe(
      false,
    );
    expect(isAllowedNavigationOrigin("http://127.0.0.1:3060/", base)).toBe(
      false,
    );
    expect(isAllowedNavigationOrigin("https://localhost:3060/", base)).toBe(
      false,
    );
    expect(isAllowedNavigationOrigin("https://evil.example.com/", base)).toBe(
      false,
    );
  });

  it("rejects unsafe schemes from external open", () => {
    expect(isSafeExternalUrl("https://example.com")).toBe(true);
    expect(isSafeExternalUrl("http://example.com")).toBe(true);
    expect(isSafeExternalUrl("mailto:support@dubai.io")).toBe(true);
    expect(isSafeExternalUrl("javascript:alert(1)")).toBe(false);
    expect(isSafeExternalUrl("file:///etc/passwd")).toBe(false);
    expect(isSafeExternalUrl("data:text/html,<script>1</script>")).toBe(false);
  });

  it("classifies same-origin, external, and blocked URLs cleanly", () => {
    expect(classifyDesktopNavigation("http://localhost:3060/create", base)).toBe(
      "allow",
    );
    expect(classifyDesktopNavigation("https://dubai.ae/guide", base)).toBe(
      "external",
    );
    expect(classifyDesktopNavigation("file:///C:/secret.txt", base)).toBe(
      "block",
    );
    expect(classifyDesktopNavigation("javascript:alert(1)", base)).toBe(
      "block",
    );
  });
});

describe("attachNavigationGuards", () => {
  function createMockWebContents() {
    let onNavigate:
      | ((event: { preventDefault: () => void }, url: string) => void)
      | undefined;
    let onAttachWebview:
      | ((event: { preventDefault: () => void }) => void)
      | undefined;
    let openHandler:
      | ((details: { url: string }) => { action: "allow" | "deny" })
      | undefined;

    const contents: GuardedWebContents = {
      on(event: string, listener: (...args: never[]) => void) {
        if (event === "will-navigate") {
          onNavigate = listener as typeof onNavigate;
        } else if (event === "will-attach-webview") {
          onAttachWebview = listener as typeof onAttachWebview;
        }
        return contents;
      },
      setWindowOpenHandler(handler) {
        openHandler = handler;
      },
    };

    return {
      contents,
      triggerNavigate(url: string) {
        const preventDefault = vi.fn();
        onNavigate?.({ preventDefault }, url);
        return preventDefault;
      },
      triggerWindowOpen(url: string) {
        return openHandler?.({ url });
      },
      triggerAttachWebview() {
        const preventDefault = vi.fn();
        onAttachWebview?.({ preventDefault });
        return preventDefault;
      },
    };
  }

  it("allows same-origin navigation and blocks + opens external links via openExternal", () => {
    const mock = createMockWebContents();
    const openExternal = vi.fn();
    const loadUrl = vi.fn();
    const onBlocked = vi.fn();

    attachNavigationGuards(mock.contents, {
      allowedOriginUrl: "http://localhost:3060",
      openExternal,
      loadUrl,
      onBlocked,
    });

    const sameOriginPrevent = mock.triggerNavigate(
      "http://localhost:3060/communities",
    );
    expect(sameOriginPrevent).not.toHaveBeenCalled();

    const extPrevent = mock.triggerNavigate("https://example.org/post");
    expect(extPrevent).toHaveBeenCalledTimes(1);
    expect(openExternal).toHaveBeenCalledWith("https://example.org/post");

    const unsafePrevent = mock.triggerNavigate("file:///C:/Windows/win.ini");
    expect(unsafePrevent).toHaveBeenCalledTimes(1);
    expect(onBlocked).toHaveBeenCalledWith("file:///C:/Windows/win.ini");
    expect(openExternal).toHaveBeenCalledTimes(1);

    const popupExt = mock.triggerWindowOpen("https://docs.example.com");
    expect(popupExt).toEqual({ action: "deny" });
    expect(openExternal).toHaveBeenCalledWith("https://docs.example.com");

    const popupSame = mock.triggerWindowOpen("http://localhost:3060/inbox");
    expect(popupSame).toEqual({ action: "deny" });
    expect(loadUrl).toHaveBeenCalledWith("http://localhost:3060/inbox");

    const webviewPrevent = mock.triggerAttachWebview();
    expect(webviewPrevent).toHaveBeenCalledTimes(1);
  });
});

describe("buildFallbackHtml", () => {
  it("escapes target URL and error reason and includes Retry button", () => {
    const html = buildFallbackHtml(
      "http://localhost:3060",
      "<script>alert(1)</script>",
    );
    expect(html).toContain("Dubai-io Community");
    expect(html).toContain("Retry connection");
    expect(html).toContain("&lt;script&gt;alert(1)&lt;/script&gt;");
    expect(html).not.toContain("<script>alert(1)</script>");
  });
});
