import { createStore } from '../../storeFactory';
import { getMailbox, getMailMessage, sendMail, type GmailMessage } from '../../api';
import { actions, getState } from '../../store';
import type { EmailDraft } from '../../types';
import { emails, type Category, type Email, type Folder } from './data';
type Compose = { to: string; subject: string; body: string; draftId?: string };
interface State { emails: Email[]; selected: string; folder: Folder; category: Category; query: string; starredOnly: boolean; compose: Compose | null; summaries: Record<string, 'working' | 'ready'>; following: Record<string, boolean>; toast: string }
const mailStore = createStore<State>({ emails, selected: emails[0].id, folder: 'Inbox', category: 'All', query: '', starredOnly: false, compose: null, summaries: {}, following: {}, toast: '' });
const getMail = mailStore.get;
const set = mailStore.set;
const stamp = () => new Date().toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
const today = () => new Date().toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
/** An email the person wrote (a draft or a sent message), in the list's shape. */
function mine(id: string, to: string, subject: string, body: string, time: string, extra: Partial<Email> = {}): Email {
  const paragraphs = body.split(/\n\s*\n/).map(p => p.trim()).filter(Boolean);
  return { id, sender: to || '(no recipient)', address: to, category: 'Primary', subject: subject || '(no subject)', preview: paragraphs[0] ?? '',
    time, date: today(), unread: false, starred: false, initials: (to || '?').slice(0, 2).toUpperCase(), tone: 'purple', paragraphs,
    summary: paragraphs.slice(0, 2).join(' '), website: to.split('@')[1] ?? '', phone: '—', location: '—', attachments: [], ...extra };
}
const fromDraft = (d: EmailDraft): Email => mine(d.id, d.to, d.subject, d.body, d.time, { draftId: d.id, draftBy: d.by });


export function useMail() { return mailStore.useState(); }
export function visibleEmails(st: State, drafts: EmailDraft[] = getState().mailDrafts) {
  const query = st.query.trim().toLowerCase();
  const box = st.folder === 'Drafts' ? drafts.map(fromDraft) : st.emails.filter(e => (e.folder ?? 'Inbox') === st.folder);
  return box.filter(e => (st.folder !== 'Inbox' || st.category === 'All' || e.category === st.category) && (!st.starredOnly || e.starred) && `${e.sender} ${e.subject} ${e.preview}`.toLowerCase().includes(query));
}
/** The open email: from the folder in view (drafts live in the store). */
export function selectedEmail(st: State, drafts: EmailDraft[] = getState().mailDrafts) {
  return st.folder === 'Drafts' ? drafts.map(fromDraft).find(e => e.id === st.selected) : st.emails.find(e => e.id === st.selected);
}
function filter(patch: Partial<State>) { set(patch); const cur = getMail(); const visible = visibleEmails(cur); if (!visible.some(e => e.id === cur.selected)) set({ selected: visible[0]?.id ?? '' }); }
let toastTimer: ReturnType<typeof setTimeout>;
export function notify(toast: string) { clearTimeout(toastTimer); set({ toast }); toastTimer = setTimeout(() => set({ toast: '' }), 3500); }
const tones = ['blue', 'purple', 'red', 'green'] as const;
/** A Gmail message (agents service, linked test account) in the inbox's shape; the body loads when it is opened. */
function fromGmail(m: GmailMessage, i: number): Email {
  const d = new Date(m.internalDate);
  return {
    id: m.id, sender: m.sender, address: m.address, category: m.category, subject: m.subject, preview: m.preview,
    time: d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
    date: d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }),
    unread: m.unread, starred: m.starred, initials: m.sender.slice(0, 2), tone: tones[i % tones.length],
    paragraphs: [m.preview], summary: m.preview, website: m.address.split('@')[1] ?? '', phone: '—', location: '—', attachments: [],
  };
}
let live = false;
const bodies = new Set<string>();
async function loadBody(id: string) {
  if (!live || bodies.has(id)) return;
  bodies.add(id);
  try {
    const full = await getMailMessage(id);
    const paragraphs = (full.body ?? '').split(/\n\s*\n/).map(p => p.trim()).filter(Boolean).slice(0, 40);
    if (paragraphs.length) set({ emails: getMail().emails.map(e => e.id === id ? { ...e, paragraphs, summary: paragraphs.slice(0, 2).join(' ').slice(0, 400) } : e) });
  } catch { bodies.delete(id); }
}

export const mail = {
  /** Swap in the real inbox when the Gmail test account is linked; otherwise the demo inbox stays. */
  async loadLive() {
    if (live) return;
    try {
      const box = await getMailbox();
      if (box.mode !== 'gmail' || !box.messages.length) return;
      live = true;
      set({ emails: box.messages.map(fromGmail), selected: box.messages[0].id });
      void loadBody(box.messages[0].id);
    } catch { /* agents service off: demo inbox */ }
  },
  /** The compose Send button is the visible confirmation; only then does a real email leave the test account. */
  async send(to: string, subject: string, body: string, draftId?: string) {
    const sent = () => {
      if (draftId) actions.removeMailDraft(draftId);
      set({ emails: [mine(`sent-${Date.now()}`, to, subject, body, stamp(), { folder: 'Sent' }), ...getMail().emails] });
    };
    if (!live) { sent(); return notify(`Demo email sent to ${to} · in Sent`); }
    try { await sendMail(to, subject, body); sent(); notify(`Sent to ${to}`); } catch (err) { notify(`Not sent · ${err instanceof Error ? err.message.slice(0, 60) : 'error'}`); }
  },
  /** Keep what's in Compose as a draft (replaces the draft it was opened from). */
  saveDraft(c: Compose) {
    if (!c.to.trim() && !c.subject.trim() && !c.body.trim()) return;
    actions.saveMailDraft({ id: c.draftId, to: c.to, subject: c.subject, body: c.body });
    notify('Saved to Drafts');
  },
  folder(folder: Folder) {
    set({ folder, starredOnly: false });
    set({ selected: visibleEmails(getMail())[0]?.id ?? '' });
  },
  /** Mail opened on a draft (e.g. from a trip plan). */
  focusDraft(id: string) { set({ folder: 'Drafts', selected: id, query: '' }); },
  category: (category: Category) => filter({ category }), query: (query: string) => filter({ query }),
  starredOnly: () => filter({ starredOnly: !getMail().starredOnly }),
  select(id: string) { const cur = getMail(); set({ selected: id, emails: cur.emails.map(e => e.id === id ? { ...e, unread: false } : e) }); if (cur.folder === 'Inbox') void loadBody(id); },
  star(id: string) { filter({ emails: getMail().emails.map(e => e.id === id ? { ...e, starred: !e.starred } : e) }); },
  /** Delete moves to Deleted (deleting there removes it); Archive takes it out of every folder. Drafts are discarded. */
  remove(id: string, action: string) {
    if (getMail().folder === 'Drafts') { actions.removeMailDraft(id); filter({}); return notify('Draft discarded'); }
    const toDeleted = action === 'Deleted' && getMail().folder !== 'Deleted';
    filter({ emails: toDeleted ? getMail().emails.map(e => e.id === id ? { ...e, folder: 'Deleted' as const } : e) : getMail().emails.filter(e => e.id !== id) });
    notify(toDeleted ? 'Moved to Deleted' : action === 'Deleted' ? 'Deleted for good' : `${action} · removed from ${getMail().folder}`);
  },
  summary(id: string) { if (getMail().summaries[id] === 'working') return; set({ summaries: { ...getMail().summaries, [id]: 'working' } }); setTimeout(() => set({ summaries: { ...getMail().summaries, [id]: 'ready' } }), 1000); },
  follow(sender: string) { const value = !getMail().following[sender]; set({ following: { ...getMail().following, [sender]: value } }); notify(value ? `Following ${sender}` : `Unfollowed ${sender}`); },
  compose: (compose: State['compose']) => set({ compose }),
};
