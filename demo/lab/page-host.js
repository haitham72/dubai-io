// One host for registered HTML pages and website handoffs across the app.
// Account grants belong to the server; this host never stores or shares tokens.
import { $, esc, svg, openSheet, closeSheet } from './ui.js';
const pages = new Map(), destinations = new Map(), triggers = [];
let history = [], wired = false;

export function registerPageTrigger(selector, action) { triggers.push({ selector, action }); }
export function registerPage(id, definition) { pages.set(id, definition); }
export function registerDestination(url, definition) {
  const target = new URL(url); if (target.protocol !== 'https:') throw new Error('HTTPS destination required');
  destinations.set(target.href, definition);
}
function captureParent() {
  const sheet = $('#sheet'), body = $('#sheetBody');
  if (sheet.hidden || !body.querySelector('.page-host')) { history = []; return; }
  // Preserve host-owned form values and listeners. Provider frames keep their
  // separate widget lifecycle rather than being reparented as generic pages.
  if (body.querySelector('iframe')) return;
  const fragment = document.createDocumentFragment();
  const scrollTop = body.scrollTop, focusId = document.activeElement?.id;
  while (body.firstChild) fragment.append(body.firstChild);
  history.push({ fragment, scrollTop, focusId });
  if (history.length > 12) history.shift();
}
function back() {
  const previous = history.pop(); if (!previous) { closeSheet(); return; }
  const body = openSheet('', () => { history = []; });
  body.append(previous.fragment); body.scrollTop = previous.scrollTop;
  if (previous.focusId) body.querySelector('[id="' + CSS.escape(previous.focusId) + '"]')?.focus({ preventScroll: true });
}
export function openPage(id, context = {}, { replace = false } = {}) {
  const definition = pages.get(id); if (!definition) throw new Error('Unregistered page: ' + id);
  if (!replace) captureParent();
  const title = typeof definition.title === 'function' ? definition.title(context) : definition.title;
  const html = definition.render(context);
  const body = openSheet(`<section class="page-host" data-page-id="${esc(id)}"><header class="page-host-bar">${history.length ? '<button class="round page-host-back" aria-label="Back">' + svg('back') + '</button>' : '<span class="page-host-mark">' + svg('app') + '</span>'}<div><h2 id="sheetTitle">${esc(title)}</h2><span>${esc(definition.source || 'Dubai-io')}</span></div><button class="round page-host-close" aria-label="Close page">${svg('close')}</button></header><div class="page-host-content">${html}</div></section>`, () => { history = []; });
  definition.mount?.(body.querySelector('.page-host-content'), context);
  return body;
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
export function resetPageHost() { history = []; }
export function initPageHost() {
  if (wired) return; wired = true;
  document.addEventListener('click', e => {
    for (const trigger of triggers) {
      const control = e.target.closest(trigger.selector);
      if (control && trigger.action(control) === true) { e.preventDefault(); e.stopPropagation(); return; }
    }
  }, { capture: true });
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
