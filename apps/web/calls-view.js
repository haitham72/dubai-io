// Calls view of the Chat tab: action row, favorites carousel, Recent (real + demo calls),
// and the in-place keypad / contacts / add panes. Calls are a handoff to the phone's
// dialer; there is no in-app call screen. Demo rows only ever open their chat thread.
import { esc, svg, toast, closeSheet } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage, openPage } from './page-host.js';
import { avatar, filterCallPeople, callRequest } from './social-ui.js';
import { recentCalls, createFavorites, resolveFavorites, when } from './chat-logic.js';
import { openThread } from './thread-nav.js';

const initial = s => esc((String(s).trim()[0] || '·').toUpperCase());
export const favorites = () => createFavorites(localStorage);

// Log the call in-app, then hand off to the phone's dialer.
export async function startCall(target) {
  const { tel } = await api(...callRequest(target));
  toast('Opening your phone app…'); location.href = tel;
}
const contactAvatar = (p, cls = 't-avatar') => `<span class="${cls}" aria-hidden="true">${initial(p.name)}</span>`;

export function createCallsView(el) {
  let pane = 'main', contacts = [], calls = [], demo = [], threads = [], search = '', generation = 0, loaded = false;
  const fav = favorites();

  const actionBtn = (id, icon, label) => `<button class="act" data-act="${id}"><span class="act-dot">${svg(icon)}</span><small>${label}</small></button>`;
  const rowHTML = r => `<div class="recent-row${r.missed ? ' missed' : ''}"><button class="recent-main" data-recent="${esc(r.key)}" aria-label="${r.kind === 'demo' ? 'Open chat with ' : 'Call '}${esc(r.name)}">${r.kind === 'demo' ? avatar({ avatar: r.avatar, name: r.name }, 't-avatar') : contactAvatar(r)}<span class="t-copy"><b>${esc(r.name)}${r.kind === 'demo' ? ' <span class="pill demo sm">Demo</span>' : ''}</b><span class="sub">${r.missed ? svg('missed', 'ic xs') + ' ' : r.kind === 'real' ? svg('up2', 'ic xs out') + ' ' : ''}${esc(r.label)}</span></span><time>${esc(when(r.at))}</time></button><button class="round info" data-info="${esc(r.key)}" aria-label="Details for ${esc(r.name)}">${svg('info')}</button></div>`;

  function main() {
    const favs = resolveFavorites(fav.list(), contacts, threads), rows = recentCalls(calls, demo);
    return `<h1 class="big-title">Calls</h1>
      <div class="act-row">${actionBtn('call', 'phone', 'Call')}${actionBtn('contacts', 'person', 'Contacts')}${actionBtn('keypad', 'keypad', 'Keypad')}${actionBtn('favorites', 'heart', 'Favorites')}${actionBtn('add', 'plus', 'Add')}</div>
      ${favs.length ? `<div class="fav-rail" role="list" aria-label="Favorites">${favs.map(f => `<button role="listitem" class="fav-chip" data-fav="${esc(f.id)}" aria-label="${f.type === 'contact' ? 'Call ' : 'Open chat with '}${esc(f.name)}">${f.type === 'thread' ? avatar({ avatar: f.avatar, name: f.name }, 't-avatar') : contactAvatar(f)}<small>${esc(f.name.split(' ')[0])}</small></button>`).join('')}</div>` : ''}
      <div class="recent-head"><h2>Recent</h2>${calls.length ? '<button class="link" data-clear>Clear</button>' : ''}</div>
      <div class="recent-list">${loaded ? rows.map(rowHTML).join('') || '<p class="today-quiet">No calls yet. Calls you start here appear in this list.</p>' : '<p role="status" class="today-quiet">Loading…</p>'}</div>
      <p class="fine tab-fine">Calls open your phone’s dialer; Dubai-io only keeps a log. Rows marked Demo are fictional AI personas and open their chat.</p>`;
  }
  const back = title => `<div class="pane-head"><button class="round" data-pane="main" aria-label="Back to Calls">${svg('back')}</button><h1>${title}</h1></div>`;
  const personRow = p => `<div class="thread contact">${contactAvatar(p)}<span class="t-copy"><b>${esc(p.name)}</b><span>${esc(p.phone)}</span></span><button class="round" data-favorite="${esc(p.id)}" aria-label="${fav.has(p.id) ? 'Remove favorite ' : 'Favorite '}${esc(p.name)}" aria-pressed="${fav.has(p.id)}">${svg('heart', fav.has(p.id) ? 'ic on' : 'ic')}</button><button class="round" data-call="${esc(p.id)}" aria-label="Call ${esc(p.name)}">${svg('phone')}</button><button class="round" data-del="${esc(p.id)}" aria-label="Delete ${esc(p.name)}">${svg('close')}</button></div>`;
  function render() {
    if (pane === 'main') { el.innerHTML = main(); return; }
    if (pane === 'keypad') el.innerHTML = back('Keypad') + `<form data-dial class="contact-add"><label>Phone number<input name="number" type="tel" inputmode="tel" maxlength="24" placeholder="+971" required></label><div class="call-keypad">${'123456789*0#'.split('').map(n => `<button type="button" data-digit="${n}">${n}</button>`).join('')}</div><button type="button" class="btn" data-backspace>Delete digit</button><button class="btn primary" type="submit">Call with your phone app</button><p class="fine">Opens your phone app to place the call. No in-app voice connection is made.</p></form>`;
    if (pane === 'add') el.innerHTML = back('New contact') + `<form class="contact-add" data-add><label>Name<input name="name" maxlength="80" required autocomplete="off"></label><label>Phone<input name="phone" inputmode="tel" maxlength="20" required placeholder="+971 50 123 4567" autocomplete="off"></label><button class="btn primary wide" type="submit">Add new contact</button></form>`;
    if (pane === 'contacts') el.innerHTML = back('Contacts') + `<label class="calls-search"><span class="sr-only">Search contacts</span><input type="search" data-search placeholder="Search contacts" aria-label="Search contacts" value="${esc(search)}"></label><div class="thread-list" data-people>${peopleHTML()}</div><button class="btn wide" data-pane="add" style="margin-top:12px">${svg('plus', 'ic sm')} Add new contact</button>`;
  }
  const peopleHTML = () => filterCallPeople(contacts, search).map(personRow).join('') || '<p class="today-quiet">No matching contacts.</p>';

  async function load() {
    const mine = ++generation;
    try {
      const [people, log, chats] = await Promise.all([api('/api/contacts'), api('/api/calls'), api('/api/chats?filter=all')]);
      if (mine !== generation) return;
      contacts = people.contacts; calls = log.calls || []; demo = log.demo_calls || []; threads = chats.threads || []; loaded = true;
      if (pane === 'main' || pane === 'contacts') render();
    } catch { if (mine === generation) { loaded = true; if (pane === 'main') { render(); toast('Calls could not load.'); } } }
  }
  const find = key => recentCalls(calls, demo).find(r => r.key === key);
  const openRow = r => {
    if (!r) return;
    if (r.action.type === 'thread') return openThread({ id: r.action.threadId, title: r.name });
    if (r.action.type === 'dial') return startCall(r.action.contactId ? { contactId: r.action.contactId } : { number: r.action.number }).then(load);
  };

  el.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    try {
      if (b.dataset.act) {
        const a = b.dataset.act;
        if (a === 'favorites') return openPage('chat.favorites');
        pane = a === 'call' ? 'keypad' : a; render(); el.closest('.tabview')?.scrollTo({ top: 0 }); return;
      }
      if (b.dataset.pane) { pane = b.dataset.pane; search = ''; render(); load(); return; }
      if (b.dataset.recent) return await openRow(find(b.dataset.recent));
      if (b.dataset.info) { const r = find(b.dataset.info); if (r) openPage('call.detail', { row: r, contact: contacts.find(c => c.id === r.contactId) || null, onClose: load }); return; }
      if (b.dataset.fav) { const f = resolveFavorites([b.dataset.fav], contacts, threads)[0]; if (!f) return; return await (f.type === 'thread' ? openThread({ ...f.thread, title: f.name }) : startCall({ contactId: f.contact.id }).then(load)); }
      if (b.hasAttribute('data-clear')) { await api('/api/calls', { method: 'DELETE' }); return load(); }
      if (b.dataset.digit) { const input = el.querySelector('[name=number]'); input.value = (input.value + b.dataset.digit).slice(0, 24); return; }
      if (b.hasAttribute('data-backspace')) { const input = el.querySelector('[name=number]'); input.value = input.value.slice(0, -1); return; }
      if (b.dataset.favorite) { fav.toggle(b.dataset.favorite); render(); return; }
      if (b.dataset.call) return await startCall({ contactId: b.dataset.call }).then(load);
      if (b.dataset.del) { await api('/api/contacts/' + encodeURIComponent(b.dataset.del), { method: 'DELETE' }); fav.remove(b.dataset.del); return load(); }
    } catch (err) { toast(err.message); }
  });
  el.addEventListener('input', e => { if (e.target.matches('[data-search]')) { search = e.target.value.toLowerCase(); el.querySelector('[data-people]').innerHTML = peopleHTML(); } });
  el.addEventListener('submit', async e => {
    e.preventDefault(); const f = new FormData(e.target);
    try {
      if (e.target.matches('[data-dial]')) {
        const number = String(f.get('number')).replace(/[^+0-9*#]/g, '');
        if (!/^\+?[0-9*#]{7,20}$/.test(number)) { toast('Enter a valid phone number.'); return; }
        await startCall({ number }); pane = 'main'; render(); load(); return;
      }
      if (e.target.matches('[data-add]')) {
        await api('/api/contacts', { method: 'POST', body: JSON.stringify({ name: f.get('name'), phone: f.get('phone') }) });
        toast('Contact added.'); pane = 'contacts'; render(); load();
      }
    } catch (err) { toast(err.message); }
  });
  render();
  return { load, reset() { pane = 'main'; search = ''; render(); } };
}

// ⓘ detail: contact detail for real calls, person/thread for demo rows.
registerPage('call.detail', {
  title: c => c.row.name, source: 'Call details',
  render: c => {
    const r = c.row;
    return r.kind === 'demo'
      ? `<div class="call-detail"><span class="pill demo">Demo</span><h3>${esc(r.name)}</h3><p>${esc(r.label)} · ${esc(when(r.at))}</p><p class="fine">This is a fictional AI persona in the preview. The call is demo data; no real line was involved.</p><button class="btn primary wide" data-open-thread>${svg('bubble', 'ic sm')} Open chat</button></div>`
      : `<div class="call-detail"><h3>${esc(r.name)}</h3><p>${esc(r.phone || '')}</p><p class="fine">Started in Dubai-io · ${esc(when(r.at))}. You gave this number yourself (user supplied). Calling opens your phone app.</p><button class="btn primary wide" data-call-now>${svg('phone', 'ic sm')} Call with your phone app</button>${c.contact ? `<button class="btn wide" data-fav-toggle style="margin-top:8px">${favorites().has(c.contact.id) ? 'Remove from favorites' : 'Add to favorites'}</button>` : ''}</div>`;
  },
  mount(root, c) {
    root.addEventListener('click', async e => {
      const b = e.target.closest('button'); if (!b) return;
      try {
        if (b.hasAttribute('data-open-thread') && c.row.threadId) { closeSheet(); openThread({ id: c.row.threadId, title: c.row.name }); }
        if (b.hasAttribute('data-call-now')) await startCall(c.row.action.contactId ? { contactId: c.row.action.contactId } : { number: c.row.action.number });
        if (b.hasAttribute('data-fav-toggle')) { favorites().toggle(c.contact.id); b.textContent = favorites().has(c.contact.id) ? 'Remove from favorites' : 'Add to favorites'; c.onClose?.(); }
      } catch (err) { toast(err.message); }
    });
  },
});
