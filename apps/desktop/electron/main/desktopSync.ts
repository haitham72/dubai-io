import type { DesktopCredentials, TokenStore } from "./ownerHook";
import type { SyncRecord } from "./localReader";
import type { SyncSource } from "./continuousSync";

export type UploadKind = "browser" | "agent_sessions";

export interface DesktopSyncResult {
  signedIn: boolean;
  uploaded: number;
  errors: { source: string; message: string }[];
}

export interface DesktopSyncDeps {
  tokens: TokenStore;
  apiBaseUrl: string;
  enabledSources: SyncSource[];
  collect: (source: SyncSource) => Promise<SyncRecord[]>;
  fetchImpl?: typeof fetch;
  seen?: Set<string>;
}

const BATCH = 500;

export function uploadKindFor(source: SyncSource): UploadKind {
  return source === "chrome" || source === "edge" ? "browser" : "agent_sessions";
}

export function uploadErrorMessage(status: number): string {
  if (status === 401) return "Session expired. Sign in again.";
  if (status === 403 || status === 409) return "Turn on consent for this source in Connect first.";
  if (status >= 500) return "Server error. Nothing was imported.";
  return `Upload refused (${status}).`;
}

/**
 * Posts redacted local records through apps/api (the single gateway) as the signed-in owner.
 * Uses the owner-scoped, revocable memory-device-token; ids are stable so repeats add nothing.
 */
export async function runDesktopSync(deps: DesktopSyncDeps): Promise<DesktopSyncResult> {
  const result: DesktopSyncResult = { signedIn: false, uploaded: 0, errors: [] };
  if (!deps.tokens.authStatus().signedIn) {
    result.errors.push({ source: "all", message: "Sign in required" });
    return result;
  }
  result.signedIn = true;
  const fetchImpl = deps.fetchImpl ?? fetch;
  const base = deps.apiBaseUrl.replace(/\/$/, "");
  const seen = deps.seen ?? new Set<string>();
  let creds: DesktopCredentials | null = null;
  deps.tokens.withCredentials((c) => {
    creds = { ...c };
  });
  const c = creds as DesktopCredentials | null;
  if (!c) return result;

  for (const source of deps.enabledSources) {
    try {
      const records = (await deps.collect(source)).filter((r) => !seen.has(r.id));
      for (let i = 0; i < records.length; i += BATCH) {
        const batch = records.slice(i, i + BATCH);
        const res = await fetchImpl(`${base}/api/ingest/desktop/${uploadKindFor(source)}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
            "X-App-Session": c.sessionToken,
            "X-Memory-Device-Token": c.deviceToken,
          },
          body: JSON.stringify({ records: batch }),
        });
        if (!res.ok) {
          result.errors.push({ source, message: uploadErrorMessage(res.status) });
          break;
        }
        for (const r of batch) seen.add(r.id);
        result.uploaded += batch.length;
      }
    } catch (err) {
      result.errors.push({ source, message: err instanceof Error ? err.message : "Sync failed" });
    }
  }
  return result;
}
