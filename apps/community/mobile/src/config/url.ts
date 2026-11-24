export const DEFAULT_COMMUNITY_URL = "http://localhost:3060";

const ALLOWED_SCHEMES = new Set(["http:", "https:"]);
const EXTERNAL_SCHEMES = new Set(["http:", "https:", "mailto:", "tel:"]);

export type NormalizeUrlResult =
  | { ok: true; url: string }
  | { ok: false; error: string };

export function normalizeCommunityUrl(raw: string): NormalizeUrlResult {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: false, error: "Server URL cannot be empty." };
  }

  const candidate = /^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(trimmed)
    ? trimmed
    : `http://${trimmed}`;

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return { ok: false, error: "Enter a valid http:// or https:// URL." };
  }

  if (!ALLOWED_SCHEMES.has(parsed.protocol)) {
    return {
      ok: false,
      error: `Unsupported scheme "${parsed.protocol}". Use http:// or https://.`,
    };
  }

  if (!parsed.hostname) {
    return { ok: false, error: "Server URL must include a host or IP address." };
  }

  const normalized =
    parsed.pathname === "/" && !parsed.search && !parsed.hash
      ? parsed.origin
      : parsed.toString().replace(/\/+$/, "");

  return { ok: true, url: normalized };
}

export function getConfiguredCommunityUrl(
  envUrl?: string,
  extraUrl?: string,
): string {
  for (const candidate of [envUrl, extraUrl]) {
    if (typeof candidate === "string" && candidate.trim().length > 0) {
      const normalized = normalizeCommunityUrl(candidate);
      if (normalized.ok) {
        return normalized.url;
      }
    }
  }
  return DEFAULT_COMMUNITY_URL;
}

export function isAllowedOrigin(targetUrl: string, baseUrl: string): boolean {
  try {
    const target = new URL(targetUrl);
    const base = new URL(baseUrl);
    if (!ALLOWED_SCHEMES.has(target.protocol)) {
      return false;
    }
    if (!ALLOWED_SCHEMES.has(base.protocol)) {
      return false;
    }
    return target.origin === base.origin;
  } catch {
    return false;
  }
}

export type MobileRouteAction = "in-app" | "external" | "block";

export function classifyNavigation(
  targetUrl: string,
  baseUrl: string,
): MobileRouteAction {
  if (targetUrl === "about:blank") {
    return "in-app";
  }
  if (isAllowedOrigin(targetUrl, baseUrl)) {
    return "in-app";
  }
  try {
    const parsed = new URL(targetUrl);
    if (EXTERNAL_SCHEMES.has(parsed.protocol)) {
      return "external";
    }
  } catch {
    return "block";
  }
  return "block";
}

export function buildLanHint(currentUrl: string): string {
  let isLocalhost = false;
  try {
    const parsed = new URL(currentUrl);
    isLocalhost =
      parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1";
  } catch {
    isLocalhost = false;
  }

  if (isLocalhost) {
    return "localhost points to your iPhone itself. Tap Server URL and enter your PC's LAN IP (e.g. http://192.168.1.x:3060), with Next.js bound to 0.0.0.0:3060 and Windows Firewall TCP 3060 open.";
  }

  return "Ensure your iPhone and PC are on the same Wi-Fi, Next.js is running with `npm run dev -- -H 0.0.0.0 -p 3060`, and Windows Firewall allows inbound TCP 3060.";
}
