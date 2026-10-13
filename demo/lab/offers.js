// Services path (not Maps): one service, many competing providers. Each row
// says where it comes from (partner mini-app, merchant mini-app, website,
// marketplace), its published price and any offer the provider published.
// Mini-apps open in <iframe sandbox="allow-scripts"> and can only ask; the
// host shows the approval and rebuilds the order from its own price table.
import { $, svg, esc, toast, openSheet, closeSheet, wait } from './ui.js';

export const SERVICE_GROUPS = [
  { id: 'laundry', label: 'Laundry & pressing', glyph: 'drop', img: 'media/laundry.jpg', blurb: 'Pickup, wash and press',
    keys: ['laundry', 'iron', 'press', 'dry clean', 'wash my', 'shirt'],
    providers: [
      { id: 'marinaexpress', name: 'Marina Express Laundry', logo: 'ME', color: '#0A9CC2', source: 'mini-app', rating: 4.8, from: 6, unit: 'per shirt', eta: 'Same-day by 20:00', etaH: 6, entry: 'miniapps/marinaexpress.html', prices: { 'Shirt wash + press': 6 } },
      { id: 'foldpress', name: 'Fold & Press Laundry', logo: 'FP', color: '#A8843F', source: 'mini-app', rating: 4.6, from: 5, unit: 'per shirt', eta: 'Express by 08:30', etaH: 10, offer: 'Express ironing included before 22:00', entry: 'miniapps/foldpress.html' },
      { id: 'palmquick', name: 'Palm Quick Press', logo: 'PQ', color: '#6B5CA5', source: 'mini-app', rating: 4.3, from: 4, unit: 'per shirt', eta: 'Next-day by 08:00', etaH: 14, entry: 'miniapps/palmquick.html' },
      { id: 'presspal', name: 'PressPal', logo: 'PP', color: '#2F4858', source: 'website', rating: 4.2, from: 7, unit: 'per shirt', eta: 'In 48 hours', etaH: 48, offer: 'First order 20% off (their website, as of 13 Oct)' },
    ] },
  { id: 'cleaning', label: 'Home cleaning', glyph: 'home', img: 'media/home-green.jpg', blurb: 'Hourly or bundles',
    keys: ['clean', 'cleaner', 'cleaning', 'housekeep'],
    providers: [
      { id: 'nest-clean', name: 'Nest Helpers', logo: 'NH', color: '#0F766E', source: 'partner', rating: 4.5, from: 40, unit: 'per hour (bundle)', eta: 'Tomorrow 09:00', etaH: 20, offer: '4 hours for AED 160, a published bundle', entry: 'provider',
        line: 'Vetted cleaners · materials included', items: [{ id: 'h2', name: '2 hours', price: 90 }, { id: 'h4', name: '4 hours (bundle)', price: 160 }], slots: ['Tomorrow 09:00', 'Tomorrow 14:00', 'Sat 10:00'] },
      { id: 'sparkle', name: 'Sparkle Home', logo: 'SH', color: '#DB2777', source: 'website', rating: 4.4, from: 39, unit: 'per hour', eta: 'In 2 days', etaH: 48, offer: 'Weekly plan 10% off (their website)' },
      { id: 'maidmatch-c', name: 'Maid Match', logo: 'MM', color: '#7C3AED', source: 'marketplace', rating: 4.3, from: 42, unit: 'per hour', eta: 'Today 18:00', etaH: 6 },
    ] },
  { id: 'ac', label: 'AC service', glyph: 'wrench', img: 'media/ac.jpg', blurb: 'Checks, deep clean, gas',
    keys: ['ac ', ' ac', 'aircon', 'air con', 'a/c', 'cooling', 'not cooling'],
    providers: [
      { id: 'fixit', name: 'FixIt Pros', logo: 'FX', color: '#EA580C', source: 'partner', rating: 4.6, from: 150, unit: 'call-out', eta: 'Today 17:00', etaH: 4, offer: 'Free gas top-up with a deep clean', entry: 'provider',
        line: 'Licensed technicians · 90-day warranty (demo)', items: [{ id: 'chk', name: 'AC check', price: 150 }, { id: 'deep', name: 'Deep clean + gas top-up', price: 220 }], slots: ['Today 17:00', 'Tomorrow 09:00', 'Tomorrow 14:00'] },
      { id: 'coolcare', name: 'CoolCare', logo: 'CC', color: '#0369A1', source: 'marketplace', rating: 4.2, from: 99, unit: 'check', eta: 'Tomorrow', etaH: 24 },
      { id: 'albarsha-cool', name: 'Al Barsha Cooling', logo: 'AB', color: '#475569', source: 'website', rating: 4.5, from: 120, unit: 'check', eta: 'Tomorrow 09:00', etaH: 18 },
    ] },
  { id: 'grooming', label: 'Pet grooming at home', glyph: 'paw', img: 'media/pets.jpg', blurb: 'Mobile vans come to you',
    keys: ['groom', 'pet wash', 'dog wash'],
    providers: [
      { id: 'paws-van', name: 'Paws & Co. Mobile', logo: 'PC', color: '#0E7490', source: 'partner', rating: 4.8, from: 220, unit: 'medium dog', eta: 'Thu 10:00', etaH: 30, offer: 'Bath + trim + nails for AED 220, saves AED 30', entry: 'provider',
        line: 'Grooming van at your building', items: [{ id: 'bath', name: 'Bath + dry', price: 120 }, { id: 'full', name: 'Bath + trim + nails (bundle)', price: 220 }], slots: ['Thu 10:00', 'Thu 15:00', 'Fri 11:00'] },
      { id: 'groomwagon', name: 'Groom Wagon', logo: 'GW', color: '#9333EA', source: 'website', rating: 4.5, from: 199, unit: 'medium dog', eta: 'Next week', etaH: 120 },
    ] },
  { id: 'carwash', label: 'Car wash at home', glyph: 'taxi', img: null, blurb: 'In your parking spot',
    keys: ['car wash', 'wash my car', 'wash the car'],
    providers: [
      { id: 'shine', name: 'Shine at Home', logo: 'SA', color: '#1D4ED8', source: 'partner', rating: 4.6, from: 45, unit: 'sedan', eta: 'Today 19:00', etaH: 3, entry: 'provider',
        line: 'Comes to your parking bay', items: [{ id: 'ext', name: 'Exterior wash', price: 45 }, { id: 'full', name: 'Exterior + interior', price: 75 }], slots: ['Today 19:00', 'Tomorrow 08:00', 'Tomorrow 18:00'] },
      { id: 'waterless', name: 'Waterless Wash Co', logo: 'WW', color: '#15803D', source: 'website', rating: 4.3, from: 39, unit: 'sedan', eta: 'Tomorrow', etaH: 24, offer: '3 washes for AED 99 (their website)' },
    ] },
  { id: 'pharmacy', label: 'Pharmacy delivery', glyph: 'shield', img: null, blurb: 'Everyday medicines',
    keys: ['pharmacy', 'medicine', 'paracetamol', 'panadol', 'chemist'],
    providers: [
      { id: 'palmleaf', name: 'Palm Leaf Pharmacy', logo: 'PL', color: '#2F7D5B', source: 'mini-app', rating: 4.5, from: 9, unit: 'item', eta: 'Delivery ~1 h', etaH: 1, entry: 'miniapps/palmleaf.html' },
      { id: 'nightowl', name: 'Night Owl Pharmacy 24h', logo: 'NO', color: '#1E2A4A', source: 'mini-app', rating: 4.7, from: 12, unit: 'item', eta: 'Open 24 h', etaH: 2, entry: 'miniapps/nightowl.html' },
      { id: 'bloom', name: 'Bloom Care', logo: 'BC', color: '#B4587A', source: 'mini-app', rating: 4.4, from: 68, unit: 'kit', eta: 'Pickup in 30 min', etaH: .5, entry: 'miniapps/bloom.html' },
    ] },
  { id: 'maid', label: 'Maid hire with visa', glyph: 'home', img: 'media/home.jpg', blurb: 'Agency + visa office', caseRef: 'C1',
    keys: ['maid', 'nanny', 'housemaid', 'helper with visa'],
    providers: [
      { id: 'nest-maid', name: 'Nest Helpers', logo: 'NH', color: '#0F766E', source: 'partner', rating: 4.5, from: 6400, unit: 'Filipina placement', eta: '9 days', etaH: 216, entry: 'provider',
        line: 'Placement agency · licensed (demo)', items: [{ id: 'place', name: 'Placement (Filipina)', price: 6400 }], slots: ['Call back today', 'Visit Sat 10:00', 'Visit Sun 16:00'] },
      { id: 'maidmatch', name: 'Maid Match', logo: 'MM', color: '#7C3AED', source: 'website', rating: 4.3, from: 5900, unit: 'Filipina placement', eta: '21 days', etaH: 504 },
      { id: 'homeally', name: 'Home Ally', logo: 'HA', color: '#B45309', source: 'marketplace', rating: 4.1, from: 5600, unit: 'Filipina placement', eta: '30 days', etaH: 720 },
    ] },
];

const SOURCE = {
  partner: { icon: 'check', label: 'Partner mini-app' },
  'mini-app': { icon: 'app', label: 'Merchant mini-app' },
  website: { icon: 'globe', label: 'Website' },
  marketplace: { icon: 'store', label: 'Marketplace' },
};

export function matchService(q) {
  const s = ' ' + q.toLowerCase() + ' ';
  return SERVICE_GROUPS.find(g => g.keys.some(k => s.includes(k)));
}

// ---------------------------------------------------------------- services list (tab)
export function renderServiceGrid(el) {
  el.innerHTML = SERVICE_GROUPS.map(g => {
    const min = Math.min(...g.providers.map(p => p.from));
    const offers = g.providers.filter(p => p.offer).length;
    return `<button class="sg-card" data-svc="${g.id}">
      <span class="sg-img" style="${g.img ? `background-image:url('${g.img}')` : ''}"></span>
      <span class="sg-ic">${svg(g.glyph, 'ic sm')}</span>
      ${offers ? `<span class="sg-badge">${svg('tag', 'ic xs')} ${offers} offer${offers === 1 ? '' : 's'}</span>` : ''}
      <span class="sg-txt"><b>${esc(g.label)}</b><span>${g.providers.length} providers · from AED ${min.toLocaleString('en-US')}</span><em>${esc(g.blurb)}</em></span>
    </button>`;
  }).join('') + `<button class="sg-card ask" data-ask="1"><span class="sg-ic">${svg('spark', 'ic sm')}</span><span class="sg-txt"><b>Anything else</b><span>Ask in the chat. A new service is added as data, not code.</span></span></button>`;
}

// ---------------------------------------------------------------- offers page
let ctx = null; // { post(chatItem), showChat() } from app.js
export function initOffers(c) { ctx = c; }

let current = null, sort = 'value';
export function openOffers(id) {
  current = SERVICE_GROUPS.find(g => g.id === id); if (!current) return;
  sort = 'value';
  renderOffers();
  $('#offers').classList.add('open');
  $('#offersScroll').scrollTop = 0;
}
export function closeOffers() { $('#offers').classList.remove('open'); }

function renderOffers() {
  const g = current;
  const list = [...g.providers].sort(sort === 'value' ? (a, b) => a.from - b.from : sort === 'fast' ? (a, b) => a.etaH - b.etaH : (a, b) => b.rating - a.rating);
  const cheapest = Math.min(...g.providers.map(p => p.from));
  const fastest = Math.min(...g.providers.map(p => p.etaH));
  $('#offersHead').innerHTML = `
    <div class="of-hero" style="${g.img ? `background-image:url('${g.img}')` : ''}"><span class="of-ic">${svg(g.glyph, 'ic sm')}</span></div>
    <h2>${esc(g.label)}</h2>
    <p>${g.providers.length} providers competing · published prices only · nothing is negotiated${g.caseRef ? ` · full flow: case ${g.caseRef}` : ''}</p>
    <div class="seg glass" role="group" aria-label="Sort">
      <button data-sort="value" aria-pressed="${sort === 'value'}">Best price</button>
      <button data-sort="fast" aria-pressed="${sort === 'fast'}">Fastest</button>
      <button data-sort="rated" aria-pressed="${sort === 'rated'}">Top rated</button>
    </div>`;
  $('#offersList').innerHTML = list.map(p => {
    const s = SOURCE[p.source];
    const badges = [p.from === cheapest ? '<span class="holo foil">Best price</span>' : '', p.etaH === fastest ? '<span class="holo alu">Fastest</span>' : ''].join('');
    const cta = p.entry ? `<button class="btn primary sm" data-open="${p.id}">Open ${svg('chev', 'ic xs')}</button>` : `<button class="btn sm" data-visit="${p.id}">Visit ${svg('globe', 'ic xs')}</button>`;
    return `<article class="offer-row">
      <div class="or-top">
        <span class="logo" style="background:${p.color}">${esc(p.logo)}</span>
        <div class="or-name"><b>${esc(p.name)}</b><span class="src-pill">${svg(s.icon, 'ic xs')} ${s.label}</span></div>
        ${cta}
      </div>
      <div class="or-meta">
        <span class="price">from <b>AED ${p.from.toLocaleString('en-US')}</b> <em>${esc(p.unit)} (demo)</em></span>
        <span>${svg('clock', 'ic xs')} ${esc(p.eta)}</span>
        <span>★ ${p.rating.toFixed(1)}</span>
      </div>
      ${p.offer ? `<div class="or-offer">${svg('tag', 'ic xs')} <span>Their published offer: ${esc(p.offer)}</span></div>` : ''}
      ${badges ? `<div class="or-badges">${badges}</div>` : ''}
    </article>`;
  }).join('');
  $('#offersFine').textContent = 'Fictional providers. Prices, offers and times are demo data; every offer is the provider’s own published offer. Mini-apps can only ask for your approval; websites and marketplaces open outside Dubai-io and nothing is sent for you.';
}

export function wireOffers() {
  $('#offers').addEventListener('click', e => {
    const s = e.target.closest('[data-sort]');
    if (s) { sort = s.dataset.sort; renderOffers(); return; }
    const o = e.target.closest('[data-open]');
    if (o) { openMini(current.providers.find(p => p.id === o.dataset.open)); return; }
    const v = e.target.closest('[data-visit]');
    if (v) { const p = current.providers.find(x => x.id === v.dataset.visit); toast(`Opens ${p.name}${p.source === 'marketplace' ? ' on its marketplace' : '’s website'}. Nothing is sent for you.`); }
  });
  $('#offersBack').addEventListener('click', closeOffers);
  addEventListener('message', onBridge);
}

// ---------------------------------------------------------------- mini-app host + bridge
let mini = null; // { p, frame }
async function openMini(p) {
  const url = p.entry === 'provider' ? 'miniapps/provider.html' : p.entry;
  const body = openSheet(`
    <div class="mini-head"><span class="logo" style="background:${p.color}">${esc(p.logo)}</span>
      <div><b id="sheetTitle">${esc(p.name)}</b><span>${p.source === 'partner' ? 'Partner mini-app' : 'Merchant mini-app'} · their own HTML · sandboxed</span></div></div>
    <p class="mini-scope">manifest scopes: order.request · the app can ask, Dubai-io decides</p>
    <iframe class="mini-frame" id="miniFrame" sandbox="allow-scripts" title="${esc(p.name)} mini-app"></iframe>`, () => { mini = null; });
  const frame = body.querySelector('#miniFrame');
  mini = { p, frame };
  try {
    const html = await fetch(url).then(r => { if (!r.ok) throw new Error(r.status); return r.text(); });
    frame.srcdoc = html; // inline document: no network access, no same-origin
  } catch {
    frame.replaceWith(Object.assign(document.createElement('p'), { className: 'empty', textContent: 'This mini-app could not load. The provider list still works.' }));
  }
}

function onBridge(e) {
  if (!mini || e.source !== mini.frame.contentWindow) return;
  const m = e.data;
  if (!m || m.v !== 1 || typeof m.kind !== 'string') return;
  const p = mini.p;
  if (m.kind === 'app.ready') {
    const provider = p.entry === 'provider' ? { name: p.name, logo: p.logo, color: p.color, line: p.line, items: p.items, slots: p.slots, offer: p.offer } : undefined;
    mini.frame.contentWindow.postMessage({ v: 1, kind: 'host.context', payload: { area: 'Dubai Marina', lang: 'en', provider } }, '*');
    return;
  }
  if (m.kind !== 'order.request') {
    mini.frame.contentWindow.postMessage({ v: 1, kind: 'host.error', payload: { reason: 'scope_denied', kind: m.kind } }, '*');
    toast(`Blocked "${m.kind}": not in this app’s scopes.`);
    return;
  }
  // Rebuild the order from the host's own price table, never from the app's numbers.
  let lines, total;
  if (p.items) {
    lines = (m.payload.items || []).map(x => { const it = p.items.find(i => i.id === x.id); return it && x.qty > 0 ? { name: it.name, qty: x.qty, price: it.price } : null; }).filter(Boolean);
    total = lines.reduce((a, l) => a + l.qty * l.price, 0);
  } else {
    lines = (m.payload.items || []).map(x => ({ name: String(x.name || 'Item'), qty: Math.max(1, x.qty | 0), price: Number(x.price) || 0 }));
    total = lines.reduce((a, l) => a + l.qty * l.price, 0);
  }
  const slot = m.payload.slot || m.payload.summary || '';
  closeSheet();
  setTimeout(() => approval(p, lines, total, slot), 340);
}

function approval(p, lines, total, slot) {
  openSheet(`
    <h3 id="sheetTitle">Send to ${esc(p.name)}?</h3>
    <p class="lead">${lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')}${slot ? ` · ${esc(slot)}` : ''}</p>
    <div class="appr">
      <div class="appr-total"><span>Total at their published prices</span><b>AED ${total.toLocaleString('en-US')} (demo)</b></div>
      <h4>Shared with ${esc(p.name)}</h4>
      <ul><li>${svg('check', 'ic xs')} The items and slot above</li><li>${svg('check', 'ic xs')} Area: Dubai Marina (you told me)</li><li>${svg('check', 'ic xs')} Contact through in-app chat (your number stays hidden)</li></ul>
      <h4>Never shared</h4>
      <ul class="no"><li>${svg('close', 'ic xs')} Your profile and anything I noticed about you</li><li>${svg('close', 'ic xs')} Your other orders and chats</li></ul>
    </div>
    <div class="actions"><button class="btn" id="apNo">Cancel</button><button class="btn primary" id="apYes">Approve and send</button></div>
    <p class="fine">One approval. The price can’t change after you send; the merchant can accept or decline.</p>`);
  $('#apNo').addEventListener('click', () => { closeSheet(); toast('Nothing was sent.'); });
  $('#apYes').addEventListener('click', async () => {
    closeSheet(); closeOffers();
    const ref = 'DIO-' + Math.floor(1000 + Math.random() * 9000);
    const id = ctx.post({ type: 'status', provider: p, lines, total, slot, ref, steps: [{ at: new Date(), label: 'Sent to merchant', code: 'SUBMITTED' }] });
    ctx.showChat();
    await wait(2600);
    ctx.update(id, s => s.steps.push({ at: new Date(), label: 'Merchant accepted', code: 'ACCEPTED', sim: true }));
    await wait(2400);
    ctx.update(id, s => s.steps.push({ at: new Date(), label: `Confirmed for ${slot || 'the slot'}`, code: 'SLOT_CONFIRMED', sim: true }));
  });
}
