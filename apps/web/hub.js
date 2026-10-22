// Chat tab: the assistant pinned first, then groups and community threads, with
// Contacts and a log of calls started from Dubai-io. Group members and community
// threads are labelled demo data; what the user writes stays with them.
import { esc, svg, toast } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage, openPage } from './page-host.js';

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
    root.innerHTML = `<header class="tab-head"><h1>Chat</h1><div><button class="round" data-contacts aria-label="Contacts and calls">${svg('phone')}</button><button class="round" data-me aria-label="Your profile">${svg('person')}</button></div></header>
      <div class="segments" role="tablist" aria-label="Filter chats">${FILTERS.map(([id, label]) => `<button role="tab" data-filter="${id}" aria-selected="${id === filter}">${label}${id === 'unread' && data?.unread ? ` <span class="badge">${data.unread}</span>` : ''}</button>`).join('')}</div>
      <div class="thread-list">
        ${filter === 'all' ? `<button class="thread pinned" data-assistant><span class="t-avatar assistant">${svg('orb')}</span><span class="t-copy"><b>Dubai-io assistant</b><span>Ask, plan, keep track of things</span></span><small>Pinned</small></button>` : ''}
        ${threads.map(t => `<button class="thread" data-thread="${esc(t.id)}" data-title="${esc(t.title)}"><span class="t-avatar ${t.kind}">${t.kind === 'community' ? svg('grid') : initial(t.title)}</span><span class="t-copy"><b>${esc(t.title)}</b><span>${t.last_author ? esc(t.last_author) + ': ' : ''}${esc(t.last)}</span></span><small>${t.at ? ago(t.at) : ''}${t.unread ? `<span class="badge">${t.unread}</span>` : ''}</small></button>`).join('')}
        ${!threads.length && data ? `<p class="today-quiet">${filter === 'communities' ? 'Join a community in Feed to chat with it here.' : filter === 'unread' ? 'You’re all caught up.' : 'No conversations yet.'}</p>` : ''}
      </div>
      <p class="fine tab-fine">Groups and community members are demo data in this preview. Your messages stay on your account.</p>`;
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
    if (b.dataset.thread) return openPage('chat.thread', { id: b.dataset.thread, title: b.dataset.title, onClose: load });
    if (b.hasAttribute('data-contacts')) return openPage('contacts');
    if (b.hasAttribute('data-me')) return openMe();
  });
  addEventListener('dubaiio:chats-changed', () => { if (!root.inert) load(); });
  render();
  return { show(visible) { if (visible) load(); } };
}

registerPage('chat.thread', {
  title: c => c.title, source: 'Chat',
  render: () => '<div class="thread-view" data-messages><p role="status">Loading…</p></div><form class="thread-compose" data-compose><label class="sr" for="threadText">Message</label><input id="threadText" maxlength="500" placeholder="Message" autocomplete="off"><button class="btn primary" type="submit">Send</button></form>',
  mount(root, c) {
    const box = root.querySelector('[data-messages]');
    const draw = d => {
      box.innerHTML = d.messages.map(m => `<div class="bubble ${m.mine ? 'me' : ''}">${m.mine ? '' : `<b>${esc(m.author)}${m.provenance === 'demo_fixture' ? ' <span class="pill demo">Demo</span>' : ''}</b>`}<p>${esc(m.text)}</p><small>${ago(m.at)}</small></div>`).join('') || '<p class="today-quiet">Say hello.</p>';
      box.scrollTop = box.scrollHeight;
    };
    const load = () => api('/api/chats/' + encodeURIComponent(c.id) + '/messages').then(d => { if (root.isConnected) draw(d); dispatchEvent(new CustomEvent('dubaiio:chats-changed')); }).catch(() => { box.innerHTML = '<p role="alert">This conversation could not load.</p>'; });
    root.querySelector('[data-compose]').addEventListener('submit', async e => {
      e.preventDefault();
      const input = root.querySelector('#threadText'), text = input.value.trim(); if (!text) return;
      input.disabled = true;
      try { await api('/api/chats/' + encodeURIComponent(c.id) + '/messages', { method: 'POST', body: JSON.stringify({ text }) }); input.value = ''; await load(); }
      catch (err) { toast(err.message); } finally { input.disabled = false; input.focus(); }
    });
    load();
  },
});

registerPage('contacts', {
  title: 'Contacts', source: 'Calls start in your phone’s dialer',
  render: () => `<div class="segments" role="tablist"><button role="tab" data-ctab="people" aria-selected="true">Contacts</button><button role="tab" data-ctab="log" aria-selected="false">Call log</button></div><div data-contacts-body></div>`,
  mount(root) {
    const body = root.querySelector('[data-contacts-body]');
    let tab = 'people';
    async function load() {
      try {
        if (tab === 'people') {
          const { contacts } = await api('/api/contacts');
          body.innerHTML = `<form class="contact-add" data-add><label>Name<input name="name" maxlength="80" required autocomplete="off"></label><label>Phone<input name="phone" inputmode="tel" maxlength="20" required placeholder="+971 50 123 4567" autocomplete="off"></label><button class="btn primary wide" type="submit">${svg('person', 'ic sm')} Add new contact</button></form>
            <div class="thread-list">${contacts.map(p => `<div class="thread contact"><span class="t-avatar">${initial(p.name)}</span><span class="t-copy"><b>${esc(p.name)}</b><span>${esc(p.phone)}</span></span><button class="round" data-call="${esc(p.id)}" aria-label="Call ${esc(p.name)}">${svg('phone')}</button><button class="round" data-del="${esc(p.id)}" aria-label="Delete ${esc(p.name)}">${svg('close')}</button></div>`).join('') || '<p class="today-quiet">No contacts yet. Importing from your iPhone comes with the native app.</p>'}</div>`;
        } else {
          const { calls } = await api('/api/calls');
          body.innerHTML = `<div class="thread-list">${calls.map(x => `<div class="thread contact"><span class="t-avatar">${svg('phone', 'ic sm')}</span><span class="t-copy"><b>${esc(x.name)}</b><span>${esc(x.phone)} · started from Dubai-io</span></span><small>${ago(x.at)}</small></div>`).join('') || '<p class="today-quiet">Calls you start here are listed here. Your phone’s own call history stays private to iOS.</p>'}</div>${calls.length ? '<button class="btn wide" data-clear>Clear call log</button>' : ''}`;
        }
      } catch { body.innerHTML = '<p role="alert">Contacts could not load.</p>'; }
    }
    root.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      if (b.dataset.ctab) { tab = b.dataset.ctab; root.querySelectorAll('[data-ctab]').forEach(x => x.setAttribute('aria-selected', x === b)); return load(); }
      try {
        if (b.dataset.call) { const { tel } = await api('/api/calls', { method: 'POST', body: JSON.stringify({ contact_id: b.dataset.call }) }); location.href = tel; toast('Opening your phone’s dialer…'); }
        if (b.dataset.del) { await api('/api/contacts/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); load(); }
        if (b.hasAttribute('data-clear')) { await api('/api/calls', { method: 'DELETE' }); load(); }
      } catch (err) { toast(err.message); }
    });
    root.addEventListener('submit', async e => {
      if (!e.target.matches('[data-add]')) return;
      e.preventDefault();
      const f = new FormData(e.target);
      try { await api('/api/contacts', { method: 'POST', body: JSON.stringify({ name: f.get('name'), phone: f.get('phone') }) }); load(); }
      catch (err) { toast(err.message.includes('Could not') ? 'Check the phone number (digits, +, spaces).' : err.message); }
    });
    load();
  },
});
