/** Configuration, origin allowlist, and WebSocket URL derivation for the Messenger iPhone shell. */

export const DEFAULT_MESSENGER_URL = "http://localhost:5173";

const ALLOWED_WEB_PROTOCOLS = new Set(["http:", "https:"]);
const EXTERNAL_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:", "sms:"]);

/** Validate and normalize a Messenger HTTP/HTTPS base URL (stripping trailing slashes and hash). */
export function normalizeMessengerUrl(raw?: string | null): string {
  const trimmed = (raw ?? "").trim();
  if (!trimmed) return DEFAULT_MESSENGER_URL;

  const parsed = new URL(trimmed);
  if (!ALLOWED_WEB_PROTOCOLS.has(parsed.protocol)) {
    throw new Error(`Unsupported Messenger URL protocol: ${parsed.protocol}`);
  }
  parsed.hash = "";
  const normalized = parsed.toString();
  return normalized.endsWith("/") && parsed.pathname === "/" ? normalized.slice(0, -1) : normalized;
}

/** Resolve the active Messenger URL from an optional user override or EXPO_PUBLIC_MESSENGER_URL. */
export function getConfiguredMessengerUrl(
  env?: Record<string, string | undefined>,
  overrideUrl?: string | null,
): string {
  const overrideTrimmed = (overrideUrl ?? "").trim();
  if (overrideTrimmed) {
    return normalizeMessengerUrl(overrideTrimmed);
  }
  const envUrl = env?.EXPO_PUBLIC_MESSENGER_URL;
  return normalizeMessengerUrl(envUrl);
}

/** Return the normalized origin (scheme + host + optional port) for the configured Messenger URL. */
export function deriveMessengerOrigin(messengerUrl: string): string {
  const normalized = normalizeMessengerUrl(messengerUrl);
  return new URL(normalized).origin;
}

/** Derive the /api/messenger/ws WebSocket URL (ws: or wss:) from the configured Messenger URL. */
export function deriveWsUrl(messengerUrl: string, wsPath = "/api/messenger/ws"): string {
  const parsed = new URL(normalizeMessengerUrl(messengerUrl));
  parsed.protocol = parsed.protocol === "https:" ? "wss:" : "ws:";
  parsed.pathname = wsPath.startsWith("/") ? wsPath : `/${wsPath}`;
  parsed.search = "";
  parsed.hash = "";
  return parsed.toString();
}

/** Allow only same-origin HTTP(S) navigations inside the WebView (plus about:blank). */
export function isAllowedMessengerNavigation(targetUrl: string, allowedOrigin: string): boolean {
  const trimmed = targetUrl.trim();
  if (!trimmed) return false;
  if (trimmed === "about:blank") return true;

  let parsed: URL;
  let expectedOrigin: string;
  try {
    parsed = new URL(trimmed);
    expectedOrigin = new URL(allowedOrigin).origin;
  } catch {
    return false;
  }

  return ALLOWED_WEB_PROTOCOLS.has(parsed.protocol) && parsed.origin === expectedOrigin;
}

/** Determine whether a tapped link should be handed off to the system browser or OS handler. */
export function shouldOpenExternally(targetUrl: string, allowedOrigin: string): boolean {
  const trimmed = targetUrl.trim();
  if (!trimmed || trimmed === "about:blank") return false;

  let parsed: URL;
  let expectedOrigin: string;
  try {
    parsed = new URL(trimmed);
    expectedOrigin = new URL(allowedOrigin).origin;
  } catch {
    return false;
  }

  if (!EXTERNAL_PROTOCOLS.has(parsed.protocol)) {
    return false;
  }
  if (ALLOWED_WEB_PROTOCOLS.has(parsed.protocol)) {
    return parsed.origin !== expectedOrigin;
  }
  return true;
}
