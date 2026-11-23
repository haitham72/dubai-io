// Global app store — owned by the lead session. The glue between every session's work.
// Read with useStore(s => s.x); change only through the `actions` below.
import { createStore } from "./storeFactory";
import type { EmailDraft, CalendarEvent, Chat, MessageBody, Message, MirsalTask, ModalId, QuickCard, ScreenId } from "./types";
import { seedMessages } from "./chats/data";
import { seedTasks } from "./updates/seed";
import { videoSeedTasks } from "./videos";
import { applyFrost, loadFrost } from "./frost";

applyFrost(loadFrost());

interface State {
  screen: ScreenId;
  modal: ModalId;
  /** Flight results or a mail draft shown as a card over the current screen (rendered by src/quick). */
  quick: QuickCard;
  activeChatId: string;
  chatRequest: number;
  messageFocus: { id: string; request: number } | null;
  messages: Message[];
  /** Chats created in this session (e.g. a group from an @mirsal plan); shown above the seeded ones. */
  extraChats: Chat[];
  tasks: MirsalTask[];
  /** Bumped by openUpdates(): the desktop tray and the phone sheet open when it changes (voice, shortcuts). */
  updatesRequest: number;
  /** Mail drafts (yours from Compose, or Mirsal's — e.g. the leave email from a trip plan). Never sent by themselves. */
  mailDrafts: EmailDraft[];
  /** An email to open in Compose (voice "email Rashid that …"); Mail opens it, the person presses Send. */
  mailCompose: { to: string; subject: string; body: string } | null;
  events: CalendarEvent[];
  theme: Theme;
  wallpaper: Wallpaper;
}

const EVENTS_KEY = "mirsal.events";
const DRAFTS_KEY = "mirsal.drafts";
function loadDrafts(): EmailDraft[] {
  try { return JSON.parse(localStorage.getItem(DRAFTS_KEY) ?? "[]") as EmailDraft[]; } catch { return []; }
}

/* Theme: "system" follows the OS live. Applied as <html data-theme="light|dark"> (tokens.css). */
export type Theme = "light" | "dark" | "system";
const THEME_KEY = "mirsal.theme";
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
function loadTheme(): Theme {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "dark" || v === "system" ? v : "light";
  } catch {
    return "light";
  }
}
function applyTheme(theme: Theme) {
  const dark = theme === "dark" || (theme === "system" && darkQuery.matches);
  document.documentElement.dataset.theme = dark ? "dark" : "light";
}

/* Mac desktop wallpaper id. Applied as data-wallpaper on the desktop root (tokens.css). */
export type Wallpaper = "aurora" | "desert" | "ocean" | "mono";
const WALLPAPER_KEY = "mirsal.wallpaper";
function loadWallpaper(): Wallpaper {
  try {
    const v = localStorage.getItem(WALLPAPER_KEY);
    return v === "desert" || v === "ocean" || v === "mono" ? v : "aurora";
  } catch {
    return "aurora";
  }
}

function loadEvents(): CalendarEvent[] {
  try {
    const raw = localStorage.getItem(EVENTS_KEY);
    return raw ? (JSON.parse(raw) as CalendarEvent[]) : [];
  } catch {
    return [];
  }
}

/** Persistence + theme side effects that used to live inside `set`. Runs after every merge. */
function persist(s: State, patch: Partial<State>) {
  if (patch.mailDrafts) {
    try { localStorage.setItem(DRAFTS_KEY, JSON.stringify(s.mailDrafts)); } catch { /* storage unavailable */ }
  }
  if (patch.events) {
    try { localStorage.setItem(EVENTS_KEY, JSON.stringify(s.events)); } catch { /* storage unavailable */ }
  }
  if (patch.theme) {
    applyTheme(s.theme);
    try { localStorage.setItem(THEME_KEY, s.theme); } catch { /* storage unavailable */ }
  }
  if (patch.wallpaper) {
    try { localStorage.setItem(WALLPAPER_KEY, s.wallpaper); } catch { /* storage unavailable */ }
  }
}

const store = createStore<State>({
  screen: "chats",
  modal: null,
  quick: null,
  activeChatId: "arif",
  chatRequest: 0,
  messageFocus: null,
  updatesRequest: 0,
  mailDrafts: loadDrafts(),
  mailCompose: null,
  messages: seedMessages,
  extraChats: [],
  tasks: [...videoSeedTasks(), ...seedTasks],
  events: loadEvents(),
  theme: loadTheme(),
  wallpaper: loadWallpaper(),
}, persist);

export const getState = store.get;
const set = store.set;

/** Subscribe outside React (e.g. to persist tasks). Returns the unsubscribe function. */
export const subscribe = store.subscribe;

export function useStore<T>(select: (s: State) => T): T {
  return store.use(select);
}

applyTheme(getState().theme);
darkQuery.addEventListener("change", () => { if (getState().theme === "system") applyTheme("system"); });

const uid = () => Math.random().toString(36).slice(2, 10);
const nowTime = () => new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

export const actions = {
  /* navigation */
  navigate(screen: ScreenId) { set({ screen }); },
  openModal(modal: ModalId) { set({ modal }); },
  /** Save an email draft; returns its id. An existing `id` replaces that draft. */
  saveMailDraft(d: { to: string; subject: string; body: string; id?: string; by?: "mirsal" }): string {
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
  /** Show agent results (desktop: the Mirsal AI workspace with the Ready cards fanned out; phone: the Updates sheet). */
  openUpdates() { set({ screen: "ai", updatesRequest: getState().updatesRequest + 1 }); },
  closeModal() { set({ modal: null }); },
  setTheme(theme: Theme) { set({ theme }); },
  setWallpaper(wallpaper: Wallpaper) { set({ wallpaper }); },

  /* chats */
  openChat(chatId: string) { set({ screen: "chats", activeChatId: chatId, messageFocus: null, chatRequest: getState().chatRequest + 1 }); },
  openLatestMessage(chatId: string) {
    const messages = getState().messages.filter(m => m.chatId === chatId);
    const incoming = messages.filter(m => !m.fromMe && m.by !== "mirsal");
    const latest = incoming[incoming.length - 1] ?? messages[messages.length - 1];
    set({ screen: "chats", activeChatId: chatId, chatRequest: getState().chatRequest + 1, messageFocus: latest ? { id: latest.id, request: (getState().messageFocus?.request ?? 0) + 1 } : null });
  },
  /** Post a message into a chat (default: the open chat) as me. Used by "Use in chat". Returns its id. */
  sendToChat(body: MessageBody, chatId = getState().activeChatId, replyTo?: Message["replyTo"]): string {
    const msg: Message = { id: uid(), chatId, fromMe: true, time: nowTime(), body, ...(replyTo ? { replyTo } : {}) };
    set({ messages: [...getState().messages, msg], screen: "chats", activeChatId: chatId });
    return msg.id;
  },

  /** A message arriving from the other side (a contact auto-reply, or Mirsal with `by: "mirsal"`). Never switches screens. */
  receiveMessage(body: MessageBody, chatId: string, extra: Pick<Message, "by" | "replyTo"> = {}): string {
    const msg: Message = { id: uid(), chatId, fromMe: false, time: nowTime(), body, ...extra };
    set({ messages: [...getState().messages, msg] });
    return msg.id;
  },
  /** Replace a message's body (an @mirsal card filling in: images ready, a sticker chosen, flights loaded). */
  updateMessage(id: string, body: MessageBody) {
    set({ messages: getState().messages.map((m) => (m.id === id ? { ...m, body } : m)) });
  },
  /** A new group chat; opens it. Returns the chat id. */
  createGroup(chat: Omit<Chat, "id">, first?: string): string {
    const id = `group-${uid()}`;
    const msg: Message[] = first ? [{ id: uid(), chatId: id, fromMe: false, time: nowTime(), body: { kind: "text", text: first }, by: "mirsal" }] : [];
    set({ extraChats: [{ ...chat, id }, ...getState().extraChats], messages: [...getState().messages, ...msg], screen: "chats", activeChatId: id });
    return id;
  },

  /* Mirsal tasks */
  addTask(task: Omit<MirsalTask, "id" | "startedAt" | "unread"> & { id?: string }): string {
    const id = task.id ?? uid();
    set({ tasks: [{ ...task, id, startedAt: Date.now(), unread: true }, ...getState().tasks] });
    return id;
  },
  updateTask(id: string, patch: Partial<MirsalTask>) {
    set({ tasks: getState().tasks.map((t) => (t.id === id ? { ...t, ...patch } : t)) });
  },
  /** Hide a notification from Mirsal Updates. Kept in state so in-flight work (e.g. @mirsal in Chats) still delivers. */
  dismissTask(id: string) {
    set({ tasks: getState().tasks.map((t) => (t.id === id ? { ...t, dismissed: true, unread: false } : t)) });
  },
  /** Bring back finished tasks saved by the agents service (Redis); tasks already in this tab win. */
  restoreTasks(saved: MirsalTask[]) {
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
