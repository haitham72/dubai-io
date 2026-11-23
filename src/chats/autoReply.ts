// One debounced contact reply per chat; lives beyond the mounted conversation.
import { createStore } from '../storeFactory';
import { getContactReply } from '../api';
import { actions, getState } from '../store';
import type { Message, MessageBody } from '../types';
import { contacts } from './data';

const groups = new Set(['travel', 'family', 'gaming', 'study']);
const DELAY_MS = 1200;
const REACT_WINDOW = 5; // a reaction to Mirsal reads only the last few messages
interface Pending { revision: number; due: number; running: boolean; window: number; timer?: ReturnType<typeof setTimeout> }
const pending = new Map<string, Pending>();
// Empty sender means still waiting for the group member to be selected.
const typingStore = createStore<Record<string, string | undefined>>({});
function setTyping(chatId: string, sender?: string) {
  typingStore.update((typing) => {
    const next = { ...typing };
    if (sender === undefined) delete next[chatId];
    else next[chatId] = sender;
    return next;
  });
}
export function useContactTyping(chatId: string) {
  return typingStore.use((t) => t[chatId]);
}
function historyText(body: MessageBody): string {
  switch (body.kind) {
    case 'text': return body.text;
    case 'image': return '[photo]';
    case 'video': return '[video]';
    case 'voice': return '[voice note]';
    case 'card': return `[shared: ${body.title}]`;
    case 'sticker': return '[sticker]';
    case 'ai': return `${body.verdict ? `fact check: ${body.verdict.replace('_', ' ')} — ` : ''}${body.text}`;
    case 'choices': return body.title;
    case 'plan': return `trip plan: ${body.plan.title} — ${body.plan.summary}`;
  }
}
/** One line of history for the contact's model. Mirsal is the user's assistant: its replies sit on the user's side,
 *  clearly labelled, so the contact reacts to Mirsal instead of speaking as it. */
function historyLine(m: Message) {
  return m.by === 'mirsal'
    ? { fromMe: true, text: `[Mirsal, the AI assistant in this chat, replied: ${historyText(m.body)}]` }
    : { fromMe: m.fromMe, text: historyText(m.body) };
}
function arm(chatId: string, contactName: string, entry: Pending) {
  entry.timer = setTimeout(() => { entry.timer = undefined; void reply(chatId, contactName, entry); }, Math.max(0, entry.due - Date.now()));
}
async function reply(chatId: string, contactName: string, entry: Pending) {
  if (entry.running) return; // the in-flight request will rearm the latest burst
  entry.running = true;
  const revision = entry.revision;
  setTyping(chatId, '');
  try {
    const history = getState().messages.filter(m => m.chatId === chatId).slice(-entry.window).map(historyLine);
    const result = await getContactReply(chatId, contactName, groups.has(chatId), history);
    if (revision !== entry.revision) return; // ignore an answer to an older burst
    if (!result.text?.trim()) throw new Error('Empty contact reply');
    const sender = groups.has(chatId) ? result.sender?.trim() : undefined;
    setTyping(chatId, sender ?? '');
    // Briefly retain the selected member's typing feedback before their bubble arrives.
    await new Promise(resolve => setTimeout(resolve, 300));
    if (revision !== entry.revision) return;
    actions.receiveMessage({ kind: 'text', text: sender ? `${sender}: ${result.text.trim()}` : result.text.trim() }, chatId);
  } catch {
    if (revision === entry.revision) console.warn('Contact reply unavailable; chatting can continue.');
  } finally {
    entry.running = false;
    if (revision === entry.revision) {
      pending.delete(chatId); setTyping(chatId);
    } else if (!entry.timer) arm(chatId, contactName, entry);
  }
}
/** Called only from the user's composer send, never from Use in chat or incoming posts. */
export function scheduleContactReply(chatId: string, contactName: string, text: string) {
  if (!text.trim() || /^\s*@mirsal(?:\s|$)/i.test(text)) return;
  const entry = pending.get(chatId) ?? { revision: 0, due: 0, running: false, window: 20 };
  entry.revision += 1; entry.due = Date.now() + DELAY_MS; entry.window = 20;
  if (entry.timer) clearTimeout(entry.timer);
  setTyping(chatId); // a new burst supersedes the currently displayed typing state
  pending.set(chatId, entry);
  arm(chatId, contactName, entry);
}

/** After Mirsal answers in a chat (fact check, plan, ideas…), the person or group reacts to it in character, reading
 *  only the last 5 messages — e.g. Arif replying to a "False" verdict on his own claim. */
export function scheduleReaction(chatId: string) {
  const name = (contacts as Record<string, { name: string }>)[chatId]?.name ?? getState().extraChats.find(c => c.id === chatId)?.contact.name;
  if (!name) return;
  const entry = pending.get(chatId) ?? { revision: 0, due: 0, running: false, window: REACT_WINDOW };
  entry.revision += 1; entry.due = Date.now() + DELAY_MS + 600; entry.window = REACT_WINDOW;
  if (entry.timer) clearTimeout(entry.timer);
  setTyping(chatId);
  pending.set(chatId, entry);
  arm(chatId, name, entry);
}
