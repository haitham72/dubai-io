// io chat. A lab stand-in for Luna: a deterministic intent router (clearly
// labelled "lab router") until the LangGraph service in apps/api replaces it.
// Intents: lost item -> recovery, airport -> guide, service -> competing offers,
// place -> map, greeting, otherwise a clarifying question. Never invents a
// status: reports are "prepared, not filed"; items stay "not recovered".
import { $, svg, esc, toast, told, wait } from './ui.js';
import { CATEGORIES } from './data.js';
import { SERVICE_GROUPS, matchService } from './offers.js';

let ctx = null; // { enterResults, openOffers, startGuide, showChat }
const items = [];
let seq = 0;

export function initChat(c) { ctx = c; }

// ---------------------------------------------------------------- router
const LOST_VERB = /\b(lost|lose|losing|left|forgot|forgotten|missing|can'?t find|cannot find|dropped)\b/;
const LOST_ITEM = /\b(wallet|purse|bag|backpack|handbag|phone|iphone|mobile|passport|keys?|laptop|cards?|luggage|suitcase|watch|glasses|id)\b/;
const AIRPORT = /\b(airport|dxb|terminal|t1|t2|t3|landed|landing|arrivals?|immigration|passport control|baggage|belt|customs)\b|guide me/;
const NEAR = /\b(near|nearby|around|close by|closest|nearest|map|where is|where's|walking distance)\b/;
const HELLO = /^(hi|hello|hey|salam|salaam|marhaba|good (morning|evening|afternoon))\b/;
const THANKS = /\b(thanks|thank you|shukran)\b/;

export function route(text) {
  const q = text.toLowerCase().trim();
  if (LOST_VERB.test(q)) {
    const m = q.match(LOST_ITEM);
    return { intent: 'lost_item', item: m ? m[1].replace(/s$/, '') : 'item', conf: m ? 0.92 : 0.7 };
  }
  if (AIRPORT.test(q)) return { intent: 'airport_guide', conf: 0.9 };
  const svc = matchService(q);
  const cat = CATEGORIES.find(c => c.keywords.some(k => q.includes(k)));
  if (svc && !NEAR.test(q)) return { intent: 'service_offers', service: svc.id, conf: 0.85 };
  if (cat || NEAR.test(q)) {
    let sub = null;
    if (cat) for (const [s, keys] of Object.entries(cat.subKeys || {})) if (keys.some(k => q.includes(k))) { sub = s; break; }
    return { intent: 'places_near', cat: cat ? cat.id : 'all', sub, conf: cat ? 0.82 : 0.6 };
  }
  if (svc) return { intent: 'service_offers', service: svc.id, conf: 0.75 };
  if (HELLO.test(q)) return { intent: 'greeting', conf: 0.95 };
  if (THANKS.test(q)) return { intent: 'thanks', conf: 0.95 };
  return { intent: 'unclear', conf: 0.3 };
}

// ---------------------------------------------------------------- thread
export function post(it) { it.id = ++seq; items.push(it); render(); return it.id; }
export function update(id, fn) { const it = items.find(i => i.id === id); if (it) { fn(it); render(); } }
export const hasThread = () => items.length > 0;

async function botSay(html, extra = {}) {
  const typing = post({ who: 'bot', typing: true });
  await wait(520);
  const it = items.find(i => i.id === typing);
  Object.assign(it, { typing: false, html, ...extra });
  render();
  return typing;
}

const fmtT = d => d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

function render() {
  const list = $('#chatList'); if (!list) return;
  list.innerHTML = items.map(it => {
    if (it.who === 'me') return `<div class="msg me"><p>${esc(it.text)}</p>${it.r ? `<span class="luna">${svg('orb', 'ic xs')} Luna (lab router) · ${esc(it.r.intent)}${it.r.item ? ` · item: ${esc(it.r.item)}` : ''}${it.r.service ? ` · ${esc(it.r.service)}` : ''}${it.r.cat ? ` · ${esc(it.r.cat)}${it.r.sub ? ' › ' + esc(it.r.sub) : ''}` : ''} · ${Math.round(it.r.conf * 100)}%</span>` : ''}</div>`;
    if (it.typing) return `<div class="msg bot typing"><span class="orbdot"></span><span class="orbdot"></span><span class="orbdot"></span></div>`;
    if (it.type === 'status') return statusHTML(it);
    return `<div class="msg bot">${it.html}</div>`;
  }).join('');
  requestAnimationFrame(() => { const s = $('#chatScroll'); if (s) s.scrollTop = s.scrollHeight; });
}

function statusHTML(s) {
  const last = s.steps[s.steps.length - 1];
  return `<div class="msg bot wide status">
    <div class="st-head"><span class="logo" style="background:${s.provider.color}">${esc(s.provider.logo)}</span><div><b>${esc(s.provider.name)}</b><span>${s.lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')} · AED ${s.total.toLocaleString('en-US')} (demo)</span></div></div>
    <ol class="st-steps">${s.steps.map(x => `<li class="${x === last ? 'now' : ''}"><span class="st-dot"></span><div><b>${esc(x.label)}</b><span><code>${x.code}</code> · ${fmtT(x.at)}${x.sim ? ' · merchant role, simulated' : ''}</span></div></li>`).join('')}</ol>
    <p class="st-ref">Ref ${esc(s.ref)} · the price can’t change now</p>
  </div>`;
}

// ---------------------------------------------------------------- entry
export async function handle(text) {
  const r = route(text);
  post({ who: 'me', text, r });
  ctx.showChat();
  switch (r.intent) {
    case 'lost_item': return lost(r.item);
    case 'airport_guide': return airport();
    case 'service_offers': return offers(r.service);
    case 'places_near': {
      await botSay(`<p>Here’s what’s near you, closest first. Opening the map.</p>`);
      await wait(500);
      return ctx.enterResults({ ask: text, cat: r.cat, sub: r.sub });
    }
    case 'greeting': return botSay(`<p>Hi! Ask me for a service, a place nearby or help at the airport, or tell me if you’ve lost something.</p>${chips(['Guide me through the airport', 'Home cleaning prices', 'Coffee near me', 'I lost my wallet'])}`);
    case 'thanks': return botSay(`<p>Anytime.</p>`);
    default: return botSay(`<p>I’m not sure I got that. Which of these is closest?</p>${chips(['Find a place near me', 'Compare a service', 'I lost something', 'Help at the airport'])}<p class="hint">I’d rather ask than guess.</p>`);
  }
}
const chips = list => `<div class="qchips">${list.map(t => `<button data-say="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;

// ---------------------------------------------------------------- flows
async function offers(id) {
  const g = SERVICE_GROUPS.find(x => x.id === id);
  const top = [...g.providers].sort((a, b) => a.from - b.from).slice(0, 3);
  await botSay(`<p>${g.providers.length} providers compete for <b>${esc(g.label.toLowerCase())}</b>. Cheapest first; every offer is the provider’s own published one.</p>
    <div class="mini-rows">${top.map(p => `<div class="mr"><span class="logo" style="background:${p.color}">${esc(p.logo)}</span><span class="mr-t"><b>${esc(p.name)}</b><em>from AED ${p.from.toLocaleString('en-US')} ${esc(p.unit)} · ${esc(p.eta)}</em></span>${p.offer ? `<span class="mr-o">${svg('tag', 'ic xs')}</span>` : ''}</div>`).join('')}</div>
    <button class="btn primary sm" data-offers="${g.id}">See all ${g.providers.length} offers ${svg('chev', 'ic xs')}</button>`);
}

async function airport() {
  await botSay(`<p>I’ll guide you by the airport’s signs, one step at a time, and you tell me when you’re through each one. I won’t guess where you are.</p><p>Which terminal did you land at?</p>
    <div class="qchips">${['1', '2', '3'].map(t => `<button data-flow="guide:${t}">Terminal ${t}</button>`).join('')}<button data-flow="guide:?">Not sure</button></div>`);
}
async function startGuideFlow(term) {
  ctx.startGuide({
    terminal: term,
    onDone: async res => {
      if (!res || !res.mode) { await botSay(`<p>Guide closed. Say “guide me” any time to pick it up again.</p>`); return; }
      const mem = [told.belt && `belt ${esc(told.belt)}`, told.plate && `taxi ${esc(told.plate)}${told.roof ? ` (${esc(told.roof)} roof)` : ''}`].filter(Boolean);
      await botSay(`<p>${res.mode === 'Metro' ? 'Enjoy the ride. Keep your Nol card handy.' : res.mode === 'Taxi' ? 'Safe ride to Dubai Marina.' : 'You’re through arrivals.'}</p>
        ${mem.length ? `<p class="told">${svg('check', 'ic xs')} You told me: ${mem.join(' · ')}</p><p class="hint">If you leave something in the car, just say “I lost my wallet”.</p>` : ''}`);
    },
  });
}

async function lost(item) {
  const what = item === 'item' ? 'something' : `your ${item}`;
  await botSay(`<p>I’m sorry. Losing ${esc(what)} is stressful. Let’s go step by step.</p><p>Where did you last have it?</p>
    <div class="qchips"><button data-flow="lost:taxi:${esc(item)}">In a taxi</button><button data-flow="lost:metro:${esc(item)}">On the Metro</button><button data-flow="lost:shop:${esc(item)}">In a shop or mall</button><button data-flow="lost:unsure:${esc(item)}">Not sure</button></div>`);
}

async function lostWhere(where, item) {
  const label = item === 'item' ? 'Item' : item[0].toUpperCase() + item.slice(1);
  if (where === 'shop') {
    await botSay(`<p>Go back to the shop first, then the mall’s customer service desk; malls keep lost property.</p><button class="btn sm" data-near="1">${svg('map', 'ic xs')} Show me what’s nearby</button>${cardsTip(item)}`);
    return;
  }
  if (where === 'unsure') {
    await botSay(`<p>Let’s retrace. Check these, most likely first:</p>
      <ol class="checklist"><li>The last place you paid for something</li><li>The taxi or Metro you took (RTA lost and found covers both)</li><li>Your hotel reception</li></ol>
      <div class="qchips"><button data-flow="lost:taxi:${esc(item)}">It might be the taxi</button><button data-flow="lost:metro:${esc(item)}">It might be the Metro</button></div>${cardsTip(item)}`);
    return;
  }
  const isTaxi = where === 'taxi';
  const trip = told.trip;
  const rows = isTaxi ? [
    ['When', trip ? `${trip.at.toLocaleString('en-GB', { weekday: 'short', hour: '2-digit', minute: '2-digit' })} (you told me)` : null, 'when'],
    ['Pickup', trip ? `${trip.from} (you told me)` : null, 'from'],
    ['Drop-off', trip ? `${trip.to} (you told me)` : null, 'to'],
    ['Taxi plate', told.plate ? `${told.plate} (you told me)` : null, 'plate'],
    ['Roof colour', told.roof ? `${told.roof} (you told me)` : null, 'roof'],
  ] : [
    ['When', null, 'when'], ['Line and station', null, 'station'],
  ];
  const id = await botSay(reportHTML({ label, isTaxi, rows, desc: null, done: false }));
  wireReport(id, { label, isTaxi, rows, item });
}

function reportHTML({ label, isTaxi, rows, desc, done }) {
  return `<div class="report">
    <div class="rp-head">${svg(isTaxi ? 'taxi' : 'train', 'ic sm')}<b>Report for RTA lost and found</b><span class="pill-st ${done ? 'ready' : ''}">${done ? 'Prepared · not filed' : 'Draft'}</span></div>
    <ul class="rp-rows">
      <li><span>${esc(label)}</span><b>${desc ? esc(desc) : '<em>Describe it below</em>'}</b></li>
      ${rows.map(([k, v, key]) => `<li><span>${esc(k)}</span>${v ? `<b>${esc(v)}</b>` : `<input data-f="${key}" placeholder="${k === 'When' ? 'e.g. today 22:10' : 'add if you know'}" />`}</li>`).join('')}
    </ul>
    ${done ? `<div class="rp-next">
        <p><b>Not recovered yet.</b> Send this to RTA through their official channels; I can’t file it for you.</p>
        <div class="callbox"><span>RTA call centre</span><b>800 9090</b><button class="btn sm" data-copy="8009090">Copy</button></div>
        <button class="btn sm" data-official="rta">${svg('globe', 'ic xs')} Open RTA lost and found (official)</button>
      </div>` : `<form class="rp-desc" data-desc="1"><input placeholder="Colour, size, what was inside (no card numbers)" /><button class="btn primary sm">Prepare</button></form>
      <p class="hint">I only ask for what I don’t already know.</p>`}
  </div>`;
}
function wireReport(id, st) {
  const it = items.find(i => i.id === id);
  it.after = form => {
    const vals = {};
    form.closest('.report').querySelectorAll('[data-f]').forEach(i => { if (i.value.trim()) vals[i.dataset.f] = i.value.trim(); });
    const desc = form.querySelector('input').value.trim();
    if (!desc) { toast('Describe it in a few words first.'); return; }
    const rows = st.rows.map(([k, v, key]) => [k, v || (vals[key] ? `${vals[key]} (you told me)` : 'not given'), key]);
    it.html = reportHTML({ ...st, rows, desc, done: true }) + cardsTip(st.item);
    render();
  };
}
const cardsTip = item => (['wallet', 'purse', 'card', 'bag', 'handbag'].includes(item)
  ? `<p class="hint">${svg('shield', 'ic xs')} If bank cards were inside, freeze them in your bank’s app now. If your Emirates ID or passport was inside, report it through the official channels.</p>` : '');

// ---------------------------------------------------------------- clicks inside the thread
export function wireChat() {
  $('#chatList').addEventListener('click', e => {
    const say = e.target.closest('[data-say]');
    if (say) { handle(say.dataset.say); return; }
    const f = e.target.closest('[data-flow]');
    if (f) {
      const [kind, a, b] = f.dataset.flow.split(':');
      f.closest('.qchips')?.querySelectorAll('button').forEach(x => { x.disabled = true; x.classList.toggle('picked', x === f); });
      post({ who: 'me', text: f.textContent.trim() });
      if (kind === 'guide') startGuideFlow(a);
      if (kind === 'lost') lostWhere(a, b);
      return;
    }
    const o = e.target.closest('[data-offers]');
    if (o) { ctx.openOffers(o.dataset.offers); return; }
    if (e.target.closest('[data-near]')) { ctx.enterResults({ cat: 'all' }); return; }
    const c = e.target.closest('[data-copy]');
    if (c) { navigator.clipboard?.writeText(c.dataset.copy).then(() => toast('Number copied.'), () => toast('Select the number to copy it.')); return; }
    if (e.target.closest('[data-official]')) { toast('Opens RTA’s official lost-and-found page. Dubai-io doesn’t file anything.'); }
  });
  $('#chatList').addEventListener('submit', e => {
    const form = e.target.closest('[data-desc]'); if (!form) return;
    e.preventDefault();
    const msg = form.closest('.msg');
    const idx = [...$('#chatList').children].indexOf(msg);
    const it = items[idx];
    it?.after?.(form);
  });
}
