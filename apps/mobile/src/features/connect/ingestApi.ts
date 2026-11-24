/** E3 ingest client: consent, Google source connect/pull, uploads and status. Always via apps/api with X-App-Session. */
import { Platform } from "react-native";
import type { Fetcher } from "../vault/vaultApi";

export type GoogleSource = "gmail" | "calendar" | "youtube";
export type IngestSource = GoogleSource | "takeout" | "whatsapp";

export const GOOGLE_SOURCES: { id: GoogleSource; label: string }[] = [
  { id: "gmail", label: "Gmail" },
  { id: "calendar", label: "Calendar" },
  { id: "youtube", label: "YouTube" },
];

export interface SourceStatus {
  enabled?: boolean;
  connected?: boolean;
  last_pull?: unknown;
  records?: unknown;
  queued?: unknown;
  done?: unknown;
  failed?: unknown;
}
export interface IngestStatus {
  sources: Record<string, SourceStatus>;
  onboarding_percent?: unknown;
  runner?: string | null;
  model?: string | null;
}

const defaultFetcher: Fetcher = (url, init) => fetch(url, init);
const base = (u: string) => u.replace(/\/$/, "");
const headers = (token: string, json = true): Record<string, string> => ({
  Accept: "application/json",
  "X-App-Session": token,
  ...(json ? { "Content-Type": "application/json" } : {}),
});

/** Receipt numbers arrive wrapped as {value, provenance, as_of}; unwrap for display. */
export function receiptValue(v: unknown): number | null {
  if (typeof v === "number") return v;
  if (v && typeof v === "object" && typeof (v as { value?: unknown }).value === "number") {
    return (v as { value: number }).value;
  }
  return null;
}

export function ingestErrorMessage(status: number): string {
  if (status === 401) return "Session expired. Sign in again.";
  if (status === 403 || status === 409) return "Turn on consent for this source first.";
  if (status === 413) return "File is too large.";
  if (status === 400 || status === 422) return "The server rejected this file.";
  if (status >= 500) return "Server error. Nothing was imported.";
  return `Request failed (${status}). Nothing was imported.`;
}

export async function setSourceConsent(
  apiBaseUrl: string, token: string, source: IngestSource, enabled: boolean, fetcher: Fetcher = defaultFetcher,
): Promise<boolean> {
  try {
    const res = await fetcher(`${base(apiBaseUrl)}/api/ingest/consent/${source}`, {
      method: "PUT", headers: headers(token), body: JSON.stringify({ enabled }),
    });
    return res.ok;
  } catch { return false; }
}

export async function getIngestStatus(
  apiBaseUrl: string, token: string, fetcher: Fetcher = defaultFetcher,
): Promise<IngestStatus | null> {
  try {
    const res = await fetcher(`${base(apiBaseUrl)}/api/ingest/status`, { method: "GET", headers: headers(token) });
    if (!res.ok) return null;
    const body = (await res.json()) as Partial<IngestStatus>;
    return { ...body, sources: body.sources ?? {} } as IngestStatus;
  } catch { return null; }
}

/** Returns the one-time Google consent URL (server-built; no client secret ever reaches the app). */
export async function startSourceConnect(
  apiBaseUrl: string, token: string, source: GoogleSource, fetcher: Fetcher = defaultFetcher,
): Promise<{ url: string | null; error: string | null }> {
  try {
    const res = await fetcher(`${base(apiBaseUrl)}/api/ingest/google/${source}/connect`, {
      method: "POST", headers: headers(token), body: "{}",
    });
    if (!res.ok) return { url: null, error: ingestErrorMessage(res.status) };
    const body = (await res.json()) as { authorization_url?: string };
    return body.authorization_url
      ? { url: body.authorization_url, error: null }
      : { url: null, error: "Server returned no consent URL." };
  } catch { return { url: null, error: "Could not reach the API server." }; }
}

export async function pullSource(
  apiBaseUrl: string, token: string, source: GoogleSource, fetcher: Fetcher = defaultFetcher,
): Promise<{ added: number | null; error: string | null }> {
  try {
    const res = await fetcher(`${base(apiBaseUrl)}/api/ingest/google/${source}/pull`, {
      method: "POST", headers: headers(token), body: "{}",
    });
    if (!res.ok) return { added: null, error: ingestErrorMessage(res.status) };
    const body = (await res.json()) as { records_added?: unknown };
    return { added: receiptValue(body.records_added), error: null };
  } catch { return { added: null, error: "Could not reach the API server." }; }
}

export async function uploadIngestFile(
  apiBaseUrl: string, token: string | null | undefined, kind: "takeout" | "whatsapp",
  asset: { name: string; uri: string; mimeType?: string | null; file?: Blob },
  fetcher: Fetcher = defaultFetcher,
): Promise<{ ok: boolean; added: number | null; message: string }> {
  if (!token) return { ok: false, added: null, message: "Sign in first." };
  try {
    const form = new FormData();
    if (Platform.OS === "web" && asset.file) {
      form.append("file", asset.file, asset.name);
    } else {
      form.append("file", { uri: asset.uri, name: asset.name, type: asset.mimeType ?? "application/octet-stream" } as unknown as Blob);
    }
    const res = await fetcher(`${base(apiBaseUrl)}/api/ingest/${kind}`, {
      method: "POST", headers: headers(token, false), body: form,
    });
    if (!res.ok) return { ok: false, added: null, message: ingestErrorMessage(res.status) };
    const body = (await res.json()) as { records_added?: unknown };
    return { ok: true, added: receiptValue(body.records_added), message: "" };
  } catch { return { ok: false, added: null, message: "Upload failed. Server unreachable." }; }
}
