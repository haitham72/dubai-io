// Snapchat-style story viewer for a community. Tap right/left (or arrows) to move,
// hold to pause, swipe down or Escape to close. Reduced motion: no auto-advance.
import { esc, svg, toast, reduced } from './ui.js';
import { api } from './service-workflow.js';
import { openPage } from './page-host.js';
import { ago } from './hub.js';

const FRAME_MS = 5000;
let layer = null;

export async function openStories(communityId) {
  let data;
  try { data = await api('/api/communities/' + encodeURIComponent(communityId) + '/stories'); }
  catch { toast('Stories could not load.'); return; }
  if (!data.frames.length) { toast('No stories right now.'); return; }
  layer?.remove();
  layer = document.createElement('div');
  layer.className = 'story-viewer'; layer.setAttribute('role', 'dialog'); layer.setAttribute('aria-label', data.community.name + ' stories');
  document.querySelector('#app').append(layer);
  let i = 0, timer = 0, started = 0, left = FRAME_MS, paused = false, startY = null, held = false;
  const opener = document.activeElement;

  function close() { clearTimeout(timer); layer?.remove(); layer = null; removeEventListener('keydown', onKey); opener?.focus?.({ preventScroll: true }); }
  function go(n) { if (n < 0) n = 0; if (n >= data.frames.length) return close(); i = n; left = FRAME_MS; draw(); }
  function schedule() {
    clearTimeout(timer);
    if (reduced || paused) return;
    started = performance.now();
    timer = setTimeout(() => go(i + 1), left);
  }
  function draw() {
    const f = data.frames[i];
    layer.innerHTML = `<div class="sv-bars">${data.frames.map((_, k) => `<span class="${k < i ? 'done' : k === i ? 'now' : ''}"><i style="${k === i && !reduced ? `animation-duration:${left}ms` : ''}"></i></span>`).join('')}</div>
      <header class="sv-head"><span class="p-avatar" aria-hidden="true">${esc(f.emoji)}</span><span><b>${esc(f.author)}</b><small>${esc(data.community.name)} · ${ago(f.created_at)}</small></span>${f.provenance === 'demo_fixture' ? '<span class="pill demo">Demo</span>' : ''}<button class="round" data-sv-close aria-label="Close stories">${svg('close')}</button></header>
      <img class="sv-img" src="${esc(f.image)}" alt="${esc(f.text)}">
      <p class="sv-caption">${esc(f.text)}</p>
      <button class="sv-zone prev" data-sv-prev aria-label="Previous story"></button><button class="sv-zone next" data-sv-next aria-label="Next story"></button>
      <footer class="sv-foot"><button class="btn" data-sv-reply>${svg('bubble', 'ic sm')} Reply in chat</button></footer>`;
    layer.classList.toggle('paused', paused);
    schedule();
  }
  async function reply() {
    close();
    try {
      await api('/api/communities/' + encodeURIComponent(communityId) + '/join', { method: 'POST' });
      dispatchEvent(new CustomEvent('dubaiio:chats-changed'));
      openPage('chat.thread', { id: 'community:' + communityId, title: data.community.name });
    } catch (err) { toast(err.message); }
  }
  function pause(on) {
    if (on === paused) return;
    paused = on;
    if (on) { clearTimeout(timer); left = Math.max(300, left - (performance.now() - started)); }
    layer.classList.toggle('paused', on);
    if (!on) schedule();
  }
  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    if (e.key === 'ArrowRight') go(i + 1);
    if (e.key === 'ArrowLeft') go(i - 1);
    if (e.key === ' ') { e.preventDefault(); pause(!paused); }
  }
  layer.addEventListener('click', e => {
    if (e.target.closest('[data-sv-close]')) return close();
    if (e.target.closest('[data-sv-reply]')) return reply();
    if (held && e.target.closest('.sv-zone')) { held = false; return; }  // a hold pauses; it is not a tap
    if (e.target.closest('[data-sv-next]')) return go(i + 1);
    if (e.target.closest('[data-sv-prev]')) return go(i - 1);
  });
  layer.addEventListener('pointerdown', e => { startY = e.clientY; if (e.target.closest('.sv-zone')) setTimeout(() => { if (startY !== null) { held = true; pause(true); } }, 220); });
  layer.addEventListener('pointerup', e => { if (startY !== null && e.clientY - startY > 90) close(); startY = null; if (paused) pause(false); });
  addEventListener('keydown', onKey);
  draw();
  layer.querySelector('[data-sv-close]').focus({ preventScroll: true });
}
