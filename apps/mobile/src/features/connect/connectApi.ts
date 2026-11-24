/** Connect helpers: SecureStore persistence, honest health check, OAuth, QR pairing, sessions, uploads. */
import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import * as WebBrowser from "expo-web-browser";
import type { Fetcher } from "../vault/vaultApi";

export const API_URL_KEY = "dubaiio.apiBaseUrl";
export const OWNER_KEY = "dubaiio.owner";
export const REGION_KEY = "dubaiio.youtubeRegion";
export const DEMO_KEY = "dubaiio.demoMode";

export type YoutubeRegion = "EEA" | "UAE";
export type ConnectionStatus = "unknown" | "reachable" | "offline";

export interface DeviceSessionInfo {
  session_id: string;
  app_id: string;
  device_label: string | null;
  created_at: string;
  expires_at: string;
  is_current: boolean;
}

export interface PairingStartOut {
  code: string;
  expires_at: string;
  ttl_seconds: number;
  qr_payload: string;
}

const defaultFetcher: Fetcher = (url, init) => fetch(url, init);

export function isLocalhostUrl(value: string): boolean {
  try {
    const host = new URL(value).hostname.toLowerCase();
    return host === "localhost" || host === "127.0.0.1" || host === "::1" || host.endsWith(".localhost");
  } catch {
    return /localhost|127\.0\.0\.1/.test(value);
  }
}
export const LOCALHOST_WARNING =
  "This phone cannot reach localhost — use your PC's LAN IP (http://192.168.x.x:8000) or a tunnel URL.";

async function putSetting(key: string, value: string): Promise<void> {
  if (Platform.OS === "web") {
    globalThis.localStorage?.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function getSetting(key: string): Promise<string | null> {
  if (Platform.OS === "web") return globalThis.localStorage?.getItem(key) ?? null;
  return SecureStore.getItemAsync(key);
}

export async function saveSettings(apiBaseUrl: string, owner: string, demo: boolean): Promise<void> {
  await putSetting(API_URL_KEY, apiBaseUrl);
  await putSetting(OWNER_KEY, owner);
  await putSetting(DEMO_KEY, demo ? "1" : "0");
}
export async function loadSettings(): Promise<{ apiBaseUrl: string; owner: string; demo: boolean }> {
  return {
    apiBaseUrl: (await getSetting(API_URL_KEY)) ?? "",
    owner: (await getSetting(OWNER_KEY)) ?? "",
    demo: (await getSetting(DEMO_KEY)) === "1",
  };
}
export async function saveRegion(region: YoutubeRegion): Promise<void> {
  await putSetting(REGION_KEY, region);
}
export async function loadRegion(): Promise<YoutubeRegion> {
  return (await getSetting(REGION_KEY)) === "EEA" ? "EEA" : "UAE";
}

/** Honest check: only a real 2xx from GET /api/health counts as reachable. */
export async function testConnection(apiBaseUrl: string, fetcher: Fetcher = defaultFetcher): Promise<ConnectionStatus> {
  try {
    const res = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/health`);
    return res.ok ? "reachable" : "offline";
  } catch {
    return "offline";
  }
}

/** Identity Google Sign-In (PKCE + state -> short-lived auth_code). */
export async function startGoogleSignIn(
  apiBaseUrl: string,
  returnTo?: string,
): Promise<WebBrowser.WebBrowserAuthSessionResult | void> {
  const base = apiBaseUrl.replace(/\/$/, "");
  const defaultWebReturn =
    typeof window !== "undefined" && window.location?.origin
      ? `${window.location.origin}/connect`
      : "http://localhost:8081/connect";
  const targetReturn = returnTo ?? defaultWebReturn;
  const startUrl = `${base}/api/identity/google/start?client=web&return_to=${encodeURIComponent(targetReturn)}`;
  if (Platform.OS === "web" && typeof window !== "undefined" && window.location?.assign) {
    window.location.assign(startUrl);
    return;
  }
  return WebBrowser.openAuthSessionAsync(startUrl, targetReturn);
}

/** Provider Google OAuth (Gmail/mail connector) — server-side; the app never bundles a client secret. */
export async function startGoogleOAuth(apiBaseUrl: string): Promise<WebBrowser.WebBrowserAuthSessionResult> {
  const start = `${apiBaseUrl.replace(/\/$/, "")}/api/auth/google/start`;
  return WebBrowser.openAuthSessionAsync(start, "dubaiio://auth/google");
}

export async function startDevicePairing(
  apiBaseUrl: string,
  sessionToken: string,
  fetcher: Fetcher = defaultFetcher,
): Promise<PairingStartOut> {
  const res = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/identity/pair/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
      "X-App-Session": sessionToken,
    },
    body: JSON.stringify({ ttl_seconds: 300 }),
  });
  if (!res.ok) {
    throw new Error(`Could not start pairing (${res.status})`);
  }
  return (await res.json()) as PairingStartOut;
}

export async function listActiveSessions(
  apiBaseUrl: string,
  sessionToken: string,
  fetcher: Fetcher = defaultFetcher,
): Promise<DeviceSessionInfo[]> {
  const res = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/identity/sessions`, {
    method: "GET",
    headers: {
      Accept: "application/json",
      "X-App-Session": sessionToken,
    },
  });
  if (!res.ok) {
    throw new Error(`Could not load sessions (${res.status})`);
  }
  const body = (await res.json()) as { sessions?: DeviceSessionInfo[] };
  return Array.isArray(body.sessions) ? body.sessions : [];
}

export async function revokeDeviceSession(
  apiBaseUrl: string,
  sessionToken: string,
  sessionId: string,
  fetcher: Fetcher = defaultFetcher,
): Promise<void> {
  const res = await fetcher(`${apiBaseUrl.replace(/\/$/, "")}/api/identity/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
    headers: {
      Accept: "application/json",
      "X-App-Session": sessionToken,
    },
  });
  if (!res.ok) {
    throw new Error(`Could not revoke session (${res.status})`);
  }
}

export async function uploadPickedFile(
  apiBaseUrl: string, owner: string, kind: "takeout" | "whatsapp",
  asset: { name: string; uri: string },
  fetcher: Fetcher = defaultFetcher,
): Promise<boolean> {
  try {
    const res = await fetcher(
      `${apiBaseUrl.replace(/\/$/, "")}/api/connectors/${kind}?owner=${encodeURIComponent(owner)}&name=${encodeURIComponent(asset.name)}`,
    );
    return res.ok;
  } catch {
    return false;
  }
}
