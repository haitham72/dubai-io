// Voice commands through the agents service (agents/): speech or a transcript in, decided actions out.
// In-app actions run at once (even mid-sentence); a message to a person waits out an undo window; anything that
// costs money waits for an explicit Confirm. Without the service, voice keeps its original path (state.ts).
import { createStore } from "../storeFactory";
import { agentsHealth, openVoiceStream } from "../api";
import { actions, getState } from "../store";
import { chats } from "../chats/data";
import { askMirsal } from "../chats/mirsal";
import { plainText } from "../chats/skills";
import { emails } from "../screens/mail/data";
import { runAction, sendUserMessage } from "../ai/runAction";
import { ai } from "../ai/state";
import type { ScreenId } from "../types";

export interface CommandEvent {
  type: "ready" | "partial" | "final" | "listening" | "act" | "undo" | "confirm" | "ask" | "cancel" | "chat" | "done" | "error";
  id?: string; action?: string; args?: Record<string, string>; label?: string; ref?: string;
  undoMs?: number; text?: string; message?: string; stt?: "live" | "fake"; budget?: boolean;
  /** The turn must stay open for dictation after this event ("reply"): the chat is open, words still coming. */
  awaiting?: string;
  clause?: string;
}
export interface PendingCommand { id: string; kind: "undo" | "confirm"; label: string; action: string; args: Record<string, string>; until?: number }
interface CommandState { pending: PendingCommand[]; note: string }

export interface MeetingDraft { id: string; args: Record<string, string> }
interface MeetingState { drafts: MeetingDraft[] }
const commandsStore = createStore<CommandState & MeetingState>({ pending: [], note: "", drafts: [] });
const getCommands = commandsStore.get;
const set = commandsStore.set;


export function useCommands<T>(select: (s: CommandState & MeetingState) => T): T {
  return commandsStore.use(select);
}

const timers = new Map<string, number>();
let noteTimer = 0;
function note(text: string) { window.clearTimeout(noteTimer); set({ note: text }); noteTimer = window.setTimeout(() => set({ note: "" }), 2600); }
const drop = (id: string) => { window.clearTimeout(timers.get(id)); timers.delete(id); set({ pending: getCommands().pending.filter((p) => p.id !== id) }); };

/** One id per tab, so "Sara Ali or Sarah Malik?" and the answer land in the same conversation on the server. */
const sid = (() => {
  try {
    let v = sessionStorage.getItem("mirsal.voice.sid");
    if (!v) { v = Math.random().toString(36).slice(2); sessionStorage.setItem("mirsal.voice.sid", v); }
    return v;
  } catch { return Math.random().toString(36).slice(2); }
})();

/** "stream" = live speech-to-text on the service · "text" = service up, transcript from the existing route · null = off. */
export async function commandMode(): Promise<"stream" | "text" | null> {
  const h = await agentsHealth();
  if (!h?.ok || h.budget.stopped) return null;
  return h.live.stt ? "stream" : "text";
}
void agentsHealth(); // warm the cache before the first tap

export interface Outcome { reply: string; ask: boolean; chat?: string }

/** One utterance over one WebSocket. Resolves once the service has decided everything that was said. */
export class CommandStream {
  private events: CommandEvent[] = [];
  private finished!: (o: Outcome) => void;
  readonly outcome = new Promise<Outcome>((r) => { this.finished = r; });

  private constructor(private ws: WebSocket, private onPartial: (text: string) => void, private onHold?: (kind: string) => void) {}

  static open(audio: boolean, onPartial: (text: string) => void, onHold?: (kind: string) => void): Promise<CommandStream | null> {
    return new Promise((resolve) => {
      let ws: WebSocket;
      try { ws = openVoiceStream(sid); } catch { return resolve(null); }
      const stream = new CommandStream(ws, onPartial, onHold);
      const timer = window.setTimeout(() => { ws.close(); resolve(null); }, 2500);
      ws.onopen = () => ws.send(JSON.stringify({ type: "start", audio, contacts: recentFirst().map((c) => ({ id: c.id, name: c.contact.name })) }));
      ws.onerror = () => { window.clearTimeout(timer); resolve(null); };
      ws.onclose = () => stream.finish();
      ws.onmessage = (m) => {
        const e = JSON.parse(String(m.data)) as CommandEvent;
        if (e.type === "ready") { window.clearTimeout(timer); resolve(stream); return; }
        stream.handle(e);
      };
    });
  }

  audio(chunk: ArrayBuffer) { if (this.ws.readyState === WebSocket.OPEN) this.ws.send(chunk); }
  text(text: string) { this.ws.send(JSON.stringify({ type: "text", text })); }
  end() { if (this.ws.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify({ type: "end" })); return this.outcome; }
  close() { this.ws.close(); }

  private handle(e: CommandEvent) {
    if (e.type === "partial" || e.type === "final") { if (e.text) this.onPartial(e.text); return; }
    if (e.type === "listening") { this.onHold?.(e.awaiting ?? "reply"); note("Listening… speak your reply"); return; }
    if (e.type === "done") { this.finish(); this.ws.close(); return; }
    if (e.type === "error") { note(e.budget ? "Voice budget reached" : "Voice commands unavailable"); this.finish(); return; }
    this.events.push(e);
    // The chat is open but the reply is still being dictated: keep the turn open and say so.
    if (e.type === "act" && e.awaiting) { this.onHold?.(e.awaiting); note("Listening… speak your reply"); }
    const said = execute(e);
    if (said) e.label = said; // what was found is what gets spoken
  }

  private finish() {
    const shown = this.events.filter((e) => e.type !== "cancel" && !this.events.some((c) => c.type === "cancel" && c.ref === e.id));
    const ask = shown.find((e) => e.type === "ask");
    const chat = shown.find((e) => e.type === "chat");
    this.finished({ reply: ask?.label ?? shown.map((e) => e.label).filter(Boolean).join(" · "), ask: !!ask, chat: chat?.args?.text });
  }
}

/** The last chat opened or sent to comes first. Seed messages are grouped by chat, not chronological. */
export function recentFirst() {
  const { messages: msgs, activeChatId, extraChats } = getState();
  const last = new Map<string, number>();
  msgs.forEach((m, i) => last.set(m.chatId, i));
  return [...extraChats, ...chats].sort((a, b) => {
    if (a.id === b.id) return 0;
    if (a.id === activeChatId) return -1;
    if (b.id === activeChatId) return 1;
    return (last.get(b.id) ?? -1) - (last.get(a.id) ?? -1);
  });
}

/* ---------------- spoken summaries (read from what the app holds; short enough to say) ---------------- */
const clip = (s: string, n = 90) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);
const nameOf = (chatId: string) => [...getState().extraChats, ...chats].find((c) => c.id === chatId)?.contact.name ?? "Someone";

function notificationsSummary(): string {
  const fresh = getState().tasks.filter((t) => t.unread && !t.dismissed);
  if (!fresh.length) return "Nothing new — you're all caught up.";
  return `${fresh.length} new: ${fresh.slice(0, 3).map((t) => t.title.replace(/^\w+ · /, "")).join("; ")}.`;
}
/** One person's latest messages, or the unread chats. */
function messagesSummary(contactId?: string): string {
  const incoming = (chatId: string) => getState().messages.filter((m) => m.chatId === chatId && !m.fromMe && m.by !== "mirsal");
  if (contactId) {
    const last = incoming(contactId).slice(-3);
    return last.length ? `${nameOf(contactId)} said: ${last.map((m) => `“${clip(plainText(m), 70)}”`).join(" ")}` : `No messages from ${nameOf(contactId)} yet.`;
  }
  const unread = [...getState().extraChats, ...chats].filter((c) => c.unread > 0);
  if (!unread.length) return "No unread messages.";
  const lines = unread.slice(0, 3).map((c) => { const list = incoming(c.id); const m = list[list.length - 1]; return m ? `${c.contact.name}: “${clip(plainText(m), 60)}”` : c.contact.name; });
  return `${unread.length} unread chat${unread.length > 1 ? "s" : ""}. ${lines.join(". ")}.`;
}
/** Opening Mail or Research also says what's at the top (Mail: the app's inbox; a linked Gmail shows on screen). */
function screenSummary(screen: string): string | undefined {
  if (screen === "mail") {
    const unread = emails.filter((m) => m.unread);
    const top = unread[0] ?? emails[0];
    return top ? `${unread.length ? `${unread.length} unread. ` : ""}Latest from ${top.sender}: ${clip(top.subject, 70)}.` : undefined;
  }
  if (screen === "research") {
    const done = getState().tasks.filter((t) => t.result?.type === "research" && t.status === "completed")
      .sort((x, y) => (y.completedAt ?? 0) - (x.completedAt ?? 0))[0];
    const brief = done?.result?.type === "research" ? done.result.items[0] : undefined;
    return brief ? `Your latest report: ${clip(brief.title, 80)} — ${brief.findings.length} key findings.` : undefined;
  }
}

/* ---------------- executor ---------------- */
/** Runs one event; returns what to say instead of its label, when there is something better to say. */
function execute(e: CommandEvent): string | undefined {
  const a = e.args ?? {};
  switch (e.type) {
    case "act":
      if (e.action === "open_screen") { actions.navigate(a.screen as ScreenId); return screenSummary(a.screen); }
      else if (e.action === "check_notifications") { const said = notificationsSummary(); actions.openUpdates(); return said; }
      else if (e.action === "read_messages") {
        const said = messagesSummary(a.contactId);
        if (a.contactId) actions.openChat(a.contactId); else actions.navigate("chats");
        return said;
      }
      else if (e.action === "compose_email") actions.composeMail({ to: a.to ?? "", subject: a.subject ?? "", body: a.body ?? "" });
      else if (e.action === "open_chat") {
        if (/\b(?:last|latest|recent)\s+message\b/i.test(e.clause ?? "")) actions.openLatestMessage(a.contactId);
        else actions.openChat(a.contactId);
      }
      else if (e.action === "plan_meeting" && e.id && !getCommands().drafts.some(d => d.id === e.id)) {
        commands.showMeeting(e.id, a);
      }
      else if (e.action === "get_weather") void runAction({ type: "weather", city: a.city }, "").then((m) => ai.push(m)).catch(() => note(`Couldn't get the weather for ${a.city}`));
      break;
    case "undo": {
      const until = Date.now() + (e.undoMs ?? 3000);
      set({ pending: [...getCommands().pending, { id: e.id!, kind: "undo", label: e.label ?? "", action: e.action!, args: a, until }] });
      timers.set(e.id!, window.setTimeout(() => commands.commit(e.id!), e.undoMs ?? 3000));
      break;
    }
    case "confirm":
      set({ pending: [...getCommands().pending, { id: e.id!, kind: "confirm", label: e.label ?? "", action: e.action!, args: a }] });
      break;
    case "cancel":
      if (e.args?.all) { getCommands().pending.forEach((p) => drop(p.id)); set({ drafts: [] }); note("Cancelled"); }
      else if (e.ref) commands.closeDraft(e.ref);
      break;
  }
}

/** Paid actions run only from here, after a tap on Confirm. */
async function runPaid(p: PendingCommand) {
  const a = p.args;
  if (p.action === "search_flights") return sendUserMessage(a.utterance); // the chat route resolves airports and dates
  if (p.action === "plan_trip") {
    // The same planner as "@mirsal plan …" in a chat: with the named person, else in the chat that is open.
    const chatId = a.contactId ?? getState().activeChatId;
    const request = `@mirsal ${a.request}`;
    actions.openChat(chatId);
    askMirsal(chatId, request, actions.sendToChat({ kind: "text", text: request }, chatId));
    return;
  }
  const action = p.action === "generate_image" ? { type: "image" as const, prompt: a.prompt }
    : p.action === "generate_video" ? { type: "video" as const, prompt: a.prompt }
    : { type: "research" as const, topic: a.topic };
  const text = action.type === "research" ? "" : action.type === "image" ? `Creating “${a.prompt}”.` : `Making a video of “${a.prompt}”.`;
  try { ai.push(await runAction(action, text)); } catch { note("That didn't start — please try again"); }
}

export const commands = {
  showMeeting(id: string, args: Record<string, string>) {
    if (!getCommands().drafts.some(d => d.id === id)) set({ drafts: [...getCommands().drafts, { id, args }] });
  },
  closeDraft(id: string) { set({ drafts: getCommands().drafts.filter(d => d.id !== id) }); },
  /** Undo window over (or "Send now"): post the message into the chat. */
  commit(id: string) {
    const p = getCommands().pending.find((x) => x.id === id);
    if (!p) return;
    drop(id);
    if (p.action === "send_message") {
      actions.sendToChat({ kind: "text", text: p.args.text }, p.args.contactId);
      note(`Sent to ${p.args.name}`);
    }
  },
  undo(id: string) { drop(id); note("Not sent"); },
  confirm(id: string) {
    const p = getCommands().pending.find((x) => x.id === id);
    if (!p) return;
    drop(id);
    void runPaid(p);
  },
  decline(id: string) { drop(id); note("Cancelled"); },
};
