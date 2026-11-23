// Chat-local mentions and request lifecycle. Network/generation stay in the shared API/action flow.
import { useEffect } from 'react';
import { createStore } from '../storeFactory';
import { askAi, mirsalLook, photoForCheck } from '../api';
import { retryTask, runAction } from '../ai/runAction';
import { actions, getState, useStore } from '../store';
import type { Message, MessageBody, MirsalTask } from '../types';
import { avatar } from '../ui';
import { scheduleReaction } from './autoReply';
import { contacts } from './data';
import { chatContext, cleanImage, commandOf, factCheck, images, photoQuestionUrl, plan, runCommand, serviceUp, skillOf, stickers, type Skill } from './skills';

export interface Mention { name: string; token: string; face?: string }
const groups = new Set(['travel', 'family', 'gaming', 'study']);
export function chatMentions(chatId: string, messages: Message[]): Mention[] {
  const people: Mention[] = [];
  if (groups.has(chatId)) {
    const names = new Set<string>();
    messages.filter(m => m.chatId === chatId && !m.fromMe).forEach(m => {
      const text = m.body.kind === 'text' ? m.body.text : m.body.kind === 'image' || m.body.kind === 'video' ? m.body.caption : '';
      const name = text?.match(/^([\p{L}\p{M}][\p{L}\p{M} '-]{0,39}):\s/u)?.[1]?.trim();
      if (name && name.toLowerCase() !== 'mirsal') names.add(name);
    });
    names.forEach(name => {
      const known = Object.values(contacts).find(c => c.name.split(' ')[0].toLowerCase() === name.toLowerCase());
      const hash = Array.from(name).reduce((n, char) => n + char.charCodeAt(0), 0);
      people.push({ name, token: `@${name.split(' ')[0]}`, face: known?.avatar ?? avatar(1 + hash % 70) });
    });
  } else {
    const contact = (contacts as Record<string, { name: string; avatar: string }>)[chatId];
    if (contact) people.push({ name: contact.name, token: `@${contact.name.split(' ')[0]}`, face: contact.avatar });
  }
  return [{ name: 'Mirsal AI', token: '@mirsal' }, ...people];
}
export function mentionAt(text: string, caret: number) {
  const match = text.slice(0, caret).match(/(?:^|\s)@([\p{L}\p{M}\d_-]*)$/u);
  return match ? { start: caret - match[1].length - 1, end: caret, query: match[1] } : null;
}

export interface MirsalRequest {
  id: string; chatId: string; request: string; status: 'asking' | 'working' | 'ready' | 'failed';
  label: string; taskId?: string; body?: MessageBody;
}
const requestsStore = createStore<MirsalRequest[]>([]);
const patch = (id: string, update: Partial<MirsalRequest>) => { requestsStore.update((requests) => requests.map(r => r.id === id ? { ...r, ...update } : r)); };
const uid = () => Math.random().toString(36).slice(2, 10);
const error = (id: string) => patch(id, { status: 'failed', label: "Mirsal couldn't do that", body: undefined });
function resultBody(task: MirsalTask): MessageBody | undefined {
  const result = task.result;
  if (result?.type === 'image') return { kind: 'image', url: result.imageUrl };
  if (result?.type === 'video') return { kind: 'video', url: result.videoUrl, caption: result.title };
  if (result?.type === 'flight' && result.flights.length) {
    const cheapest = result.flights.reduce((a, b) => a.price <= b.price ? a : b);
    return { kind: 'card', icon: 'flight', title: `${result.query.from} → ${result.query.to} · ${result.flights.length} flights`, subtitle: `from ${cheapest.currency} ${cheapest.price.toLocaleString()} · tap to view` };
  }
}
function shortWeather(text: string) {
  const line = text.split('\n')[0];
  const place = line.match(/^\*\*(.+?), [^*]+\*\* · (.+)$/);
  const range = text.match(/H ([^\n]+?) \/ L ([^\n]+?) ·/);
  return `☀️ ${place ? `${place[1]}: ${place[2]}` : line.replace(/\*\*/g, '')}${range ? ` · H ${range[1]} / L ${range[2]}` : ''}`;
}
let flushing = false;
/** Store subscription bridge, never server polling. Runs again on returning to Chats. */
function reconcile() {
  if (flushing) return;
  flushing = true;
  try {
    for (const request of [...requestsStore.get()]) {
      if (request.taskId && request.status !== 'ready') {
        const task = getState().tasks.find(t => t.id === request.taskId);
        if (task?.status === 'failed' && request.status !== 'failed') error(request.id);
        if (task?.status === 'running' && request.status === 'failed') patch(request.id, { status: 'working', label: `Mirsal is generating your ${task.type}…` });
        if (task?.status === 'completed') {
          const body = resultBody(task);
          if (body) patch(request.id, { status: 'ready', label: task.type === 'image' ? 'Image ready' : 'Video ready', body });
          else if (request.status !== 'failed') error(request.id);
        }
      }
      const ready = requestsStore.get().find(r => r.id === request.id);
      // Mirsal's reply arrives in the chat like a message from the other side (never switches screens).
      if (ready?.status === 'ready' && ready.body) {
        requestsStore.update((requests) => requests.filter(r => r.id !== ready.id)); // mark delivered before store notifications
        actions.receiveMessage(ready.body, ready.chatId, { by: 'mirsal' });
        scheduleReaction(ready.chatId);

      }
    }
  } finally { flushing = false; }
}
async function perform(id: string) {
  const request = requestsStore.get().find(r => r.id === id);
  if (!request) return;
  try {
    // The last messages go along as context, so "this" and "that" mean what the chat is about.
    const context = chatContext(request.chatId).lines.slice(-6, -1).map(l => `${l.sender}: ${l.text}`).join('\n');
    // A question about a chat photo goes to the vision skill (text-only askAi can't see pixels).
    const photo = photoQuestionUrl(request.chatId, request.request);
    if (photo && (await serviceUp())) {
      patch(id, { status: 'working', label: 'Mirsal is looking…' });
      try {
        const seen = await mirsalLook(await photoForCheck(photo), request.request, chatContext(request.chatId).lines.slice(-6));
        if (!seen.fallback && seen.answer) {
          patch(id, { status: 'ready', label: 'Answer ready', body: { kind: 'ai', text: seen.answer } });
          reconcile();
          return;
        }
        throw new Error('live photo checking is unavailable right now');
      } catch (err) {
        // The photo was found but couldn't be opened: say so honestly and stop. Never fall through
        // to the text-only model — it can't see pixels and invents instructions instead of an answer.
        const reason = err instanceof Error && err.message ? err.message.slice(0, 140) : 'the photo could not be opened';
        patch(id, { status: 'ready', label: 'Answer ready', body: { kind: 'ai', text: `I couldn't open that photo (${reason}). Send it again and I'll take a look.` } });
        reconcile();
        return;
      }
    }
    const reply = await askAi([{ role: 'user', text: context ? `Recent chat (context only):\n${context}\n\nRequest: ${request.request}` : request.request }]);
    if (!reply.action) { patch(id, { status: 'ready', label: 'Answer ready', body: { kind: 'ai', text: reply.text } }); reconcile(); return; }
    const type = reply.action.type;
    patch(id, { status: 'working', label: type === 'flight' ? 'Mirsal is finding flights…' : type === 'weather' ? 'Mirsal is checking the weather…' : `Mirsal is generating your ${type}…` });
    const before = new Set(getState().tasks.map(t => t.id));
    const message = await runAction(reply.action, reply.text);
    if (message.taskId) { patch(id, { taskId: message.taskId }); reconcile(); return; }
    if (type === 'research') {
      const task = getState().tasks.find(t => !before.has(t.id) && t.type === 'research');
      const brief = task?.result?.type === 'research' ? task.result.items[0] : undefined;
      patch(id, task && brief
        ? { status: 'ready', label: 'Research ready', body: { kind: 'card', icon: 'research', title: brief.title, subtitle: `${brief.findings.length} key insights · tap to open`, taskId: task.id } }
        : { status: 'ready', label: 'Research', body: { kind: 'ai', text: message.text } });
    } else if (type === 'flight') {
      const task = getState().tasks.find(t => !before.has(t.id) && t.result?.type === 'flight' && t.result.flights.some(f => message.text.includes(f.flightNo)));
      const body = task && resultBody(task);
      patch(id, { status: 'ready', label: 'Flights ready', body: body ?? { kind: 'ai', text: message.text } });
    } else patch(id, { status: 'ready', label: 'Weather ready', body: { kind: 'ai', text: shortWeather(message.text) } });
    reconcile();
  } catch { error(id); }
}
const SKILL_LABEL: Record<Exclude<Skill, 'other'>, string> = {
  factcheck: 'Mirsal is checking that…', sticker: 'Mirsal is finding stickers…', image: 'Mirsal is imagining…', plan: 'Mirsal is planning…',
  clean: 'Mirsal is cleaning that image…',
};
async function runSkill(chatId: string, skill: Exclude<Skill, 'other'>, request: string, commandId?: string, replyTo?: Message['replyTo']) {
  const id = uid();
  requestsStore.update((requests) => [...requests, { id, chatId, request, status: 'asking', label: SKILL_LABEL[skill] }]);

  try {
    if (skill === 'factcheck') await factCheck(chatId, commandId ?? '', replyTo);
    else if (skill === 'sticker') await stickers(chatId, commandId ?? '');
    else if (skill === 'image') await images(chatId, commandId ?? '', request);
    else if (skill === 'clean') await cleanImage(chatId, commandId ?? '', request);
    else await plan(chatId, commandId ?? '', request);
  } finally {
    requestsStore.update((requests) => requests.filter(r => r.id !== id));

  }
}
/** "@mirsal …" anywhere in a message. `commandId` is that message (context is what came before it). */
export function askMirsal(chatId: string, request: string, commandId?: string, replyTo?: Message['replyTo']) {
  // Room behavior first (open/read/reply via the shared engine): the generic model would only say it can't.
  if (commandOf(request)) { void runCommandOrGeneric(chatId, request, commandId); return; }
  const skill = skillOf(request);
  if (skill !== 'other') { void runSkill(chatId, skill, request, commandId, replyTo); return; }
  genericAsk(chatId, request);
}
/** The shared engine decided nothing actionable (or is off): the normal AI answers. */
function genericAsk(chatId: string, request: string) {
  const id = uid();
  requestsStore.update((requests) => [...requests, { id, chatId, request, status: 'asking', label: 'Mirsal is thinking…' }]);
  void perform(id);
}
async function runCommandOrGeneric(chatId: string, request: string, commandId?: string) {
  if (await runCommand(chatId, request, commandId)) return;
  genericAsk(chatId, request);
}
export async function retryMirsal(id: string) {
  const request = requestsStore.get().find(r => r.id === id);
  if (!request || request.status !== 'failed') return;
  const task = request.taskId ? getState().tasks.find(t => t.id === request.taskId) : undefined;
  patch(id, { status: 'asking', label: 'Mirsal is retrying…' });
  if (task?.status === 'failed' && (task.type === 'image' || task.type === 'video')) {
    try { if (await retryTask(task)) { reconcile(); return; } } catch { error(id); return; }
  }
  patch(id, { taskId: undefined }); void perform(id);
}
export function useMirsalRequests() {
  const list = requestsStore.useState();
  const tasks = useStore(st => st.tasks);
  const screen = useStore(st => st.screen);
  useEffect(reconcile, [tasks, screen, list]);
  return list;
}
