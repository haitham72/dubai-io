// One host for registered HTML pages and website handoffs across the app.
// Account grants belong to the server; this host never stores or shares tokens.
import { $, esc, svg, openSheet, closeSheet, toast, reduced } from './ui.js';
import { labFetch } from './api-client.js';
import { isPanelPage, panelHash, parsePanelHash, createStack } from './panels.js';
const pages = new Map(), destinations = new Map(), triggers = [];
let sheetHistory = [], wired = false;

export function registerPageTrigger(selector, action) { triggers.push({ selector, action }); }
export function registerPage(id, definition) { pages.set(id, definition); }
export function registerDestination(url, definition) {
  const target = new URL(url); if (target.protocol !== 'https:') throw new Error('HTTPS destination required');
  destinations.set(target.href, definition);
}
function captureParent() {
  const sheet = $('#sheet'), body = $('#sheetBody');
  if (sheet.hidden || !body.querySelector('.page-host')) { sheetHistory = []; return; }
  // Preserve host-owned form values and listeners. Provider frames keep their
  // separate widget lifecycle rather than being reparented as generic pages.
  if (body.querySelector('iframe')) return;
  const fragment = document.createDocumentFragment();
  const scrollTop = body.scrollTop, focusId = document.activeElement?.id;
  while (body.firstChild) fragment.append(body.firstChild);
  sheetHistory.push({ fragment, scrollTop, focusId });
  if (sheetHistory.length > 12) sheetHistory.shift();
}
function back() {
  const previous = sheetHistory.pop(); if (!previous) { closeSheet(); return; }
  const body = openSheet('', () => { sheetHistory = []; });
  body.append(previous.fragment); body.scrollTop = previous.scrollTop;
  body.querySelector('.page-host-content')?.dispatchEvent(new CustomEvent('dubaiio:page-restored'));
  if (previous.focusId) body.querySelector('[id="' + CSS.escape(previous.focusId) + '"]')?.focus({ preventScroll: true });
}
export function openPage(id, context = {}, { replace = false } = {}) {
  const definition = pages.get(id); if (!definition) throw new Error('Unregistered page: ' + id);
  if (isPanelPage(id)) { if (replace && !$('#sheet').hidden) closeSheet(); return openPanel(id, context, definition, { replace }); }
  if (!replace) captureParent();
  const title = typeof definition.title === 'function' ? definition.title(context) : definition.title;
  const html = definition.render(context);
  const body = openSheet(`<section class="page-host" data-page-id="${esc(id)}"><header class="page-host-bar">${sheetHistory.length ? '<button class="round page-host-back" aria-label="Back">' + svg('back') + '</button>' : '<span class="page-host-mark">' + svg('app') + '</span>'}<div><h2 id="sheetTitle">${esc(title)}</h2><span>${esc(definition.source || 'Dubai-io')}</span></div><button class="round page-host-close" aria-label="Close page">${svg('close')}</button></header><div class="page-host-content">${html}</div></section>`, () => { sheetHistory = []; });
  definition.mount?.(body.querySelector('.page-host-content'), context);
  return body;
}
// ---------------------------------------------------------------- panels
// Full-height panels slide in from the right over the current tab (threads, the
// post view, settings). Interruptive UI (approvals, confirms) stays in the sheet.
const stack = createStack(); let hooks = {}, opener = null, lastTap = null, underlay = [], savedScroll = [];
export function configurePanels(h) { hooks = h || {}; }
export const panelDepth = () => stack.size;
const SLIDE_MS = 280;
const baseUrl = () => location.pathname + location.search;
function layer() {
  let el = $('#panels');
  if (!el) { el = document.createElement('div'); el.id = 'panels'; $('#app').append(el); }
  return el;
}
// Safari does not focus buttons on tap, so remember the last control tapped as the opener,
// plus a selector in case its list re-renders while the panel is open.
const selectorFor = el => { if (el.id) return '#' + CSS.escape(el.id); const a = [...el.attributes].find(x => x.name.startsWith('data-')); return a ? `${el.localName}[${a.name}="${CSS.escape(a.value)}"]` : ''; };
function captureOpener() {
  const el = document.activeElement && document.activeElement !== document.body ? document.activeElement : lastTap;
  opener = el ? { el, sel: selectorFor(el), host: el.closest('.tabview, #homeFeed, #svcGrid') || $('#app') } : null;
}
function restoreOpener() {
  const o = opener; opener = null; if (!o) return;
  const go = () => { const el = o.el.isConnected ? o.el : o.sel && o.host.querySelector(o.sel); el?.focus({ preventScroll: true }); };
  go();
  // Lists re-render after a close and drop focus: re-apply it for a moment when that happens.
  const host = o.host, stop = () => { obs.disconnect(); removeEventListener('focusin', stop, true); };
  const obs = new MutationObserver(() => { if (!stack.size && document.activeElement === document.body) go(); });
  obs.observe(host, { childList: true, subtree: true });
  setTimeout(stop, 3000);
}
function lockUnderlay() {
  const keep = new Set(['panels', 'sheet', 'scrim', 'toast']);
  underlay = [...$('#app').children].filter(c => !keep.has(c.id) && !c.inert && !c.classList.contains('notify-host'));
  underlay.forEach(c => { c.inert = true; });
  savedScroll = [...document.querySelectorAll('#app .tabview, #homeFeed, #svcGrid')].map(c => [c, c.scrollTop]);
}
function unlockUnderlay() {
  underlay.forEach(c => { c.inert = false; }); underlay = [];
  savedScroll.forEach(([c, top]) => { c.scrollTop = top; }); savedScroll = [];
  dispatchEvent(new CustomEvent('dubaiio:chats-changed'));
}
function openPanel(id, context, definition, { replace = false, fromHash = false } = {}) {
  if (replace && stack.size) removeTop(true);
  if (!stack.size) { captureOpener(); lockUnderlay(); } else stack.top.el.inert = true;
  const title = (typeof definition.title === 'function' ? definition.title(context) : definition.title) || definition.fallbackTitle || 'Dubai-io';
  const n = Date.now() + '-' + stack.size, el = document.createElement('section');
  el.className = 'panel'; el.dataset.pageId = id; el.setAttribute('role', 'dialog'); el.setAttribute('aria-modal', 'true'); el.setAttribute('aria-labelledby', 'panelTitle-' + n);
  el.innerHTML = `<header class="panel-bar"><button class="round panel-back" aria-label="Back">${svg('back')}</button><div><h2 id="panelTitle-${n}" tabindex="-1">${esc(title)}</h2><span>${esc(definition.source || 'Dubai-io')}</span></div></header><div class="panel-body"><div class="page-host-content page-host">${definition.render(context)}</div></div>`;
  layer().append(el);
  const hash = panelHash(id, context), state = { ...history.state, dubaiioPanel: stack.size + 1 };
  const entry = { el, id, context, hash, pushed: !fromHash && !replace };
  if (fromHash || replace) history.replaceState(state, '', hash || location.href); else history.pushState(state, '', hash || location.href);
  stack.push(entry);
  definition.mount?.(el.querySelector('.page-host-content'), context);
  if (reduced) el.classList.add('in'); else { void el.offsetWidth; requestAnimationFrame(() => el.classList.add('in')); }
  el.querySelector('h2').focus({ preventScroll: true });
  return el.querySelector('.panel-body');
}
function removeTop(instant = false) {
  const entry = stack.pop(); if (!entry) return;
  entry.el.inert = true; entry.el.classList.remove('in');
  const gone = () => entry.el.remove();
  if (instant || reduced) gone(); else setTimeout(gone, SLIDE_MS + 40);
  if (stack.size) { stack.top.el.inert = false; stack.top.el.querySelector('h2')?.focus({ preventScroll: true }); }
  else { unlockUnderlay(); restoreOpener(); }
}
// User-initiated close (back control, Escape): go through history so the browser
// stack stays in step; an entry reached by deep link has no history behind it, so
// replace the URL with its parent instead.
export function closeTopPanel() {
  const top = stack.top; if (!top) return false;
  if (top.pushed) { history.back(); return true; }
  removeTop();
  history.replaceState({ ...history.state, dubaiioPanel: stack.size }, '', stack.top?.hash || baseUrl());
  return true;
}
export function closeAllPanels() { while (stack.size) removeTop(true); }
// Called from the app's popstate handler; returns true when the event was about panels.
export function handlePanelPop(e) {
  const depth = e.state?.dubaiioPanel || 0; let touched = false;
  while (stack.size > depth) { removeTop(); touched = true; }
  if (depth > stack.size) {
    const p = parsePanelHash(location.hash), def = p && pages.get(p.route.page);
    if (def) { openPanel(p.route.page, p.ctx, def, { fromHash: true }); touched = true; }
  }
  return touched;
}
// Reload / shared link: open the panel named by the hash, or land on its parent.
export async function restorePanelFromHash() {
  const p = parsePanelHash(location.hash); if (!p) return false;
  hooks.showView?.(p.route.parent);
  const def = pages.get(p.route.page);
  try {
    if (!def) throw new Error('unregistered');
    if (p.route.probe) {
      const r = await labFetch(p.route.probe(p.ctx.id), { signal: AbortSignal.timeout(6000) });
      if (!r.ok) throw new Error('missing');
      const data = await r.json().catch(() => ({}));
      if (data.thread?.title) p.ctx.title = data.thread.title;
    }
    openPanel(p.route.page, p.ctx, def, { fromHash: true });
  } catch {
    history.replaceState(history.state, '', baseUrl());
    toast('That page is no longer available.');
  }
  return true;
}
export function openDestination(url) {
  const target = new URL(url, location.href);
  if (target.protocol !== 'https:') return false;
  const definition = destinations.get(target.href);
  if (definition?.page) { openPage(definition.page); return true; }
  openPage('website.handoff', { url: target.href, domain: target.hostname, ...definition });
  return true;
}
registerPage('website.handoff', {
  title: c => c.domain,
  source: 'Website · in-app handoff',
  render: c => `<div class="page-handoff"><span class="page-tag">Website</span>${c.embed === true ? '<iframe class="page-web-frame" sandbox="allow-scripts" title="Website preview" src="' + esc(c.url) + '"></iframe><p>If this website does not load, continue on its own site below.</p>' : '<h3>Continue with this provider.</h3><p>This website is not registered for embedded access yet. Keep your conversation here and choose when to open the provider’s site.</p>'}<a class="btn primary wide" href="${esc(c.url)}" data-page-external target="_blank" rel="noopener noreferrer">Continue on website · opens browser ${svg('globe', 'ic sm')}</a><p class="fine">Account connections are managed by Dubai-io. Provider pages never receive your saved OAuth tokens.</p></div>`,
});
export function resetPageHost() { sheetHistory = []; closeAllPanels(); }
export function initPageHost() {
  if (wired) return; wired = true;
  document.addEventListener('click', e => {
    for (const trigger of triggers) {
      const control = e.target.closest(trigger.selector);
      if (control && trigger.action(control) === true) { e.preventDefault(); e.stopPropagation(); return; }
    }
  }, { capture: true });
  document.addEventListener('click', e => { lastTap = e.target.closest?.('button, a[href]') || null; }, { capture: true });
  document.addEventListener('click', e => { if (e.target.closest('.panel-back')) closeTopPanel(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && stack.size && $('#sheet').hidden && !e.defaultPrevented) { e.preventDefault(); closeTopPanel(); } });
  $('#sheetBody').addEventListener('click', e => {
    if (e.target.closest('.page-host-back')) back();
    else if (e.target.closest('.page-host-close')) closeSheet();
  });
  document.addEventListener('click', e => {
    const link = e.target.closest('a[href]');
    if (!link || link.hasAttribute('data-page-external') || e.defaultPrevented || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button > 0) return;
    const url = new URL(link.href, location.href);
    if (url.protocol !== 'https:' || url.origin === location.origin) return;
    e.preventDefault(); openDestination(url.href);
  });
}
