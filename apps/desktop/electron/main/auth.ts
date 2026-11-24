import http from "http";
import type { AddressInfo } from "net";
import { shell } from "electron";
import type { DesktopAuthStatus, HookLog, TokenStore } from "./ownerHook";

export interface SignInOptions {
  apiBaseUrl: string;
  deviceLabel?: string;
  openExternal?: (url: string) => Promise<void> | void;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
}

export interface SignOutOptions {
  apiBaseUrl?: string;
  fetchImpl?: typeof fetch;
}

const DEFAULT_API_BASE_URL = process.env.DUBAI_API_URL || "http://127.0.0.1:8000";

function validateApiBaseUrl(raw: string): string {
  const trimmed = raw.trim().replace(/\/$/, "");
  let parsed: URL;
  try {
    parsed = new URL(trimmed);
  } catch {
    throw new Error("Invalid apiBaseUrl");
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("apiBaseUrl must use http or https");
  }
  return trimmed;
}

interface LoopbackHandle {
  callbackUrl: string;
  waitForAuthCode: () => Promise<string>;
  close: () => void;
}

function startLoopbackServer(timeoutMs: number): Promise<LoopbackHandle> {
  return new Promise((resolveStart, rejectStart) => {
    let settleCode: ((code: string) => void) | null = null;
    let rejectCode: ((err: Error) => void) | null = null;
    let settled = false;

    const codePromise = new Promise<string>((resolve, reject) => {
      settleCode = resolve;
      rejectCode = reject;
    });

    const server = http.createServer((req, res) => {
      const reqUrl = new URL(req.url || "/", "http://127.0.0.1");
      if (reqUrl.pathname !== "/callback") {
        res.writeHead(404, { "Content-Type": "text/plain" });
        res.end("Not found");
        return;
      }

      const error = reqUrl.searchParams.get("error");
      const authCode = reqUrl.searchParams.get("auth_code")?.trim() || "";
      if (error || !authCode) {
        res.writeHead(400, {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "no-store",
        });
        res.end("<!doctype html><html><body><p>Sign-in did not complete. Return to Dubai-io Desktop.</p></body></html>");
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          server.close();
          rejectCode?.(new Error(error ? `Google sign-in failed: ${error}` : "Missing auth_code in callback"));
        }
        return;
      }

      res.writeHead(200, {
        "Content-Type": "text/html; charset=utf-8",
        "Cache-Control": "no-store",
      });
      res.end("<!doctype html><html><body><p>Signed in to Dubai-io. You may close this tab.</p></body></html>");
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        server.close();
        settleCode?.(authCode);
      }
    });

    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        server.close();
        rejectCode?.(new Error("Google sign-in timed out"));
      }
    }, timeoutMs);

    server.on("error", (err) => {
      clearTimeout(timer);
      if (!settled) {
        settled = true;
        rejectStart(err);
        rejectCode?.(err);
      }
    });

    server.listen(0, "127.0.0.1", () => {
      const addr = server.address() as AddressInfo | null;
      if (!addr || typeof addr.port !== "number") {
        clearTimeout(timer);
        server.close();
        rejectStart(new Error("Could not bind loopback callback port"));
        return;
      }
      resolveStart({
        callbackUrl: `http://127.0.0.1:${addr.port}/callback`,
        waitForAuthCode: () => codePromise,
        close: () => {
          clearTimeout(timer);
          if (!settled) {
            settled = true;
            server.close();
          }
        },
      });
    });
  });
}

export class DesktopAuthManager {
  private lastApiBaseUrl: string = DEFAULT_API_BASE_URL;

  constructor(
    private readonly tokens: TokenStore,
    private readonly log: HookLog,
  ) {}

  status(): DesktopAuthStatus {
    return this.tokens.authStatus();
  }

  async signIn(options: SignInOptions): Promise<DesktopAuthStatus> {
    const baseUrl = validateApiBaseUrl(options.apiBaseUrl || this.lastApiBaseUrl);
    this.lastApiBaseUrl = baseUrl;
    const fetchImpl = options.fetchImpl ?? fetch;
    const openExternal = options.openExternal ?? ((url: string) => shell.openExternal(url));
    const deviceLabel = (options.deviceLabel || "Dubai-io Desktop").trim();
    const timeoutMs = options.timeoutMs ?? 180_000;

    const loopback = await startLoopbackServer(timeoutMs);
    let authCode: string;
    try {
      const startUrl = `${baseUrl}/api/identity/google/start?client=desktop&return_to=${encodeURIComponent(loopback.callbackUrl)}`;
      await openExternal(startUrl);
      authCode = await loopback.waitForAuthCode();
    } finally {
      loopback.close();
    }

    const exchangeRes = await fetchImpl(`${baseUrl}/api/identity/google/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ auth_code: authCode, device_label: deviceLabel }),
    });
    if (!exchangeRes.ok) {
      throw new Error(`Google sign-in exchange failed (${exchangeRes.status})`);
    }
    const exchangeData = (await exchangeRes.json()) as {
      session_id: string;
      session_token: string;
      user_id: string;
      display_name?: string | null;
      email?: string | null;
    };
    if (!exchangeData.session_token || !exchangeData.session_id || !exchangeData.user_id) {
      throw new Error("Incomplete session response from API");
    }

    const mintRes = await fetchImpl(`${baseUrl}/api/identity/memory-device-token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-App-Session": exchangeData.session_token,
      },
      body: JSON.stringify({ label: deviceLabel }),
    });
    if (!mintRes.ok) {
      throw new Error(`Memory device token mint failed (${mintRes.status})`);
    }
    const mintData = (await mintRes.json()) as {
      tm_token_id: string;
      token: string;
      owner_id: string;
    };
    if (!mintData.token || !mintData.tm_token_id) {
      throw new Error("Incomplete memory device token response from API");
    }

    this.tokens.saveCredentials({
      sessionToken: exchangeData.session_token,
      sessionId: exchangeData.session_id,
      deviceToken: mintData.token,
      tmTokenId: mintData.tm_token_id,
      userId: exchangeData.user_id,
      displayName: exchangeData.display_name ?? null,
      email: exchangeData.email ?? null,
    });
    this.log.info(`desktop signed in as ${exchangeData.user_id}`);
    return this.tokens.authStatus();
  }

  async signOut(options: SignOutOptions = {}): Promise<DesktopAuthStatus> {
    const baseUrl = validateApiBaseUrl(options.apiBaseUrl || this.lastApiBaseUrl);
    const fetchImpl = options.fetchImpl ?? fetch;
    if (this.tokens.authStatus().signedIn) {
      let creds: { sessionToken: string; sessionId: string; tmTokenId: string } | null = null;
      try {
        this.tokens.withCredentials((c) => {
          creds = { sessionToken: c.sessionToken, sessionId: c.sessionId, tmTokenId: c.tmTokenId };
        });
      } catch {
        creds = null;
      }
      if (creds) {
        const { sessionToken, sessionId, tmTokenId } = creds;
        try {
          await fetchImpl(`${baseUrl}/api/identity/memory-device-token/${encodeURIComponent(tmTokenId)}`, {
            method: "DELETE",
            headers: { "X-App-Session": sessionToken },
          });
        } catch {
          // Best-effort revoke.
        }
        try {
          await fetchImpl(`${baseUrl}/api/identity/sessions/${encodeURIComponent(sessionId)}`, {
            method: "DELETE",
            headers: { "X-App-Session": sessionToken },
          });
        } catch {
          // Best-effort revoke.
        }
      }
    }
    this.tokens.clear();
    return this.tokens.authStatus();
  }
}
