// One sign-in across Quest / Community / Messenger: the Google flow runs on apps/api (:8000), the code is redeemed at
// THIS app's own API for a community-scoped session of the same user_id. The token only lives in this browser.

/** Rewrite a loopback base URL (localhost / 127.0.0.1) to the browser's LAN host when accessed from another device. */
export function rewriteLoopbackForLanHost(baseUrl: string): string {
  const clean = baseUrl.trim().replace(/\/+$/, "");
  const m = clean.match(/^https?:\/\/(?:localhost|127\.0\.0\.1)(:\d+)?(\/.*)?$/i);
  if (!m) return clean;
  const loc = typeof window !== "undefined" ? window.location : globalThis.location;
  if (loc?.hostname && loc.hostname !== "localhost" && loc.hostname !== "127.0.0.1") {
    const proto = loc.protocol === "https:" ? "https:" : "http:";
    return `${proto}//${loc.hostname}${m[1] ?? ""}${m[2] ?? ""}`;
  }
  return clean;
}

export function getDubaiApi(): string {
  const envBase = process.env.NEXT_PUBLIC_DUBAI_API?.trim();
  return rewriteLoopbackForLanHost(envBase || "http://localhost:8000");
}

export const DUBAI_API = getDubaiApi();
export const SESSION_KEY = "dubaiio_community_session";

export function getSessionToken(): string | null {
  try { return window.localStorage.getItem(SESSION_KEY); } catch { return null; }
}
export function isSignedIn(): boolean {
  return !!getSessionToken();
}
export function setSessionToken(token: string | null): void {
  try {
    if (token) window.localStorage.setItem(SESSION_KEY, token);
    else window.localStorage.removeItem(SESSION_KEY);
  } catch { /* storage blocked: stay signed out */ }
}
export function googleStartUrl(returnTo: string, dubaiApi: string = getDubaiApi()): string {
  const q = new URLSearchParams({ client: "web", return_to: returnTo });
  return `${dubaiApi}/api/identity/google/start?${q.toString()}`;
}
export function authHeaders(token: string | null): Record<string, string> {
  return token ? { "X-App-Session": token } : {};
}
