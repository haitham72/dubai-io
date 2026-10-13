// Home v2 lab: coverflow stage over one WebGL2 canvas, soft card-by-card
// onboarding, "You, over time" profile, and the universal Services surface.
// Static, no build. Flags: ?fps ?tune ?nogl ?intro, or #fps / #tune / #services
// / #profile / #intro (hash tokens joined with '.', e.g. #fps.tune).
import { createRenderer } from './gl.js';
import { VARIANT } from './shaders.js';
import { PALETTES, ONBOARDING, CASES, PROFILE_CARD, CATEGORIES, PLACES, EPISODES, HYPOTHESES, TOLD_LABELS } from './data.js';
import { profileAt } from './profile.js';

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
  search: '<path d="M10.5 18a7.5 7.5 0 1 1 5.3-2.2L21 21" />',
  orb: '<circle cx="12" cy="12" r="8" /><path d="M8.5 13.5c1.8 1.6 5.2 1.6 7 0" />',
  grid: '<rect x="4" y="4" width="7" height="7" rx="2" /><rect x="13" y="4" width="7" height="7" rx="2" /><rect x="4" y="13" width="7" height="7" rx="2" /><rect x="13" y="13" width="7" height="7" rx="2" />',
  civic: '<path d="M4 20h16M6 20v-8M10 20v-8M14 20v-8M18 20v-8M3 10l9-6 9 6z" />',
  person: '<circle cx="12" cy="8" r="4" /><path d="M4.5 20c1.4-3.6 4.2-5.4 7.5-5.4s6.1 1.8 7.5 5.4" />',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6" />',
  chevron: '<path d="M6 9l6 6 6-6" />',
  close: '<path d="M6 6l12 12M18 6L6 18" />',
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
  phone: '<path d="M6.5 3.5h3l1.5 4-2 1.5a11 11 0 0 0 6 6l1.5-2 4 1.5v3a2 2 0 0 1-2 2A16 16 0 0 1 4.5 5.5a2 2 0 0 1 2-2z" />',
  cal: '<rect x="4" y="5" width="16" height="15" rx="2.5" /><path d="M4 10h16M9 3v4M15 3v4" />',
  app: '<rect x="6" y="3" width="12" height="18" rx="3" /><path d="M10.5 18h3" />',
};
const svg = (name, cls = 'ic') => `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICON[name] || ICON.dots}</svg>`;
const $ = (s, r = document) => r.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

document.documentElement.dataset.palette = paletteName;
document.body.insertAdjacentHTML('beforeend', `
<div id="app" class="${reduced ? 'reduced' : ''}">
  <canvas id="gl" aria-hidden="true"></canvas>
  <header class="top">
    <form class="search glass" id="search" role="search">
      ${svg('search')}
      <label class="sr" for="q">Ask Dubai-io</label>
      <input id="q" name="q" type="search" placeholder="Ask Dubai-io" autocomplete="off" enterkeyhint="search" />
    </form>
    <span class="pill demo" title="Everything here is demo data">Demo data</span>
  </header>
  <main id="stage" aria-roledescription="carousel" aria-label="Home cards"></main>
  <nav class="rail" id="rail" aria-label="Cards"></nav>
  <p class="caption" id="caption" aria-live="polite"></p>
  <section id="services" class="services" hidden aria-label="Services">
    <div class="svc-bar">
      <button class="cat-btn glass" id="catBtn" aria-haspopup="listbox" aria-expanded="false"><span class="cat-ic"></span><span id="catLabel">All</span>${svg('chevron', 'ic sm')}</button>
      <div class="seg glass" role="group" aria-label="View">
        <button type="button" id="vMap" aria-pressed="true">Map</button>
        <button type="button" id="vList" aria-pressed="false">List</button>
      </div>
    </div>
    <div class="subs" id="subs"></div>
    <div class="notice" id="notice" hidden></div>
    <div class="map" id="mapWrap"><canvas id="map" aria-hidden="true"></canvas><div class="pins" id="pins"></div>
      <p class="map-note">Stylised lab map. Live mode shows Google Maps with attribution.</p></div>
    <div class="tiles" id="tiles" hidden></div>
    <div class="menu glass" id="menu" role="listbox" hidden></div>
  </section>
  <nav class="tabbar glass" aria-label="Tabs">
    <button data-tab="home" aria-current="page">${svg('orb')}<span>Companion</span></button>
    <button data-tab="services">${svg('grid')}<span>Services</span></button>
    <button data-tab="civic">${svg('civic')}<span>Civic</span></button>
    <button data-tab="me">${svg('person')}<span>Me</span></button>
  </nav>
  <div class="scrim" id="scrim" hidden></div>
  <section class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle" hidden>
    <button class="grab" id="sheetClose" aria-label="Close"><span></span></button>
    <div class="sheet-body" id="sheetBody"></div>
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
  overrides: {}, asOf: T1, active: -1, cat: 'all', sub: null, svcView: 'map', selected: null,
};
const G = {};
window.__lab = { S, G };
let seedN = 1;

function mkCard(def) {
  return { ...def, variant: VARIANT[def.kind] ?? 0, seed: (seedN++ * 7.31) % 13, rev: reduced ? 1 : 0, revStart: 0, revDur: 1100, out: false, el: null };
}

// ---------------------------------------------------------------- layout
function layout() {
  const r = app.getBoundingClientRect();
  const s = stageEl.getBoundingClientRect();
  Object.assign(G, { W: r.width, H: r.height, sx: s.left - r.left, sy: s.top - r.top, sw: s.width, sh: s.height });
  G.cw = Math.round(Math.min(318, G.sw * 0.78));
  G.ch = Math.round(Math.min(G.sh * 0.95, G.cw * 1.46));
  G.bandH = Math.round(G.ch * 0.52);
  G.cx = G.sx + G.sw / 2; G.cy = G.sy + G.sh / 2;
  G.spacing = G.cw * 0.84; G.P = 1100; G.radius = 28;
  app.style.setProperty('--cw', G.cw + 'px');
  app.style.setProperty('--ch', G.ch + 'px');
  app.style.setProperty('--band', G.bandH + 'px');
  canvas.style.width = G.W + 'px'; canvas.style.height = G.H + 'px';
  renderer?.resize(G.W, G.H, S.maxDpr);
  if (S.view === 'services') drawMap();
}

function params(i) {
  const d = i - S.pos, ad = Math.abs(d), sg = Math.sign(d);
  const tx = sg * (Math.min(ad, 1) * G.spacing + Math.max(ad - 1, 0) * G.cw * 0.26);
  const rot = -sg * Math.min(ad, 1) * 18 * Math.PI / 180;
  const sc = 1 - 0.13 * Math.min(ad, 1) - 0.05 * Math.max(ad - 1, 0);
  const c = S.deck[i];
  const e = 1 - Math.pow(1 - c.rev, 3);
  return { d, ad, tx, ty: (1 - e) * 26, rot, sc };
}

// Same math as the CSS transform: translate(tx,ty) rotateY(rot) scale(sc),
// perspective P with origin at the stage centre.
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
  let body = `<p>${esc(c.body)}</p>`;
  if (c.id === 'you') body = `<ul class="mini" id="youMini"></ul>`;
  return `<article class="card ${c.kind}" data-i="${i}" aria-label="${esc(c.title)}" tabindex="-1">
    <div class="band" style="${!renderer ? bandFallback(c) : ''}">
      <span class="eyebrow">${esc(c.eyebrow)}</span>
      <h2>${esc(c.title)}</h2>
    </div>
    <div class="body">
      ${body}
      <div class="foot"><span class="meta">${c.meta.map(m => `<span>${esc(m)}</span>`).join('')}</span>${next}</div>
    </div>
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
  buildRail();
  renderYouMini();
  S.active = -1;
}
function appendCard(c) {
  S.deck.push(c);
  const i = S.deck.length - 1;
  stageEl.insertAdjacentHTML('beforeend', cardHTML(c, i));
  c.el = stageEl.lastElementChild;
  buildRail();
}
function reveal(c, delay = 0, dur = 1100) {
  c.out = false; c.revStart = performance.now() + delay; c.revDur = dur;
  if (reduced) c.rev = 1;
}

function buildRail() {
  railEl.innerHTML = S.deck.map((c, i) => {
    const bg = c.img ? `background-image:url('${c.img}')` : `background:radial-gradient(circle at 30% 30%, ${palette.ramp[3]}, ${palette.ramp[1]} 60%, ${palette.ramp[0]})`;
    return `<button class="dot" data-i="${i}" style="${bg}" aria-label="${esc(c.title)}"></button>`;
  }).join('');
}

// ---------------------------------------------------------------- flows
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
    appendCard(c);
    reveal(c, 160, 1200);
    S.target = S.deck.length - 1;
  } else {
    finishOnboarding();
  }
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
  const scored = CASES.map((c, k) => {
    const h = c.because && byId[c.because];
    const boost = h && (h.surfaced || h.provenance === 'user_supplied') ? h.conf : 0;
    return { c, k, h: boost ? h : null, score: boost * 10 - k };
  }).sort((a, b) => b.score - a.score);
  return scored;
}
function buildHome() {
  S.mode = 'home';
  const order = homeOrder();
  S.deck = [mkCard(PROFILE_CARD), ...order.map(o => mkCard({ ...o.c, becauseHyp: o.h }))];
  S.pos = S.target = 1; S.vel = 0;
  mountDeck();
  S.deck.forEach((c, i) => reveal(c, 120 + Math.abs(i - 1) * 140, 1000));
}

// ---------------------------------------------------------------- captions + profile mini
function captionFor(c) {
  if (!c) return '';
  if (S.mode === 'onboard') return c.next === 'Start' ? 'Tap Start, or swipe back to read again.' : 'Swipe, or tap Next.';
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
let last = performance.now(), fpsAcc = 0, fpsN = 0, lowFor = 0, fpsShown = 0;
function frame(now) {
  const dt = Math.min(0.033, (now - last) / 1000); last = now;
  const n = S.deck.length;

  // spring for the carousel position (rubber-band at the ends while dragging)
  if (!S.drag) {
    if (reduced) { S.pos = S.target; S.vel = 0; }
    else {
      const k = 210, c = 27;
      const a = -k * (S.pos - S.target) - c * S.vel;
      S.vel += a * dt; S.pos += S.vel * dt;
      if (Math.abs(S.pos - S.target) < 1e-4 && Math.abs(S.vel) < 1e-3) { S.pos = S.target; S.vel = 0; }
    }
  }
  // tilt eases toward its target, target relaxes to 0
  for (let k = 0; k < 2; k++) {
    if (!S.drag) S.tiltTarget[k] *= Math.pow(0.02, dt);
    S.tilt[k] += (S.tiltTarget[k] - S.tilt[k]) * Math.min(1, dt * 9);
  }

  const time = reduced ? 8 : now / 1000;
  const glCards = [], auras = [];
  for (let i = 0; i < n; i++) {
    const c = S.deck[i];
    // reveal progress
    if (!reduced && now >= c.revStart) {
      const t = Math.min(1, (now - c.revStart) / c.revDur);
      c.rev = c.out ? 1 - t : t;
    }
    const p = params(i);
    const el = c.el;
    const hidden = p.ad > 2.6 || c.rev <= 0.001;
    if (hidden) { if (el.style.visibility !== 'hidden') el.style.visibility = 'hidden'; continue; }
    el.style.visibility = 'visible';
    el.style.transform = `translate3d(${p.tx.toFixed(2)}px, ${p.ty.toFixed(2)}px, 0) rotateY(${p.rot.toFixed(4)}rad) scale(${p.sc.toFixed(4)})`;
    el.style.zIndex = String(100 - Math.round(p.ad * 10));
    el.style.opacity = String(Math.min(1, c.rev * 1.5));
    el.style.filter = c.rev < 0.999 ? `blur(${((1 - c.rev) * 12).toFixed(1)}px)` : 'none';
    el.style.setProperty('--dim', (Math.min(p.ad, 1) * 0.22).toFixed(3));
    el.classList.toggle('is-center', p.ad < 0.5);

    if (renderer) {
      const hw = G.cw / 2, top = -G.ch / 2, bot = top + G.bandH;
      const quad = [project(-hw, top, p), project(hw, top, p), project(-hw, bot, p), project(hw, bot, p)];
      const tilt = p.ad < 0.6 ? S.tilt : [S.tilt[0] * 0.3 - p.d * 0.4, S.tilt[1] * 0.3];
      const card = {
        quad, variant: c.variant, img: c.img, holo: c.holo || 0, rev: Math.max(0, c.rev), seed: c.seed,
        dim: Math.min(p.ad, 1) * 0.22, w: G.cw, bandH: G.bandH, radius: G.radius, tilt, ad: p.ad,
      };
      glCards.push(card);
      if (p.ad < 0.7) {
        const xs = quad.map(q => q[0]), ys = quad.map(q => q[1]);
        card.bbox = [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
        card.bottom = project(0, G.ch / 2, p)[1];
        auras.push({ card, weight: Math.pow(1 - p.ad / 0.7, 1.6) });
      }
    }
  }

  const active = Math.max(0, Math.min(n - 1, Math.round(S.pos)));
  if (active !== S.active) {
    S.active = active;
    [...railEl.children].forEach((d, i) => d.setAttribute('aria-current', i === active ? 'true' : 'false'));
    captionEl.innerHTML = captionFor(S.deck[active]);
  }

  if (renderer && S.view === 'home' && !document.hidden) {
    glCards.sort((a, b) => b.ad - a.ad);
    auras.sort((a, b) => b.weight - a.weight);
    renderer.render({ cards: glCards, auras: auras.slice(0, 2), time, tune: S.tune, shape: S.shape });
  }

  // frame budget: step down resolution if the phone can't keep up
  fpsAcc += dt; fpsN++;
  if (fpsAcc >= 0.5) {
    const fps = fpsN / fpsAcc; fpsAcc = 0; fpsN = 0; fpsShown = fps;
    lowFor = fps < 45 ? lowFor + 0.5 : 0;
    if (lowFor >= 2 && S.maxDpr > 1.25) {
      S.maxDpr = S.maxDpr > 2 ? 2 : 1.5; lowFor = 0; layout();
    }
    if (flags.has('fps')) $('#fps').textContent = `${fps.toFixed(0)} fps · dpr ${renderer ? renderer.dpr.toFixed(2) : '-'} · ${renderer ? 'webgl2' : 'no gl'}`;
  }
  requestAnimationFrame(frame);
}

// ---------------------------------------------------------------- input
function onDown(e) {
  if (S.view !== 'home' || e.button > 0) return;
  if (e.target.closest('button')) return; // buttons handle their own clicks
  S.drag = { x: e.clientX, y: e.clientY, pos: S.pos, t: performance.now(), lastX: e.clientX, lastT: performance.now(), v: 0, moved: false, id: e.pointerId, card: e.target.closest('.card') };
  stageEl.setPointerCapture(e.pointerId);
  const r = e.target.closest('.card');
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
  const inst = (e.clientX - d.lastX) / Math.max(1, now - d.lastT);
  d.v = d.v * 0.7 + inst * 0.3; d.lastX = e.clientX; d.lastT = now;
  let pos = d.pos - dx / G.spacing;
  const max = S.deck.length - 1;
  if (pos < 0) pos = pos * 0.35; else if (pos > max) pos = max + (pos - max) * 0.35;
  S.pos = pos;
  S.tiltTarget = [Math.max(-1, Math.min(1, -d.v * 0.9)), S.tiltTarget[1] * 0.9];
}
function onUp(e) {
  const d = S.drag; if (!d || e.pointerId !== d.id) return;
  S.drag = null;
  const max = S.deck.length - 1;
  if (!d.moved) {
    const card = d.card;
    if (card) {
      const i = +card.dataset.i;
      if (i !== Math.round(S.pos)) S.target = i; else openCard(S.deck[i]);
    }
    S.target = Math.max(0, Math.min(max, S.target));
    return;
  }
  const fling = -d.v * 1000 / G.spacing; // cards per second
  S.vel = fling;
  let t = Math.round(S.pos + fling * 0.18);
  t = Math.max(Math.round(d.pos) - 2, Math.min(Math.round(d.pos) + 2, t));
  S.target = Math.max(0, Math.min(max, t));
}
stageEl.addEventListener('pointerdown', onDown);
stageEl.addEventListener('pointermove', onMove);
stageEl.addEventListener('pointerup', onUp);
stageEl.addEventListener('pointercancel', onUp);
stageEl.addEventListener('click', e => {
  const b = e.target.closest('[data-act="next"]');
  if (b) { e.stopPropagation(); advance(); }
});
railEl.addEventListener('click', e => { const d = e.target.closest('.dot'); if (d) S.target = +d.dataset.i; });
addEventListener('keydown', e => {
  if (!$('#sheet').hidden || S.view !== 'home') { if (e.key === 'Escape') closeSheet(); return; }
  if (e.key === 'ArrowRight') { S.target = Math.min(S.deck.length - 1, Math.round(S.pos) + 1); if (S.mode === 'onboard' && Math.round(S.pos) === S.deck.length - 1) advance(); }
  if (e.key === 'ArrowLeft') S.target = Math.max(0, Math.round(S.pos) - 1);
  if (e.key === 'Enter') openCard(S.deck[Math.round(S.pos)]);
});

// ---------------------------------------------------------------- sheet + toast
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
  const cat = CATEGORIES.find(k => k.id === c.category);
  openSheet(`
    <div class="sheet-hero" style="background-image:url('${c.img}')"><span class="eyebrow">${esc(c.eyebrow)}</span></div>
    <h3 id="sheetTitle">${esc(c.title)}</h3>
    <p class="lead">${esc(c.body)}</p>
    <div class="chips"><span class="chip">${esc(c.id)}</span><span class="chip">status: idea</span>${cat ? `<span class="chip">${esc(cat.label)}</span>` : ''}</div>
    <p class="fine">This case is built in the pick → build → review loop. Its script lives in the services list (cases.md).</p>
    ${cat ? `<button class="btn primary" id="openCat">${svg(cat.glyph, 'ic sm')} See ${esc(cat.label)} on the map</button>` : ''}
  `);
  $('#openCat')?.addEventListener('click', () => { closeSheet(); showServices(cat.id); });
}

// ---------------------------------------------------------------- profile sheet
function fmtDate(ms) {
  return new Date(ms).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false });
}
function openProfile() {
  openSheet(`
    <h3 id="sheetTitle">You, over time</h3>
    <p class="lead">Everything I believe about you, and why. Drag the timeline to see it change.</p>
    <div class="scrub">
      <label for="asof">As of <b id="asofLbl"></b></label>
      <input type="range" id="asof" min="${T0}" max="${T1}" step="${3600000}" value="${S.asOf}" />
      <div class="scrub-ends"><span>1 Oct</span><span>13 Oct</span></div>
    </div>
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
    const pct = Math.round(h.conf * 100);
    const state = h.surfaced ? '' : `<span class="learning">Still learning · needs ${Math.max(0, 2 - h.n) || 'more'} signal${2 - h.n === 1 ? '' : 's'}</span>`;
    return `<li class="hyp ${h.surfaced ? 'on' : ''}" style="--c:${h.conf.toFixed(3)}">
      <div class="hyp-top"><span>${esc(h.label)}</span><span class="pct">${pct}%</span></div>
      <div class="bar"><i></i></div>
      <div class="hyp-meta">${esc(h.facet)} · ${h.n} signal${h.n === 1 ? '' : 's'} ${state}</div>
      <details><summary>Why I think this</summary><ul>${h.evidence.map(e => `<li>${esc(fmtDate(Date.parse(e.at)))} — ${esc(e.text)}</li>`).join('')}</ul></details>
      <div class="acts"><button data-h="${h.id}" data-o="confirmed">Confirm</button><button data-h="${h.id}" data-o="rejected">Not true</button><button data-h="${h.id}" data-o="forgotten">Forget</button></div>
    </li>`;
  }).join('') || '<li class="empty">Nothing noticed yet at this point in time.</li>';
  const changed = p.changed.map(c => c.rejected
    ? `<li class="fact"><div>${esc(c.label)}</div><span class="src">You said not true. I won’t raise it for 90 days.</span></li>`
    : `<li class="fact"><div><b>${esc(TOLD_LABELS[c.key] || c.key)}</b> ${esc(c.from)} → ${esc(c.to)}</div><span class="src">${esc(fmtDate(Date.parse(c.at)))}</span></li>`).join('') || '<li class="empty">No changes yet.</li>';
  $('#prof').innerHTML = `
    <h4>You told me</h4><ul class="list">${told}</ul>
    <h4>I noticed</h4><ul class="list">${noticed}</ul>
    <h4>Changed</h4><ul class="list">${changed}</ul>`;
  $('#prof').querySelectorAll('.acts button').forEach(b => b.addEventListener('click', () => {
    S.overrides[b.dataset.h] = b.dataset.o;
    const verb = { confirmed: 'Confirmed. It now counts as something you told me.', rejected: 'Marked not true.', forgotten: 'Forgotten, with its evidence.' }[b.dataset.o];
    toast(verb);
    renderProfile();
  }));
}
function refreshHomeCaptions() {
  if (S.mode !== 'home') return;
  const order = homeOrder();
  for (const c of S.deck) {
    const o = order.find(x => x.c.id === c.id);
    if (o) c.becauseHyp = o.h;
  }
  S.active = -1;
}

// ---------------------------------------------------------------- services surface
const svc = $('#services');
function catOf(id) { return CATEGORIES.find(c => c.id === id); }
function visiblePlaces() {
  return PLACES.filter(p => (S.cat === 'all' || S.cat === 'other' || p.cat === S.cat) && (!S.sub || p.sub === S.sub));
}
function showServices(catId = S.cat, notice = '') {
  S.view = 'services'; S.cat = catId; S.sub = null;
  svc.hidden = false; app.classList.add('svc');
  setTab('services');
  renderer?.clear();
  const n = $('#notice'); n.hidden = !notice; n.innerHTML = notice;
  renderServices();
  requestAnimationFrame(drawMap);
}
function showHome() {
  S.view = 'home'; svc.hidden = true; app.classList.remove('svc'); setTab('home'); closeMenu();
}
function setTab(t) {
  document.querySelectorAll('.tabbar button').forEach(b => b.toggleAttribute('aria-current', b.dataset.tab === t));
}
function renderServices() {
  const cat = catOf(S.cat);
  $('#catLabel').textContent = cat ? cat.label : (S.cat === 'other' ? 'Other' : 'All');
  $('.cat-ic').innerHTML = svg(cat ? cat.glyph : 'grid', 'ic sm');
  $('#subs').innerHTML = cat && cat.subs.length
    ? [`<button class="chip ${!S.sub ? 'on' : ''}" data-sub="">All ${esc(cat.label.toLowerCase())}</button>`, ...cat.subs.map(s => `<button class="chip ${S.sub === s ? 'on' : ''}" data-sub="${esc(s)}">${esc(s)}</button>`)].join('')
    : '';
  const places = visiblePlaces();
  $('#pins').innerHTML = places.map(p => {
    const k = catOf(p.cat);
    return `<button class="pin ${p.partner ? 'partner' : ''} ${S.selected === p.id ? 'sel' : ''}" data-p="${p.id}" style="left:${p.x * 100}%;top:${p.y * 100}%" aria-label="${esc(p.name)}">${svg(k.glyph, 'ic')}</button>`;
  }).join('');
  $('#tiles').innerHTML = places.map(p => {
    const k = catOf(p.cat);
    const media = p.img ? `<div class="tile-img" style="background-image:url('${p.img}')"></div>` : `<div class="tile-img glyph">${svg(k.glyph, 'ic lg')}</div>`;
    return `<button class="tile" data-p="${p.id}">${media}
      <div class="tile-txt"><b>${esc(p.name)}</b><span>★ ${p.rating.toFixed(1)} · ${esc(p.area)}${p.km != null ? ` · ${p.km} km` : ''}</span>${p.partner ? '<span class="chip mini">Partner (demo)</span>' : `<span class="chip mini ghost">${esc(p.sub || k.label)}</span>`}</div></button>`;
  }).join('') || '<p class="empty">No places for this filter in the lab data.</p>';
  $('#mapWrap').hidden = S.svcView !== 'map';
  $('#tiles').hidden = S.svcView !== 'list';
  $('#vMap').setAttribute('aria-pressed', S.svcView === 'map');
  $('#vList').setAttribute('aria-pressed', S.svcView === 'list');
}
function openMenu() {
  const m = $('#menu');
  m.innerHTML = [
    `<button role="option" data-cat="all" aria-selected="${S.cat === 'all'}">${svg('grid', 'ic sm')}<span>All</span><em>${PLACES.length}</em></button>`,
    ...CATEGORIES.map(c => `<button role="option" data-cat="${c.id}" aria-selected="${S.cat === c.id}">${svg(c.glyph, 'ic sm')}<span>${esc(c.label)}</span><em>${PLACES.filter(p => p.cat === c.id).length}</em></button>`),
  ].join('');
  m.hidden = false; $('#catBtn').setAttribute('aria-expanded', 'true');
}
function closeMenu() { $('#menu').hidden = true; $('#catBtn').setAttribute('aria-expanded', 'false'); }
$('#catBtn').addEventListener('click', () => ($('#menu').hidden ? openMenu() : closeMenu()));
$('#menu').addEventListener('click', e => {
  const b = e.target.closest('[data-cat]'); if (!b) return;
  S.cat = b.dataset.cat; S.sub = null; S.selected = null; closeMenu(); $('#notice').hidden = true; renderServices();
});
$('#subs').addEventListener('click', e => { const b = e.target.closest('[data-sub]'); if (!b) return; S.sub = b.dataset.sub || null; renderServices(); });
$('#vMap').addEventListener('click', () => { S.svcView = 'map'; renderServices(); requestAnimationFrame(drawMap); });
$('#vList').addEventListener('click', () => { S.svcView = 'list'; renderServices(); });
svc.addEventListener('click', e => {
  const b = e.target.closest('[data-p]'); if (!b) return;
  S.selected = b.dataset.p; renderServices(); openPlace(PLACES.find(p => p.id === b.dataset.p));
});

function openPlace(p) {
  const k = catOf(p.cat);
  const act = {
    directions: [`${svg('pin', 'ic sm')} Directions`, 'Hands off to Maps in the live build.'],
    call: [`${svg('phone', 'ic sm')} Call`, null],
    book: [`${svg('cal', 'ic sm')} Book`, 'Opens the shop’s own mini-app at its published prices (next build).'],
    order: [`${svg('bag', 'ic sm')} Order`, 'Opens the shop’s own mini-app at its published prices (next build).'],
    app: [`${svg('app', 'ic sm')} Open app`, 'Hands off to their app. Nothing is sent on your behalf.'],
  };
  const hero = p.img ? `<div class="sheet-hero" style="background-image:url('${p.img}')"></div>` : `<div class="sheet-hero glyph">${svg(k.glyph, 'ic xl')}</div>`;
  openSheet(`
    ${hero}
    <h3 id="sheetTitle">${esc(p.name)}</h3>
    <div class="chips"><span class="chip">${svg(k.glyph, 'ic xs')} ${esc(p.sub || k.label)}</span>${p.partner ? '<span class="chip tint">Partner (demo)</span>' : ''}</div>
    <p class="rating">★ ${p.rating.toFixed(1)} <span>(${p.count.toLocaleString('en-US')}) · Google (demo)</span></p>
    <p class="where">${esc(p.area)}${p.km != null ? ` · ${p.km} km away (estimate)` : ''}</p>
    ${p.price ? `<p class="price">${esc(p.price)}</p>` : ''}
    <div class="actions">${p.actions.map(a => `<button class="btn ${a === 'book' || a === 'order' ? 'primary' : ''}" data-a="${a}">${act[a][0]}</button>`).join('')}</div>
    <div class="callbox" id="callbox" hidden><span>Phone</span><b class="sel">${esc(p.phone)} (demo)</b><button class="btn sm" id="copyPhone">Copy</button></div>
    <p class="fine">Fictional place. Rating, distance and prices are demo data.</p>
  `, () => { S.selected = null; renderServices(); });
  sheetBody.querySelectorAll('[data-a]').forEach(b => b.addEventListener('click', () => {
    const a = b.dataset.a;
    if (a === 'call') { $('#callbox').hidden = false; return; }
    toast(act[a][1]);
  }));
  $('#copyPhone')?.addEventListener('click', () => {
    navigator.clipboard?.writeText(p.phone).then(() => toast('Number copied.'), () => toast('Select the number to copy it.'));
  });
}

// Stylised map: drawn once per resize, palette-tinted, no real geometry.
// A coast running south-west to north-east, a street grid aligned to it,
// one highway parallel to the coast, a marina inlet, a few parks.
function drawMap() {
  const c = $('#map'); if (!c || S.view !== 'services' || S.svcView !== 'map') return;
  const r = c.getBoundingClientRect(); if (!r.width) return;
  const dpr = Math.min(devicePixelRatio || 1, 2);
  c.width = r.width * dpr; c.height = r.height * dpr;
  const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
  const w = r.width, h = r.height;
  const coast = [[w * .86, -10], [w * .62, h * .12], [w * .40, h * .25], [w * .18, h * .40], [-10, h * .52]];
  const coastPath = (close) => {
    g.beginPath(); g.moveTo(...coast[0]);
    for (let i = 1; i < coast.length; i++) {
      const [x0, y0] = coast[i - 1], [x1, y1] = coast[i];
      g.quadraticCurveTo(x0, y0, (x0 + x1) / 2, (y0 + y1) / 2);
    }
    g.lineTo(...coast[coast.length - 1]);
    if (close === 'sea') { g.lineTo(-10, -10); g.closePath(); }
    if (close === 'land') { g.lineTo(-10, h + 10); g.lineTo(w + 10, h + 10); g.lineTo(w + 10, -10); g.closePath(); }
  };
  // land
  g.fillStyle = '#EEF2F4'; g.fillRect(0, 0, w, h);
  // sea + beach edge
  const sea = g.createLinearGradient(0, 0, w * .45, h * .45);
  sea.addColorStop(0, '#BCE3EE'); sea.addColorStop(1, '#D8F0F7');
  coastPath('sea'); g.fillStyle = sea; g.fill();
  coastPath(); g.strokeStyle = '#F4EFE6'; g.lineWidth = 7; g.stroke();
  coastPath(); g.strokeStyle = 'rgba(10,156,194,.25)'; g.lineWidth = 1; g.stroke();

  // everything else is clipped to land
  g.save(); coastPath('land'); g.clip();
  const ang = Math.atan2(h * .52, -w * .86); // coast direction
  const ux = Math.cos(ang), uy = Math.sin(ang), vx = -uy, vy = ux;
  const L = Math.hypot(w, h) * 1.2, cx = w / 2, cy = h / 2;
  const line = (ox, oy, dx, dy) => { g.beginPath(); g.moveTo(ox - dx * L, oy - dy * L); g.lineTo(ox + dx * L, oy + dy * L); g.stroke(); };
  // parks
  g.fillStyle = '#E2EDE8';
  [[.50, .70, 70, 40], [.80, .40, 54, 54], [.30, .84, 60, 34]].forEach(([x, y, a, b]) => { g.beginPath(); g.roundRect(w * x - a / 2, h * y - b / 2, a, b, 10); g.fill(); });
  // street grid
  g.strokeStyle = '#FFFFFF'; g.lineWidth = 2.2; g.lineCap = 'butt';
  for (let k = -14; k <= 14; k++) line(cx + vx * k * 38, cy + vy * k * 38, ux, uy);
  g.lineWidth = 1.6;
  for (let k = -14; k <= 14; k++) line(cx + ux * k * 52, cy + uy * k * 52, vx, vy);
  // highway parallel to the coast
  const hx = cx + vx * 70, hy = cy + vy * 70;
  g.strokeStyle = '#D7E1E6'; g.lineWidth = 13; line(hx, hy, ux, uy);
  g.strokeStyle = '#FFFFFF'; g.lineWidth = 9; line(hx, hy, ux, uy);
  g.strokeStyle = palette.ramp[3]; g.globalAlpha = .7; g.lineWidth = 1.4; line(hx, hy, ux, uy); g.globalAlpha = 1;
  g.restore();
  // marina inlet
  g.strokeStyle = '#CDEBF3'; g.lineWidth = 10; g.lineCap = 'round';
  g.beginPath(); g.moveTo(w * .16, h * .42); g.bezierCurveTo(w * .22, h * .50, w * .17, h * .60, w * .27, h * .68); g.stroke();
  // area labels, placed clear of the pins
  g.fillStyle = '#8796A0'; g.font = '600 10px -apple-system, system-ui, sans-serif';
  if ('letterSpacing' in g) g.letterSpacing = '1.4px';
  [['DUBAI MARINA', .05, .73], ['JLT', .45, .19], ['AL BARSHA', .70, .76], ['AL QUOZ', .78, .25]].forEach(([t, x, y]) => g.fillText(t, w * x, h * y));
}

// ---------------------------------------------------------------- tabs, search
document.querySelector('.tabbar').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const t = b.dataset.tab;
  if (t === 'home') showHome();
  else if (t === 'services') showServices(S.cat);
  else if (t === 'civic') toast('Civic guidance is LATER in the plan.');
  else if (t === 'me') openMe();
});
function openMe() {
  openSheet(`
    <h3 id="sheetTitle">Me</h3>
    <p class="lead">Lab build · palette: ${esc(paletteName)}</p>
    <div class="actions col">
      <button class="btn" id="meProfile">${svg('person', 'ic sm')} You, over time</button>
      <button class="btn" id="meIntro">${svg('orb', 'ic sm')} Replay the intro</button>
    </div>
    <p class="fine">Flags: add #fps, #tune or #nogl to the link (join with dots, e.g. #fps.tune).</p>
  `);
  $('#meProfile').addEventListener('click', () => { closeSheet(); setTimeout(openProfile, 340); });
  $('#meIntro').addEventListener('click', () => { closeSheet(); showHome(); startOnboarding(); });
}
$('#search').addEventListener('submit', e => {
  e.preventDefault();
  const q = $('#q').value.trim().toLowerCase(); if (!q) return;
  $('#q').blur();
  const hit = CATEGORIES.find(c => c.keywords.some(k => q.includes(k)) || q.includes(c.label.toLowerCase()));
  if (hit) { showServices(hit.id); toast(`Showing ${hit.label}.`); }
  else {
    showServices('other', `No category for “${esc(q)}” yet. Showing everything nearby. New categories are added as data, not code.`);
  }
});

// ---------------------------------------------------------------- dev panels
if (flags.has('fps')) $('#fps').hidden = false;
if (flags.has('tune')) {
  const T = $('#tune');
  const rows = [
    ['ribs', 'Rib frequency', 4, 26, 0.5, S.tune], ['foil', 'Foil', 0, 2, 0.05, S.tune], ['grain', 'Grain', 0, 0.25, 0.01, S.tune],
    ['aura', 'Aura strength', 0, 1.6, 0.05, S.tune], ['height', 'Aura height', 0.2, 1.6, 0.05, S.shape],
    ['falloff', 'Aura falloff', 0.8, 6, 0.1, S.shape], ['glow', 'Bottom glow', 0, 0.8, 0.02, S.shape],
  ];
  T.innerHTML = rows.map(([k, l, a, b, s, o]) => `<label>${l}<input type="range" id="t_${k}" min="${a}" max="${b}" step="${s}" value="${o[k]}"><output>${o[k]}</output></label>`).join('');
  rows.forEach(([k, , , , , o]) => {
    const i = $('#t_' + k);
    i.addEventListener('input', () => { o[k] = +i.value; i.nextElementSibling.textContent = i.value; });
  });
  T.hidden = false;
}

// ---------------------------------------------------------------- boot
addEventListener('resize', layout);
document.addEventListener('visibilitychange', () => { last = performance.now(); });
layout();
if (flags.has('intro') || !store.get('onboarded')) startOnboarding(); else buildHome();
if (flags.has('services')) showServices('pets');
if (flags.has('profile')) { if (S.mode === 'onboard') buildHome(); setTimeout(openProfile, 400); }
requestAnimationFrame(t => { last = t; frame(t); });
