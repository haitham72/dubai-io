// Chat tab: two in-place views, Chats and Calls, under one top bar (menu left; swap and the
// shared profile icon right). Threads open in the slide-in panel. Group members and community
// threads are labelled demo data; what the user writes stays with them.
import { esc, svg, toast, profileButton } from './ui.js';
import { api } from './service-workflow.js';
import { registerPage } from './page-host.js';
import { avatar, generationText, socialRequest } from './social-ui.js';
import { createChatsView } from './chats-view.js';
import { createCallsView } from './calls-view.js';
import './favorites-panel.js';

export function ago(iso) {
  const m = Math.max(0, Math.round((Date.now() - Date.parse(iso)) / 60000));
  return m < 1 ? 'now' : m < 60 ? m + 'm' : m < 1440 ? Math.round(m / 60) + 'h' : Math.round(m / 1440) + 'd';
}
const VIEW_KEY = 'dubaiio.chatView';
const lastView = () => { try { return sessionStorage.getItem(VIEW_KEY) === 'calls' ? 'calls' : 'chats'; } catch { return 'chats'; } };

export function createHub(root, { openAssistant, openMe, openAsk, openJoin }) {
  let view = lastView();
  root.innerHTML = `<header class="tab-head chat-bar"><div class="menu-wrap"><button class="round" data-menu aria-label="More" aria-haspopup="menu" aria-expanded="false">${svg('dots')}</button><div class="menu-pop" role="menu" hidden><button role="menuitem" data-join>${svg('plus', 'ic sm')} New group</button><button role="menuitem" data-me>${svg('person', 'ic sm')} Settings</button></div></div><div><button class="round" data-swap></button>${profileButton()}</div></header>
    <section data-chats></section><section data-calls hidden></section>`;
  const chats = createChatsView(root.querySelector('[data-chats]'), { openAssistant, openAsk, openJoin });
  const calls = createCallsView(root.querySelector('[data-calls]'));
  const pop = root.querySelector('.menu-pop'), menuBtn = root.querySelector('[data-menu]'), swap = root.querySelector('[data-swap]');
  const closeMenu = () => { pop.hidden = true; menuBtn.setAttribute('aria-expanded', 'false'); };
  function paint() {
    root.querySelector('[data-chats]').hidden = view !== 'chats';
    root.querySelector('[data-calls]').hidden = view !== 'calls';
    swap.innerHTML = svg(view === 'chats' ? 'phone' : 'bubble');
    swap.setAttribute('aria-label', view === 'chats' ? 'Calls' : 'Chats');
    try { sessionStorage.setItem(VIEW_KEY, view); } catch { /* this visit */ }
  }
  const refresh = () => (view === 'chats' ? chats.load() : calls.load());
  root.querySelector('.chat-bar').addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.hasAttribute('data-menu')) { pop.hidden = !pop.hidden; menuBtn.setAttribute('aria-expanded', String(!pop.hidden)); return; }
    closeMenu();
    if (b.hasAttribute('data-swap')) { view = view === 'chats' ? 'calls' : 'chats'; paint(); refresh(); return; }
    if (b.hasAttribute('data-join')) return openJoin();
    if (b.hasAttribute('data-me')) return openMe();
  });
  document.addEventListener('click', e => { if (!pop.hidden && !e.target.closest('.menu-wrap')) closeMenu(); });
  root.addEventListener('keydown', e => { if (e.key === 'Escape' && !pop.hidden) { closeMenu(); menuBtn.focus(); } });
  addEventListener('dubaiio:chats-changed', () => { if (!root.inert) refresh(); });
  paint();
  return { show(visible) { if (visible) refresh(); } };
}

registerPage('chat.thread', {
  title: c => c.title, fallbackTitle: 'Conversation', source: 'Chat · fictional AI personas',
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
