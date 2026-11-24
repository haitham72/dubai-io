import { describe, expect, it } from "vitest";
import {
  DEFAULT_COMMUNITY_URL,
  buildLanHint,
  classifyNavigation,
  getConfiguredCommunityUrl,
  isAllowedOrigin,
  normalizeCommunityUrl,
} from "../src/config/url";

describe("normalizeCommunityUrl", () => {
  it("normalizes bare LAN IP:port and strips trailing slash on root", () => {
    expect(normalizeCommunityUrl("192.168.1.42:3060")).toEqual({
      ok: true,
      url: "http://192.168.1.42:3060",
    });
    expect(normalizeCommunityUrl("  https://community.dubai.io/  ")).toEqual({
      ok: true,
      url: "https://community.dubai.io",
    });
  });

  it("rejects empty values and unsafe schemes", () => {
    expect(normalizeCommunityUrl("   ").ok).toBe(false);
    expect(normalizeCommunityUrl("javascript:alert(1)").ok).toBe(false);
    expect(normalizeCommunityUrl("file:///etc/passwd").ok).toBe(false);
    expect(normalizeCommunityUrl("ftp://192.168.1.10").ok).toBe(false);
  });
});

describe("getConfiguredCommunityUrl", () => {
  it("prefers envUrl over extraUrl and falls back to localhost:3060", () => {
    expect(
      getConfiguredCommunityUrl(
        "http://192.168.1.25:3060/",
        "http://10.0.0.5:3060",
      ),
    ).toBe("http://192.168.1.25:3060");

    expect(
      getConfiguredCommunityUrl(undefined, "https://tunnel.dubai.io/"),
    ).toBe("https://tunnel.dubai.io");

    expect(getConfiguredCommunityUrl(undefined, "javascript:bad")).toBe(
      DEFAULT_COMMUNITY_URL,
    );
  });
});

describe("isAllowedOrigin & classifyNavigation", () => {
  const base = "http://192.168.1.42:3060";

  it("keeps same-origin URLs in-app and routes external links outside", () => {
    expect(isAllowedOrigin("http://192.168.1.42:3060/inbox", base)).toBe(true);
    expect(isAllowedOrigin("http://192.168.1.42:3061/inbox", base)).toBe(false);
    expect(isAllowedOrigin("https://192.168.1.42:3060/inbox", base)).toBe(
      false,
    );

    expect(classifyNavigation("http://192.168.1.42:3060/create", base)).toBe(
      "in-app",
    );
    expect(classifyNavigation("about:blank", base)).toBe("in-app");
    expect(classifyNavigation("https://u.ae/en", base)).toBe("external");
    expect(classifyNavigation("mailto:hello@dubai.io", base)).toBe("external");
    expect(classifyNavigation("javascript:alert(1)", base)).toBe("block");
    expect(classifyNavigation("file:///var/mobile/secret", base)).toBe("block");
  });
});

describe("buildLanHint", () => {
  it("warns specifically when target URL is localhost", () => {
    const hint = buildLanHint("http://localhost:3060");
    expect(hint).toContain("localhost points to your iPhone");
    expect(hint).toContain("0.0.0.0:3060");
  });

  it("mentions Wi-Fi, 0.0.0.0, and TCP 3060 for LAN IPs", () => {
    const hint = buildLanHint("http://192.168.1.42:3060");
    expect(hint).toContain("TCP 3060");
    expect(hint).toContain("0.0.0.0");
  });
});
