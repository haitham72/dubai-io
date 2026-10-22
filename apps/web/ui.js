import { getFacts, saveFacts } from './session-state.js';
// Shared UI helpers for the lab modules. DOM lookups are lazy, so modules can
// import this before app.js has inserted the shell.
export const ICON = {
  search: '<circle cx="11" cy="11" r="6.5" /><path d="M16 16l4.5 4.5" />',
  orb: '<circle cx="12" cy="12" r="8" /><path d="M8.5 13.5c1.8 1.6 5.2 1.6 7 0" />',
  grid: '<rect x="4" y="4" width="7" height="7" rx="2" /><rect x="13" y="4" width="7" height="7" rx="2" /><rect x="4" y="13" width="7" height="7" rx="2" /><rect x="13" y="13" width="7" height="7" rx="2" />',
  person: '<circle cx="12" cy="8" r="4" /><path d="M4.5 20c1.4-3.6 4.2-5.4 7.5-5.4s6.1 1.8 7.5 5.4" />',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6" />',
  up: '<path d="M12 19V5M6 11l6-6 6 6" />',
  back: '<path d="M15 5l-7 7 7 7" />',
  chev: '<path d="M9 5l7 7-7 7" />',
  close: '<path d="M6 6l12 12M18 6L6 18" />',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21" />',
  wifi: '<path d="M2.5 9a14 14 0 0 1 19 0M5.5 12.2a9.5 9.5 0 0 1 13 0M8.6 15.4a5 5 0 0 1 6.8 0" /><circle cx="12" cy="18.6" r="1.1" />',
  check: '<path d="M5 12.5l4.2 4.2L19 7" />',
  lock: '<rect x="5" y="10.5" width="14" height="10" rx="2.5" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" />',
  play: '<path d="M8 5.5v13l11-6.5z" />',
  star: '<path d="M12 3.5l2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8L3.5 9.7l5.9-.8z" />',
  paw: '<circle cx="7" cy="9" r="1.8" /><circle cx="11" cy="6" r="1.8" /><circle cx="15.5" cy="7" r="1.8" /><circle cx="18" cy="11" r="1.6" /><path d="M8.5 17.5c0-3 2-5.5 4.2-5.5 2.4 0 4.3 2.5 4.3 5.2 0 2-1.6 2.6-4.2 2.3-2.4.3-4.3.2-4.3-2z" />',
  fork: '<path d="M7 3v8M5 3v5a2 2 0 0 0 4 0V3M7 11v10M17 3c-2 1-3 3.5-3 6.5V13h3v8" />',
  cup: '<path d="M4 9h12v5a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5zM16 10h1.5a2.5 2.5 0 0 1 0 5H16M8 3c-.8 1 .8 2 0 3M12 3c-.8 1 .8 2 0 3" />',
  scissors: '<circle cx="6" cy="7" r="2.6" /><circle cx="6" cy="17" r="2.6" /><path d="M8.2 8.4L20 17M8.2 15.6L20 7" />',
  home: '<path d="M4 11l8-7 8 7M6 9.5V20h12V9.5M10 20v-5h4v5" />',
  drop: '<path d="M12 3c3 4 6 7 6 11a6 6 0 0 1-12 0c0-4 3-7 6-11z" />',
  bag: '<path d="M5 8h14l-1 12H6zM9 8V6a3 3 0 0 1 6 0v2" />',
  wrench: '<path d="M14.5 6.5a4 4 0 0 0 5 5L13 18a2.1 2.1 0 0 1-3-3l6.5-6.5a4 4 0 0 0-5-5l2.5 2.5-1.5 1.5z" />',
  dots: '<circle cx="6" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="18" cy="12" r="1.6" />',
  pin: '<path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" /><circle cx="12" cy="10" r="2.3" />',
  nav: '<path d="M4 11.5L20 4l-7.5 16-1.8-6.7z" />',
  phone: '<path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 0 0 6 6l1.5-2 4 1.5v3a2 2 0 0 1-2 2A16 16 0 0 1 4.5 5.5a2 2 0 0 1 2-2z" />',
  cal: '<rect x="4" y="5" width="16" height="15" rx="2.5" /><path d="M4 10h16M9 3v4M15 3v4" />',
  app: '<rect x="6" y="3" width="12" height="18" rx="3" /><path d="M10.5 18h3" />',
  clock: '<circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" />',
  map: '<path d="M9 4.5L3.5 6.5v13l5.5-2 6 2 5.5-2v-13l-5.5 2z" /><path d="M9 4.5v13M15 6.5v13" />',
  spark: '<path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" />',
  globe: '<circle cx="12" cy="12" r="8.5" /><path d="M3.5 12h17M12 3.5c2.6 2.5 3.8 5.3 3.8 8.5s-1.2 6-3.8 8.5c-2.6-2.5-3.8-5.3-3.8-8.5s1.2-6 3.8-8.5z" />',
  store: '<path d="M4 9l1.5-5h13L20 9M4 9v11h16V9M4 9h16M9 20v-6h6v6" />',
  tag: '<path d="M3.5 12.5V4h8.5l8.5 8.5-8.5 8.5z" /><circle cx="8" cy="8.5" r="1.4" />',
  plane: '<path d="M21 15.5l-8-4.5V5a1.5 1.5 0 0 0-3 0v6l-8 4.5V17l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-4.5l8 2.5z" />',
  wallet: '<rect x="3.5" y="6" width="17" height="13" rx="2.5" /><path d="M16 12.5h4.5M3.5 9.5h17M6 6l9-3 1.5 3" />',
  taxi: '<path d="M5 16V11l2-4h10l2 4v5M4 16h16v3H4zM9 4.5h6M7.5 13h.01M16.5 13h.01" />',
  train: '<rect x="6" y="3.5" width="12" height="13" rx="3" /><path d="M6 11h12M9 20l-2 1.5M15 20l2 1.5M9.5 14h.01M14.5 14h.01" />',
  shield: '<path d="M12 3.5l7.5 3v5.5c0 4.5-3.2 7.8-7.5 9-4.3-1.2-7.5-4.5-7.5-9V6.5z" />',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" /><circle cx="12" cy="12" r="3" />',
};
export const svg = (name, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ICON.dots}</svg>`;
export const $ = (s, r = document) => r.querySelector(s);
export const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
export const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
export const wait = ms => new Promise(r => setTimeout(r, reduced ? 0 : ms));

let toastTimer = 0;
export function toast(msg) {
  const t = $('#toast'); if (!t) return;
  t.textContent = msg; t.hidden = false; t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.classList.remove('show'); setTimeout(() => { t.hidden = true; }, 250); }, 2800);
}

let sheetOnClose = null, sheetHideTimer = 0, sheetGeneration = 0, sheetReturnFocus = null;
export function openSheet(html, onClose) {
  const sheet = $('#sheet'), scrim = $('#scrim'), body = $('#sheetBody');
  clearTimeout(sheetHideTimer);
  const generation = ++sheetGeneration;
  if (sheet.hidden || !sheet.classList.contains('open')) sheetReturnFocus = document.activeElement;
  body.innerHTML = html; sheetOnClose = onClose || null;
  sheet.hidden = false; scrim.hidden = false;
  requestAnimationFrame(() => {
    if (generation !== sheetGeneration) return;
    sheet.classList.add('open'); scrim.classList.add('open');
    if (!body.contains(document.activeElement)) (body.querySelector('[autofocus]') || body.querySelector('.page-host-back, .page-host-close, button, input, textarea, a[href]') || $('#sheetClose')).focus({ preventScroll: true });
  });
  body.scrollTop = 0;
  return body;
}
export function closeSheet() {
  const sheet = $('#sheet'), scrim = $('#scrim');
  if (!sheet || sheet.hidden) return;
  const generation = ++sheetGeneration;
  sheet.classList.remove('open'); scrim.classList.remove('open');
  clearTimeout(sheetHideTimer);
  sheetHideTimer = setTimeout(() => {
    if (generation !== sheetGeneration) return;
    sheet.hidden = true; scrim.hidden = true;
    document.dispatchEvent(new CustomEvent('dubaiio:sheet-closed'));
    if (sheetReturnFocus?.isConnected) sheetReturnFocus.focus({ preventScroll: true });
    sheetReturnFocus = null;
  }, reduced ? 0 : 320);
  const f = sheetOnClose; sheetOnClose = null; f?.();
}
// Keep keyboard navigation inside whichever host/provider sheet is open.
document.addEventListener('keydown', e => {
  const sheet = $('#sheet'); if (!sheet || sheet.hidden || !sheet.classList.contains('open')) return;
  if (e.key === 'Escape') { e.preventDefault(); closeSheet(); return; }
  if (e.key !== 'Tab') return;
  const controls = [...sheet.querySelectorAll('button, a[href], input, textarea, select, iframe, [tabindex]')]
    .filter(el => !el.disabled && el.tabIndex >= 0 && el.getClientRects().length && !el.closest('[hidden]'));
  const first = controls[0], last = controls.at(-1);
  if (!first) { e.preventDefault(); return; }
  if (e.shiftKey && (document.activeElement === first || !sheet.contains(document.activeElement))) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && (document.activeElement === last || !sheet.contains(document.activeElement))) { e.preventDefault(); first.focus(); }
});

// A tiny in-memory store for what the user told us during this session
// (belt, taxi plate). Shown back with "You told me"; never inferred.
const restoredFacts = getFacts();
if (typeof restoredFacts.trip?.at === 'string') { const date = new Date(restoredFacts.trip.at); restoredFacts.trip.at = Number.isFinite(date.getTime()) ? date : null; }
export const told = new Proxy(restoredFacts, { set(target,key,value){target[key]=value;saveFacts(target);return true;},deleteProperty(target,key){delete target[key];saveFacts(target);return true;} });

// Dubai local time for time-aware advice.
export function dubaiNow() {
  const parts = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dubai', weekday: 'short', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date());
  const get = t => parts.find(p => p.type === t)?.value;
  return { day: get('weekday'), h: +get('hour') % 24, m: +get('minute') };
}
