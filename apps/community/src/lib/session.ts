// One sign-in across Quest / Community / Messenger: the Google flow runs on apps/api (:8000), the code is redeemed at
// THIS app's own API for a community-scoped session of the same user_id. The token only lives in this browser.
export const DUBAI_API =
  process.env.NEXT_PUBLIC_DUBAI_API ?? "http://localhost:8000";
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
export function googleStartUrl(returnTo: string, dubaiApi: string = DUBAI_API): string {
  const q = new URLSearchParams({ client: "web", return_to: returnTo });
  return `${dubaiApi}/api/identity/google/start?${q.toString()}`;
}
export function authHeaders(token: string | null): Record<string, string> {
  return token ? { "X-App-Session": token } : {};
}
