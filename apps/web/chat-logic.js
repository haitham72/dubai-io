// Pure logic for the Chats / Calls views. No DOM access so it runs under node tests.
export const FAV_KEY = 'dubaiio.callFavorites';
export const SWIPE = { reveal: 56, full: 170, lock: 8 };

// Recent calls: real outgoing calls merged with seeded demo calls, newest first.
// A demo row can only ever open its chat thread; it never yields a dial action.
export function recentCalls(calls = [], demo = []) {
  const real = calls.map(c => ({
    key: 'call:' + c.id, kind: 'real', name: c.name || c.phone, phone: c.phone, at: c.at, missed: false,
    label: 'Started in Dubai-io', contactId: c.contact_id || null,
    action: c.contact_id ? { type: 'dial', contactId: c.contact_id } : c.phone ? { type: 'dial', number: c.phone } : { type: 'none' },
  }));
  const seeded = demo.map(c => ({
    key: 'demo:' + c.id, kind: 'demo', name: c.name, avatar: c.avatar, at: c.at, missed: c.direction === 'missed',
    label: c.direction === 'missed' ? 'Missed' : 'Incoming', threadId: c.thread_id || null, phone: null,
    action: c.thread_id ? { type: 'thread', threadId: c.thread_id } : { type: 'none' },
  }));
  return [...real, ...seeded].sort((a, b) => Date.parse(b.at) - Date.parse(a.at));
}

// Favorites: ordered list of ids in localStorage. Contact ids are stored plain (as before);
// thread ids are stored as "thread:<id>". Pure functions over a Storage-like object.
export const threadFav = id => 'thread:' + id;
export const isThreadFav = id => String(id).startsWith('thread:');
export const favThreadId = id => String(id).slice(7);
export function createFavorites(storage) {
  const read = () => { try { const v = JSON.parse(storage.getItem(FAV_KEY) || '[]'); return Array.isArray(v) ? [...new Set(v.filter(x => typeof x === 'string'))] : []; } catch { return []; } };
  const write = list => { try { storage.setItem(FAV_KEY, JSON.stringify(list)); } catch { /* this visit only */ } return list; };
  return {
    list: read,
    has: id => read().includes(id),
    add: id => { const l = read(); return l.includes(id) ? l : write([...l, id]); },
    remove: id => write(read().filter(x => x !== id)),
    toggle(id) { return this.has(id) ? this.remove(id) : this.add(id); },
    // dir -1 = up, +1 = down; out-of-range moves are ignored.
    move(id, dir) {
      const l = read(), i = l.indexOf(id), j = i + dir;
      if (i < 0 || j < 0 || j >= l.length) return l;
      [l[i], l[j]] = [l[j], l[i]]; return write(l);
    },
  };
}

// Resolve favorite ids against live contacts / threads; unresolved (deleted) ids are dropped.
export function resolveFavorites(ids, contacts = [], threads = []) {
  const c = new Map(contacts.map(x => [x.id, x])), t = new Map(threads.map(x => [x.id, x]));
  return ids.flatMap(id => {
    if (isThreadFav(id)) { const th = t.get(favThreadId(id)); return th ? [{ id, type: 'thread', name: th.title, avatar: th.avatar, thread: th }] : []; }
    const p = c.get(id); return p ? [{ id, type: 'contact', name: p.name, phone: p.phone, contact: p }] : [];
  });
}

// Swipe-left on a row: dx is negative to the left. Vertical movement wins (scroll).
export function swipeDecision(dx, dy) {
  if (Math.abs(dy) > Math.abs(dx) && Math.abs(dx) < SWIPE.lock * 3) return 'scroll';
  if (dx <= -SWIPE.full) return 'archive';
  if (dx <= -SWIPE.reveal) return 'reveal';
  return 'close';
}

// Search box: Enter with a question or with no matching thread goes to Ask.
export function searchAction(text, matches) {
  const q = String(text).trim(); if (!q) return 'none';
  return q.endsWith('?') || !matches.length ? 'ask' : 'none';
}
export function filterThreads(threads, query, favSet = null) {
  const q = String(query).trim().toLowerCase();
  return threads.filter(t => (!favSet || favSet.has(threadFav(t.id))) && (!q || (t.title + ' ' + (t.last || '') + ' ' + (t.last_author || '')).toLowerCase().includes(q)));
}

// WhatsApp-style timestamp: time today, "Yesterday", weekday within a week, else dd/mm/yyyy.
export function when(iso, now = new Date()) {
  const d = new Date(iso); if (Number.isNaN(d.getTime())) return '';
  const day = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const diff = Math.round((day(now) - day(d)) / 86400000), pad = n => String(n).padStart(2, '0');
  if (diff <= 0) return `${pad(d.getHours())}:${pad(d.getMinutes())}`;
  if (diff === 1) return 'Yesterday';
  if (diff < 7) return ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'][d.getDay()];
  return `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}`;
}
