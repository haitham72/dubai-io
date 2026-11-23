// Global app store — owned by the lead session. The glue between every session's work.
// Read with useStore(s => s.x); change only through the `actions` below.
import { createStore } from "./storeFactory";
import type { EmailDraft, CalendarEvent, Chat, MessageBody, Message, MessengerTask, ModalId, QuickCard, ScreenId } from "./types";
import { seedMessages } from "./chats/data";
import { seedTasks } from "./updates/seed";
import { videoSeedTasks } from "./videos";
import { applyFrost, loadFrost } from "./frost";
import {
  ChatApiError,
  ChatCoreSocket,
  createConversation as apiCreateConversation,
  deleteMessageRest,
  editMessageRest,
  fetchMessages,
  getIdentityMe,
  listConversations,
  openIdentitySession,
  resolveApiBase,
  sendMessageRest,
  signInSupabasePassword,
  type AgeBand,
  type ChatCoreSocketOptions,
  type ChatMessageRow,
  type ConversationRow,
  type IdentitySession,
  type SocketConnectionState,
} from "./apiclient/chatCore";

if (typeof document !== "undefined") {
  applyFrost(loadFrost());
}

export type AppMode = "real" | "demo";
export type ConnectionState = SocketConnectionState;

export interface AuthState {
  status: "signed_out" | "signing_in" | "signed_in" | "error";
  userId: string | null;
  displayName: string;
  sessionToken: string | null;
  error?: string;
}

export interface OutboxItem {
  id: string;
  chatId: string;
  clientMsgId: string;
  text: string;
  replyTo?: Message["replyTo"];
  status: "queued" | "sending" | "failed";
}

export interface TransportOptions {
  apiBase?: string;
  wsBase?: string;
  origin?: string;
  fetchImpl?: typeof fetch;
  WebSocketImpl?: ChatCoreSocketOptions["WebSocketImpl"];
}

export interface SignInWithJwtOptions extends TransportOptions {
  displayName?: string;
  ageBand?: AgeBand;
}

export interface SignInWithPasswordOptions extends SignInWithJwtOptions {
  supabaseUrl?: string;
  anonKey?: string;
  email: string;
  password: string;
}

interface PersistedSession {
  sessionToken: string;
  userId: string;
  displayName: string;
  apiBase: string;
  activeChatId: string;
}

interface State {
  screen: ScreenId;
  modal: ModalId;
  /** Flight results or a mail draft shown as a card over the current screen (rendered by src/quick). */
  quick: QuickCard;
  activeChatId: string;
  chatRequest: number;
  messageFocus: { id: string; request: number } | null;
  messages: Message[];
  /** Chats created in this session (e.g. a group from an @messenger plan); shown above the seeded ones. */
  extraChats: Chat[];
  tasks: MessengerTask[];
  /** Bumped by openUpdates(): the desktop tray and the phone sheet open when it changes (voice, shortcuts). */
  updatesRequest: number;
  /** Mail drafts (yours from Compose, or Messenger's — e.g. the leave email from a trip plan). Never sent by themselves. */
  mailDrafts: EmailDraft[];
  /** An email to open in Compose (voice "email Rashid that …"); Mail opens it, the person presses Send. */
  mailCompose: { to: string; subject: string; body: string } | null;
  events: CalendarEvent[];
  theme: Theme;
  wallpaper: Wallpaper;
  /* Real-mode & auth/socket state */
  mode: AppMode;
  auth: AuthState;
  connection: ConnectionState;
  conversations: Chat[];
  lastError: string | null;
  outbox: OutboxItem[];
}

const EVENTS_KEY = "messenger.events";
const DRAFTS_KEY = "messenger.drafts";
const SESSION_KEY = "messenger.session";

function safeStorage(kind: "local" | "session"): Storage | null {
  try {
    if (kind === "local" && typeof localStorage !== "undefined") return localStorage;
    if (kind === "session" && typeof sessionStorage !== "undefined") return sessionStorage;
  } catch {
    /* storage unavailable */
  }
  return null;
}

function detectInitialMode(): AppMode {
  try {
    const search =
      typeof window !== "undefined"
        ? window.location?.search
        : typeof globalThis.location !== "undefined"
          ? globalThis.location?.search
          : "";
    if (search && new URLSearchParams(search).get("demo") === "1") {
      return "demo";
    }
  } catch {
    /* ignore invalid search */
  }
  return "real";
}

function loadDrafts(): EmailDraft[] {
  try {
    const raw = safeStorage("local")?.getItem(DRAFTS_KEY);
    return raw ? (JSON.parse(raw) as EmailDraft[]) : [];
  } catch {
    return [];
  }
}

/* Theme: "system" follows the OS live. Applied as <html data-theme="light|dark"> (tokens.css). */
export type Theme = "light" | "dark" | "system";
const THEME_KEY = "messenger.theme";
const darkQuery =
  typeof window !== "undefined" && typeof window.matchMedia === "function"
    ? window.matchMedia("(prefers-color-scheme: dark)")
    : null;

function loadTheme(): Theme {
  try {
    const v = safeStorage("local")?.getItem(THEME_KEY);
    return v === "dark" || v === "system" ? v : "light";
  } catch {
    return "light";
  }
}
function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const dark = theme === "dark" || (theme === "system" && (darkQuery?.matches ?? false));
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

/* Mac desktop wallpaper id. Applied as data-wallpaper on the desktop root (tokens.css). */
export type Wallpaper = "aurora" | "desert" | "ocean" | "mono";
const WALLPAPER_KEY = "messenger.wallpaper";
function loadWallpaper(): Wallpaper {
  try {
    const v = safeStorage("local")?.getItem(WALLPAPER_KEY);
    return v === "desert" || v === "ocean" || v === "mono" ? v : "aurora";
  } catch {
    return "aurora";
  }
}

function loadEvents(): CalendarEvent[] {
  try {
    const raw = safeStorage("local")?.getItem(EVENTS_KEY);
    return raw ? (JSON.parse(raw) as CalendarEvent[]) : [];
  } catch {
    return [];
  }
}

function saveSessionStorage(data: PersistedSession | null) {
  const storage = safeStorage("session");
  if (!storage) return;
  try {
    if (!data) storage.removeItem(SESSION_KEY);
    else storage.setItem(SESSION_KEY, JSON.stringify(data));
  } catch {
    /* storage unavailable */
  }
}

function loadSessionStorage(): PersistedSession | null {
  const storage = safeStorage("session");
  if (!storage) return null;
  try {
    const raw = storage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PersistedSession>;
    if (!parsed.sessionToken || !parsed.userId) return null;
    return {
      sessionToken: parsed.sessionToken,
      userId: parsed.userId,
      displayName: parsed.displayName || parsed.userId,
      apiBase: parsed.apiBase ?? "",
      activeChatId: parsed.activeChatId ?? "",
    };
  } catch {
    return null;
  }
}

/** Persistence + theme side effects that used to live inside `set`. Runs after every merge. */
function persist(s: State, patch: Partial<State>) {
  const local = safeStorage("local");
  if (patch.mailDrafts && local) {
    try { local.setItem(DRAFTS_KEY, JSON.stringify(s.mailDrafts)); } catch { /* storage unavailable */ }
  }
  if (patch.events && local) {
    try { local.setItem(EVENTS_KEY, JSON.stringify(s.events)); } catch { /* storage unavailable */ }
  }
  if (patch.theme) {
    applyTheme(s.theme);
    if (local) {
      try { local.setItem(THEME_KEY, s.theme); } catch { /* storage unavailable */ }
    }
  }
  if (patch.wallpaper && local) {
    try { local.setItem(WALLPAPER_KEY, s.wallpaper); } catch { /* storage unavailable */ }
  }
}

const initialMode = detectInitialMode();

const store = createStore<State>(
  {
    screen: "chats",
    modal: null,
    quick: null,
    activeChatId: initialMode === "demo" ? "arif" : "",
    chatRequest: 0,
    messageFocus: null,
    updatesRequest: 0,
    mailDrafts: loadDrafts(),
    mailCompose: null,
    messages: initialMode === "demo" ? seedMessages : [],
    extraChats: [],
    tasks: [...videoSeedTasks(), ...seedTasks],
    events: loadEvents(),
    theme: loadTheme(),
    wallpaper: loadWallpaper(),
    mode: initialMode,
    auth: {
      status: "signed_out",
      userId: null,
      displayName: "",
      sessionToken: null,
    },
    connection: "disconnected",
    conversations: [],
    lastError: null,
    outbox: [],
  },
  persist,
);

export const getState = store.get;
const set = store.set;

/** Subscribe outside React (e.g. to persist tasks). Returns the unsubscribe function. */
export const subscribe = store.subscribe;

export function useStore<T>(select: (s: State) => T): T {
  return store.use(select);
}

applyTheme(getState().theme);
darkQuery?.addEventListener?.("change", () => {
  if (getState().theme === "system") applyTheme("system");
});

const uid = () => Math.random().toString(36).slice(2, 10);
const nowTime = () => new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

/* ---------- real-mode transport & sync helpers ---------- */
let socket: ChatCoreSocket | null = null;
let flushingOutbox = false;
const convMaxSeq = new Map<string, number>();
let transport: {
  apiBase: string;
  wsBase?: string;
  origin?: string;
  fetchImpl?: typeof fetch;
  WebSocketImpl?: ChatCoreSocketOptions["WebSocketImpl"];
} = {
  apiBase: resolveApiBase(),
};

function setTransport(opts: TransportOptions = {}) {
  transport = {
    apiBase: opts.apiBase !== undefined ? resolveApiBase(opts.apiBase) : transport.apiBase,
    wsBase: opts.wsBase !== undefined ? opts.wsBase : transport.wsBase,
    origin: opts.origin !== undefined ? opts.origin : transport.origin,
    fetchImpl: opts.fetchImpl !== undefined ? opts.fetchImpl : transport.fetchImpl,
    WebSocketImpl: opts.WebSocketImpl !== undefined ? opts.WebSocketImpl : transport.WebSocketImpl,
  };
}

function clientOpts() {
  return { apiBase: transport.apiBase, fetchImpl: transport.fetchImpl };
}

function formatRowTime(iso?: string | null): string {
  if (!iso) return nowTime();
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return nowTime();
  return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function neutralAvatarDataUri(label: string): string {
  const ch = (label.trim()[0] || "C").toUpperCase();
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80"><rect width="80" height="80" rx="40" fill="#e2e8f0"/><text x="40" y="48" text-anchor="middle" font-family="system-ui,sans-serif" font-size="30" font-weight="600" fill="#334155">${ch}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function mapConversationRow(row: ConversationRow, currentUserId: string | null): Chat {
  const members = row.member_ids ?? row.members ?? [];
  const otherMember = row.other_member_id || members.find((m) => m !== currentUserId) || row.id;
  const name = row.title?.trim() || otherMember;
  const preview = row.preview ?? (row.last_message && !row.last_message.deleted ? row.last_message.body : "") ?? "";
  const time = row.last_message?.created_at
    ? formatRowTime(row.last_message.created_at)
    : row.updated_at
      ? formatRowTime(row.updated_at)
      : "";
  return {
    id: row.id,
    contact: {
      id: otherMember,
      name,
      avatar: neutralAvatarDataUri(name),
    },
    preview,
    time,
    unread: row.unread ?? 0,
  };
}

function bodyToText(body: MessageBody): string {
  switch (body.kind) {
    case "text":
      return body.text;
    case "image":
      return body.caption?.trim() || body.url;
    case "video":
      return body.caption?.trim() || body.url;
    case "sticker":
      return `[sticker:${body.pack ?? "pack"}] ${body.url}`;
    case "ai":
      return body.text;
    case "card":
      return `${body.title}: ${body.subtitle}`;
    case "voice":
      return `[voice 0:${String(body.seconds).padStart(2, "0")}]`;
    case "choices":
      return body.title;
    case "plan":
      return body.plan.title;
  }
}

function upsertServerMessages(rows: ChatMessageRow[]) {
  if (!rows.length) return;
  const st = getState();
  const userId = st.auth.userId;
  let nextMessages = [...st.messages];
  let nextOutbox = [...st.outbox];
  let nextConvs = [...st.conversations];
  let convsChanged = false;

  for (const row of rows) {
    const prevSeq = convMaxSeq.get(row.conversation_id) ?? 0;
    if (typeof row.seq === "number" && row.seq > prevSeq) {
      convMaxSeq.set(row.conversation_id, row.seq);
      socket?.updateLastSeq(row.conversation_id, row.seq);
    }

    if (row.client_msg_id && row.sender_id === userId) {
      nextOutbox = nextOutbox.filter((o) => o.clientMsgId !== row.client_msg_id);
    }

    if (row.deleted) {
      nextMessages = nextMessages.filter(
        (m) => m.id !== row.id && !(row.client_msg_id && m.id === row.client_msg_id),
      );
      continue;
    }

    const mapped: Message = {
      id: row.id,
      chatId: row.conversation_id,
      fromMe: row.sender_id === userId,
      time: formatRowTime(row.created_at),
      body: { kind: "text", text: row.body },
    };

    const existingIdx = nextMessages.findIndex(
      (m) => m.id === row.id || (row.client_msg_id && m.id === row.client_msg_id),
    );
    if (existingIdx >= 0) {
      const existing = nextMessages[existingIdx];
      nextMessages[existingIdx] = {
        ...mapped,
        ...(existing.replyTo ? { replyTo: existing.replyTo } : {}),
      };
    } else {
      nextMessages.push(mapped);
    }

    const convIdx = nextConvs.findIndex((c) => c.id === row.conversation_id);
    if (convIdx >= 0) {
      nextConvs[convIdx] = {
        ...nextConvs[convIdx],
        preview: row.body,
        time: formatRowTime(row.created_at),
      };
      convsChanged = true;
    }
  }

  set({
    messages: nextMessages,
    outbox: nextOutbox,
    ...(convsChanged ? { conversations: nextConvs } : {}),
  });
}

function removeDeletedMessage(id: string) {
  if (!id) return;
  const nextMessages = getState().messages.filter((m) => m.id !== id);
  if (nextMessages.length !== getState().messages.length) {
    set({ messages: nextMessages });
  }
}

function resetSendingOutboxToQueued() {
  const current = getState().outbox;
  if (!current.some((o) => o.status === "sending")) return;
  set({
    outbox: current.map((o) => (o.status === "sending" ? { ...o, status: "queued" } : o)),
  });
}

function closeSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }
}

function connectSocket(sessionToken: string) {
  closeSocket();
  socket = new ChatCoreSocket({
    sessionToken,
    apiBase: transport.apiBase,
    wsBase: transport.wsBase,
    origin: transport.origin,
    fetchImpl: transport.fetchImpl,
    WebSocketImpl: transport.WebSocketImpl,
    onStateChange: (connection) => {
      set({ connection });
      if (connection === "reconnecting" || connection === "disconnected") {
        resetSendingOutboxToQueued();
      }
    },
    onReady: () => {
      void actions.retryOutbox();
    },
    onReplay: (rows) => {
      upsertServerMessages(rows);
    },
    onAck: (msg) => {
      upsertServerMessages([msg]);
    },
    onMessage: (msg) => {
      upsertServerMessages([msg]);
    },
    onEdit: (msg) => {
      upsertServerMessages([msg]);
    },
    onDelete: (msg) => {
      if ("seq" in msg && typeof msg.seq === "number" && msg.conversation_id) {
        const prev = convMaxSeq.get(msg.conversation_id) ?? 0;
        if (msg.seq > prev) convMaxSeq.set(msg.conversation_id, msg.seq);
      }
      removeDeletedMessage(msg.id);
    },
    onError: (code) => {
      set({ lastError: code });
    },
  });

  const activeId = getState().activeChatId;
  if (activeId) {
    socket.subscribe(activeId, convMaxSeq.get(activeId) ?? 0);
  }
  socket.connect();
}

function persistActiveSession() {
  const { auth, activeChatId, mode } = getState();
  if (mode !== "real" || auth.status !== "signed_in" || !auth.sessionToken || !auth.userId) return;
  saveSessionStorage({
    sessionToken: auth.sessionToken,
    userId: auth.userId,
    displayName: auth.displayName,
    apiBase: transport.apiBase,
    activeChatId,
  });
}

export const actions = {
  /* navigation */
  navigate(screen: ScreenId) { set({ screen }); },
  openModal(modal: ModalId) { set({ modal }); },
  /** Save an email draft; returns its id. An existing `id` replaces that draft. */
  saveMailDraft(d: { to: string; subject: string; body: string; id?: string; by?: "messenger" }): string {
    const id = d.id ?? `draft-${Math.random().toString(36).slice(2, 10)}`;
    const time = new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
    set({ mailDrafts: [{ id, to: d.to, subject: d.subject, body: d.body, time, by: d.by }, ...getState().mailDrafts.filter((x) => x.id !== id)] });
    return id;
  },
  removeMailDraft(id: string) { set({ mailDrafts: getState().mailDrafts.filter((d) => d.id !== id) }); },
  /** Open Mail with Compose filled in (nothing is sent until the person presses Send). */
  composeMail(c: { to: string; subject: string; body: string } | null) { set(c ? { screen: "mail", mailCompose: c } : { mailCompose: null }); },
  /** Show a card over the current screen: flight results or a mail draft. */
  openQuick(quick: QuickCard) { set({ quick }); },
  closeQuick() { set({ quick: null }); },
  /** Show agent results (desktop: the Messenger AI workspace with the Ready cards fanned out; phone: the Updates sheet). */
  openUpdates() { set({ screen: "ai", updatesRequest: getState().updatesRequest + 1 }); },
  closeModal() { set({ modal: null }); },
  setTheme(theme: Theme) { set({ theme }); },
  setWallpaper(wallpaper: Wallpaper) { set({ wallpaper }); },

  /* mode & authentication */
  enterDemoMode() {
    closeSocket();
    set({
      mode: "demo",
      messages: seedMessages,
      activeChatId: "arif",
      connection: "disconnected",
      lastError: null,
      outbox: [],
    });
  },
  exitDemoMode() {
    closeSocket();
    convMaxSeq.clear();
    set({
      mode: "real",
      messages: [],
      conversations: [],
      extraChats: [],
      activeChatId: "",
      connection: "disconnected",
      lastError: null,
      outbox: [],
    });
  },
  async signInWithPassword(opts: SignInWithPasswordOptions): Promise<IdentitySession> {
    set({
      auth: { ...getState().auth, status: "signing_in", error: undefined },
      lastError: null,
    });
    try {
      const { accessToken, user } = await signInSupabasePassword(
        opts.supabaseUrl,
        opts.anonKey,
        opts.email,
        opts.password,
        opts.fetchImpl,
      );
      const fallbackName =
        (typeof user?.user_metadata?.display_name === "string" && user.user_metadata.display_name) ||
        user?.email ||
        opts.email;
      return await actions.signInWithJwt(accessToken, {
        ...opts,
        displayName: opts.displayName || fallbackName,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        auth: { status: "error", userId: null, displayName: "", sessionToken: null, error: msg },
        lastError: err instanceof ChatApiError ? err.code : msg,
      });
      throw err;
    }
  },
  async signInWithJwt(jwt: string, opts: SignInWithJwtOptions = {}): Promise<IdentitySession> {
    setTransport(opts);
    set({
      mode: "real",
      auth: { ...getState().auth, status: "signing_in", error: undefined },
      lastError: null,
    });
    try {
      const session = await openIdentitySession(jwt, {
        apiBase: transport.apiBase,
        ageBand: opts.ageBand,
        setCookie: typeof window !== "undefined",
        fetchImpl: transport.fetchImpl,
      });
      const displayName = opts.displayName || session.userId;
      set({
        mode: "real",
        messages: [],
        extraChats: [],
        outbox: [],
        auth: {
          status: "signed_in",
          userId: session.userId,
          displayName,
          sessionToken: session.sessionToken,
        },
      });
      persistActiveSession();
      await actions.refreshConversations();
      connectSocket(session.sessionToken);
      const activeId = getState().activeChatId;
      if (activeId) {
        await actions.openChat(activeId);
      }
      return session;
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      set({
        auth: { status: "error", userId: null, displayName: "", sessionToken: null, error: msg },
        lastError: err instanceof ChatApiError ? err.code : msg,
      });
      throw err;
    }
  },
  async restoreSession(opts: TransportOptions = {}): Promise<boolean> {
    if (getState().mode !== "real") return false;
    const saved = loadSessionStorage();
    if (!saved) return false;
    setTransport({ apiBase: saved.apiBase, ...opts });
    try {
      const me = await getIdentityMe(saved.sessionToken, clientOpts());
      set({
        mode: "real",
        activeChatId: saved.activeChatId || "",
        auth: {
          status: "signed_in",
          userId: me.user_id,
          displayName: saved.displayName || me.user_id,
          sessionToken: saved.sessionToken,
        },
        lastError: null,
      });
      await actions.refreshConversations();
      connectSocket(saved.sessionToken);
      const activeId = getState().activeChatId;
      if (activeId) {
        await actions.openChat(activeId);
      }
      return true;
    } catch {
      saveSessionStorage(null);
      set({
        auth: { status: "signed_out", userId: null, displayName: "", sessionToken: null },
        connection: "disconnected",
      });
      return false;
    }
  },
  signOut() {
    closeSocket();
    saveSessionStorage(null);
    convMaxSeq.clear();
    set({
      auth: { status: "signed_out", userId: null, displayName: "", sessionToken: null },
      connection: "disconnected",
      conversations: [],
      extraChats: [],
      messages: getState().mode === "demo" ? getState().messages : [],
      activeChatId: getState().mode === "demo" ? getState().activeChatId : "",
      lastError: null,
      outbox: [],
    });
  },
  async refreshConversations(): Promise<Chat[]> {
    const { auth, activeChatId, mode } = getState();
    if (mode !== "real" || !auth.sessionToken) return getState().conversations;
    const rows = await listConversations(auth.sessionToken, clientOpts());
    const mapped = rows.map((r) => mapConversationRow(r, auth.userId));
    const keepActive = activeChatId && mapped.some((c) => c.id === activeChatId);
    const nextActive = keepActive ? activeChatId : mapped[0]?.id ?? "";
    set({
      conversations: mapped,
      activeChatId: nextActive,
    });
    persistActiveSession();
    return mapped;
  },
  async createConversation(input: { memberIds: string[]; kind?: "direct" | "group"; title?: string }): Promise<string> {
    const sessionToken = getState().auth.sessionToken;
    if (!sessionToken) throw new ChatApiError(401, "not_signed_in", "Sign in required");
    const created = await apiCreateConversation(sessionToken, input, clientOpts());
    await actions.refreshConversations();
    await actions.openChat(created.id);
    return created.id;
  },

  /* chats */
  openChat(chatId: string): void | Promise<void> {
    const st = getState();
    if (st.mode === "demo") {
      set({ screen: "chats", activeChatId: chatId, messageFocus: null, chatRequest: st.chatRequest + 1 });
      return;
    }
    set({
      screen: "chats",
      activeChatId: chatId,
      messageFocus: null,
      lastError: null,
      chatRequest: st.chatRequest + 1,
    });
    persistActiveSession();
    const sessionToken = getState().auth.sessionToken;
    if (!chatId || !sessionToken) return;
    return (async () => {
      try {
        const rows = await fetchMessages(sessionToken, chatId, 0, clientOpts());
        upsertServerMessages(rows);
        socket?.subscribe(chatId, convMaxSeq.get(chatId) ?? 0);
      } catch (err) {
        const code = err instanceof ChatApiError ? err.code : err instanceof Error ? err.message : "load_failed";
        set({
          lastError: code,
          messages: getState().messages.filter((m) => m.chatId !== chatId),
        });
      }
    })();
  },
  openLatestMessage(chatId: string) {
    const messages = getState().messages.filter((m) => m.chatId === chatId);
    const incoming = messages.filter((m) => !m.fromMe && m.by !== "messenger");
    const latest = incoming[incoming.length - 1] ?? messages[messages.length - 1];
    set({
      screen: "chats",
      activeChatId: chatId,
      chatRequest: getState().chatRequest + 1,
      messageFocus: latest ? { id: latest.id, request: (getState().messageFocus?.request ?? 0) + 1 } : null,
    });
  },
  /** Post a message into a chat (default: the open chat) as me. Used by "Use in chat". Returns its id. */
  sendToChat(body: MessageBody, chatId = getState().activeChatId, replyTo?: Message["replyTo"]): string {
    const st = getState();
    if (st.mode === "demo") {
      const msg: Message = { id: uid(), chatId, fromMe: true, time: nowTime(), body, ...(replyTo ? { replyTo } : {}) };
      set({ messages: [...st.messages, msg], screen: "chats", activeChatId: chatId });
      return msg.id;
    }
    const clientMsgId = `cm-${uid()}-${Date.now().toString(36)}`;
    if (!chatId) return clientMsgId;
    const text = bodyToText(body).trim();
    if (!text) return clientMsgId;

    const optimistic: Message = {
      id: clientMsgId,
      chatId,
      fromMe: true,
      time: nowTime(),
      body,
      ...(replyTo ? { replyTo } : {}),
    };

    const canSendWs = socket?.isConnected() ?? false;
    const item: OutboxItem = {
      id: clientMsgId,
      chatId,
      clientMsgId,
      text,
      ...(replyTo ? { replyTo } : {}),
      status: canSendWs ? "sending" : "queued",
    };

    set({
      messages: [...st.messages, optimistic],
      outbox: [...st.outbox, item],
      screen: "chats",
      activeChatId: chatId,
    });

    if (canSendWs && socket?.send(chatId, clientMsgId, text)) {
      return clientMsgId;
    }
    if (canSendWs) {
      set({
        outbox: getState().outbox.map((o) => (o.clientMsgId === clientMsgId ? { ...o, status: "queued" } : o)),
      });
    }
    void actions.retryOutbox();
    return clientMsgId;
  },
  async editMessage(chatId: string, messageId: string, text: string): Promise<ChatMessageRow> {
    const sessionToken = getState().auth.sessionToken;
    if (!sessionToken) throw new ChatApiError(401, "not_signed_in", "Sign in required");
    const updated = await editMessageRest(sessionToken, chatId, messageId, text, clientOpts());
    upsertServerMessages([updated]);
    return updated;
  },
  async deleteMessage(chatId: string, messageId: string): Promise<ChatMessageRow> {
    const sessionToken = getState().auth.sessionToken;
    if (!sessionToken) throw new ChatApiError(401, "not_signed_in", "Sign in required");
    const deleted = await deleteMessageRest(sessionToken, chatId, messageId, clientOpts());
    if (typeof deleted.seq === "number") {
      const prev = convMaxSeq.get(chatId) ?? 0;
      if (deleted.seq > prev) convMaxSeq.set(chatId, deleted.seq);
    }
    removeDeletedMessage(messageId);
    return deleted;
  },
  async retryOutbox(): Promise<void> {
    const st = getState();
    if (st.mode !== "real" || !st.auth.sessionToken || flushingOutbox) return;
    const sessionToken = st.auth.sessionToken;
    const queued = st.outbox.filter((o) => o.status === "queued");
    if (!queued.length) return;
    flushingOutbox = true;
    try {
      for (const item of queued) {
        if (!getState().outbox.some((o) => o.clientMsgId === item.clientMsgId)) continue;
        if (socket?.isConnected()) {
          set({
            outbox: getState().outbox.map((o) =>
              o.clientMsgId === item.clientMsgId ? { ...o, status: "sending" } : o,
            ),
          });
          if (socket.send(item.chatId, item.clientMsgId, item.text)) {
            continue;
          }
          set({
            outbox: getState().outbox.map((o) =>
              o.clientMsgId === item.clientMsgId ? { ...o, status: "queued" } : o,
            ),
          });
        }
        try {
          const row = await sendMessageRest(sessionToken, item.chatId, item.clientMsgId, item.text, clientOpts());
          upsertServerMessages([row]);
        } catch (err) {
          if (err instanceof ChatApiError && err.status >= 400 && err.status < 500) {
            set({
              lastError: err.code,
              outbox: getState().outbox.map((o) =>
                o.clientMsgId === item.clientMsgId ? { ...o, status: "failed" } : o,
              ),
            });
          } else {
            set({
              outbox: getState().outbox.map((o) =>
                o.clientMsgId === item.clientMsgId ? { ...o, status: "queued" } : o,
              ),
            });
          }
        }
      }
    } finally {
      flushingOutbox = false;
    }
  },

  /** A message arriving from the other side (a contact auto-reply, or Messenger with `by: "messenger"`). Never switches screens. */
  receiveMessage(body: MessageBody, chatId: string, extra: Pick<Message, "by" | "replyTo"> = {}): string {
    const msg: Message = { id: uid(), chatId, fromMe: false, time: nowTime(), body, ...extra };
    set({ messages: [...getState().messages, msg] });
    return msg.id;
  },
  /** Replace a message's body (an @messenger card filling in: images ready, a sticker chosen, flights loaded). */
  updateMessage(id: string, body: MessageBody) {
    set({ messages: getState().messages.map((m) => (m.id === id ? { ...m, body } : m)) });
  },
  /** A new group chat; opens it. Returns the chat id. */
  createGroup(chat: Omit<Chat, "id">, first?: string): string {
    const id = `group-${uid()}`;
    const msg: Message[] = first ? [{ id: uid(), chatId: id, fromMe: false, time: nowTime(), body: { kind: "text", text: first }, by: "messenger" }] : [];
    set({ extraChats: [{ ...chat, id }, ...getState().extraChats], messages: [...getState().messages, ...msg], screen: "chats", activeChatId: id });
    return id;
  },

  /* Messenger tasks */
  addTask(task: Omit<MessengerTask, "id" | "startedAt" | "unread"> & { id?: string }): string {
    const id = task.id ?? uid();
    set({ tasks: [{ ...task, id, startedAt: Date.now(), unread: true }, ...getState().tasks] });
    return id;
  },
  updateTask(id: string, patch: Partial<MessengerTask>) {
    set({ tasks: getState().tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)) });
  },
  /** Hide a notification from Messenger Updates. Kept in state so in-flight work (e.g. @messenger in Chats) still delivers. */
  dismissTask(id: string) {
    set({ tasks: getState().tasks.map((t) => (t.id === id ? { ...t, dismissed: true, unread: false } : t)) });
  },
  /** Bring back finished tasks saved by the agents service (Redis); tasks already in this tab win. */
  restoreTasks(saved: MessengerTask[]) {
    const have = new Set(getState().tasks.map((t) => t.id));
    const back = saved.filter((t) => !have.has(t.id) && t.status !== "running").map((t) => ({ ...t, unread: false }));
    if (back.length) set({ tasks: [...getState().tasks, ...back].sort((a, b) => b.startedAt - a.startedAt) });
  },
  markTasksRead() { set({ tasks: getState().tasks.map((t) => ({ ...t, unread: false })) }); },

  /* calendar (persisted to localStorage) */
  addEvent(e: Omit<CalendarEvent, "id">): string {
    const id = uid();
    set({ events: [...getState().events, { ...e, id }] });
    return id;
  },
  updateEvent(id: string, patch: Partial<CalendarEvent>) {
    set({ events: getState().events.map((e) => (e.id === id ? { ...e, ...patch } : e)) });
  },
  deleteEvent(id: string) { set({ events: getState().events.filter((e) => e.id !== id) }); },
};
