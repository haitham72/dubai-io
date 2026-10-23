// Chats view of the Chat tab: search, filter chips, Archived row and WhatsApp-style rows
// with swipe-left Archive (touch) or long-press / right-click (desktop).
import { esc, svg, toast, toastAction } from './ui.js';
import { api } from './service-workflow.js';
import { avatar } from './social-ui.js';
import { filterThreads, searchAction, swipeDecision, SWIPE, when, createFavorites } from './chat-logic.js';
import { openThread } from './thread-nav.js';

const FILTERS = [['all', 'All'], ['unread', 'Unread'], ['favorites', 'Favorites'], ['groups', 'Groups']];
const REVEAL_W = 88;

export function createChatsView(el, { openAssistant, openAsk, openJoin }) {
  let filter = 'all', mode = 'list', data = null, archived = [], query = '', generation = 0;
  const fav = createFavorites(localStorage);

  const rowHTML = (t, isArchive) => `<div class="row-swipe" data-row="${esc(t.id)}"><button class="swipe-act" data-archive="${esc(t.id)}" tabindex="-1">${svg('archive')}<span>Archive</span></button><button class="thread chat-row" data-thread="${esc(t.id)}" data-title="${esc(t.title)}" data-community="${esc(t.community_id || '')}">${avatar({ avatar: t.avatar, name: t.title }, 't-avatar')}<span class="t-copy"><span class="t-line"><b>${esc(t.title)}</b><time class="${t.unread ? 'new' : ''}">${t.at ? esc(when(t.at)) : ''}</time></span><span class="t-line"><span class="t-prev">${t.last_author ? '<i>' + esc(t.last_author) + ':</i> ' : ''}${esc(t.last)}</span>${t.unread ? `<span class="badge">${t.unread}</span>` : ''}</span></span></button></div>`;
  const archivedRow = t => `<div class="thread chat-row static">${avatar({ avatar: t.avatar, name: t.title }, 't-avatar')}<span class="t-copy"><span class="t-line"><b>${esc(t.title)}</b><time>${t.at ? esc(when(t.at)) : ''}</time></span><span class="t-line"><span class="t-prev">${esc(t.last)}</span></span></span><button class="btn sm" data-unarchive="${esc(t.id)}">Unarchive</button></div>`;

  function visible() {
    const base = data?.threads || [];
    return filterThreads(base, query, filter === 'favorites' ? new Set(fav.list()) : null);
  }
  function listHTML() {
    const rows = visible();
    const pinned = filter === 'all' && !query ? `<button class="thread chat-row pinned" data-assistant><span class="t-avatar assistant">${svg('orb')}</span><span class="t-copy"><span class="t-line"><b>Dubai-io assistant</b><time>Pinned</time></span><span class="t-line"><span class="t-prev">Ask, plan, keep track of things</span></span></span></button>` : '';
    const empty = !rows.length && data ? `<p class="today-quiet">${query ? 'No chats match. Press Enter to ask Dubai-io.' : filter === 'unread' ? 'You’re all caught up.' : filter === 'favorites' ? 'No favorite chats yet. Add some from Calls › Favorites.' : filter === 'groups' ? 'No groups yet.' : 'No conversations yet.'}</p>` : '';
    return pinned + rows.map(t => rowHTML(t)).join('') + empty;
  }
  function render() {
    if (mode === 'archived') {
      el.innerHTML = `<div class="pane-head"><button class="round" data-back aria-label="Back to Chats">${svg('back')}</button><h1>Archived</h1></div><div class="chat-list">${archived.map(archivedRow).join('') || '<p class="today-quiet">Nothing archived. Swipe a chat left to archive it.</p>'}</div>`;
      return;
    }
    el.innerHTML = `<h1 class="big-title">Chats</h1>
      <label class="chat-search">${svg('search', 'ic sm')}<span class="sr-only">Ask Dubai-io or Search</span><input type="search" data-q enterkeyhint="search" placeholder="Ask Dubai-io or Search" aria-label="Ask Dubai-io or Search" autocomplete="off" value="${esc(query)}"></label>
      <div class="chat-chips" role="tablist" aria-label="Filter chats">${FILTERS.map(([id, label]) => `<button role="tab" data-filter="${id}" aria-selected="${id === filter}">${label}${id === 'unread' && data?.unread ? ` <span class="badge">${data.unread}</span>` : ''}</button>`).join('')}<button class="chip-plus" data-join aria-label="Join or start a group">${svg('plus', 'ic sm')}</button></div>
      ${data?.archived_count ? `<button class="archived-row" data-archived>${svg('archive', 'ic sm')}<span>Archived</span><small>${data.archived_count}</small>${svg('chev', 'ic xs')}</button>` : ''}
      <div class="chat-list" data-list>${listHTML()}</div>
      <p class="fine tab-fine">These are fictional AI personas in this preview. Your messages stay on your account.</p>`;
  }
  const paintList = () => { const l = el.querySelector('[data-list]'); if (l) l.innerHTML = listHTML(); };

  async function load() {
    const mine = ++generation;
    const server = filter === 'favorites' ? 'all' : filter;
    try {
      if (mode === 'archived') { const d = await api('/api/chats?filter=archived'); if (mine === generation) { archived = d.threads || []; render(); } return; }
      const d = await api('/api/chats?filter=' + server);
      if (mine !== generation) return;
      data = d; const typing = document.activeElement?.matches?.('[data-q]');
      if (typing) { paintList(); const a = el.querySelector('.archived-row'); if (!a && data.archived_count) render(); } else render();
    } catch { if (mine === generation) { data = data || { threads: [] }; render(); toast('Chats could not load.'); } }
  }

  // ---- archive / undo
  async function archive(id, rowEl) {
    try {
      await api('/api/chats/' + encodeURIComponent(id) + '/archive', { method: 'PUT' });
      rowEl.style.height = rowEl.offsetHeight + 'px'; void rowEl.offsetHeight; rowEl.classList.add('gone'); rowEl.style.height = '0px';
      setTimeout(() => { if (data) { data.threads = data.threads.filter(t => t.id !== id); data.archived_count = (data.archived_count || 0) + 1; } render(); }, 260);
      toastAction('Chat archived.', 'Undo', async () => {
        try { await api('/api/chats/' + encodeURIComponent(id) + '/archive', { method: 'DELETE' }); } catch (err) { toast(err.message); }
        load();
      });
    } catch (err) { toast(err.message); closeOpen(); }
  }
  function closeOpen(except) {
    el.querySelectorAll('.row-swipe.open').forEach(r => { if (r !== except) { r.classList.remove('open'); r.querySelector('.chat-row').style.transform = ''; } });
  }
  const setX = (row, x, anim) => { const fg = row.querySelector('.chat-row'); fg.style.transition = anim ? '' : 'none'; fg.style.transform = x ? `translateX(${x}px)` : ''; };

  // ---- gestures. Touch/pen drag; mouse long-press or right-click reveals the same action.
  let drag = null, suppress = false;
  el.addEventListener('pointerdown', e => {
    const row = e.target.closest('.row-swipe'); if (!row || e.target.closest('.swipe-act')) return;
    closeOpen(row);
    drag = { row, x: e.clientX, y: e.clientY, dx: 0, dy: 0, id: e.pointerId, mouse: e.pointerType === 'mouse', base: row.classList.contains('open') ? -REVEAL_W : 0, lock: null };
    if (drag.mouse) drag.timer = setTimeout(() => { row.classList.add('open'); setX(row, -REVEAL_W, true); suppress = true; drag = null; }, 550);
  });
  el.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    drag.dx = e.clientX - drag.x; drag.dy = e.clientY - drag.y;
    if (drag.mouse) { if (Math.abs(drag.dx) > 6 || Math.abs(drag.dy) > 6) clearTimeout(drag.timer); return; }
    if (drag.lock === null && Math.max(Math.abs(drag.dx), Math.abs(drag.dy)) > SWIPE.lock) drag.lock = Math.abs(drag.dx) > Math.abs(drag.dy);
    if (drag.lock) { try { drag.row.setPointerCapture(e.pointerId); } catch { /* ignore */ } setX(drag.row, Math.min(0, Math.max(-(drag.row.offsetWidth), drag.dx + drag.base)), false); }
  });
  const endDrag = e => {
    if (!drag || e.pointerId !== drag.id) return;
    clearTimeout(drag.timer); const d = drag; drag = null;
    if (d.mouse || !d.lock) return;
    suppress = true; setTimeout(() => { suppress = false; }, 0);
    const act = e.type === 'pointercancel' ? 'close' : swipeDecision(d.dx + d.base, d.dy);
    if (act === 'archive') { setX(d.row, -d.row.offsetWidth, true); archive(d.row.dataset.row, d.row); }
    else if (act === 'reveal') { d.row.classList.add('open'); setX(d.row, -REVEAL_W, true); }
    else { d.row.classList.remove('open'); setX(d.row, 0, true); }
  };
  el.addEventListener('pointerup', endDrag); el.addEventListener('pointercancel', endDrag);
  el.addEventListener('contextmenu', e => { const row = e.target.closest('.row-swipe'); if (!row) return; e.preventDefault(); closeOpen(row); row.classList.add('open'); setX(row, -REVEAL_W, true); });

  // ---- clicks / search
  el.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    if (suppress) { suppress = false; if (b.matches('.chat-row')) { e.preventDefault(); return; } }
    if (b.dataset.filter) { filter = b.dataset.filter; render(); load(); return; }
    if (b.hasAttribute('data-assistant')) return openAssistant();
    if (b.hasAttribute('data-join')) return openJoin();
    if (b.hasAttribute('data-archived')) { mode = 'archived'; archived = []; render(); load(); return; }
    if (b.hasAttribute('data-back')) { mode = 'list'; render(); load(); return; }
    if (b.dataset.archive) return archive(b.dataset.archive, b.closest('.row-swipe'));
    if (b.dataset.unarchive) {
      try { await api('/api/chats/' + encodeURIComponent(b.dataset.unarchive) + '/archive', { method: 'DELETE' }); archived = archived.filter(t => t.id !== b.dataset.unarchive); render(); toast('Moved back to Chats.'); }
      catch (err) { toast(err.message); }
      return;
    }
    if (b.dataset.thread) {
      const row = b.closest('.row-swipe');
      if (row?.classList.contains('open')) { closeOpen(); return; }
      return openThread({ id: b.dataset.thread, title: b.dataset.title, community_id: b.dataset.community }, load);
    }
  });
  el.addEventListener('input', e => { if (e.target.matches('[data-q]')) { query = e.target.value; paintList(); } });
  el.addEventListener('keydown', e => {
    if (e.key !== 'Enter' || !e.target.matches('[data-q]')) return;
    e.preventDefault();
    const text = e.target.value.trim();
    if (searchAction(text, visible()) === 'ask') { query = ''; openAsk(text); }
  });
  render();
  return { load, reset() { mode = 'list'; query = ''; render(); }, repaint: render };
}
