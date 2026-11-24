import fs from "fs";
import os from "os";
import path from "path";
import { describe, expect, it, vi } from "vitest";
import { DesktopAuthManager } from "../../electron/main/auth";
import { runDesktopSync, uploadKindFor } from "../../electron/main/desktopSync";
import { IPC, assertChannel, parseSignIn } from "../../electron/main/ipcAllowlist";
import { TokenStore, type TokenVault } from "../../electron/main/ownerHook";

const vault: TokenVault = {
  isEncryptionAvailable: () => true,
  encryptString: (v: string) => Buffer.from(`enc:${v}`, "utf8"),
  decryptString: (b: Buffer) => b.toString("utf8").replace(/^enc:/, ""),
};
const log = { info: () => undefined };
const json = (body: unknown, status = 200) =>
  ({ ok: status < 300, status, json: async () => body }) as Response;

function newStore() {
  const file = path.join(fs.mkdtempSync(path.join(os.tmpdir(), "dubai-auth-")), "creds.bin");
  return { store: new TokenStore(vault, log, file), file };
}

/** Plays the browser: opens the start URL, then follows the return_to loopback with an auth_code. */
function fakeBrowser(authCode: string | null) {
  return async (startUrl: string) => {
    const returnTo = new URL(startUrl).searchParams.get("return_to") as string;
    const target = authCode ? `${returnTo}?auth_code=${authCode}` : `${returnTo}?error=access_denied`;
    setTimeout(() => void fetch(target).catch(() => undefined), 20);
  };
}

describe("desktop Google sign-in (loopback, Google exchange mocked server-side)", () => {
  it("signs in through the loopback, mints the owner-scoped device token and stores both encrypted", async () => {
    const { store, file } = newStore();
    const calls: string[] = [];
    const fetchImpl = (async (url: string) => {
      calls.push(url);
      if (url.endsWith("/google/exchange")) {
        return json({ session_id: "sid-1", session_token: "sess-tok", user_id: "uid-1", display_name: "Test Owner", email: "o@example.test" });
      }
      return json({ tm_token_id: "tmt-1", token: "dev-tok", owner_id: "uid-1" });
    }) as unknown as typeof fetch;
    const auth = new DesktopAuthManager(store, log);
    const status = await auth.signIn({
      apiBaseUrl: "http://127.0.0.1:8000",
      openExternal: fakeBrowser("one-time-code"),
      fetchImpl,
      timeoutMs: 5000,
    });
    expect(status).toMatchObject({ signedIn: true, userId: "uid-1", displayName: "Test Owner", hasDeviceToken: true });
    expect(calls).toEqual([
      "http://127.0.0.1:8000/api/identity/google/exchange",
      "http://127.0.0.1:8000/api/identity/memory-device-token",
    ]);
    const onDisk = fs.readFileSync(file, "utf8");
    expect(onDisk.startsWith("enc:")).toBe(true);
    const reloaded = new TokenStore(vault, log, file);
    expect(reloaded.loadFromDisk()).toBe(true);
    expect(reloaded.authStatus().userId).toBe("uid-1");
  });

  it("a denied Google consent signs nobody in", async () => {
    const { store } = newStore();
    const auth = new DesktopAuthManager(store, log);
    await expect(
      auth.signIn({ apiBaseUrl: "http://127.0.0.1:8000", openExternal: fakeBrowser(null), fetchImpl: vi.fn() as unknown as typeof fetch, timeoutMs: 5000 }),
    ).rejects.toThrow(/Google sign-in failed/);
    expect(store.authStatus().signedIn).toBe(false);
  });

  it("a rejected or reused auth_code is reported and stores nothing", async () => {
    const { store } = newStore();
    const auth = new DesktopAuthManager(store, log);
    const fetchImpl = (async () => json({}, 401)) as unknown as typeof fetch;
    await expect(
      auth.signIn({ apiBaseUrl: "http://127.0.0.1:8000", openExternal: fakeBrowser("used"), fetchImpl, timeoutMs: 5000 }),
    ).rejects.toThrow(/exchange failed \(401\)/);
    expect(store.authStatus().signedIn).toBe(false);
  });

  it("sign-out revokes the device token and the session server-side, then clears local credentials", async () => {
    const { store, file } = newStore();
    store.saveCredentials({ sessionToken: "s", sessionId: "sid-9", deviceToken: "d", tmTokenId: "tmt-9", userId: "u", displayName: null, email: null });
    const seen: string[] = [];
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      seen.push(`${init?.method} ${url}`);
      return json({});
    }) as unknown as typeof fetch;
    const status = await new DesktopAuthManager(store, log).signOut({ apiBaseUrl: "http://127.0.0.1:8000", fetchImpl });
    expect(status.signedIn).toBe(false);
    expect(seen).toEqual([
      "DELETE http://127.0.0.1:8000/api/identity/memory-device-token/tmt-9",
      "DELETE http://127.0.0.1:8000/api/identity/sessions/sid-9",
    ]);
    expect(fs.existsSync(file)).toBe(false);
  });
});

describe("desktop sync uses the owner's device token", () => {
  function signedIn(userId: string, session: string, device: string) {
    const { store } = newStore();
    store.saveCredentials({ sessionToken: session, sessionId: `sid-${userId}`, deviceToken: device, tmTokenId: `t-${userId}`, userId, displayName: null, email: null });
    return store;
  }

  it("posts redacted records with both the session and the owner device token, and skips repeats", async () => {
    const store = signedIn("uid-A", "sess-A", "dev-A");
    const requests: { url: string; headers: Record<string, string>; body: string }[] = [];
    const fetchImpl = (async (url: string, init?: RequestInit) => {
      requests.push({ url, headers: init?.headers as Record<string, string>, body: String(init?.body) });
      return json({});
    }) as unknown as typeof fetch;
    const seen = new Set<string>();
    const deps = {
      tokens: store,
      apiBaseUrl: "http://127.0.0.1:8000",
      enabledSources: ["chrome" as const],
      collect: async () => [{ id: "r1", at: "2026-11-24T00:00:00+04:00", text: "Browser visits to example.test: 3" }],
      fetchImpl,
      seen,
    };
    const first = await runDesktopSync(deps);
    expect(first.uploaded).toBe(1);
    expect(requests.map((r) => r.url)).toEqual(["http://127.0.0.1:8000/api/ingest/desktop/browser"]);
    expect(requests[0].headers["X-Memory-Device-Token"]).toBe("dev-A");
    expect(requests[0].headers["X-App-Session"]).toBe("sess-A");
    expect(uploadKindFor("codex")).toBe("agent_sessions");
    const second = await runDesktopSync(deps);
    expect(second.uploaded).toBe(0);
  });

  it("refuses when signed out and reports a consent-off refusal honestly", async () => {
    const { store } = newStore();
    const out = await runDesktopSync({ tokens: store, apiBaseUrl: "http://x", enabledSources: ["chrome"], collect: async () => [] });
    expect(out.signedIn).toBe(false);
    expect(out.errors[0].message).toMatch(/Sign in/);

    const signed = signedIn("uid-B", "s", "d");
    const fetchImpl = (async () => json({}, 403)) as unknown as typeof fetch;
    const refused = await runDesktopSync({
      tokens: signed, apiBaseUrl: "http://x", enabledSources: ["chrome"], fetchImpl,
      collect: async () => [{ id: "r2", at: "2026-11-24T00:00:00+04:00", text: "x" }],
    });
    expect(refused.uploaded).toBe(0);
    expect(refused.errors[0].message).toMatch(/consent/i);
  });
});

describe("auth IPC allowlist", () => {
  it("allowlists the auth channels and only accepts a plain http(s) origin", () => {
    expect(assertChannel(IPC.authSignIn)).toBe("auth:signIn");
    expect(parseSignIn(undefined)).toEqual({});
    expect(parseSignIn({ apiBaseUrl: "http://192.168.1.5:8000/path" })).toEqual({ apiBaseUrl: "http://192.168.1.5:8000" });
    expect(() => parseSignIn({ apiBaseUrl: "file:///etc/passwd" })).toThrow();
    expect(() => parseSignIn({ apiBaseUrl: "http://u:p@host" })).toThrow();
    expect(() => parseSignIn({ command: "x" })).toThrow();
  });
});
