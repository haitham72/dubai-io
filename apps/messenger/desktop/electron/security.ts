/** Electron webPreferences invariants, origin allowlists, and permission gating for Messenger desktop. */

export const DEFAULT_MESSENGER_URL = "http://localhost:5173";

const ALLOWED_WEB_PROTOCOLS = new Set(["http:", "https:"]);
const EXTERNAL_PROTOCOLS = new Set(["http:", "https:", "mailto:", "tel:"]);

/** Hardened webPreferences locked by unit tests and applied to the Messenger BrowserWindow. */
export const webPreferencesBase = {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  webviewTag: false,
} as const;

/** Permissions allowed solely for the configured Messenger origin. */
export const ORIGIN_SCOPED_PERMISSIONS: ReadonlySet<string> = new Set([
  "notifications",
  "media",
]);

/** Resolve and validate the target Messenger URL from environment variables. */
export function resolveMessengerUrl(
  env: Record<string, string | undefined> = process.env,
): string {
  const raw = (env.MESSENGER_URL || env.VITE_MESSENGER_URL || DEFAULT_MESSENGER_URL).trim();
  const parsed = new URL(raw);
  if (!ALLOWED_WEB_PROTOCOLS.has(parsed.protocol)) {
    throw new Error(`Unsupported MESSENGER_URL protocol: ${parsed.protocol}`);
  }
  parsed.hash = "";
  const formatted = parsed.toString();
  return formatted.endsWith("/") && parsed.pathname === "/" ? formatted.slice(0, -1) : formatted;
}

/** Extract the strict origin (scheme + host + port) from a validated Messenger URL. */
export function getAllowedOrigin(messengerUrl: string): string {
  const parsed = new URL(messengerUrl);
  if (!ALLOWED_WEB_PROTOCOLS.has(parsed.protocol)) {
    throw new Error(`Unsupported origin protocol: ${parsed.protocol}`);
  }
  return parsed.origin;
}

/** Allow in-app navigation only for HTTP(S) URLs matching the configured Messenger origin. */
export function isAllowedNavigation(targetUrl: string, allowedOrigin: string): boolean {
  const trimmed = targetUrl.trim();
  if (!trimmed) return false;
  try {
    const parsed = new URL(trimmed);
    const expected = new URL(allowedOrigin).origin;
    return ALLOWED_WEB_PROTOCOLS.has(parsed.protocol) && parsed.origin === expected;
  } catch {
    return false;
  }
}

/** Allow external OS browser handoff for safe off-origin HTTP(S) or mailto/tel links. */
export function shouldOpenExternally(targetUrl: string, allowedOrigin: string): boolean {
  const trimmed = targetUrl.trim();
  if (!trimmed) return false;
  try {
    const parsed = new URL(trimmed);
    const expected = new URL(allowedOrigin).origin;
    if (!EXTERNAL_PROTOCOLS.has(parsed.protocol)) {
      return false;
    }
    if (ALLOWED_WEB_PROTOCOLS.has(parsed.protocol)) {
      return parsed.origin !== expected;
    }
    return true;
  } catch {
    return false;
  }
}

/** Fail-closed Electron permission check: only allow notifications & media for the configured Messenger origin. */
export function isOriginPermissionAllowed(
  permission: string,
  requestingOriginOrUrl: string | undefined | null,
  allowedOrigin: string,
): boolean {
  if (!ORIGIN_SCOPED_PERMISSIONS.has(permission)) {
    return false;
  }
  const raw = (requestingOriginOrUrl ?? "").trim();
  if (!raw) return false;
  try {
    const parsed = new URL(raw);
    const expected = new URL(allowedOrigin).origin;
    return ALLOWED_WEB_PROTOCOLS.has(parsed.protocol) && parsed.origin === expected;
  } catch {
    return false;
  }
}

export interface SanitizedNotification {
  title: string;
  body: string;
}

/** Validate and clamp a notification payload received over preload IPC. */
export function sanitizeNotificationPayload(payload: unknown): SanitizedNotification | null {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return null;
  }
  const record = payload as Record<string, unknown>;
  const title = typeof record.title === "string" ? record.title.trim().slice(0, 120) : "";
  const body = typeof record.body === "string" ? record.body.trim().slice(0, 400) : "";
  if (!title && !body) return null;
  return {
    title: title || "Messenger",
    body,
  };
}
