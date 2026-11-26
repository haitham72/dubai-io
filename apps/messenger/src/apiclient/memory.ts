// "Save to memory" API (apps/api /api/messenger/*). Every value shown in the UI comes from these responses.
import { resolveApiBase, type ClientOptions } from "./chatCore";

export interface MemoryField { name: string; value: string }
export interface MemoryBlocker { code: string; message: string }
export interface MemoryPreview {
  offerable: boolean;
  can_save_now: boolean;
  blockers: MemoryBlocker[];
  fields: MemoryField[];
  provenance: string | null;
  as_of: string;
}
export interface SaveResult { saved: boolean; status: string; held_back: boolean; record_id: string; as_of: string }
export interface SavedItem {
  record_id: string; lowered?: boolean; conversation_id: string; text: string | null; saved_at: string;
  provenance: string | null; written_by_you: boolean;
}
export interface MemoryState { enabled: boolean; as_of: string; items: SavedItem[] }
export interface LowerResult { lowered: boolean; records: number; as_of: string }

export class MemoryApiError extends Error {
  constructor(readonly status: number, readonly code: string, message: string, readonly heldBack = false) {
    super(message);
  }
}

export interface MemoryClient {
  preview(conversationId: string, messageId: string): Promise<MemoryPreview>;
  save(conversationId: string, messageId: string): Promise<SaveResult>;
  state(): Promise<MemoryState>;
  setConsent(enabled: boolean): Promise<{ enabled: boolean; as_of: string }>;
  setChatMode(conversationId: string, mode: "off" | "save"): Promise<{ mode: string }>;
  setLowered(recordId: string, lower: boolean): Promise<LowerResult>;
}

export function createMemoryClient(sessionToken: string, opts: ClientOptions = {}): MemoryClient {
  const base = resolveApiBase(opts.apiBase);
  const call = async <T,>(method: string, path: string, body?: unknown): Promise<T> => {
    const f = opts.fetchImpl ?? fetch;
    let res: Response;
    try {
      res = await f(`${base}${path}`, {
        method,
        headers: { "X-App-Session": sessionToken, ...(body !== undefined ? { "Content-Type": "application/json" } : {}) },
        ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      });
    } catch {
      throw new MemoryApiError(0, "unreachable", "Messenger service unavailable");
    }
    if (!res.ok) {
      let code = `http_${res.status}`, message = `Request failed (${res.status})`, held = false;
      try {
        const d = (await res.json())?.detail;
        if (typeof d === "string") message = d;
        else if (d) { code = d.code ?? code; message = d.message ?? message; held = !!d.held_back; }
      } catch { /* keep defaults */ }
      throw new MemoryApiError(res.status, code, message, held);
    }
    return (await res.json()) as T;
  };
  const conv = (c: string, m: string) => `/api/messenger/conversations/${encodeURIComponent(c)}/messages/${encodeURIComponent(m)}/memory`;
  return {
    preview: (c, m) => call("GET", `${conv(c, m)}-preview`),
    save: (c, m) => call("POST", conv(c, m), { confirmed: true }),
    state: () => call("GET", "/api/messenger/memory"),
    setConsent: (enabled) => call("PUT", "/api/messenger/memory/consent", { enabled }),
    setChatMode: (c, mode) => call("PUT", `/api/messenger/conversations/${encodeURIComponent(c)}/memory-mode`, { mode }),
    setLowered: (recordId, lower) => call("POST", "/api/messenger/memory/lower", { record_id: recordId, lower }),
  };
}
