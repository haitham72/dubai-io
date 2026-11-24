/**
 * Security & navigation primitives for the Dubai-io Community Electron shell.
 * Kept pure/injectable so unit tests can lock webPreferences and origin rules.
 */

export const DEFAULT_COMMUNITY_URL = "http://localhost:3060";

/** Hardened BrowserWindow webPreferences (pattern aligned with Dubai-io desktop). */
export const webPreferencesBase = {
  contextIsolation: true,
  nodeIntegration: false,
  sandbox: true,
  webSecurity: true,
  allowRunningInsecureContent: false,
  webviewTag: false,
} as const;

export type NavigationDecision = "allow" | "external" | "block";

const ALLOWED_APP_PROTOCOLS = new Set(["http:", "https:"]);
const SAFE_EXTERNAL_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

export function resolveCommunityUrl(
  env: Record<string, string | undefined> = process.env,
): string {
  const raw = (env.COMMUNITY_URL ?? "").trim();
  if (!raw) {
    return DEFAULT_COMMUNITY_URL;
  }
  try {
    const parsed = new URL(raw);
    if (!ALLOWED_APP_PROTOCOLS.has(parsed.protocol)) {
      return DEFAULT_COMMUNITY_URL;
    }
    return parsed.toString().replace(/\/+$/, "");
  } catch {
    return DEFAULT_COMMUNITY_URL;
  }
}

export function isAllowedNavigationOrigin(
  targetUrl: string,
  allowedOriginUrl: string,
): boolean {
  try {
    const target = new URL(targetUrl);
    const allowed = new URL(allowedOriginUrl);
    if (!ALLOWED_APP_PROTOCOLS.has(target.protocol)) {
      return false;
    }
    if (!ALLOWED_APP_PROTOCOLS.has(allowed.protocol)) {
      return false;
    }
    return target.origin === allowed.origin;
  } catch {
    return false;
  }
}

export function isSafeExternalUrl(targetUrl: string): boolean {
  try {
    const parsed = new URL(targetUrl);
    return SAFE_EXTERNAL_PROTOCOLS.has(parsed.protocol);
  } catch {
    return false;
  }
}

export function classifyDesktopNavigation(
  targetUrl: string,
  allowedOriginUrl: string,
): NavigationDecision {
  if (targetUrl === "about:blank") {
    return "allow";
  }
  if (isAllowedNavigationOrigin(targetUrl, allowedOriginUrl)) {
    return "allow";
  }
  if (isSafeExternalUrl(targetUrl)) {
    return "external";
  }
  return "block";
}

export interface GuardedWebContents {
  on(
    event: "will-navigate",
    listener: (event: { preventDefault: () => void }, url: string) => void,
  ): unknown;
  on(
    event: "will-attach-webview",
    listener: (event: { preventDefault: () => void }) => void,
  ): unknown;
  setWindowOpenHandler(
    handler: (details: { url: string }) => { action: "allow" | "deny" },
  ): void;
}

export interface NavigationGuardOptions {
  allowedOriginUrl: string;
  openExternal: (url: string) => Promise<void> | void;
  loadUrl?: (url: string) => void;
  onBlocked?: (url: string) => void;
}

export function attachNavigationGuards(
  contents: GuardedWebContents,
  options: NavigationGuardOptions,
): void {
  const { allowedOriginUrl, openExternal, loadUrl, onBlocked } = options;

  contents.on("will-navigate", (event, url) => {
    const decision = classifyDesktopNavigation(url, allowedOriginUrl);
    if (decision === "allow") {
      return;
    }
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
      if (url !== "about:blank" && loadUrl) {
        loadUrl(url);
      }
      return { action: "deny" };
    }
    if (decision === "external") {
      void openExternal(url);
      return { action: "deny" };
    }
    onBlocked?.(url);
    return { action: "deny" };
  });

  contents.on("will-attach-webview", (event) => {
    event.preventDefault();
  });
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function buildFallbackHtml(targetUrl: string, reason = ""): string {
  const safeUrl = escapeHtml(targetUrl);
  const safeReason = escapeHtml(reason.trim() || "Unable to reach the Community server.");

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline';" />
  <title>Dubai-io Community — Offline</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f3f6f8;
      --card: #ffffff;
      --ink: #15202b;
      --muted: #6a7784;
      --line: #e4ebf0;
      --accent: #128c9b;
      --accent-ink: #ffffff;
      --soft: #e7f5f7;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, "Segoe UI", -apple-system, BlinkMacSystemFont, sans-serif;
      padding: 24px;
    }
    .card {
      width: 100%;
      max-width: 480px;
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 28px;
    }
    .badge {
      display: inline-block;
      background: var(--soft);
      color: var(--accent);
      font-size: 12px;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 999px;
      margin-bottom: 14px;
    }
    h1 {
      margin: 0 0 8px;
      font-size: 20px;
      font-weight: 700;
    }
    p {
      margin: 0 0 14px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }
    .box {
      background: var(--bg);
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 13px;
      margin-bottom: 18px;
      word-break: break-word;
    }
    .box code {
      display: block;
      margin-top: 6px;
      font-family: ui-monospace, SFMono-Regular, Consolas, monospace;
      color: var(--ink);
    }
    button {
      appearance: none;
      border: 0;
      border-radius: 10px;
      background: var(--accent);
      color: var(--accent-ink);
      font-size: 14px;
      font-weight: 600;
      padding: 10px 18px;
      cursor: pointer;
    }
    button:hover { opacity: 0.92; }
  </style>
</head>
<body>
  <main class="card">
    <div class="badge">Dubai-io Community</div>
    <h1>Community server is unreachable</h1>
    <p>${safeReason}</p>
    <div class="box">
      Target URL: <strong>${safeUrl}</strong>
      <code>npm run dev -- -H 0.0.0.0 -p 3060</code>
    </div>
    <button id="retry-btn" type="button">Retry connection</button>
  </main>
  <script>
    document.getElementById("retry-btn")?.addEventListener("click", function () {
      if (window.communityDesktop && typeof window.communityDesktop.retry === "function") {
        window.communityDesktop.retry();
      } else {
        window.location.reload();
      }
    });
  </script>
</body>
</html>`;
}
