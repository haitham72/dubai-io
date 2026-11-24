import { beforeEach, describe, expect, test } from "vitest";
import { authHeaders, getSessionToken, googleStartUrl, setSessionToken } from "@/lib/session";

describe("community session helpers", () => {
  beforeEach(() => window.localStorage.clear());
  test("google sign-in always starts on apps/api with a loopback return_to", () => {
    const u = new URL(googleStartUrl("http://localhost:3060/signin", "http://localhost:8000"));
    expect(u.origin + u.pathname).toBe("http://localhost:8000/api/identity/google/start");
    expect(u.searchParams.get("return_to")).toBe("http://localhost:3060/signin");
    expect(u.searchParams.get("client")).toBe("web");
  });
  test("token round-trips and sign-out clears it; headers only when signed in", () => {
    expect(authHeaders(getSessionToken())).toEqual({});
    setSessionToken("cs_community_x");
    expect(authHeaders(getSessionToken())).toEqual({ "X-App-Session": "cs_community_x" });
    setSessionToken(null);
    expect(getSessionToken()).toBeNull();
  });
});
