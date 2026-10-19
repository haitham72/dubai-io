import { openSavedDetails } from './saved-details.js';
import { openSavedRequests } from './service-workflow.js';
// Home v2 lab. Flow: iPhone Wi-Fi sign-in -> install + open Dubai-io -> soft
// card-by-card intro -> io: card stage + chat with the composer at the bottom.
// Asking lifts the cards away into the chat; the answer can be a recovery
// report, the airport guide, competing service offers (Services) or places
// near you (Maps, full-screen).
// Flags (query or hash, hash tokens joined by '.'): fps, tune, nogl, intro,
// wifi, services, maps, guide, profile.
import { createRenderer } from './gl.js';
import { VARIANT } from './shaders.js';
import { PALETTES, ONBOARDING, CASES, PROFILE_CARD, CATEGORIES, PLACES, SOURCES, EPISODES, HYPOTHESES, TOLD_LABELS } from './data.js';
import { profileAt, allowed } from './profile.js';
import { loadProfile, profileEpisodes, setOverride } from './profile-store.js';
import { createMap, km } from './map.js';
import { $, svg, esc, toast, openSheet, closeSheet, reduced, told } from './ui.js';
import { initChat, wireChat, handle, post, update, hasThread, resetChat, trackOrder } from './chat.js';
import { initOffers, wireOffers, openOffers, closeOffers } from './offers.js';
import { initPageHost, resetPageHost, registerPage, openPage } from './page-host.js';
import { initProviderPages } from './provider-pages.js';
import { openConnections } from './accounts.js';
import { renderServicesLanding } from './services.js';
import { startGuide, wireGuide } from './guide.js';
import { startArrival } from './arrival.js';

// C1 used 0.55: apply 70% of that reflection to every stage card.
const CARD_REFLECTION_STRENGTH = 0.55 * 0.70;
const INTRO_MOTION = { first: 2000, next: 1800, exit: 1500, stagger: 90, lift: 1500 };

// ---------------------------------------------------------------- setup
const flags = (() => {
  const f = new Set();
  new URLSearchParams(location.search).forEach((v, k) => f.add(k));
  location.hash.replace(/^#/, '').split('.').filter(Boolean).forEach(t => f.add(t));
  return f;
})();
// Stage mode (PLAN §3): a persistent "Scripted demo" label; ?demo or #demo, kept for this tab.
try { if (flags.has('demo')) sessionStorage.setItem('dubaiio.demo', '1'); } catch { /* storage blocked */ }
if (flags.has('demo') || (() => { try { return sessionStorage.getItem('dubaiio.demo') === '1'; } catch { return false; } })()) {
  document.body.insertAdjacentHTML('beforeend', '<div class="demo-label" role="note">Scripted demo · sandbox merchant · demo data</div>');
}
const paletteName = window.PALETTE in PALETTES ? window.PALETTE : 'cyan';
const palette = PALETTES[paletteName];
const store = {
  get(k) { try { return localStorage.getItem('dubaiio.lab.' + k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem('dubaiio.lab.' + k, v); } catch { /* private mode */ } },
};
const catOf = id => CATEGORIES.find(c => c.id === id);
const fmtN = n => n.toLocaleString('en-US');

document.documentElement.dataset.palette = paletteName;
document.body.insertAdjacentHTML('beforeend', `
<div id="app" class="mode-home ${reduced ? 'reduced' : ''}">
  <canvas id="gl" aria-hidden="true"></canvas>
  <header class="top">
    <div class="brand"><button class="brand-btn" id="brandBtn" aria-label="Dubai-io. Tap to restart the demo"><b>Dubai-io</b></button><span class="area">${svg('pin', 'ic xs')} Dubai Marina · demo area</span></div>
    <span class="pill demo" title="Everything here is demo data">Demo data</span>
  </header>
  <main id="stage" aria-roledescription="carousel" aria-label="Home cards"></main>
  <nav class="rail" id="rail" aria-label="Cards"></nav>
  <p class="caption" id="caption" aria-live="polite"></p>

  <section class="chatv" id="chat" aria-label="Chat">
    <div class="c-top">
      <button class="round glass" id="chatBack" aria-label="Back to cards">${svg('back')}</button>
      <div class="c-title"><button class="brand-btn" id="brandBtn2" aria-label="Dubai-io. Tap to restart the demo"><b>Dubai-io</b></button><span>Luna understands requests · service actions require approval</span></div>
    </div>
    <div class="c-scroll" id="chatScroll"><div class="c-list" id="chatList"></div></div>
  </section>

  <section id="results" class="results" aria-label="Map near you">
    <div id="mapEl" class="mapbox"></div>
    <div class="map-fallback" id="mapFallback" hidden>Map needs WebGL. The list below has every place.</div>
    <div class="r-top">
      <button class="round glass" id="back" aria-label="Back">${svg('back')}</button>
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

  <section class="svcgrid" id="svcGrid" aria-label="Services"></section>

  <form class="composer glass" id="composer" role="search" autocomplete="off">
    <label class="sr" for="q">Ask Dubai-io</label>
    <input id="q" name="q" type="text" placeholder="Ask Dubai-io" enterkeyhint="send" />
    <button type="button" class="c-mic" id="mic" aria-label="Voice (typed in this lab)">${svg('mic', 'ic sm')}</button>
    <button type="submit" class="c-send" aria-label="Send">${svg('up', 'ic sm')}</button>
  </form>

  <nav class="tabbar glass" aria-label="Tabs">
    <button data-tab="home" aria-current="page">${svg('orb')}<span>io</span></button>
    <button data-tab="maps">${svg('map')}<span>Maps</span></button>
    <button data-tab="services">${svg('grid')}<span>Services</span></button>
    <button data-tab="me">${svg('person')}<span>Me</span></button>
  </nav>

  <section class="offers" id="offers" aria-label="Offers">
    <div class="of-top"><button class="round glass" id="offersBack" aria-label="Back">${svg('back')}</button><span class="pill demo">Demo data</span></div>
    <div class="of-scroll" id="offersScroll"><div id="offersHead" class="of-head"></div><div id="offersList" class="of-list"></div><p class="fine of-fine" id="offersFine"></p></div>
  </section>

  <section class="guide" id="guide" aria-label="Airport guide">
    <div class="g-top"><button class="round glass" id="gClose" aria-label="Close guide">${svg('close')}</button>
      <div class="g-meta"><b>DXB arrival guide</b><span id="gTerm"></span></div><span class="pill demo">Demo</span></div>
    <div class="g-dots" id="gDots"></div>
    <div class="g-card" id="gCard"></div>
    <div class="g-actions"><button class="btn" id="gLost">I’m lost</button><button class="btn primary" id="gNext"></button></div>
  </section>

  <div class="scrim" id="scrim" hidden></div>
  <section class="sheet" id="sheet" role="dialog" aria-modal="true" aria-labelledby="sheetTitle" hidden>
    <button class="grab" id="sheetClose" aria-label="Close"><span></span></button>
    <div class="sheet-body" id="sheetBody"></div>
  </section>
  <section class="portal" id="portal" hidden aria-label="Arrival (demo)"></section>
  <div class="toast" id="toast" role="status" hidden></div>
  <div class="fps" id="fps" hidden></div>
  <div class="tune glass" id="tune" hidden></div>
</div>`);

const app = $('#app'), canvas = $('#gl'), stageEl = $('#stage'), railEl = $('#rail'), captionEl = $('#caption');
const renderer = flags.has('nogl') ? null : createRenderer(canvas, palette);
if (!renderer) app.classList.add('nogl');

// ---------------------------------------------------------------- state
const T0 = Date.parse('2026-10-01T00:00:00'), T1 = Math.max(Date.parse('2026-10-13T23:00:00'), Date.now());
const S = {
  mode: 'onboard', onboardingExit: false, deck: [], pos: 0, vel: 0, target: 0, drag: null,
  tilt: [0, 0], tiltTarget: [0, 0], view: 'home', from: 'home', maxDpr: 3,
  tune: { ribs: 8.5, foil: 1, grain: 0.07, aura: 0.95 },
  shape: { falloff: 2.4, height: 0.85, glow: 0.24 },
  overrides: {}, asOf: T1, active: -1,
  lift: 0, liftFrom: 0, liftTo: 0, liftStart: 0, liftDur: 820,
  ask: null, cat: 'all', sub: null, src: null, detail: null, snap: 'peek',
};
const G = {};
window.__lab = { S, G };
let seedN = 1, onboardingExitTimer = 0;
const mkCard = def => ({ ...def, holo: CARD_REFLECTION_STRENGTH, variant: VARIANT[def.kind] ?? 0, seed: (seedN++ * 7.31) % 13, rev: reduced ? 1 : 0, revStart: 0, revDur: 1100, out: false, outFrom: 1, exitProgress: 0, el: null });

// ---------------------------------------------------------------- views
const VIEWS = ['home', 'chat', 'results', 'services'];
function setView(v) {
  if (S.view !== v) S.from = S.view;
  S.view = v;
  for (const x of VIEWS) app.classList.toggle('mode-' + x, x === v);
  setTab(v === 'results' ? 'maps' : v === 'services' ? 'services' : 'home');
  setLift(v === 'home' ? 0 : 1);
}
function showChat() { closeOffers(); if (S.view !== 'chat') setView('chat'); }
function setTab(t) { document.querySelectorAll('.tabbar button').forEach(b => b.toggleAttribute('aria-current', b.dataset.tab === t)); }

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
const smooth = t => t * t * t * (t * (t * 6 - 15) + 10);
function params(i) {
  const d = i - S.pos, ad = Math.abs(d), sg = Math.sign(d);
  const c = S.deck[i];
  const e = 1 - Math.pow(1 - c.rev, 3);
  const li = Math.max(0, Math.min(1, S.lift * 1.35 - ad * 0.16));
  const fl = li * li * (3 - 2 * li);
  return {
    d, ad, fl,
    tx: sg * (Math.min(ad, 1) * G.spacing + Math.max(ad - 1, 0) * G.cw * 0.26),
    ty: (1 - e) * 26 - c.exitProgress * G.ch * 0.45 - fl * (G.H * 0.72),
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
function reveal(c, delay = 0, dur = 1100) { c.out = false; c.exitProgress = 0; c.revStart = performance.now() + delay; c.revDur = dur; if (reduced) c.rev = 1; }
function buildRail() {
  railEl.innerHTML = S.deck.map((c, i) => {
    const bg = c.img ? `background-image:url('${c.img}')` : `background:radial-gradient(circle at 30% 30%, ${palette.ramp[3]}, ${palette.ramp[1]} 60%, ${palette.ramp[0]})`;
    return `<button class="dot" data-i="${i}" style="${bg}" aria-label="${esc(c.title)}"></button>`;
  }).join('');
}

// ---------------------------------------------------------------- flows: intro, home
function startOnboarding() {
  clearTimeout(onboardingExitTimer);
  S.onboardingExit = false;
  S.mode = 'onboard';
  S.deck = [mkCard(ONBOARDING[0])];
  S.pos = S.target = 0; S.vel = 0;
  mountDeck();
  reveal(S.deck[0], 200, INTRO_MOTION.first);
}
function advance() {
  if (S.mode !== 'onboard' || S.onboardingExit) return;
  const at = Math.round(S.pos);
  if (at < S.deck.length - 1) { S.target = at + 1; return; }
  if (S.deck.length < ONBOARDING.length) {
    const c = mkCard(ONBOARDING[S.deck.length]);
    appendCard(c); reveal(c, 180, INTRO_MOTION.next); S.target = S.deck.length - 1;
  } else finishOnboarding();
}
function finishOnboarding() {
  if (S.onboardingExit) return;
  S.onboardingExit = true;
  store.set('onboarded', '1');
  const now = performance.now(), deck = S.deck, active = Math.round(S.pos);
  let end = 0;
  deck.forEach((c, i) => {
    const delay = Math.abs(i - active) * INTRO_MOTION.stagger;
    c.out = true; c.outFrom = c.rev; c.exitProgress = 0;
    c.revStart = now + delay; c.revDur = INTRO_MOTION.exit;
    end = Math.max(end, delay + c.revDur);
  });
  onboardingExitTimer = setTimeout(() => {
    // A replay/restart may have replaced the deck while the cards were leaving.
    if (S.deck === deck) buildHome();
  }, reduced ? 0 : end + 40);
}
function homeOrder() {
  const p = profileAt(profileEpisodes(), HYPOTHESES, S.asOf, S.overrides);
  const byId = Object.fromEntries([...p.noticed, ...p.confirmed].map(h => [h.id, h]));
  return CASES.map((c, k) => {
    const h = c.because && byId[c.because];
    // Tier rule: hypotheses may only re-rank, with a visible Because chip (allowed(h, 'rerank')).
    const boost = h && allowed(h, 'rerank') && (h.surfaced || h.provenance === 'user_supplied') ? h.conf : 0;
    return { c, h: boost ? h : null, score: boost * 10 - k };
  }).sort((a, b) => b.score - a.score);
}
function buildHome() {
  clearTimeout(onboardingExitTimer);
  S.onboardingExit = false;
  S.mode = 'home';
  S.deck = [mkCard(PROFILE_CARD), ...homeOrder().map(o => mkCard({ ...o.c, becauseHyp: o.h }))];
  S.pos = S.target = 1; S.vel = 0;
  mountDeck();
  S.deck.forEach((c, i) => reveal(c, 120 + Math.abs(i - 1) * 140, 1000));
}
function captionFor(c) {
  if (!c) return '';
  if (S.mode === 'onboard') return c.next === 'Start' ? 'Tap Start, or just ask below.' : 'Swipe, or tap Next. Or just ask below.';
  if (c.becauseHyp) {
    const h = c.becauseHyp;
    const tag = h.provenance === 'user_supplied' ? 'you confirmed' : `I noticed, ${Math.round(h.conf * 100)}%`;
    return `<span class="because">Because</span> ${esc(h.label.toLowerCase())} <span class="tag">${tag}</span>`;
  }
  return esc(c.caption || '');
}
function renderYouMini() {
  const ul = $('#youMini'); if (!ul) return;
  const p = profileAt(profileEpisodes(), HYPOTHESES, S.asOf, S.overrides);
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
      const stiffness = S.mode === 'onboard' ? 90 : 210;
      const damping = S.mode === 'onboard' ? 20 : 27;
      const a = -stiffness * (S.pos - S.target) - damping * S.vel;
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
      c.exitProgress = c.out ? smooth(t) : 0;
      c.rev = c.out ? c.outFrom * (1 - c.exitProgress) : S.mode === 'onboard' ? smooth(t) : t;
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
  if (renderer && !document.hidden) {
    if (stageVisible) {
      glCards.sort((a, b) => b.ad - a.ad);
      auras.sort((a, b) => b.weight - a.weight);
      renderer.render({ cards: glCards, auras: auras.slice(0, 2), time, tune: S.tune, shape: S.shape });
    } else renderer.clear();
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
function setLift(to) { if (S.liftTo === to) return; S.liftDur = S.mode === 'onboard' ? INTRO_MOTION.lift : 820; S.liftFrom = S.lift; S.liftTo = to; S.liftStart = performance.now(); }

// ---------------------------------------------------------------- stage input
function onDown(e) {
  if (S.view !== 'home' || S.onboardingExit || e.button > 0 || e.target.closest('button')) return;
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
railEl.addEventListener('click', e => { const d = e.target.closest('.dot'); if (d && !S.onboardingExit) S.target = +d.dataset.i; });
addEventListener('keydown', e => {
  if (e.target.closest?.('input')) return;
  if (!$('#sheet').hidden) { if (e.key === 'Escape') closeSheet(); return; }
  if (S.view !== 'home') { if (e.key === 'Escape') goBack(); return; }
  if (S.onboardingExit) { if (['ArrowLeft', 'ArrowRight', 'Enter'].includes(e.key)) e.preventDefault(); return; }
  if (e.key === 'ArrowRight') { if (S.mode === 'onboard' && Math.round(S.pos) === S.deck.length - 1) advance(); else S.target = Math.min(S.deck.length - 1, Math.round(S.pos) + 1); }
  if (e.key === 'ArrowLeft') S.target = Math.max(0, Math.round(S.pos) - 1);
  if (e.key === 'Enter') openCard(S.deck[Math.round(S.pos)]);
});
$('#sheetClose').addEventListener('click', closeSheet);
$('#scrim').addEventListener('click', closeSheet);

function openCard(c) {
  if (!c) return;
  if (S.mode === 'onboard') { advance(); return; }
  if (c.id === 'you') { openProfile(); return; }
  if (c.ask) { handle(c.ask); return; }
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
  const p = profileAt(profileEpisodes(), HYPOTHESES, S.asOf, S.overrides);
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
    const { h, o } = b.dataset;
    setOverride(h, o).then(() => {
      S.overrides[h] = o;
      toast({ confirmed: 'Confirmed. It now counts as something you told me.', rejected: 'Marked not true. Saved.', forgotten: 'Forgotten, with its evidence on this device.' }[o]);
      renderProfile(); refreshHomeCaptions();
    }).catch(err => toast('Not saved: ' + err.message));
  }));
}
function refreshHomeCaptions() {
  if (S.mode !== 'home') return;
  const order = homeOrder();
  for (const c of S.deck) { const o = order.find(x => x.c.id === c.id); if (o) c.becauseHyp = o.h; }
  S.active = -1;
}

// ---------------------------------------------------------------- Maps: near me
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
  closeSheet(); closeOffers();
  setView('results');
  ensureMap();
  setSnap('peek', true);
  renderResults();
  setTimeout(() => { MAP?.resize(); refit(); }, reduced ? 0 : 380);
}
function goBack() {
  if (S.view === 'results' && S.detail) { backToList(); return; }
  if (S.view === 'results' && S.from === 'chat') { setView('chat'); return; }
  setView('home');
}
function refit() {
  if (!MAP) return;
  const list = filtered().filter(p => p.lat != null);
  MAP.filter(new Set(list.map(p => p.id)));
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
const media = (p, cls) => p.img ? `<div class="${cls}" style="background-image:url('${p.img}')"></div>` : `<div class="${cls} glyph">${svg(catOf(p.cat).glyph, 'ic lg')}</div>`;
function renderResults() {
  renderChips();
  const ask = $('#ask');
  if (S.ask) {
    const cat = catOf(S.cat);
    ask.hidden = false;
    ask.innerHTML = `<span class="ask-q">${esc(S.ask)}</span><span class="ask-u">${svg('orb', 'ic xs')} ${cat ? `Near you · ${esc(cat.label)}${S.sub ? ' › ' + esc(S.sub) : ''}` : 'Near you · everything'}</span>`;
  } else ask.hidden = true;
  if (S.detail) { renderDetail(); return; }
  const list = filtered();
  const cat = catOf(S.cat);
  const what = S.sub ? S.sub.toLowerCase() : cat ? cat.label.toLowerCase() : 'places';
  const partners = list.filter(p => p.partner).length;
  const counts = Object.fromEntries(SOURCES.map(s => [s.id, PLACES.filter(p => (S.cat === 'all' || p.cat === S.cat) && p.why === s.id).length]));
  rsScroll.innerHTML = `
    <div class="rs-head"><h3>${list.length} ${esc(what)} near Dubai Marina</h3>
      <p>${partners ? `${partners} partner${partners === 1 ? '' : 's'} with published prices · ` : ''}closest first · distances are estimates</p></div>
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

$('#back').addEventListener('click', goBack);
$('#rChips').addEventListener('click', e => { const b = e.target.closest('[data-cat]'); if (!b) return; S.cat = b.dataset.cat; S.sub = null; S.src = null; S.detail = null; S.ask = null; renderResults(); refit(); });
$('#rSubs').addEventListener('click', e => { const b = e.target.closest('[data-sub]'); if (!b) return; S.sub = b.dataset.sub || null; S.detail = null; renderResults(); refit(); });
rsScroll.addEventListener('click', e => {
  if (rsheet.dataset.dragged === '1') return;
  const s = e.target.closest('[data-src]');
  if (s) { S.src = S.src === s.dataset.src ? null : s.dataset.src; renderResults(); refit(); return; }
  const t = e.target.closest('[data-p]');
  if (t) openDetail(t.dataset.p);
});
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

// ---------------------------------------------------------------- Services: competing offers
function enterServices() { closeSheet(); renderServicesLanding($('#svcGrid'), told.area); setView('services'); }
$('#svcGrid').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  if (b.dataset.area) { told.area = b.dataset.area; renderServicesLanding($('#svcGrid'), told.area); return; }
  if (b.dataset.servicesAsk) { $('#q').focus(); return; }
  if (b.dataset.servicesSay) { handle(b.dataset.servicesSay); return; }
  if (b.dataset.svc) openOffers(b.dataset.svc);
});

// ---------------------------------------------------------------- chat, composer, tabs
initChat({ enterResults, openOffers, startGuide, showChat });
initOffers({ post, update, showChat, trackOrder });
loadProfile().then(o => { Object.assign(S.overrides, o); refreshHomeCaptions(); });
wireChat(); wireOffers(); wireGuide(); initPageHost(); initProviderPages();
$('#chatBack').addEventListener('click', () => setView('home'));

const placeholders = ['I lost my wallet', 'Guide me through the airport', 'Home cleaning prices', 'Coffee near me', 'A groomer for my dog'];
let phI = 0;
setInterval(() => { const q = $('#q'); if (!q.value && document.activeElement !== q) q.placeholder = placeholders[phI++ % placeholders.length]; }, 3200);
$('#composer').addEventListener('submit', e => {
  e.preventDefault();
  const text = $('#q').value.trim(); if (!text) return;
  // Explicit input owns the transition; cancel the exit before dispatching chat.
  if (S.onboardingExit) buildHome();
  $('#q').value = ''; $('#q').blur();
  if (S.mode === 'onboard') { store.set('onboarded', '1'); }
  closeOffers();
  handle(text);
});
$('#mic').addEventListener('click', () => toast('Voice needs a secure page and a tap on the phone. Type for now.'));
document.querySelector('.tabbar').addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  const t = b.dataset.tab;
  if (S.onboardingExit) buildHome();
  closeOffers();
  if (t === 'home') setView(hasThread() && S.view === 'home' ? 'chat' : 'home');
  else if (t === 'maps') enterResults({ cat: 'all' });
  else if (t === 'services') enterServices();
  else if (t === 'me') openMe();
});
registerPage('account.me', { title: 'Me', source: 'Dubai-io', render: () => `
    <p class="lead">Lab build · palette: ${esc(paletteName)}</p>
    <div class="actions col">
      <button class="btn" id="meDetails">${svg('person', 'ic sm')} Your saved details</button>
      <button class="btn" id="meRequests">${svg('bag', 'ic sm')} Saved requests</button>
      <button class="btn" id="meConnections">${svg('lock', 'ic sm')} Connected accounts</button>
      <button class="btn" id="meProfile">${svg('person', 'ic sm')} You, over time</button>
      <button class="btn" id="meIntro">${svg('orb', 'ic sm')} Replay the intro</button>
      <button class="btn" id="meWifi">${svg('wifi', 'ic sm')} Replay landing and Wi-Fi sign-in</button>
    </div>
    <p class="fine">Flags: add #fps, #tune or #nogl to the link (join with dots, e.g. #fps.tune).</p>`, mount: () => {
  $('#meDetails').addEventListener('click', openSavedDetails);
  $('#meRequests').addEventListener('click', openSavedRequests);
  $('#meConnections').addEventListener('click', () => openConnections());
  $('#meProfile').addEventListener('click', () => { closeSheet(); setTimeout(openProfile, 340); });
  $('#meIntro').addEventListener('click', () => { closeSheet(); setView('home'); startOnboarding(); });
  $('#meWifi').addEventListener('click', () => { closeSheet(); setView('home'); S.deck = []; stageEl.innerHTML = ''; railEl.innerHTML = ''; startArrival(() => startOnboarding()); });
} });
function openMe() { openPage('account.me'); }

// Tapping the Dubai-io logo restarts the demo from the airport Wi-Fi.
function restartDemo() {
  resetChat(); resetPageHost();
  clearTimeout(onboardingExitTimer); S.onboardingExit = false;
  closeSheet(); closeOffers(); setView('home');
  try { localStorage.removeItem('dubaiio.lab.onboarded'); } catch { /* private mode */ }
  S.deck = []; stageEl.innerHTML = ''; railEl.innerHTML = ''; captionEl.textContent = '';
  toast('Restarting the demo from landing.');
  startArrival(() => startOnboarding());
}
$('#brandBtn').addEventListener('click', restartDemo);
$('#brandBtn2').addEventListener('click', restartDemo);

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
const direct = ['intro', 'services', 'maps', 'guide', 'profile'].some(f => flags.has(f));
if (flags.has('wifi') || (firstRun && !direct)) startArrival(() => startOnboarding());
else if (flags.has('intro')) startOnboarding();
else buildHome();
if (flags.has('services')) { if (S.mode === 'onboard') buildHome(); enterServices(); }
if (flags.has('maps')) { if (S.mode === 'onboard') buildHome(); enterResults({ cat: 'pets' }); }
if (flags.has('guide')) { if (S.mode === 'onboard') buildHome(); handle('Guide me through the airport'); }
if (flags.has('profile')) { if (S.mode === 'onboard') buildHome(); setTimeout(openProfile, 400); }
requestAnimationFrame(t => { last = t; frame(t); });
