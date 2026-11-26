// One sign-in across Quest / Community / Messenger: the Google flow runs on apps/api (:8000), the code is redeemed at
// THIS app's own API for a community-scoped session of the same user_id. The token only lives in this browser.
export function getDubaiApi(): string {
  const envBase = process.env.NEXT_PUBLIC_DUBAI_API?.trim();
  if (envBase) return envBase.replace(/\/+$/, "");
  if (typeof window !== "undefined") {
    const host = window.location?.hostname;
    if (host && host !== "localhost" && host !== "127.0.0.1") {
      const proto = window.location.protocol === "https:" ? "https:" : "http:";
      return `${proto}//${host}:8000`;
    }
  }
  return "http://localhost:8000";
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
