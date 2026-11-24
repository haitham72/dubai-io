import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import { useApiSettingsOptional } from "./api-settings";
import type { AuthSession } from "./types";

const SESSION_STORE_KEY = "dubaiio.authSession";
const DEMO_STORE_KEY = "dubaiio.demoMode";

export interface AuthContextValue {
  session: AuthSession | null;
  isAuthenticated: boolean;
  demoMode: boolean;
  ready: boolean;
  authError: string | null;
  setDemoMode: (enabled: boolean) => void;
  setSession: (next: AuthSession | null) => Promise<void>;
  exchangeAuthCode: (apiBaseUrl: string, authCode: string, deviceLabel?: string) => Promise<AuthSession>;
  completePairing: (apiBaseUrl: string, code: string, deviceLabel?: string) => Promise<AuthSession>;
  signOut: (apiBaseUrl?: string) => Promise<void>;
  refreshMe: (apiBaseUrl: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function storageGet(key: string): Promise<string | null> {
  if (Platform.OS === "web") {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  }
  try {
    return await SecureStore.getItemAsync(key);
  } catch {
    return null;
  }
}

async function storageSet(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    try {
      globalThis.localStorage?.setItem(key, value);
    } catch {
      // Ignore storage quota or private browsing errors.
    }
    return;
  }
  try {
    await SecureStore.setItemAsync(key, value);
  } catch {
    // Tests / web fallback.
  }
}

async function storageDelete(key: string): Promise<void> {
  if (Platform.OS === "web") {
    try {
      globalThis.localStorage?.removeItem(key);
    } catch {
      // Ignore.
    }
    return;
  }
  try {
    await SecureStore.deleteItemAsync(key);
  } catch {
    // Ignore.
  }
}

export function extractAuthCodeFromUrl(url: string): string | null {
  try {
    const parsed = new URL(url, "http://localhost");
    const code = parsed.searchParams.get("auth_code")?.trim();
    return code || null;
  } catch {
    return null;
  }
}

export function parsePairingPayload(raw: string): string {
  const trimmed = raw.trim();
  if (!trimmed) return "";
  if (trimmed.startsWith("{")) {
    try {
      const parsed = JSON.parse(trimmed) as { code?: unknown };
      if (typeof parsed.code === "string" && parsed.code.trim()) {
        return parsed.code.trim().toUpperCase();
      }
    } catch {
      // Fall through to URL / raw code parsing.
    }
  }
  if (/^[a-z]+:\/\//i.test(trimmed)) {
    try {
      const parsed = new URL(trimmed);
      const fromParam = parsed.searchParams.get("code")?.trim();
      if (fromParam) return fromParam.toUpperCase();
    } catch {
      // Fall through.
    }
  }
  return trimmed.toUpperCase();
}

export function mapPairingErrorCode(code: string | undefined, status: number): string {
  if (code === "expired_code") return "Pairing code expired. Generate a new QR code on your PC.";
  if (code === "code_already_used") return "Pairing code was already used. Generate a new QR code on your PC.";
  if (code === "invalid_code") return "Invalid pairing code. Check the code and try again.";
  if (status === 410) return "Pairing code expired. Generate a new QR code on your PC.";
  if (status === 409) return "Pairing code was already used. Generate a new QR code on your PC.";
  if (status >= 500) return "Server error while pairing device. Try again.";
  return "Could not pair device with that code.";
}

function parseSessionPayload(body: Record<string, unknown>): AuthSession {
  const sessionToken = typeof body.session_token === "string" ? body.session_token : "";
  const sessionId = typeof body.session_id === "string" ? body.session_id : "";
  const userId = typeof body.user_id === "string" ? body.user_id : "";
  if (!sessionToken || !sessionId || !userId) {
    throw new Error("Server returned an incomplete session response");
  }
  return {
    sessionToken,
    sessionId,
    userId,
    displayName: typeof body.display_name === "string" && body.display_name ? body.display_name : null,
    email: typeof body.email === "string" && body.email ? body.email : null,
  };
}

export function AuthProvider({
  children,
  apiBaseUrl: overrideApiBaseUrl,
  fetchImpl = fetch,
}: {
  children: React.ReactNode;
  apiBaseUrl?: string;
  fetchImpl?: typeof fetch;
}) {
  const settings = useApiSettingsOptional();
  const effectiveApiBaseUrl = (overrideApiBaseUrl ?? settings?.apiBaseUrl ?? "").trim().replace(/\/$/, "");
  const [session, setSessionState] = useState<AuthSession | null>(null);
  const [demoMode, setDemoModeState] = useState<boolean>(false);
  const [ready, setReady] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const handledAuthCodeRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([storageGet(SESSION_STORE_KEY), storageGet(DEMO_STORE_KEY)]).then(([rawSession, rawDemo]) => {
      if (cancelled) return;
      if (rawSession) {
        try {
          const parsed = JSON.parse(rawSession) as Partial<AuthSession>;
          if (parsed.sessionToken && parsed.sessionId && parsed.userId) {
            setSessionState({
              sessionToken: parsed.sessionToken,
              sessionId: parsed.sessionId,
              userId: parsed.userId,
              displayName: parsed.displayName ?? null,
              email: parsed.email ?? null,
            });
          }
        } catch {
          // Ignore corrupted local storage.
        }
      }
      setDemoModeState(rawDemo === "1");
      setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const setSession = useCallback(async (next: AuthSession | null) => {
    setSessionState(next);
    setAuthError(null);
    if (next) {
      await storageSet(SESSION_STORE_KEY, JSON.stringify(next));
    } else {
      await storageDelete(SESSION_STORE_KEY);
    }
  }, []);

  const setDemoMode = useCallback((enabled: boolean) => {
    setDemoModeState(enabled);
    void storageSet(DEMO_STORE_KEY, enabled ? "1" : "0");
  }, []);

  const exchangeAuthCode = useCallback(
    async (apiBaseUrl: string, authCode: string, deviceLabel?: string): Promise<AuthSession> => {
      const base = apiBaseUrl.trim().replace(/\/$/, "");
      if (!base) throw new Error("Set your API Server URL first.");
      const res = await fetchImpl(`${base}/api/identity/google/exchange`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          auth_code: authCode,
          device_label: deviceLabel ?? (Platform.OS === "web" ? "Web browser" : "iPhone"),
          set_cookie: Platform.OS === "web",
        }),
      });
      if (!res.ok) {
        const errBody = (await res.json().catch(() => ({}))) as { detail?: { message?: string } };
        throw new Error(errBody.detail?.message ?? `Sign-in failed (${res.status})`);
      }
      const parsed = parseSessionPayload((await res.json()) as Record<string, unknown>);
      await setSession(parsed);
      return parsed;
    },
    [fetchImpl, setSession],
  );

  const completePairing = useCallback(
    async (apiBaseUrl: string, rawCode: string, deviceLabel?: string): Promise<AuthSession> => {
      const base = apiBaseUrl.trim().replace(/\/$/, "");
      const code = parsePairingPayload(rawCode);
      if (!base) throw new Error("Set your API Server URL first.");
      if (!code) throw new Error("Enter or scan a pairing code.");
      let res: Response;
      try {
        res = await fetchImpl(`${base}/api/identity/pair/complete`, {
          method: "POST",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({
            code,
            device_label: deviceLabel ?? (Platform.OS === "ios" ? "iPhone" : "Mobile device"),
          }),
        });
      } catch {
        throw new Error("Network error: could not reach the API server.");
      }
      if (!res.ok) {
        const errBody = (await res.json().catch(() => ({}))) as { detail?: { code?: string } };
        throw new Error(mapPairingErrorCode(errBody.detail?.code, res.status));
      }
      const parsed = parseSessionPayload((await res.json()) as Record<string, unknown>);
      await setSession(parsed);
      return parsed;
    },
    [fetchImpl, setSession],
  );

  const signOut = useCallback(
    async (apiBaseUrl?: string) => {
      const base = (apiBaseUrl ?? effectiveApiBaseUrl).trim().replace(/\/$/, "");
      if (base && session?.sessionId && session?.sessionToken) {
        try {
          await fetchImpl(`${base}/api/identity/sessions/${encodeURIComponent(session.sessionId)}`, {
            method: "DELETE",
            headers: { "X-App-Session": session.sessionToken },
          });
        } catch {
          // Best-effort remote revoke; local session is always cleared.
        }
      }
      await setSession(null);
    },
    [effectiveApiBaseUrl, fetchImpl, session, setSession],
  );

  const refreshMe = useCallback(
    async (apiBaseUrl: string) => {
      const base = apiBaseUrl.trim().replace(/\/$/, "");
      if (!base || !session?.sessionToken) return;
      try {
        const res = await fetchImpl(`${base}/api/identity/me`, {
          method: "GET",
          headers: { "X-App-Session": session.sessionToken, Accept: "application/json" },
        });
        if (res.status === 401) {
          await setSession(null);
          return;
        }
        if (!res.ok) return;
        const body = (await res.json()) as Record<string, unknown>;
        const next: AuthSession = {
          sessionToken: session.sessionToken,
          sessionId: typeof body.session_id === "string" ? body.session_id : session.sessionId,
          userId: typeof body.user_id === "string" ? body.user_id : session.userId,
          displayName: typeof body.display_name === "string" ? body.display_name : session.displayName,
          email: typeof body.email === "string" ? body.email : session.email,
        };
        await setSession(next);
      } catch {
        // Keep cached session if offline.
      }
    },
    [fetchImpl, session, setSession],
  );

  // On web, automatically complete Google OAuth redirect (?auth_code=...) once on mount.
  useEffect(() => {
    if (!ready || Platform.OS !== "web" || typeof window === "undefined") return;
    const authCode = extractAuthCodeFromUrl(window.location.href);
    if (!authCode || handledAuthCodeRef.current === authCode) return;
    const base = effectiveApiBaseUrl || window.location.origin;
    if (!base) return;
    handledAuthCodeRef.current = authCode;
    void exchangeAuthCode(base, authCode, "Web browser")
      .then(() => {
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete("auth_code");
        window.history.replaceState({}, "", cleanUrl.toString());
      })
      .catch((err: unknown) => {
        setAuthError(err instanceof Error ? err.message : "Google sign-in failed");
      });
  }, [ready, effectiveApiBaseUrl, exchangeAuthCode]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isAuthenticated: Boolean(session?.sessionToken && session?.userId),
      demoMode,
      ready,
      authError,
      setDemoMode,
      setSession,
      exchangeAuthCode,
      completePairing,
      signOut,
      refreshMe,
    }),
    [session, demoMode, ready, authError, setDemoMode, setSession, exchangeAuthCode, completePairing, signOut, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}

export function useAuthOptional(): AuthContextValue | null {
  return useContext(AuthContext);
}
