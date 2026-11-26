// Typed REST + WebSocket client for /api/identity/* and /api/messenger/*.

export type AgeBand = "under_13" | "teen_13_17" | "adult_18_plus";
export type SocketConnectionState = "disconnected" | "connecting" | "connected" | "reconnecting";

export interface SupabaseUser {
  id: string;
  email?: string;
  user_metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface SupabaseSignInResult {
  accessToken: string;
  user: SupabaseUser | null;
}

export interface IdentitySession {
  sessionToken: string;
  userId: string;
  appId: string;
  ageBand: string | null;
  isMinorProtected?: boolean;
  expiresAt: number | string;
}

export interface IdentityMe {
  user_id: string;
  app_id: string;
  capabilities: string[];
  auth_mode: string;
  age_band: string | null;
  is_minor_protected: boolean;
  is_verified: boolean;
  session_id: string | null;
  session_version: number;
  expires_at: number | string | null;
}

export interface WsTicket {
  ticket: string;
  expires_at: number | string;
  session_id?: string;
  app_id?: string;
}

export interface ChatMessageRow {
  id: string;
  conversation_id: string;
  sender_id: string;
  client_msg_id: string;
  seq: number;
  body: string;
  created_at: string;
  edited_at: string | null;
  deleted: boolean;
}

export interface ConversationRow {
  id: string;
  kind?: "direct" | "group" | string;
  title?: string;
  member_ids?: string[];
  members?: string[];
  other_member_id?: string;
  last_message?: ChatMessageRow | null;
  preview?: string;
  updated_at?: string;
  created_at?: string;
  unread?: number;
}

export interface ClientOptions {
  apiBase?: string;
  fetchImpl?: typeof fetch;
}

export interface OpenIdentitySessionOptions extends ClientOptions {
  ageBand?: AgeBand;
  setCookie?: boolean;
}

export interface WsTicketOptions extends ClientOptions {
  origin?: string;
}

export interface WebSocketLike {
  readyState: number;
  send(data: string): void;
  close(code?: number, reason?: string): void;
  onopen: ((ev: unknown) => void) | null;
  onmessage: ((ev: { data: unknown }) => void) | null;
  onclose: ((ev: { code?: number; reason?: string }) => void) | null;
  onerror: ((ev: unknown) => void) | null;
}

export type WebSocketFactory = (url: string) => WebSocketLike;
export type WebSocketConstructor = new (url: string) => WebSocketLike;

export interface ChatCoreSocketOptions {
  sessionToken: string;
  apiBase?: string;
  wsBase?: string;
  origin?: string;
  fetchImpl?: typeof fetch;
  WebSocketImpl?: WebSocketFactory | WebSocketConstructor;
  minBackoffMs?: number;
  maxBackoffMs?: number;
  onStateChange?: (state: SocketConnectionState) => void;
  onReady?: (userId: string) => void;
  onReplay?: (messages: ChatMessageRow[]) => void;
  onAck?: (message: ChatMessageRow) => void;
  onMessage?: (message: ChatMessageRow) => void;
  onEdit?: (message: ChatMessageRow) => void;
  onDelete?: (message: ChatMessageRow | { id: string; conversation_id?: string }) => void;
  onError?: (code: string, raw?: unknown) => void;
}

export class ChatApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message?: string) {
    super(message || code || `HTTP ${status}`);
    this.name = "ChatApiError";
    this.status = status;
    this.code = code;
  }
}

function getEnv(key: string): string | undefined {
  const meta = import.meta as { env?: Record<string, string | undefined> };
  return meta?.env?.[key];
}

/** Resolve API base URL without hardcoding any port or tunnel host. */
export function resolveApiBase(apiBase?: string): string {
  const raw = apiBase !== undefined ? apiBase : (getEnv("VITE_MESSENGER_API_URL") ?? "");
  return raw.trim().replace(/\/+$/, "");
}

/** Derive the WebSocket endpoint URL from `apiBase` or `wsBase` (or current origin). */
export function resolveWsUrl(apiBase?: string, wsBase?: string): string {
  if (wsBase !== undefined && wsBase.trim()) {
    return `${wsBase.trim().replace(/\/+$/, "")}/api/messenger/ws`;
  }
  const base = resolveApiBase(apiBase);
  if (/^https:\/\//i.test(base)) {
    return `wss://${base.slice("https://".length)}/api/messenger/ws`;
  }
  if (/^http:\/\//i.test(base)) {
    return `ws://${base.slice("http://".length)}/api/messenger/ws`;
  }
  if (/^wss?:\/\//i.test(base)) {
    return `${base}/api/messenger/ws`;
  }
  const loc = typeof window !== "undefined" ? window.location : globalThis.location;
  if (loc?.host) {
    const proto = loc.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${loc.host}/api/messenger/ws`;
  }
  return "/api/messenger/ws";
}

/** Resolve Supabase auth URL and anon key with optional Vite env defaults. */
export function resolveSupabaseConfig(supabaseUrl?: string, anonKey?: string): { supabaseUrl: string; anonKey: string } {
  return {
    supabaseUrl: (supabaseUrl ?? getEnv("VITE_SUPABASE_URL") ?? "").trim().replace(/\/+$/, ""),
    anonKey: (anonKey ?? getEnv("VITE_SUPABASE_ANON_KEY") ?? "").trim(),
  };
}

function getFetch(fetchImpl?: typeof fetch): typeof fetch {
  return fetchImpl ?? globalThis.fetch;
}

async function parseError(res: Response): Promise<ChatApiError> {
  let text = "";
  try {
    text = await res.text();
  } catch {
    text = "";
  }
  let code = `http_${res.status}`;
  let message: string | undefined;
  if (text) {
    try {
      const data = JSON.parse(text) as {
        detail?: string | { code?: string; message?: string };
        code?: string;
        message?: string;
        error?: string;
        error_description?: string;
      };
      if (typeof data.detail === "string") {
        code = data.detail;
      } else if (data.detail && typeof data.detail === "object") {
        code = data.detail.code || code;
        message = data.detail.message;
      } else if (typeof data.code === "string") {
        code = data.code;
        message = data.message;
      } else if (typeof data.error === "string") {
        code = data.error;
        message = data.error_description || data.message;
      } else if (typeof data.message === "string") {
        message = data.message;
      }
    } catch {
      code = text.slice(0, 120);
    }
  }
  return new ChatApiError(res.status, code, message);
}

async function requestJson<T>(
  url: string,
  init: RequestInit,
  fetchImpl?: typeof fetch,
): Promise<T> {
  const res = await getFetch(fetchImpl)(url, init);
  if (!res.ok) {
    throw await parseError(res);
  }
  return (await res.json()) as T;
}

function sessionHeaders(sessionToken: string, hasBody = false): Record<string, string> {
  const headers: Record<string, string> = { "X-App-Session": sessionToken };
  if (hasBody) headers["Content-Type"] = "application/json";
  return headers;
}

/** Authenticate against Supabase GoTrue password grant. */
export async function signInSupabasePassword(
  supabaseUrl: string | undefined,
  anonKey: string | undefined,
  email: string,
  password: string,
  fetchImpl?: typeof fetch,
): Promise<SupabaseSignInResult> {
  const cfg = resolveSupabaseConfig(supabaseUrl, anonKey);
  if (!cfg.supabaseUrl || !cfg.anonKey) {
    throw new ChatApiError(400, "missing_supabase_config", "Supabase URL and anon key are required");
  }
  const data = await requestJson<{ access_token?: string; user?: SupabaseUser | null }>(
    `${cfg.supabaseUrl}/auth/v1/token?grant_type=password`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        apikey: cfg.anonKey,
        Authorization: `Bearer ${cfg.anonKey}`,
      },
      body: JSON.stringify({ email, password }),
    },
    fetchImpl,
  );
  if (!data.access_token) {
    throw new ChatApiError(500, "missing_access_token", "Supabase auth did not return an access_token");
  }
  return { accessToken: data.access_token, user: data.user ?? null };
}

/** Mint a Messenger identity session, ensure adult_18_plus age band if unset, and verify /api/identity/me. */
export async function openIdentitySession(
  jwt: string,
  opts: OpenIdentitySessionOptions = {},
): Promise<IdentitySession> {
  const base = resolveApiBase(opts.apiBase);
  const setCookie = opts.setCookie ?? false;

  const sessionRes = await requestJson<{
    session_token: string;
    user_id: string;
    app_id: string;
    age_band: string | null;
    expires_at: number | string;
  }>(
    `${base}/api/identity/sessions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${jwt}`,
      },
      body: JSON.stringify({ app_id: "messenger", set_cookie: setCookie }),
    },
    opts.fetchImpl,
  );

  const sessionToken = sessionRes.session_token;
  if (sessionRes.age_band !== "adult_18_plus" && (!opts.ageBand || sessionRes.age_band !== opts.ageBand)) {
    const targetBand: AgeBand = opts.ageBand ?? "adult_18_plus";
    await requestJson<{ age_band: string }>(
      `${base}/api/identity/age-band`,
      {
        method: "POST",
        headers: sessionHeaders(sessionToken, true),
        body: JSON.stringify({ age_band: targetBand }),
      },
      opts.fetchImpl,
    );
  }

  const me = await getIdentityMe(sessionToken, { apiBase: base, fetchImpl: opts.fetchImpl });
  return {
    sessionToken,
    userId: me.user_id || sessionRes.user_id,
    appId: me.app_id || sessionRes.app_id || "messenger",
    ageBand: me.age_band ?? sessionRes.age_band ?? null,
    isMinorProtected: me.is_minor_protected,
    expiresAt: me.expires_at ?? sessionRes.expires_at,
  };
}

/** Where the Google sign-in starts: apps/api (:8000) holds the Google client; this app only redeems the code. */
export function googleSignInStartUrl(returnTo: string, dubaiApi?: string): string {
  const configured = (dubaiApi !== undefined ? dubaiApi : getEnv("VITE_DUBAI_API_URL"))?.trim();
  let base = configured ? configured.replace(/\/+$/, "") : "";
  if (!base) {
    const loc = typeof window !== "undefined" ? window.location : globalThis.location;
    if (loc?.hostname && loc.hostname !== "localhost" && loc.hostname !== "127.0.0.1") {
      const proto = loc.protocol === "https:" ? "https:" : "http:";
      base = `${proto}//${loc.hostname}:8000`;
    } else {
      base = "http://localhost:8000";
    }
  }
  const q = new URLSearchParams({ client: "web", return_to: returnTo });
  return `${base}/api/identity/google/start?${q.toString()}`;
}

/** Redeem the one-time auth_code (from the Google redirect) at THIS app's API for a messenger session of the same user. */
export async function exchangeGoogleAuthCode(
  authCode: string,
  opts: ClientOptions = {},
): Promise<{ session_token: string; user_id: string; display_name?: string }> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson(
    `${base}/api/identity/google/exchange`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auth_code: authCode, app_id: "messenger", device_label: "Messenger web" }),
    },
    opts.fetchImpl,
  );
}

/** Fetch the current identity session principal via GET /api/identity/me. */
export async function getIdentityMe(
  sessionToken: string,
  opts: ClientOptions = {},
): Promise<IdentityMe> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<IdentityMe>(
    `${base}/api/identity/me`,
    {
      method: "GET",
      headers: sessionHeaders(sessionToken),
    },
    opts.fetchImpl,
  );
}

/** Mint a single-use Origin-bound WebSocket ticket via POST /api/identity/ws-ticket. */
export async function issueWsTicket(
  sessionToken: string,
  opts: WsTicketOptions = {},
): Promise<WsTicket> {
  const base = resolveApiBase(opts.apiBase);
  const headers = sessionHeaders(sessionToken, true);
  const body: Record<string, unknown> = { app_id: "messenger" };
  if (opts.origin) {
    headers["Origin"] = opts.origin;
    body.origin = opts.origin;
  }
  return requestJson<WsTicket>(
    `${base}/api/identity/ws-ticket`,
    {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    },
    opts.fetchImpl,
  );
}

/** List authenticated user's conversations via GET /api/messenger/conversations. */
export async function listConversations(
  sessionToken: string,
  opts: ClientOptions = {},
): Promise<ConversationRow[]> {
  const base = resolveApiBase(opts.apiBase);
  const data = await requestJson<ConversationRow[] | { conversations?: ConversationRow[] }>(
    `${base}/api/messenger/conversations`,
    {
      method: "GET",
      headers: sessionHeaders(sessionToken),
    },
    opts.fetchImpl,
  );
  return Array.isArray(data) ? data : (data.conversations ?? []);
}

/** Create a direct or group conversation via POST /api/messenger/conversations. */
export async function createConversation(
  sessionToken: string,
  input: { memberIds: string[]; kind?: "direct" | "group"; title?: string },
  opts: ClientOptions = {},
): Promise<{ id: string }> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<{ id: string }>(
    `${base}/api/messenger/conversations`,
    {
      method: "POST",
      headers: sessionHeaders(sessionToken, true),
      body: JSON.stringify({
        member_ids: input.memberIds,
        kind: input.kind ?? "direct",
        title: input.title ?? "",
      }),
    },
    opts.fetchImpl,
  );
}

/** Fetch conversation messages after `afterSeq` via GET /api/messenger/conversations/:id/messages. */
export async function fetchMessages(
  sessionToken: string,
  convId: string,
  afterSeq = 0,
  opts: ClientOptions = {},
): Promise<ChatMessageRow[]> {
  const base = resolveApiBase(opts.apiBase);
  const data = await requestJson<{ messages?: ChatMessageRow[] }>(
    `${base}/api/messenger/conversations/${encodeURIComponent(convId)}/messages?after=${encodeURIComponent(String(afterSeq))}`,
    {
      method: "GET",
      headers: sessionHeaders(sessionToken),
    },
    opts.fetchImpl,
  );
  return data.messages ?? [];
}

/** Send a message idempotently over REST via POST /api/messenger/conversations/:id/messages. */
export async function sendMessageRest(
  sessionToken: string,
  convId: string,
  clientMsgId: string,
  text: string,
  opts: ClientOptions = {},
): Promise<ChatMessageRow> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<ChatMessageRow>(
    `${base}/api/messenger/conversations/${encodeURIComponent(convId)}/messages`,
    {
      method: "POST",
      headers: sessionHeaders(sessionToken, true),
      body: JSON.stringify({ client_msg_id: clientMsgId, text }),
    },
    opts.fetchImpl,
  );
}

/** Edit an owned message via POST /api/messenger/conversations/:id/messages/:messageId/edit. */
export async function editMessageRest(
  sessionToken: string,
  convId: string,
  messageId: string,
  text: string,
  opts: ClientOptions = {},
): Promise<ChatMessageRow> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<ChatMessageRow>(
    `${base}/api/messenger/conversations/${encodeURIComponent(convId)}/messages/${encodeURIComponent(messageId)}/edit`,
    {
      method: "POST",
      headers: sessionHeaders(sessionToken, true),
      body: JSON.stringify({ text }),
    },
    opts.fetchImpl,
  );
}

/** Delete an owned message via POST /api/messenger/conversations/:id/messages/:messageId/delete. */
export async function deleteMessageRest(
  sessionToken: string,
  convId: string,
  messageId: string,
  opts: ClientOptions = {},
): Promise<ChatMessageRow> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<ChatMessageRow>(
    `${base}/api/messenger/conversations/${encodeURIComponent(convId)}/messages/${encodeURIComponent(messageId)}/delete`,
    {
      method: "POST",
      headers: sessionHeaders(sessionToken),
    },
    opts.fetchImpl,
  );
}

/** Send a delivery/read receipt via POST /api/messenger/conversations/:id/receipts. */
export async function sendReceiptRest(
  sessionToken: string,
  convId: string,
  messageId: string,
  kind: "delivered" | "read",
  opts: ClientOptions = {},
): Promise<{ ok: boolean }> {
  const base = resolveApiBase(opts.apiBase);
  return requestJson<{ ok: boolean }>(
    `${base}/api/messenger/conversations/${encodeURIComponent(convId)}/receipts`,
    {
      method: "POST",
      headers: sessionHeaders(sessionToken, true),
      body: JSON.stringify({ message_id: messageId, kind }),
    },
    opts.fetchImpl,
  );
}

function createSocketInstance(
  url: string,
  impl?: WebSocketFactory | WebSocketConstructor,
): WebSocketLike {
  if (impl) {
    try {
      return new (impl as WebSocketConstructor)(url);
    } catch {
      return (impl as WebSocketFactory)(url);
    }
  }
  return new WebSocket(url) as unknown as WebSocketLike;
}

/** Manages the Origin-bound WebSocket connection with single-use tickets, replay, and bounded backoff. */
export class ChatCoreSocket {
  private readonly sessionToken: string;
  private readonly apiBase: string;
  private readonly wsBase?: string;
  private readonly origin?: string;
  private readonly fetchImpl?: typeof fetch;
  private readonly WebSocketImpl?: WebSocketFactory | WebSocketConstructor;
  private readonly minBackoffMs: number;
  private readonly maxBackoffMs: number;
  private readonly subscriptions = new Map<string, number>();

  private ws: WebSocketLike | null = null;
  private manuallyClosed = false;
  private connecting = false;
  private ready = false;
  private attempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;

  private readonly onStateChange?: ChatCoreSocketOptions["onStateChange"];
  private readonly onReady?: ChatCoreSocketOptions["onReady"];
  private readonly onReplay?: ChatCoreSocketOptions["onReplay"];
  private readonly onAck?: ChatCoreSocketOptions["onAck"];
  private readonly onMessage?: ChatCoreSocketOptions["onMessage"];
  private readonly onEdit?: ChatCoreSocketOptions["onEdit"];
  private readonly onDelete?: ChatCoreSocketOptions["onDelete"];
  private readonly onError?: ChatCoreSocketOptions["onError"];

  constructor(opts: ChatCoreSocketOptions) {
    this.sessionToken = opts.sessionToken;
    this.apiBase = resolveApiBase(opts.apiBase);
    this.wsBase = opts.wsBase;
    this.origin = opts.origin;
    this.fetchImpl = opts.fetchImpl;
    this.WebSocketImpl = opts.WebSocketImpl;
    this.minBackoffMs = opts.minBackoffMs ?? 250;
    this.maxBackoffMs = opts.maxBackoffMs ?? 8000;
    this.onStateChange = opts.onStateChange;
    this.onReady = opts.onReady;
    this.onReplay = opts.onReplay;
    this.onAck = opts.onAck;
    this.onMessage = opts.onMessage;
    this.onEdit = opts.onEdit;
    this.onDelete = opts.onDelete;
    this.onError = opts.onError;
  }

  /** Open the WebSocket connection (mints a fresh single-use ws-ticket). */
  connect(): void {
    this.manuallyClosed = false;
    if (this.connecting || this.isConnected()) return;
    if (this.reconnectTimer !== null) {
      globalThis.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    void this.openSocket(false);
  }

  /** Close the WebSocket and stop reconnecting. */
  close(): void {
    this.manuallyClosed = true;
    this.connecting = false;
    this.ready = false;
    if (this.reconnectTimer !== null) {
      globalThis.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    const current = this.ws;
    this.ws = null;
    if (current) {
      current.onopen = null;
      current.onmessage = null;
      current.onclose = null;
      current.onerror = null;
      try {
        current.close();
      } catch {
        /* ignore close errors */
      }
    }
    this.onStateChange?.("disconnected");
  }

  /** True when the underlying WebSocket is open. */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === 1;
  }

  /** Subscribe to a conversation and track its last seen sequence number for replay. */
  subscribe(convId: string, lastSeq = 0): void {
    if (!convId) return;
    const prev = this.subscriptions.get(convId) ?? 0;
    const nextSeq = Math.max(prev, lastSeq);
    this.subscriptions.set(convId, nextSeq);
    if (this.isConnected() && this.ready) {
      this.sendRaw({ op: "subscribe", conversation_id: convId, last_seq: nextSeq });
    }
  }

  /** Update the tracked sequence high-water mark for a conversation. */
  updateLastSeq(convId: string, seq: number): void {
    if (!convId || !Number.isFinite(seq)) return;
    const prev = this.subscriptions.get(convId) ?? 0;
    if (seq > prev) this.subscriptions.set(convId, seq);
  }

  /** Send a chat message frame over the live WebSocket; returns false if offline. */
  send(convId: string, clientMsgId: string, text: string): boolean {
    if (!this.isConnected()) return false;
    return this.sendRaw({
      op: "send",
      conversation_id: convId,
      client_msg_id: clientMsgId,
      text,
    });
  }

  private sendRaw(payload: Record<string, unknown>): boolean {
    if (!this.ws || this.ws.readyState !== 1) return false;
    this.ws.send(JSON.stringify(payload));
    return true;
  }

  private trackMessageSeq(row?: ChatMessageRow | null): void {
    if (row && row.conversation_id && typeof row.seq === "number") {
      this.updateLastSeq(row.conversation_id, row.seq);
    }
  }

  private async openSocket(isReconnect: boolean): Promise<void> {
    if (this.manuallyClosed || this.connecting) return;
    this.connecting = true;
    this.ready = false;
    this.onStateChange?.(isReconnect ? "reconnecting" : "connecting");

    try {
      const ticketRes = await issueWsTicket(this.sessionToken, {
        apiBase: this.apiBase,
        origin: this.origin,
        fetchImpl: this.fetchImpl,
      });
      if (this.manuallyClosed) {
        this.connecting = false;
        return;
      }

      const wsEndpoint = resolveWsUrl(this.apiBase, this.wsBase);
      const url = `${wsEndpoint}?ticket=${encodeURIComponent(ticketRes.ticket)}`;
      const ws = createSocketInstance(url, this.WebSocketImpl);
      this.ws = ws;

      ws.onopen = () => {
        if (this.ws !== ws || this.manuallyClosed) return;
        this.connecting = false;
        this.attempt = 0;
        this.onStateChange?.("connected");
      };

      ws.onmessage = (ev) => {
        if (this.ws !== ws || this.manuallyClosed) return;
        this.handleFrame(ev.data);
      };

      ws.onerror = () => {
        if (this.ws !== ws || this.manuallyClosed) return;
        this.onError?.("ws_error");
      };

      ws.onclose = () => {
        if (this.ws !== ws) return;
        this.ws = null;
        this.connecting = false;
        this.ready = false;
        if (this.manuallyClosed) {
          this.onStateChange?.("disconnected");
          return;
        }
        this.scheduleReconnect();
      };
    } catch (err) {
      this.ws = null;
      this.connecting = false;
      this.ready = false;
      const code = err instanceof ChatApiError ? err.code : "ws_connect_failed";
      this.onError?.(code, err);
      if (!this.manuallyClosed) {
        this.scheduleReconnect();
      }
    }
  }

  private scheduleReconnect(): void {
    if (this.manuallyClosed || this.reconnectTimer !== null) return;
    const delay = Math.min(this.maxBackoffMs, this.minBackoffMs * 2 ** Math.max(0, this.attempt));
    this.attempt += 1;
    this.onStateChange?.("reconnecting");
    this.reconnectTimer = globalThis.setTimeout(() => {
      this.reconnectTimer = null;
      if (!this.manuallyClosed) {
        void this.openSocket(true);
      }
    }, delay);
  }

  private handleFrame(raw: unknown): void {
    let data: Record<string, unknown>;
    try {
      data = typeof raw === "string" ? (JSON.parse(raw) as Record<string, unknown>) : (raw as Record<string, unknown>);
    } catch {
      return;
    }
    const op = String(data.op || "");
    if (op === "ready") {
      this.ready = true;
      for (const [convId, lastSeq] of this.subscriptions.entries()) {
        this.sendRaw({ op: "subscribe", conversation_id: convId, last_seq: lastSeq });
      }
      this.onReady?.(String(data.user_id || ""));
      return;
    }
    if (op === "replay") {
      const rows = Array.isArray(data.messages) ? (data.messages as ChatMessageRow[]) : [];
      for (const row of rows) this.trackMessageSeq(row);
      this.onReplay?.(rows);
      return;
    }
    if (op === "ack") {
      const msg = data.message as ChatMessageRow | undefined;
      if (msg) {
        this.trackMessageSeq(msg);
        this.onAck?.(msg);
      }
      return;
    }
    if (op === "message") {
      const msg = (data.message ?? data) as ChatMessageRow;
      this.trackMessageSeq(msg);
      this.onMessage?.(msg);
      return;
    }
    if (op === "edit") {
      const msg = (data.message ?? data) as ChatMessageRow;
      this.trackMessageSeq(msg);
      this.onEdit?.(msg);
      return;
    }
    if (op === "delete") {
      const msg = (data.message ?? data) as ChatMessageRow | { id: string; conversation_id?: string };
      if ("seq" in msg && typeof msg.seq === "number") this.trackMessageSeq(msg);
      this.onDelete?.(msg);
      return;
    }
    if (op === "error") {
      this.onError?.(String(data.code || "ws_error"), data);
    }
  }
}
