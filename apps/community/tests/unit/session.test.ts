import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { authHeaders, getDubaiApi, getSessionToken, googleStartUrl, setSessionToken } from "@/lib/session";

describe("community session helpers", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.unstubAllEnvs();
  });
  test("google sign-in always starts on apps/api with a loopback return_to", () => {
    const u = new URL(googleStartUrl("http://localhost:3060/signin", "http://localhost:8000"));
    expect(u.origin + u.pathname).toBe("http://localhost:8000/api/identity/google/start");
    expect(u.searchParams.get("return_to")).toBe("http://localhost:3060/signin");
    expect(u.searchParams.get("client")).toBe("web");
  });
  test("getDubaiApi and googleStartUrl resolve LAN host and localhost fallback", () => {
    vi.stubGlobal("location", { hostname: "localhost", protocol: "http:" });
    expect(getDubaiApi()).toBe("http://localhost:8000");

    vi.stubGlobal("location", { hostname: "127.0.0.1", protocol: "http:" });
    expect(getDubaiApi()).toBe("http://localhost:8000");

    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "http:" });
    expect(getDubaiApi()).toBe("http://192.168.1.50:8000");
    const lanUrl = new URL(googleStartUrl("http://192.168.1.50:3060/signin"));
    expect(lanUrl.origin + lanUrl.pathname).toBe("http://192.168.1.50:8000/api/identity/google/start");

    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "https:" });
    expect(getDubaiApi()).toBe("https://192.168.1.50:8000");

    vi.stubEnv("NEXT_PUBLIC_DUBAI_API", " https://api.example.test/ ");
    expect(getDubaiApi()).toBe("https://api.example.test");
  });
  test("token round-trips and sign-out clears it; headers only when signed in", () => {
    expect(authHeaders(getSessionToken())).toEqual({});
    setSessionToken("cs_community_x");
    expect(authHeaders(getSessionToken())).toEqual({ "X-App-Session": "cs_community_x" });
    setSessionToken(null);
    expect(getSessionToken()).toBeNull();
  });
});
