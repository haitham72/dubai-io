// Chat tab: the assistant pinned first, then groups and community threads, with
// Contacts and a log of calls started from Dubai-io. Group members and community
// threads are labelled demo data; what the user writes stays with them.
import { esc, svg, toast } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage, openPage } from './page-host.js';
import { avatar, generationText, socialRequest, filterCallPeople, callRequest } from './social-ui.js';

const FILTERS = [['all', 'All'], ['unread', 'Unread'], ['groups', 'Groups'], ['communities', 'Communities']];
export function ago(iso) {
  const m = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return m < 1 ? 'now' : m < 60 ? m + 'm' : m < 1440 ? Math.round(m / 60) + 'h' : Math.round(m / 1440) + 'd';
}
const initial = s => esc((String(s).trim()[0] || '·').toUpperCase());

export function createHub(root, { openAssistant, openMe }) {
  let filter = 'all', data = null, generation = 0;
  function render() {
    const threads = data?.threads || [];
    root.innerHTML = `<header class="tab-head"><h1>Chat</h1><div><button class="round" data-me aria-label="Your profile">${svg('person')}</button></div></header>
      <button class="calls-destination" data-contacts>${svg('phone', 'ic sm')} Calls <span>Calls, contacts & keypad</span>${svg('chev', 'ic sm')}</button><div class="segments" role="tablist" aria-label="Filter chats">${FILTERS.map(([id, label]) => `<button role="tab" data-filter="${id}" aria-selected="${id === filter}">${label}${id === 'unread' && data?.unread ? ` <span class="badge">${data.unread}</span>` : ''}</button>`).join('')}</div>
      <div class="thread-list">
        ${filter === 'all' ? `<button class="thread pinned" data-assistant><span class="t-avatar assistant">${svg('orb')}</span><span class="t-copy"><b>Dubai-io assistant</b><span>Ask, plan, keep track of things</span></span><small>Pinned</small></button>` : ''}
        ${threads.map(t => `<button class="thread" data-thread="${esc(t.id)}" data-title="${esc(t.title)}" data-community="${esc(t.community_id || '')}">${avatar({ avatar: t.avatar, name: t.title }, 't-avatar')}<span class="t-copy"><b>${esc(t.title)}</b><span>${t.last_author ? esc(t.last_author) + ': ' : ''}${esc(t.last)}</span></span><small>${t.at ? ago(t.at) : ''}${t.unread ? `<span class="badge">${t.unread}</span>` : ''}</small></button>`).join('')}
        ${!threads.length && data ? `<p class="today-quiet">${filter === 'communities' ? 'Join a community in Feed to chat with it here.' : filter === 'unread' ? 'You’re all caught up.' : 'No conversations yet.'}</p>` : ''}
      </div>
      <p class="fine tab-fine">These are fictional AI personas in this preview. Your messages stay on your account.</p>`;
  }
  async function load() {
    const mine = ++generation;
    try { const d = await api('/api/chats?filter=' + filter); if (mine === generation) { data = d; render(); } }
    catch { if (mine === generation) { data = { threads: [] }; render(); toast('Chats could not load.'); } }
  }
  root.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.filter) { filter = b.dataset.filter; render(); load(); return; }
    if (b.hasAttribute('data-assistant')) return openAssistant();
    if (b.dataset.thread) return b.dataset.community ? openPage('feed.community', { id: b.dataset.community, title: b.dataset.title }) : openPage('chat.thread', { id: b.dataset.thread, title: b.dataset.title, onClose: load });
    if (b.hasAttribute('data-contacts')) return openPage('contacts');
    if (b.hasAttribute('data-me')) return openMe();
  });
  addEventListener('dubaiio:chats-changed', () => { if (!root.inert) load(); });
  render();
  return { show(visible) { if (visible) load(); } };
}

registerPage('chat.thread', {
  title: c => c.title, source: 'Chat · fictional AI personas',
  render: () => '<div class="thread-view" data-messages><p role="status">Loading…</p></div><form class="thread-compose" data-compose><label class="sr" for="threadText">Message</label><input id="threadText" maxlength="500" placeholder="Message" autocomplete="off"><button class="btn primary" type="submit">Send</button></form><p class="fine" role="status" data-generation></p>',
  mount(root, c) {
    const box = root.querySelector('[data-messages]'), request = socialRequest(); let busy = false;
    const draw = d => {
      box.innerHTML = d.messages.map(m => `<div class="bubble ${m.mine ? 'me' : ''}">${m.mine ? '' : `<b>${avatar({ avatar: m.avatar, name: m.author })}${esc(m.author)} <span class="pill demo">AI demo</span></b>`}<p>${esc(m.text)}</p><small>${ago(m.at)}</small></div>`).join('') || '<p class="today-quiet">Say hello.</p>';
      box.scrollTop = box.scrollHeight;
    };
    const load = () => api('/api/chats/' + encodeURIComponent(c.id) + '/messages').then(d => { if (root.isConnected) draw(d); dispatchEvent(new CustomEvent('dubaiio:chats-changed')); }).catch(() => { box.innerHTML = '<p role="alert">This conversation could not load.</p>'; });
    root.querySelector('[data-compose]').addEventListener('submit', async e => {
      e.preventDefault();
      const input = root.querySelector('#threadText'), text = input.value.trim(); if (!text || busy) return;
      busy = true; input.disabled = true; e.target.querySelector('button').disabled = true;
      root.querySelector('[data-generation]').textContent = 'Saving your message and waiting for an AI reply…';
      try { const result = await api('/api/chats/' + encodeURIComponent(c.id) + '/messages', request({ text })); request.reset(); input.value = ''; await load(); root.querySelector('[data-generation]').textContent = generationText(result); }
      catch (err) { root.querySelector('[data-generation]').textContent = 'Could not confirm the result. Retry to check the same message.'; toast(err.message); } finally { busy = false; input.disabled = false; e.target.querySelector('button').disabled = false; input.focus(); }
    });
    load();
  },
});

registerPage('contacts', {
  title: 'Call', source: 'Calls open your phone’s dialer',
  render: () => `<label class="calls-search"><span class="sr-only">Search</span><input type="search" data-search placeholder="Search calls or contacts" aria-label="Search calls or contacts"></label><div class="segments calls-tabs" role="tablist" aria-label="Call sections">${[['log','Calls'],['keypad','Keypad'],['favorites','Favorites']].map(([id,label]) => `<button role="tab" data-ctab="${id}" aria-selected="${id === 'log'}">${label}</button>`).join('')}</div><div class="calls-surface"><div class="calls-main" data-contacts-body></div><aside class="calls-rail" aria-label="Contacts" data-rail></aside></div>`,
  mount(root) {
    const body = root.querySelector('[data-contacts-body]'), rail = root.querySelector('[data-rail]');
    let tab = 'log', contacts = [], calls = [], search = '', favorites = new Set(), generation = 0;
    try { favorites = new Set(JSON.parse(localStorage.getItem('dubaiio.callFavorites') || '[]')); } catch { /* this visit */ }
    const personRow = p => `<div class="thread contact"><span class="t-avatar">${initial(p.name)}</span><span class="t-copy"><b>${esc(p.name)}</b><span>${esc(p.phone)}</span></span><button class="round" data-favorite="${esc(p.id)}" aria-label="Favorite ${esc(p.name)}" aria-pressed="${favorites.has(p.id)}">${favorites.has(p.id) ? '★' : '☆'}</button><button class="round" data-call="${esc(p.id)}" aria-label="Call ${esc(p.name)}">${svg('phone')}</button><button class="round" data-del="${esc(p.id)}" aria-label="Delete ${esc(p.name)}">${svg('close')}</button></div>`;
    function renderRail() {
      rail.innerHTML = `<button class="rail-add" data-ctab="manage" aria-label="Add or manage contacts" title="Add or manage contacts">+</button>` + filterCallPeople(contacts, search).map(p => `<button class="rail-person" data-call="${esc(p.id)}" aria-label="Call ${esc(p.name)}, ${esc(p.phone)}"><span class="t-avatar">${initial(p.name)}</span><small>${esc(p.name.split(' ')[0])}</small></button>`).join('');
    }
    function render() {
      renderRail();
      if (tab === 'keypad') {
        body.innerHTML = `<form data-dial class="contact-add"><label>Phone number<input name="number" type="tel" inputmode="tel" maxlength="24" placeholder="+971" required></label><div class="call-keypad">${'123456789*0#'.split('').map(n => `<button type="button" data-digit="${n}">${n}</button>`).join('')}</div><button type="button" class="btn" data-backspace>Delete digit</button><button class="btn primary" type="submit">Call with your phone app</button><p class="fine">Opens your phone app to place the call. No in-app voice connection is made.</p></form>`; return;
      }
      if (tab === 'log') {
        body.innerHTML = `<div class="thread-list">${filterCallPeople(calls, search).map(x => `<div class="thread contact"><span class="t-avatar">${svg('phone', 'ic sm')}</span><span class="t-copy"><b>${esc(x.name)}</b><span>${esc(x.phone)} · phone app opened</span></span><small>${ago(x.at)}</small></div>`).join('') || '<p class="today-quiet">No matching calls. Calls you start here appear in this log.</p>'}</div>${calls.length ? '<button class="btn wide" data-clear>Clear call log</button>' : ''}`; return;
      }
      if (tab === 'manage') {
        body.innerHTML = `<form class="contact-add" data-add><label>Name<input name="name" maxlength="80" required autocomplete="off"></label><label>Phone<input name="phone" inputmode="tel" maxlength="20" required placeholder="+971 50 123 4567" autocomplete="off"></label><button class="btn primary wide" type="submit">Add new contact</button></form><div class="thread-list">${filterCallPeople(contacts, search).map(personRow).join('') || '<p class="today-quiet">No matching contacts.</p>'}</div>`; return;
      }
      body.innerHTML = `<p class="fine">Favorites are saved on this device. Star a contact under + to add it here.</p><div class="thread-list">${filterCallPeople(contacts, search, favorites).map(personRow).join('') || '<p class="today-quiet">No favorites yet.</p>'}</div>`;
    }
    async function load() {
      const mine = ++generation;
      try { const [people, log] = await Promise.all([api('/api/contacts'), api('/api/calls')]); if (mine !== generation) return; contacts = people.contacts; calls = log.calls; render(); }
      catch { body.innerHTML = '<p role="alert">Calls could not load.</p>'; }
    }
    root.querySelector('[data-search]').addEventListener('input', e => { search = e.target.value.toLowerCase(); if (tab !== 'keypad') render(); else renderRail(); });
    // Log the call in-app, then hand off to the phone's dialer. No simulated call screen.
    async function startCall(target) {
      const { tel } = await api(...callRequest(target));
      toast('Opening your phone app…'); location.href = tel; load();
    }
    root.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.ctab) { tab = b.dataset.ctab; root.querySelectorAll('.calls-tabs [data-ctab]').forEach(x => x.setAttribute('aria-selected', String(x.dataset.ctab === tab))); render(); return; }
      if (b.dataset.digit) { const input = body.querySelector('[name=number]'); input.value = (input.value + b.dataset.digit).slice(0,24); return; }
      if (b.hasAttribute('data-backspace')) { const input = body.querySelector('[name=number]'); input.value = input.value.slice(0,-1); return; }
      if (b.dataset.favorite) { const id = b.dataset.favorite; favorites.has(id) ? favorites.delete(id) : favorites.add(id); try { localStorage.setItem('dubaiio.callFavorites', JSON.stringify([...favorites])); } catch { /* this visit */ } render(); return; }
      try {
        if (b.dataset.call) await startCall({ contactId: b.dataset.call });
        if (b.dataset.del) { await api('/api/contacts/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); load(); }
        if (b.hasAttribute('data-clear')) { await api('/api/calls', { method: 'DELETE' }); load(); }
      } catch (err) { toast(err.message); }
    });
    root.addEventListener('submit', async e => {
      e.preventDefault(); const f = new FormData(e.target);
      if (e.target.matches('[data-dial]')) {
        const number = String(f.get('number')).replace(/[^+0-9*#]/g, '');
        if (!/^\+?[0-9*#]{7,20}$/.test(number)) { toast('Enter a valid phone number.'); return; }
        try { await startCall({ number }); } catch (err) { toast(err.message); }
        return;
      }
      if (!e.target.matches('[data-add]')) return;
      try { await api('/api/contacts', { method: 'POST', body: JSON.stringify({ name: f.get('name'), phone: f.get('phone') }) }); load(); }
      catch (err) { toast(err.message); }
    });
    load();
  },
});
