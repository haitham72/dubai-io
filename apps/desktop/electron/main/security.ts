/** Electron webPreferences that the preload bridge depends on. Pure so tests can lock them. */
export const webPreferencesBase = {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  webviewTag: false,
} as const;

/** The Dubai-io app is the Expo web build served by `start-all` (E1). */
export const DEFAULT_APP_URL = "http://localhost:8081";

export type NavigationDecision = "allow" | "external" | "block";

const ALLOWED_APP_PROTOCOLS = new Set(["http:", "https:"]);
const SAFE_EXTERNAL_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

/** `DUBAI_APP_URL` overrides the default; anything that is not a valid http(s) URL falls back to the default. */
export function resolveAppUrl(env: Record<string, string | undefined> = process.env): string {
  const raw = (env.DUBAI_APP_URL ?? "").trim();
  if (!raw) return DEFAULT_APP_URL;
  try {
    const parsed = new URL(raw);
    if (!ALLOWED_APP_PROTOCOLS.has(parsed.protocol)) return DEFAULT_APP_URL;
    return parsed.toString().replace(/\/+$/, "");
  } catch {
    return DEFAULT_APP_URL;
  }
}

export function isAllowedNavigationOrigin(targetUrl: string, allowedOriginUrl: string): boolean {
  try {
    const target = new URL(targetUrl);
    const allowed = new URL(allowedOriginUrl);
    if (!ALLOWED_APP_PROTOCOLS.has(target.protocol) || !ALLOWED_APP_PROTOCOLS.has(allowed.protocol)) return false;
    return target.origin === allowed.origin;
  } catch {
    return false;
  }
}

export function isSafeExternalUrl(targetUrl: string): boolean {
  try {
    return SAFE_EXTERNAL_PROTOCOLS.has(new URL(targetUrl).protocol);
  } catch {
    return false;
  }
}

export function classifyDesktopNavigation(targetUrl: string, allowedOriginUrl: string): NavigationDecision {
  if (targetUrl === "about:blank") return "allow";
  if (isAllowedNavigationOrigin(targetUrl, allowedOriginUrl)) return "allow";
  if (isSafeExternalUrl(targetUrl)) return "external";
  return "block";
}

export interface GuardedWebContents {
  on(event: "will-navigate", listener: (event: { preventDefault: () => void }, url: string) => void): unknown;
  on(event: "will-attach-webview", listener: (event: { preventDefault: () => void }) => void): unknown;
  setWindowOpenHandler(handler: (details: { url: string }) => { action: "allow" | "deny" }): void;
}

export interface NavigationGuardOptions {
  allowedOriginUrl: string;
  openExternal: (url: string) => Promise<void> | void;
  loadUrl?: (url: string) => void;
  onBlocked?: (url: string) => void;
}

/** Same pattern as the Community and Messenger shells: stay on the app origin, hand safe links to the OS, deny the rest. */
export function attachNavigationGuards(contents: GuardedWebContents, options: NavigationGuardOptions): void {
  const { allowedOriginUrl, openExternal, loadUrl, onBlocked } = options;

  contents.on("will-navigate", (event, url) => {
    const decision = classifyDesktopNavigation(url, allowedOriginUrl);
    if (decision === "allow") return;
    event.preventDefault();
    if (decision === "external") {
      void openExternal(url);
      return;
    }
    onBlocked?.(url);
  });

  contents.setWindowOpenHandler(({ url }) => {
    const decision = classifyDesktopNavigation(url, allowedOriginUrl);
    if (decision === "allow") {
      if (url !== "about:blank" && loadUrl) loadUrl(url);
      return { action: "deny" };
    }
    if (decision === "external") {
      void openExternal(url);
      return { action: "deny" };
    }
    onBlocked?.(url);
    return { action: "deny" };
  });

  contents.on("will-attach-webview", (event) => event.preventDefault());
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Shown when the app URL cannot be reached: an honest message, never a blank window. */
export function buildFallbackHtml(targetUrl: string, reason = ""): string {
  const safeUrl = escapeHtml(targetUrl);
  const safeReason = escapeHtml(reason.trim() || "Unable to reach the Dubai-io app.");
  return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8" />
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'" />
<title>Dubai-io - Offline</title>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#fff;color:#15202b;font-family:"Segoe UI",sans-serif}
.card{max-width:480px;border:1px solid #e4e4e4;border-radius:16px;padding:28px}p{color:#6a7784;font-size:14px;line-height:1.5}</style></head>
<body><main class="card"><h1>Dubai-io is not running</h1><p>${safeReason}</p>
<p>Target URL: <strong>${safeUrl}</strong></p>
<p>Start the stack with scripts\\dev\\start-all.ps1, then choose Dubai-io &gt; Reload (Ctrl+R).</p></main></body></html>`;
}

/** Where the Settings window loads the built renderer from (first existing candidate wins). */
export function resolveRendererIndex(
  env: Record<string, string | undefined>,
  mainDir: string,
  exists: (p: string) => boolean,
  join: (...parts: string[]) => string,
): string | null {
  const candidates: string[] = [];
  if (env.DUBAI_DESKTOP_RENDERER_DIST) candidates.push(join(env.DUBAI_DESKTOP_RENDERER_DIST, "index.html"));
  candidates.push(join(mainDir, "..", "..", "renderer", "dist", "index.html"));
  candidates.push(join(mainDir, "..", "..", "..", "renderer", "dist", "index.html"));
  return candidates.find((c) => exists(c)) ?? null;
}
