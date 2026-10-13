// Home v2 lab. Flow: airport Wi-Fi portal (sponsored card) -> soft card-by-card
// intro -> Home coverflow with the composer at the bottom -> ask for a service
// -> cards fly up and dissolve -> full-screen map with floating glass menus and
// a draggable results sheet (Uber / Talabat style).
// Flags (query or hash, hash tokens joined by '.'): fps, tune, nogl, intro,
// wifi, services, profile.
import { createRenderer } from './gl.js';
import { VARIANT } from './shaders.js';
import { PALETTES, ONBOARDING, CASES, PROFILE_CARD, CATEGORIES, PLACES, SOURCES, EPISODES, HYPOTHESES, TOLD_LABELS } from './data.js';
import { profileAt } from './profile.js';
import { createMap, km } from './map.js';

// ---------------------------------------------------------------- setup
const flags = (() => {
  const f = new Set();
  new URLSearchParams(location.search).forEach((v, k) => f.add(k));
  location.hash.replace(/^#/, '').split('.').filter(Boolean).forEach(t => f.add(t));
  return f;
})();
const paletteName = window.PALETTE in PALETTES ? window.PALETTE : 'cyan';
const palette = PALETTES[paletteName];
const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
const store = {
  get(k) { try { return localStorage.getItem('dubaiio.lab.' + k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem('dubaiio.lab.' + k, v); } catch { /* private mode */ } },
};

const ICON = {
  orb: '<circle cx="12" cy="12" r="8" /><path d="M8.5 13.5c1.8 1.6 5.2 1.6 7 0" />',
  grid: '<rect x="4" y="4" width="7" height="7" rx="2" /><rect x="13" y="4" width="7" height="7" rx="2" /><rect x="4" y="13" width="7" height="7" rx="2" /><rect x="13" y="13" width="7" height="7" rx="2" />',
  civic: '<path d="M4 20h16M6 20v-8M10 20v-8M14 20v-8M18 20v-8M3 10l9-6 9 6z" />',
  person: '<circle cx="12" cy="8" r="4" /><path d="M4.5 20c1.4-3.6 4.2-5.4 7.5-5.4s6.1 1.8 7.5 5.4" />',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6" />',
  up: '<path d="M12 19V5M6 11l6-6 6 6" />',
  back: '<path d="M15 5l-7 7 7 7" />',
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
};
const svg = (name, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ICON.dots}</svg>`;
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const catOf = id => CATEGORIES.find(c => c.id === id);
const fmtN = n => n.toLocaleString('en-US');

document.documentElement.dataset.palette = paletteName;
document.body.insertAdjacentHTML('beforeend', `
<div id="app" class="mode-home ${reduced ? 'reduced' : ''}">
  <canvas id="gl" aria-hidden="true"></canvas>
  <header class="top">
    <div class="brand"><b>Dubai-io</b><span class="area">${svg('pin', 'ic xs')} Dubai Marina · you told me</span></div>
    <span class="pill demo" title="Everything here is demo data">Demo data</span>
  </header>
  <main id="stage" aria-roledescription="carousel" aria-label="Home cards"></main>
  <nav class="rail" id="rail" aria-label="Cards"></nav>
  <p class="caption" id="caption" aria-live="polite"></p>

  <section id="results" class="results" aria-label="Services map">
    <div id="mapEl" class="mapbox"></div>
    <div class="map-fallback" id="mapFallback" hidden>Map needs WebGL. The list below has every place.</div>
    <div class="r-top">
      <button class="round glass" id="back" aria-label="Back to Home">${svg('back')}</button>
      <div class="ask glass" id="ask" hidden></div>
      <span class="pill demo">Demo data</span>
    </div>
    <div class="r-chips" id="rChips"></div>
    <div class="r-chips sub" id="rSubs"></div>
    <section class="rsheet" id="rsheet" aria-label="Results">
      <button class="grab" id="rGrab" aria-label="Expand or collapse results"><span></span></button>
      <div class="rs-scroll" id="rsScroll"></div>
    </section>
  </section>

  <form class="composer glass" id="composer" role="search" autocomplete="off">
    <label class="sr" for="q">Ask Dubai-io</label>
    <input id="q" name="q" type="text" placeholder="Ask for anything nearby" enterkeyhint="send" />
    <button type="button" class="c-mic" id="mic" aria-label="Voice (typed in this lab)">${svg('mic', 'ic sm')}</button>
    <button type="submit" class="c-send" aria-label="Send">${svg('up', 'ic sm')}</button>
  </form>

  <nav class="tabbar glass" aria-label="Tabs">
    <button data-tab="home" aria-current="page">${svg('orb')}<span>io</span></button>
    <button data-tab="maps">${svg('map')}<span>Maps</span></button>
    <button data-tab="services">${svg('grid')}<span>Services</span></button>
    <button data-tab="me">${svg('person')}<span>Me</span></button>
  </nav>

  <section class="svcgrid" id="svcGrid" aria-label="Services">
    <div class="sg-head"><h2>Services</h2><p>Everything Dubai-io can find for you near Dubai Marina. New categories arrive as data, so this grid grows on its own.</p></div>
    <div class="sg-grid" id="sgGrid"></div>
  </section>

  <div class="scrim" id="scrim" hidden></div>
  <section class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle" hidden>
    <button class="grab" id="sheetClose" aria-label="Close"><span></span></button>
    <div class="sheet-body" id="sheetBody"></div>
  </section>

  <section class="portal" id="portal" hidden aria-label="Airport Wi-Fi sign-in (demo)">
    <div class="p-bg" style="background-image:url('media/airport-plane.jpg')"></div>
    <div class="p-status"><span>21:42</span><span>${svg('wifi', 'ic xs')}</span></div>
    <button class="p-notif" id="pNotif">
      <span class="p-ic">${svg('wifi', 'ic sm')}</span>
      <span class="p-txt"><b>Sign in to Wi-Fi network</b><span>Airport Free Wi-Fi (demo)</span></span>
    </button>
    <div class="p-web" id="pWeb">
      <div class="p-chrome">${svg('lock', 'ic xs')}<span>Airport Free Wi-Fi · sign-in (demo)</span><button id="pDone">Done</button></div>
      <div class="p-page">
        <div class="p-hero" style="background-image:url('media/airport-plane.jpg')">
          <p class="p-kicker">Welcome to Dubai</p>
          <h1>Free Wi-Fi at the airport</h1>
          <button class="p-btn" id="pOnline">Get online now</button>
          <p class="p-terms">I agree to the terms and conditions (demo)</p>
        </div>
        <div class="p-connected" id="pConnected" hidden>${svg('check', 'ic sm')} You’re online (demo)</div>
        <article class="p-sponsor" id="pSponsor">
          <span class="p-tag">Sponsored</span>
          <div class="p-sp-row"><span class="p-orb"></span><div><b>Dubai-io</b><span>Your Dubai companion</span></div></div>
          <p>Guides you from the gate to your hotel, remembers your taxi, and books local shops at their published prices. You approve everything that leaves your phone.</p>
          <button class="p-cta" id="pOpen">Open Dubai-io ${svg('arrow', 'ic sm')}</button>
        </article>
        <p class="p-fine">Concept mock of a sponsored airport Wi-Fi page. Not an airport or operator page.</p>
      </div>
    </div>
  </section>

  <div class="toast" id="toast" role="status" hidden></div>
  <div class="fps" id="fps" hidden></div>
  <div class="tune glass" id="tune" hidden></div>
</div>`);

const app = $('#app'), canvas = $('#gl'), stageEl = $('#stage'), railEl = $('#rail'), captionEl = $('#caption');
const renderer = flags.has('nogl') ? null : createRenderer(canvas, palette);
if (!renderer) app.classList.add('nogl');

// ---------------------------------------------------------------- state
const T0 = Date.parse('2026-10-01T00:00:00'), T1 = Date.parse('2026-10-13T23:00:00');
const S = {
  mode: 'onboard', deck: [], pos: 0, vel: 0, target: 0, drag: null,
  tilt: [0, 0], tiltTarget: [0, 0], view: 'home', maxDpr: 3,
  tune: { ribs: 8.5, foil: 1, grain: 0.07, aura: 0.95 },
  shape: { falloff: 2.4, height: 0.85, glow: 0.24 },
  overrides: {}, asOf: T1, active: -1,
  lift: 0, liftFrom: 0, liftTo: 0, liftStart: 0, liftDur: 820,
  ask: null, cat: 'all', sub: null, src: null, detail: null, snap: 'peek',
};
const G = {};
window.__lab = { S, G };
let seedN = 1;
const mkCard = def => ({ ...def, variant: VARIANT[def.kind] ?? 0, seed: (seedN++ * 7.31) % 13, rev: reduced ? 1 : 0, revStart: 0, revDur: 1100, out: false, el: null });

// ---------------------------------------------------------------- layout
function layout() {
  const r = app.getBoundingClientRect();
  const s = stageEl.getBoundingClientRect();
  Object.assign(G, { W: r.width, H: r.height, sx: s.left - r.left, sy: s.top - r.top, sw: s.width, sh: s.height });
  G.cw = Math.round(Math.min(318, G.sw * 0.78));
  G.ch = Math.round(Math.min(G.sh * 0.96, G.cw * 1.46));
  G.bandH = Math.round(G.ch * 0.52);
  G.cx = G.sx + G.sw / 2; G.cy = G.sy + G.sh / 2;
  G.spacing = G.cw * 0.84; G.P = 1100; G.radius = 28;
  app.style.setProperty('--cw', G.cw + 'px');
  app.style.setProperty('--ch', G.ch + 'px');
  app.style.setProperty('--band', G.bandH + 'px');
  canvas.style.width = G.W + 'px'; canvas.style.height = G.H + 'px';
  renderer?.resize(G.W, G.H, S.maxDpr);
  G.snaps = { peek: 300, half: Math.round(G.H * 0.56), full: Math.round(G.H - 120) };
  setSnap(S.snap, true);
  MAP?.resize();
}

const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
function params(i) {
  const d = i - S.pos, ad = Math.abs(d), sg = Math.sign(d);
  const c = S.deck[i];
  const e = 1 - Math.pow(1 - c.rev, 3);
  // fly-up: the centre card leaves first, neighbours follow
  const li = Math.max(0, Math.min(1, S.lift * 1.35 - ad * 0.16));
  const fl = li * li * (3 - 2 * li);
  return {
    d, ad, fl,
    tx: sg * (Math.min(ad, 1) * G.spacing + Math.max(ad - 1, 0) * G.cw * 0.26),
    ty: (1 - e) * 26 - fl * (G.H * 0.72),
    rot: -sg * Math.min(ad, 1) * 18 * Math.PI / 180,
    sc: (1 - 0.13 * Math.min(ad, 1) - 0.05 * Math.max(ad - 1, 0)) * (1 + 0.07 * fl),
  };
}
function project(x, y, p) {
  const xs = x * p.sc, ys = y * p.sc;
  const c = Math.cos(p.rot), sn = Math.sin(p.rot);
  const x1 = xs * c, z1 = -xs * sn;
  const f = G.P / (G.P - z1);
  return [G.cx + (x1 + p.tx) * f, G.cy + (ys + p.ty) * f, (G.P - z1) / G.P];
}

// ---------------------------------------------------------------- cards
function cardHTML(c, i) {
  const next = c.next ? `<button class="next ${c.next === 'Start' ? 'primary' : ''}" data-act="next">${esc(c.next)} ${svg('arrow', 'ic sm')}</button>` : '';
  const body = c.id === 'you' ? `<ul class="mini" id="youMini"></ul>` : `<p>${esc(c.body)}</p>`;
  return `<article class="card ${c.kind}" data-i="${i}" aria-label="${esc(c.title)}" tabindex="-1">
    <div class="band" style="${!renderer ? bandFallback(c) : ''}"><span class="eyebrow">${esc(c.eyebrow)}</span><h2>${esc(c.title)}</h2></div>
    <div class="body">${body}<div class="foot"><span class="meta">${c.meta.map(m => `<span>${esc(m)}</span>`).join('')}</span>${next}</div></div>
  </article>`;
}
function bandFallback(c) {
  if (c.img) return `background-image:url('${c.img}')`;
  const r = palette.ramp;
  return `background:linear-gradient(135deg, ${r[0]}, ${r[2]} 45%, ${r[3]} 75%, ${palette.fringe[2]})`;
}
function mountDeck() {
  stageEl.innerHTML = S.deck.map(cardHTML).join('');
  S.deck.forEach((c, i) => { c.el = stageEl.children[i]; });
  buildRail(); renderYouMini(); S.active = -1;
}
function appendCard(c) {
  S.deck.push(c);
  stageEl.insertAdjacentHTML('beforeend', cardHTML(c, S.deck.length - 1));
  c.el = stageEl.lastElementChild;
  buildRail();
}
function reveal(c, delay = 0, dur = 1100) { c.out = false; c.revStart = performance.now() + delay; c.revDur = dur; if (reduced) c.rev = 1; }
function buildRail() {
  railEl.innerHTML = S.deck.map((c, i) => {
    const bg = c.img ? `background-image:url('${c.img}')` : `background:radial-gradient(circle at 30% 30%, ${palette.ramp[3]}, ${palette.ramp[1]} 60%, ${palette.ramp[0]})`;
    return `<button class="dot" data-i="${i}" style="${bg}" aria-label="${esc(c.title)}"></button>`;
  }).join('');
}

// ---------------------------------------------------------------- flows: portal, intro, home
function startPortal() {
  const P = $('#portal');
  P.hidden = false; P.className = 'portal'; app.classList.add('mode-portal');
  $('#pOnline').hidden = false; $('#pOnline').disabled = false; $('#pOnline').textContent = 'Get online now';
  $('#pConnected').hidden = true; $('#pSponsor').classList.remove('lit');
  requestAnimationFrame(() => P.classList.add('in'));
  setTimeout(() => P.classList.add('notif'), reduced ? 0 : 700);
}
$('#pNotif').addEventListener('click', () => $('#portal').classList.add('web'));
$('#pOnline').addEventListener('click', () => {
  $('#pOnline').disabled = true; $('#pOnline').textContent = 'Connecting…';
  setTimeout(() => { $('#pOnline').hidden = true; $('#pConnected').hidden = false; $('#pSponsor').classList.add('lit'); }, reduced ? 0 : 900);
});
$('#pDone').addEventListener('click', () => toast('Tap Open Dubai-io to continue.'));
$('#pOpen').addEventListener('click', () => {
  const P = $('#portal');
  P.classList.add('out');
  setTimeout(() => { P.hidden = true; P.className = 'portal'; app.classList.remove('mode-portal'); startOnboarding(); }, reduced ? 0 : 650);
});

function startOnboarding() {
  S.mode = 'onboard';
  S.deck = [mkCard(ONBOARDING[0])];
  S.pos = S.target = 0; S.vel = 0;
  mountDeck();
  reveal(S.deck[0], 200, 1400);
}
function advance() {
  if (S.mode !== 'onboard') return;
  const at = Math.round(S.pos);
  if (at < S.deck.length - 1) { S.target = at + 1; return; }
  if (S.deck.length < ONBOARDING.length) {
    const c = mkCard(ONBOARDING[S.deck.length]);
    appendCard(c); reveal(c, 160, 1200); S.target = S.deck.length - 1;
  } else finishOnboarding();
}
function finishOnboarding() {
  store.set('onboarded', '1');
  const now = performance.now();
  S.deck.forEach(c => { c.out = true; c.revStart = now; c.revDur = 520; });
  setTimeout(buildHome, reduced ? 0 : 560);
}
function homeOrder() {
  const p = profileAt(EPISODES, HYPOTHESES, S.asOf, S.overrides);
  const byId = Object.fromEntries([...p.noticed, ...p.confirmed].map(h => [h.id, h]));
  return CASES.map((c, k) => {
    const h = c.because && byId[c.because];
    const boost = h && (h.surfaced || h.provenance === 'user_supplied') ? h.conf : 0;
    return { c, h: boost ? h : null, score: boost * 10 - k };
  }).sort((a, b) => b.score - a.score);
}
function buildHome() {
  S.mode = 'home';
  S.deck = [mkCard(PROFILE_CARD), ...homeOrder().map(o => mkCard({ ...o.c, becauseHyp: o.h }))];
  S.pos = S.target = 1; S.vel = 0;
  mountDeck();
  S.deck.forEach((c, i) => reveal(c, 120 + Math.abs(i - 1) * 140, 1000));
}
function captionFor(c) {
  if (!c) return '';
  if (S.mode === 'onboard') return c.next === 'Start' ? 'Tap Start, or swipe back to read again.' : 'Swipe, or tap Next. Or just ask below.';
  if (c.becauseHyp) {
    const h = c.becauseHyp;
    const tag = h.provenance === 'user_supplied' ? 'you confirmed' : `I noticed, ${Math.round(h.conf * 100)}%`;
    return `<span class="because">Because</span> ${esc(h.label.toLowerCase())} <span class="tag">${tag}</span>`;
  }
  return esc(c.caption || '');
}
function renderYouMini() {
  const ul = $('#youMini'); if (!ul) return;
  const p = profileAt(EPISODES, HYPOTHESES, S.asOf, S.overrides);
  const rows = [
    ...p.told.slice(0, 1).map(t => ({ label: `${TOLD_LABELS[t.key] || t.key}: ${t.value}`, tag: 'You told me', conf: 1 })),
    ...p.noticed.filter(h => h.surfaced).slice(0, 3).map(h => ({ label: h.label, tag: `${Math.round(h.conf * 100)}%`, conf: h.conf })),
  ];
  ul.innerHTML = rows.map(r => `<li><span class="lbl">${esc(r.label)}</span><span class="cf"><i style="--c:${r.conf}"></i>${esc(r.tag)}</span></li>`).join('');
}

// ---------------------------------------------------------------- loop
let last = performance.now(), fpsAcc = 0, fpsN = 0, lowFor = 0;
function frame(now) {
  const dt = Math.min(0.033, (now - last) / 1000); last = now;
  const n = S.deck.length;
  if (!S.drag) {
    if (reduced) { S.pos = S.target; S.vel = 0; }
    else {
      const a = -210 * (S.pos - S.target) - 27 * S.vel;
      S.vel += a * dt; S.pos += S.vel * dt;
      if (Math.abs(S.pos - S.target) < 1e-4 && Math.abs(S.vel) < 1e-3) { S.pos = S.target; S.vel = 0; }
    }
  }
  for (let k = 0; k < 2; k++) {
    if (!S.drag) S.tiltTarget[k] *= Math.pow(0.02, dt);
    S.tilt[k] += (S.tiltTarget[k] - S.tilt[k]) * Math.min(1, dt * 9);
  }
  if (S.lift !== S.liftTo) {
    const t = reduced ? 1 : Math.min(1, (now - S.liftStart) / S.liftDur);
    S.lift = S.liftFrom + (S.liftTo - S.liftFrom) * ease(t);
    if (t >= 1) S.lift = S.liftTo;
  }
  const stageVisible = S.lift < 0.999;
  stageEl.style.visibility = stageVisible ? 'visible' : 'hidden';

  const time = reduced ? 8 : now / 1000;
  const glCards = [], auras = [];
  if (stageVisible) for (let i = 0; i < n; i++) {
    const c = S.deck[i];
    if (!reduced && now >= c.revStart) {
      const t = Math.min(1, (now - c.revStart) / c.revDur);
      c.rev = c.out ? 1 - t : t;
    }
    const p = params(i);
    const el = c.el;
    const vis = c.rev * (1 - p.fl);
    if (p.ad > 2.6 || vis <= 0.002) { if (el.style.visibility !== 'hidden') el.style.visibility = 'hidden'; continue; }
    el.style.visibility = 'visible';
    el.style.transform = `translate3d(${p.tx.toFixed(2)}px, ${p.ty.toFixed(2)}px, 0) rotateY(${p.rot.toFixed(4)}rad) scale(${p.sc.toFixed(4)})`;
    el.style.zIndex = String(100 - Math.round(p.ad * 10));
    el.style.opacity = String(Math.min(1, c.rev * 1.5) * Math.pow(1 - p.fl, 1.3));
    const blur = (1 - c.rev) * 12 + p.fl * 10;
    el.style.filter = blur > 0.05 ? `blur(${blur.toFixed(1)}px)` : 'none';
    el.style.setProperty('--dim', (Math.min(p.ad, 1) * 0.22).toFixed(3));
    el.classList.toggle('is-center', p.ad < 0.5);
    if (renderer) {
      const hw = G.cw / 2, top = -G.ch / 2, bot = top + G.bandH;
      const quad = [project(-hw, top, p), project(hw, top, p), project(-hw, bot, p), project(hw, bot, p)];
      const tilt = p.ad < 0.6 ? S.tilt : [S.tilt[0] * 0.3 - p.d * 0.4, S.tilt[1] * 0.3];
      const card = { quad, variant: c.variant, img: c.img, holo: c.holo || 0, rev: Math.max(0, vis), seed: c.seed,
        dim: Math.min(p.ad, 1) * 0.22, w: G.cw, bandH: G.bandH, radius: G.radius, tilt, ad: p.ad };
      glCards.push(card);
      if (p.ad < 0.7) {
        const xs = quad.map(q => q[0]), ys = quad.map(q => q[1]);
        card.bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        card.bottom = project(0, G.ch / 2, p)[1];
        auras.push({ card, weight: Math.pow(1 - p.ad / 0.7, 1.6) * (1 - p.fl) });
      }
    }
  }
  const active = Math.max(0, Math.min(n - 1, Math.round(S.pos)));
  if (active !== S.active) {
    S.active = active;
    [...railEl.children].forEach((d, i) => d.setAttribute('aria-current', i === active ? 'true' : 'false'));
    captionEl.innerHTML = captionFor(S.deck[active]);
  }
  if (renderer && !document.hidden && stageVisible) {
    glCards.sort((a, b) => b.ad - a.ad);
    auras.sort((a, b) => b.weight - a.weight);
    renderer.render({ cards: glCards, auras: auras.slice(0, 2), time, tune: S.tune, shape: S.shape });
  }
  fpsAcc += dt; fpsN++;
  if (fpsAcc >= 0.5) {
    const fps = fpsN / fpsAcc; fpsAcc = 0; fpsN = 0;
    lowFor = fps < 45 && stageVisible ? lowFor + 0.5 : 0;
    if (lowFor >= 2 && S.maxDpr > 1.25) { S.maxDpr = S.maxDpr > 2 ? 2 : 1.5; lowFor = 0; layout(); }
    if (flags.has('fps')) $('#fps').textContent = `${fps.toFixed(0)} fps · dpr ${renderer ? renderer.dpr.toFixed(2) : '-'} · ${renderer ? 'webgl2' : 'no gl'}`;
  }
  requestAnimationFrame(frame);
}
function setLift(to) { S.liftFrom = S.lift; S.liftTo = to; S.liftStart = performance.now(); }

// ---------------------------------------------------------------- stage input
function onDown(e) {
  if (S.view !== 'home' || e.button > 0 || e.target.closest('button')) return;
  S.drag = { x: e.clientX, pos: S.pos, lastX: e.clientX, lastT: performance.now(), v: 0, moved: false, id: e.pointerId, card: e.target.closest('.card') };
  stageEl.setPointerCapture(e.pointerId);
  const r = S.drag.card;
  if (r && r.classList.contains('is-center')) {
    const b = r.getBoundingClientRect();
    S.tiltTarget = [((e.clientX - b.left) / b.width - 0.5) * 1.6, ((e.clientY - b.top) / b.height - 0.5) * 1.6];
  }
}
function onMove(e) {
  const d = S.drag; if (!d || e.pointerId !== d.id) return;
  const dx = e.clientX - d.x;
  if (Math.abs(dx) > 6) d.moved = true;
  const now = performance.now();
  d.v = d.v * 0.7 + ((e.clientX - d.lastX) / Math.max(1, now - d.lastT)) * 0.3; d.lastX = e.clientX; d.lastT = now;
  let pos = d.pos - dx / G.spacing; const max = S.deck.length - 1;
  if (pos < 0) pos *= 0.35; else if (pos > max) pos = max + (pos - max) * 0.35;
  S.pos = pos;
  S.tiltTarget = [Math.max(-1, Math.min(1, -d.v * 0.9)), S.tiltTarget[1] * 0.9];
}
function onUp(e) {
  const d = S.drag; if (!d || e.pointerId !== d.id) return;
  S.drag = null;
  const max = S.deck.length - 1;
  if (!d.moved) {
    if (d.card) { const i = +d.card.dataset.i; if (i !== Math.round(S.pos)) S.target = i; else openCard(S.deck[i]); }
    return;
  }
  const fling = -d.v * 1000 / G.spacing;
  S.vel = fling;
  const t = Math.max(Math.round(d.pos) - 2, Math.min(Math.round(d.pos) + 2, Math.round(S.pos + fling * 0.18)));
  S.target = Math.max(0, Math.min(max, t));
}
stageEl.addEventListener('pointerdown', onDown);
stageEl.addEventListener('pointermove', onMove);
stageEl.addEventListener('pointerup', onUp);
stageEl.addEventListener('pointercancel', onUp);
stageEl.addEventListener('click', e => { if (e.target.closest('[data-act="next"]')) { e.stopPropagation(); advance(); } });
railEl.addEventListener('click', e => { const d = e.target.closest('.dot'); if (d) S.target = +d.dataset.i; });
addEventListener('keydown', e => {
  if (e.target.closest?.('input')) return;
  if (!$('#sheet').hidden) { if (e.key === 'Escape') closeSheet(); return; }
  if (S.view === 'results') { if (e.key === 'Escape') exitResults(); return; }
  if (e.key === 'ArrowRight') { if (S.mode === 'onboard' && Math.round(S.pos) === S.deck.length - 1) advance(); else S.target = Math.min(S.deck.length - 1, Math.round(S.pos) + 1); }
  if (e.key === 'ArrowLeft') S.target = Math.max(0, Math.round(S.pos) - 1);
  if (e.key === 'Enter') openCard(S.deck[Math.round(S.pos)]);
});

// ---------------------------------------------------------------- modal sheet + toast
const sheet = $('#sheet'), scrim = $('#scrim'), sheetBody = $('#sheetBody');
let sheetOnClose = null;
function openSheet(html, onClose) {
  sheetBody.innerHTML = html; sheetOnClose = onClose || null;
  sheet.hidden = false; scrim.hidden = false;
  requestAnimationFrame(() => { sheet.classList.add('open'); scrim.classList.add('open'); });
  sheetBody.scrollTop = 0;
}
function closeSheet() {
  if (sheet.hidden) return;
  sheet.classList.remove('open'); scrim.classList.remove('open');
  setTimeout(() => { sheet.hidden = true; scrim.hidden = true; }, reduced ? 0 : 320);
  sheetOnClose?.(); sheetOnClose = null;
}
$('#sheetClose').addEventListener('click', closeSheet);
scrim.addEventListener('click', closeSheet);
let toastTimer = 0;
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.hidden = false; t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.classList.remove('show'); setTimeout(() => { t.hidden = true; }, 250); }, 2600);
}
function openCard(c) {
  if (!c) return;
  if (S.mode === 'onboard') { advance(); return; }
  if (c.id === 'you') { openProfile(); return; }
  const cat = catOf(c.category);
  openSheet(`
    <div class="sheet-hero" style="background-image:url('${c.img}')"><span class="eyebrow">${esc(c.eyebrow)}</span></div>
    <h3 id="sheetTitle">${esc(c.title)}</h3>
    <p class="lead">${esc(c.body)}</p>
    <div class="chips"><span class="chip">${esc(c.id)}</span><span class="chip">status: idea</span>${cat ? `<span class="chip">${esc(cat.label)}</span>` : ''}</div>
    <p class="fine">This case is built in the pick → build → review loop. Its script lives in the services list.</p>
    ${cat ? `<button class="btn primary wide" id="openCat">${svg(cat.glyph, 'ic sm')} Show ${esc(cat.label.toLowerCase())} near me</button>` : ''}
  `);
  $('#openCat')?.addEventListener('click', () => { closeSheet(); setTimeout(() => enterResults({ cat: cat.id }), 280); });
}

// ---------------------------------------------------------------- profile
const fmtDate = ms => new Date(ms).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });
function openProfile() {
  openSheet(`
    <h3 id="sheetTitle">You, over time</h3>
    <p class="lead">Everything I believe about you, and why. Drag the timeline to see it change.</p>
    <div class="scrub"><label for="asof">As of <b id="asofLbl"></b></label>
      <input type="range" id="asof" min="${T0}" max="${T1}" step="3600000" value="${S.asOf}" />
      <div class="scrub-ends"><span>1 Oct</span><span>13 Oct</span></div></div>
    <div id="prof"></div>
    <p class="fine">Things I noticed can reorder suggestions, always with a “Because” note. They never fill a form, reach a shop or send you a reminder until you confirm them. Health, religion, ethnicity, nationality, gender, sexuality and politics are never inferred.</p>
  `, () => { renderYouMini(); refreshHomeCaptions(); });
  const input = $('#asof');
  input.addEventListener('input', () => { S.asOf = +input.value; renderProfile(); });
  renderProfile();
}
function renderProfile() {
  $('#asofLbl').textContent = fmtDate(S.asOf);
  const p = profileAt(EPISODES, HYPOTHESES, S.asOf, S.overrides);
  const told = [
    ...p.told.map(t => `<li class="fact"><div><b>${esc(TOLD_LABELS[t.key] || t.key)}</b> ${esc(t.value)}</div><span class="src">You told me · ${esc(fmtDate(Date.parse(t.at)))}</span></li>`),
    ...p.confirmed.map(h => `<li class="fact"><div>${esc(h.label)}</div><span class="src">You confirmed</span></li>`),
  ].join('') || '<li class="empty">Nothing yet.</li>';
  const noticed = p.noticed.map(h => {
    const need = Math.max(0, 2 - h.n);
    const state = h.surfaced ? '' : `<span class="learning">Still learning${need ? ` · needs ${need} more signal${need === 1 ? '' : 's'}` : ''}</span>`;
    return `<li class="hyp ${h.surfaced ? 'on' : ''}" style="--c:${h.conf.toFixed(3)}">
      <div class="hyp-top"><span>${esc(h.label)}</span><span class="pct">${Math.round(h.conf * 100)}%</span></div>
      <div class="bar"><i></i></div>
      <div class="hyp-meta">${esc(h.facet)} · ${h.n} signal${h.n === 1 ? '' : 's'} ${state}</div>
      <details><summary>Why I think this</summary><ul>${h.evidence.map(e => `<li>${esc(fmtDate(Date.parse(e.at)))} — ${esc(e.text)}</li>`).join('')}</ul></details>
      <div class="acts"><button data-h="${h.id}" data-o="confirmed">Confirm</button><button data-h="${h.id}" data-o="rejected">Not true</button><button data-h="${h.id}" data-o="forgotten">Forget</button></div>
    </li>`;
  }).join('') || '<li class="empty">Nothing noticed yet at this point in time.</li>';
  const changed = p.changed.map(c => c.rejected
    ? `<li class="fact"><div>${esc(c.label)}</div><span class="src">You said not true. I won’t raise it for 90 days.</span></li>`
    : `<li class="fact"><div><b>${esc(TOLD_LABELS[c.key] || c.key)}</b> ${esc(c.from)} → ${esc(c.to)}</div><span class="src">${esc(fmtDate(Date.parse(c.at)))}</span></li>`).join('') || '<li class="empty">No changes yet.</li>';
  $('#prof').innerHTML = `<h4>You told me</h4><ul class="list">${told}</ul><h4>I noticed</h4><ul class="list">${noticed}</ul><h4>Changed</h4><ul class="list">${changed}</ul>`;
  $('#prof').querySelectorAll('.acts button').forEach(b => b.addEventListener('click', () => {
    S.overrides[b.dataset.h] = b.dataset.o;
    toast({ confirmed: 'Confirmed. It now counts as something you told me.', rejected: 'Marked not true.', forgotten: 'Forgotten, with its evidence.' }[b.dataset.o]);
    renderProfile();
  }));
}
function refreshHomeCaptions() {
  if (S.mode !== 'home') return;
  const order = homeOrder();
  for (const c of S.deck) { const o = order.find(x => x.c.id === c.id); if (o) c.becauseHyp = o.h; }
  S.active = -1;
}

// ---------------------------------------------------------------- understanding an ask
// Lab stand-in for Luna: keyword routing into the category registry. An ask
// with no category still gets every place nearby.
function understand(text) {
  const q = text.toLowerCase();
  const cat = CATEGORIES.find(c => c.keywords.some(k => q.includes(k)) || q.includes(c.label.toLowerCase()));
  if (!cat) return { cat: 'all', sub: null, label: 'Nearby', other: true };
  let sub = null;
  for (const [s, keys] of Object.entries(cat.subKeys || {})) if (keys.some(k => q.includes(k))) { sub = s; break; }
  return { cat: cat.id, sub, label: sub ? `${cat.label} › ${sub}` : cat.label };
}

// ---------------------------------------------------------------- results: full-screen map + sheet
let MAP = null;
window.__lab.map = () => MAP;
const rsheet = $('#rsheet'), rsScroll = $('#rsScroll');
function ensureMap() {
  if (MAP !== null) return;
  MAP = createMap($('#mapEl'), paletteName, svg, id => openDetail(id));
  if (!MAP) { MAP = undefined; $('#mapFallback').hidden = false; }
}
function filtered() {
  return PLACES.filter(p => (S.cat === 'all' || p.cat === S.cat) && (!S.sub || p.sub === S.sub) && (!S.src || p.why === S.src))
    .map(p => ({ ...p, km: km(p) }))
    .sort((a, b) => (a.km ?? 99) - (b.km ?? 99) || b.rating - a.rating);
}
function enterResults({ ask = null, cat = 'all', sub = null } = {}) {
  S.ask = ask; S.cat = cat; S.sub = sub; S.src = null; S.detail = null;
  S.view = 'results';
  closeSheet();
  app.classList.add('mode-results'); app.classList.remove('mode-home', 'mode-services');
  setTab('maps');
  setLift(1);
  ensureMap();
  setSnap('peek', true);
  renderResults();
  setTimeout(() => { MAP?.resize(); refit(); }, reduced ? 0 : 380);
}
function exitResults() {
  S.view = 'home'; S.detail = null;
  app.classList.remove('mode-results'); app.classList.add('mode-home');
  setTab('home');
  setLift(0);
  $('#q').value = '';
}
function refit() {
  if (!MAP) return;
  const list = filtered().filter(p => p.lat != null);
  MAP.filter(new Set(list.map(p => p.id)));
  // frame you + the closest few, like ride and delivery apps; the rest sit just off-screen
  MAP.ready.then(() => MAP.fit(new Set(list.slice(0, 4).map(p => p.id)), G.snaps.peek));
}
function renderChips() {
  $('#rChips').innerHTML = [
    `<button class="chip glass ${S.cat === 'all' ? 'on' : ''}" data-cat="all">${svg('grid', 'ic xs')} All</button>`,
    ...CATEGORIES.map(c => `<button class="chip glass ${S.cat === c.id ? 'on' : ''}" data-cat="${c.id}">${svg(c.glyph, 'ic xs')} ${esc(c.label)}</button>`),
  ].join('');
  const cat = catOf(S.cat);
  $('#rSubs').innerHTML = cat && cat.subs.length
    ? [`<button class="chip glass ${!S.sub ? 'on' : ''}" data-sub="">All ${esc(cat.label.toLowerCase())}</button>`, ...cat.subs.map(s => `<button class="chip glass ${S.sub === s ? 'on' : ''}" data-sub="${esc(s)}">${esc(s)}</button>`)].join('')
    : '';
  $('#rSubs').hidden = !$('#rSubs').innerHTML;
  const on = $('#rChips .on'); if (on) on.parentElement.scrollLeft = on.offsetLeft - 16;
}
const WHY = {
  video: p => `${svg('play', 'ic xs')} ${esc(p.video.handle)} · ${esc(p.video.at)}`,
  partner: () => `${svg('check', 'ic xs')} Partner · published prices`,
  visited: () => `${svg('clock', 'ic xs')} You went before`,
  google: p => `${svg('star', 'ic xs')} Google · ${fmtN(p.count)} reviews (demo)`,
};
function media(p, cls) {
  return p.img ? `<div class="${cls}" style="background-image:url('${p.img}')"></div>` : `<div class="${cls} glyph">${svg(catOf(p.cat).glyph, 'ic lg')}</div>`;
}
function renderResults() {
  renderChips();
  const ask = $('#ask');
  if (S.ask) {
    const u = understand(S.ask);
    ask.hidden = false;
    ask.innerHTML = `<span class="ask-q">${esc(S.ask)}</span><span class="ask-u">${svg('orb', 'ic xs')} ${u.other ? 'No category yet · showing everything nearby' : `Understood · ${esc(u.label)}`}</span>`;
  } else ask.hidden = true;
  if (S.detail) { renderDetail(); return; }
  const list = filtered();
  const cat = catOf(S.cat);
  const what = S.sub ? S.sub.toLowerCase() : cat ? cat.label.toLowerCase() : 'places';
  const partners = list.filter(p => p.partner).length;
  const counts = Object.fromEntries(SOURCES.map(s => [s.id, PLACES.filter(p => (S.cat === 'all' || p.cat === S.cat) && p.why === s.id).length]));
  rsScroll.innerHTML = `
    <div class="rs-head">
      <h3>${list.length} ${esc(what)} near Dubai Marina</h3>
      <p>${partners ? `${partners} partner${partners === 1 ? '' : 's'} with published prices · ` : ''}closest first · distances are estimates</p>
    </div>
    <div class="hcards" id="hcards">${list.map(p => `
      <button class="hcard" data-p="${p.id}">${media(p, 'hc-img')}
        <span class="hc-txt"><b>${esc(p.name)}</b><span>★ ${p.rating.toFixed(1)} · ${esc(p.area)}${p.km != null ? ` · ${p.km} km` : ''}</span>
        ${p.partner ? '<span class="chip mini tint">Partner (demo)</span>' : `<span class="chip mini ghost">${esc(p.sub || catOf(p.cat).label)}</span>`}</span>
      </button>`).join('') || '<p class="empty">Nothing here yet in the lab data.</p>'}</div>
    <div class="more">
      <h4 class="sec">Picked up from</h4>
      <div class="srcs">${SOURCES.map(s => `
        <button class="srcb ${S.src === s.id ? 'on' : ''}" data-src="${s.id}" ${counts[s.id] ? '' : 'disabled'}>
          <span class="src-ph" style="background-image:url('${s.img}')"></span><span class="src-l">${esc(s.label)}</span><em>${counts[s.id]}</em>
        </button>`).join('')}</div>
      <h4 class="sec">Good spots <span class="count">${list.length}</span></h4>
      <div class="masonry">${list.map((p, i) => `
        <button class="tile" data-p="${p.id}">
          <div class="tile-media ${i % 3 === 1 ? 'tall' : ''}">${media(p, 'tile-img')}<span class="tile-tag">${esc(p.sub || catOf(p.cat).label)}</span></div>
          <div class="tile-txt">
            <div class="tile-row"><b>${esc(p.name)}</b><span class="rt">★ ${p.rating.toFixed(1)}</span></div>
            <span class="tile-area">${esc(p.area)}${p.km != null ? ` · ${p.km} km` : ''}</span>
            <span class="tile-why">${WHY[p.why](p)}</span>
            <span class="tile-snip">${esc(p.snippet)}</span>
          </div>
        </button>`).join('')}</div>
      <p class="fine">Fictional places on real streets. Ratings, prices and distances are demo data. Map data © OpenStreetMap contributors.</p>
    </div>`;
}
function openDetail(id) {
  if (S.view !== 'results') enterResults({ cat: PLACES.find(p => p.id === id).cat });
  S.detail = id;
  renderResults();
  setSnap('half');
  rsScroll.scrollTop = 0;
  MAP?.ready.then(() => MAP.select(id, G.snaps.half));
}
function renderDetail() {
  const p0 = PLACES.find(p => p.id === S.detail); if (!p0) return;
  const p = { ...p0, km: km(p0) }, k = catOf(p.cat);
  const primary = p.actions.find(a => a === 'book' || a === 'order') || (p.lat != null ? 'directions' : p.actions[0]);
  const label = { book: ['cal', 'Book'], order: ['bag', 'Order'], directions: ['nav', 'Navigate'], call: ['phone', 'Call'], app: ['app', 'Open app'] };
  const strip = PLACES.filter(x => x.cat === p.cat && x.img && x.id !== p.id).slice(0, 4);
  rsScroll.innerHTML = `
    <button class="d-back" id="dBack">${svg('back', 'ic sm')} All results</button>
    <div class="d-hero">${media(p, 'd-img')}
      <div class="d-over"><span class="chip mini dark">${svg(k.glyph, 'ic xs')} ${esc(p.sub || k.label)}</span><h3>${esc(p.name)}</h3></div></div>
    <ul class="d-rows">
      <li>${svg('star', 'ic sm')}<span><b>${p.rating.toFixed(1)}</b> (${fmtN(p.count)}) · Google (demo)</span>${p.partner ? '<span class="chip mini tint">Partner (demo)</span>' : ''}</li>
      <li>${svg('clock', 'ic sm')}<span>${esc(p.hours)}</span></li>
      <li>${svg('pin', 'ic sm')}<span>${esc(p.area)}${p.km != null ? ` · ${p.km} km away (estimate)` : ''}</span></li>
      ${p.price ? `<li>${svg('bag', 'ic sm')}<span>${esc(p.price)}</span></li>` : ''}
    </ul>
    <button class="btn primary wide big" data-a="${primary}">${svg(label[primary][0], 'ic sm')} ${label[primary][1]}</button>
    <div class="actions">${p.actions.filter(a => a !== primary).map(a => `<button class="btn" data-a="${a}">${svg(label[a][0], 'ic sm')} ${label[a][1]}</button>`).join('')}</div>
    <div class="callbox" id="callbox" hidden><span>Phone</span><b>${esc(p.phone)} (demo)</b><button class="btn sm" id="copyPhone">Copy</button></div>
    <h4 class="sec">Why it’s here</h4>
    <p class="d-why">${WHY[p.why](p)}</p><p class="d-snip">${esc(p.snippet)}</p>
    ${strip.length ? `<h4 class="sec">More ${esc(k.label.toLowerCase())} nearby</h4><div class="d-strip">${strip.map(x => `<button data-p="${x.id}" style="background-image:url('${x.img}')" aria-label="${esc(x.name)}"></button>`).join('')}</div>` : ''}
    <p class="fine">Fictional place. ${p.partner ? 'Book and Order open the shop’s own mini-app at its published prices; nothing is sent until you approve it.' : 'Not a partner: Dubai-io can hand you off, but cannot order here.'}</p>`;
  $('#dBack').addEventListener('click', backToList);
  rsScroll.querySelectorAll('[data-a]').forEach(b => b.addEventListener('click', () => {
    const a = b.dataset.a;
    if (a === 'call') { $('#callbox').hidden = false; return; }
    toast({ directions: 'Hands off to Maps in the live build.', book: 'Opens the shop’s own mini-app (next build).', order: 'Opens the shop’s own mini-app (next build).', app: 'Hands off to their app. Nothing is sent for you.' }[a]);
  }));
  $('#copyPhone')?.addEventListener('click', () => navigator.clipboard?.writeText(p.phone).then(() => toast('Number copied.'), () => toast('Select the number to copy it.')));
}
function backToList() { S.detail = null; renderResults(); setSnap('peek'); refit(); }

$('#back').addEventListener('click', () => { if (S.detail) backToList(); else exitResults(); });
$('#rChips').addEventListener('click', e => { const b = e.target.closest('[data-cat]'); if (!b) return; S.cat = b.dataset.cat; S.sub = null; S.src = null; S.detail = null; S.ask = null; renderResults(); refit(); });
$('#rSubs').addEventListener('click', e => { const b = e.target.closest('[data-sub]'); if (!b) return; S.sub = b.dataset.sub || null; S.detail = null; renderResults(); refit(); });
rsScroll.addEventListener('click', e => {
  if (rsheet.dataset.dragged === '1') return;
  const s = e.target.closest('[data-src]');
  if (s) { S.src = S.src === s.dataset.src ? null : s.dataset.src; renderResults(); refit(); return; }
  const t = e.target.closest('[data-p]');
  if (t) openDetail(t.dataset.p);
});

// sheet snapping: peek (carousel) -> half -> full (Good spots grid)
function setSnap(name, instant) {
  S.snap = name;
  if (!G.snaps) return;
  rsheet.style.transition = instant || reduced ? 'none' : '';
  rsheet.style.setProperty('--sh', G.snaps[name] + 'px');
  rsheet.dataset.snap = name;
  if (instant) requestAnimationFrame(() => { rsheet.style.transition = ''; });
}
(() => {
  let drag = null;
  rsheet.addEventListener('pointerdown', e => {
    const onGrab = !!e.target.closest('.grab');
    const inHead = !!e.target.closest('.rs-head');
    if (!onGrab && !inHead && !(S.snap !== 'full' && !e.target.closest('.hcards'))) return;
    if (S.snap === 'full' && rsScroll.scrollTop > 2 && !onGrab) return;
    drag = { y: e.clientY, h: G.snaps[S.snap], id: e.pointerId, t: performance.now(), moved: false };
    rsheet.dataset.dragged = '0';
  });
  rsheet.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dy) < 6) return;
    if (!drag.moved) { drag.moved = true; rsheet.setPointerCapture(e.pointerId); rsheet.dataset.dragged = '1'; }
    rsheet.style.transition = 'none';
    rsheet.style.setProperty('--sh', Math.max(G.snaps.peek - 70, Math.min(G.snaps.full + 20, drag.h - dy)) + 'px');
  });
  const end = e => {
    if (!drag || e.pointerId !== drag.id) return;
    const d = drag; drag = null;
    if (!d.moved) return;
    const dy = e.clientY - d.y, v = dy / Math.max(1, performance.now() - d.t), h = d.h - dy;
    rsheet.style.transition = '';
    let best = Object.entries(G.snaps).sort((a, b) => Math.abs(a[1] - h) - Math.abs(b[1] - h))[0][0];
    if (v < -0.5) best = S.snap === 'peek' ? 'half' : 'full';
    if (v > 0.5) best = S.snap === 'full' ? 'half' : 'peek';
    setSnap(best);
    setTimeout(() => { rsheet.dataset.dragged = '0'; }, 50);
  };
  rsheet.addEventListener('pointerup', end);
  rsheet.addEventListener('pointercancel', end);
  $('#rGrab').addEventListener('click', () => { if (rsheet.dataset.dragged !== '1') setSnap(S.snap === 'peek' ? 'half' : S.snap === 'half' ? 'full' : 'peek'); });
})();

// ---------------------------------------------------------------- composer, tabs
const placeholders = ['A groomer for my dog this week', 'Koshari near me', 'Somebody to fix my AC', 'A haircut tonight', 'Specialty coffee'];
let phI = 0;
setInterval(() => { const q = $('#q'); if (!q.value && document.activeElement !== q) q.placeholder = placeholders[phI++ % placeholders.length]; }, 3200);
$('#composer').addEventListener('submit', e => {
  e.preventDefault();
  const text = $('#q').value.trim(); if (!text) return;
  $('#q').blur();
  if (S.mode === 'onboard') store.set('onboarded', '1');
  const u = understand(text);
  $('#q').value = '';
  enterResults({ ask: text, cat: u.cat, sub: u.sub });
});
$('#mic').addEventListener('click', () => toast('Voice needs a secure page and a tap on the phone. Type for now.'));
document.querySelector('.tabbar').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const t = b.dataset.tab;
  if (t === 'home') { if (S.view === 'results') exitResults(); else if (S.view === 'services') exitServices(); }
  else if (t === 'maps') { if (S.view === 'services') hideServicesGrid(); enterResults({ cat: 'all' }); }
  else if (t === 'services') enterServices();
  else if (t === 'me') openMe();
});

// Services tab: one card per registry category (data, not code), plus "ask
// for anything" for categories that don't exist yet.
function enterServices() {
  if (S.view === 'results') { app.classList.remove('mode-results'); }
  S.view = 'services';
  app.classList.add('mode-services'); app.classList.remove('mode-home');
  setTab('services'); setLift(1);
  const cover = id => (PLACES.find(p => p.cat === id && p.img) || {}).img;
  $('#sgGrid').innerHTML = CATEGORIES.map(c => {
    const n = PLACES.filter(p => p.cat === c.id).length, partners = PLACES.filter(p => p.cat === c.id && p.partner).length;
    const img = cover(c.id);
    return `<button class="sg-card" data-cat="${c.id}">
      <span class="sg-img" style="${img ? `background-image:url('${img}')` : ''}"></span>
      <span class="sg-ic">${svg(c.glyph, 'ic sm')}</span>
      <span class="sg-txt"><b>${esc(c.label)}</b><span>${n} nearby${partners ? ` · ${partners} partner${partners === 1 ? '' : 's'}` : ''}</span>${c.subs.length ? `<em>${c.subs.slice(0, 3).map(esc).join(' · ')}</em>` : ''}</span>
    </button>`;
  }).join('') + `<button class="sg-card ask" data-ask="1"><span class="sg-ic">${svg('spark', 'ic sm')}</span><span class="sg-txt"><b>Anything else</b><span>Ask below. If there is no category yet, I still search nearby.</span></span></button>`;
}
function hideServicesGrid() { app.classList.remove('mode-services'); }
function exitServices() { S.view = 'home'; hideServicesGrid(); app.classList.add('mode-home'); setTab('home'); setLift(0); }
$('#sgGrid').addEventListener('click', e => {
  const b = e.target.closest('.sg-card'); if (!b) return;
  if (b.dataset.ask) { $('#q').focus(); return; }
  hideServicesGrid(); enterResults({ cat: b.dataset.cat });
});
function setTab(t) { document.querySelectorAll('.tabbar button').forEach(b => b.toggleAttribute('aria-current', b.dataset.tab === t)); }
function openMe() {
  openSheet(`
    <h3 id="sheetTitle">Me</h3>
    <p class="lead">Lab build · palette: ${esc(paletteName)}</p>
    <div class="actions col">
      <button class="btn" id="meProfile">${svg('person', 'ic sm')} You, over time</button>
      <button class="btn" id="meIntro">${svg('orb', 'ic sm')} Replay the intro</button>
      <button class="btn" id="meWifi">${svg('wifi', 'ic sm')} Replay the airport Wi-Fi arrival</button>
    </div>
    <p class="fine">Flags: add #fps, #tune or #nogl to the link (join with dots, e.g. #fps.tune).</p>`);
  $('#meProfile').addEventListener('click', () => { closeSheet(); setTimeout(openProfile, 340); });
  $('#meIntro').addEventListener('click', () => { closeSheet(); if (S.view === 'results') exitResults(); startOnboarding(); });
  $('#meWifi').addEventListener('click', () => { closeSheet(); if (S.view === 'results') exitResults(); S.deck = []; stageEl.innerHTML = ''; startPortal(); });
}

// ---------------------------------------------------------------- dev panels
if (flags.has('fps')) $('#fps').hidden = false;
if (flags.has('tune')) {
  const T = $('#tune');
  const rows = [['ribs', 'Rib frequency', 4, 26, 0.5, S.tune], ['foil', 'Foil', 0, 2, 0.05, S.tune], ['grain', 'Grain', 0, 0.25, 0.01, S.tune],
    ['aura', 'Aura strength', 0, 1.6, 0.05, S.tune], ['height', 'Aura height', 0.2, 1.6, 0.05, S.shape], ['falloff', 'Aura falloff', 0.8, 6, 0.1, S.shape], ['glow', 'Bottom glow', 0, 0.8, 0.02, S.shape]];
  T.innerHTML = rows.map(([k, l, a, b, s, o]) => `<label>${l}<input type="range" id="t_${k}" min="${a}" max="${b}" step="${s}" value="${o[k]}"><output>${o[k]}</output></label>`).join('');
  rows.forEach(([k, , , , , o]) => { const i = $('#t_' + k); i.addEventListener('input', () => { o[k] = +i.value; i.nextElementSibling.textContent = i.value; }); });
  T.hidden = false;
}

// ---------------------------------------------------------------- boot
addEventListener('resize', layout);
document.addEventListener('visibilitychange', () => { last = performance.now(); });
layout();
const firstRun = !store.get('onboarded');
if (flags.has('wifi') || (firstRun && !flags.has('intro') && !flags.has('services') && !flags.has('profile'))) startPortal();
else if (flags.has('intro')) startOnboarding();
else buildHome();
if (flags.has('services')) { if (S.mode === 'onboard') buildHome(); enterResults({ cat: 'pets' }); }
if (flags.has('profile')) { if (S.mode === 'onboard') buildHome(); setTimeout(openProfile, 400); }
requestAnimationFrame(t => { last = t; frame(t); });
