import { labFetch } from './api-client.js';
import { openServiceRequest } from './service-workflow.js';
// io chat. A lab stand-in for Luna: a deterministic intent router (clearly
// labelled "lab router") until the LangGraph service in apps/api replaces it.
// Intents: lost item -> recovery, airport -> guide, service -> competing offers,
// place -> map, greeting, otherwise a clarifying question. Never invents a
// status: reports are "prepared, not filed"; items stay "not recovered".
import { $, svg, esc, toast, told, wait } from './ui.js';
import { CATEGORIES } from './data.js';
import { SERVICE_GROUPS, matchService } from './offers.js';
import { createLunaClient } from './luna-client.js';
import { identity, getMessages, saveMessages, resetSession } from './session-state.js';
import { initRecovery, startRecovery, resetRecovery, handleRecoveryClick, restoreReport } from './recovery.js';

let ctx = null; // { enterResults, openOffers, startGuide, showChat }
const items = [];
let seq = 0, threadEpoch = 0;
// Luna runs wherever the API answers with a configured model key; one probe, re-tried after a failure.
let health=null, healthAt=0;
const lunaReady=()=>{if(!health||(health.failed&&Date.now()-healthAt>30000)){healthAt=Date.now();health=fetch('/api/health',{signal:AbortSignal.timeout(3000)}).then(r=>r.ok?r.json():null).then(h=>!!h?.openai_key).catch(()=>false);health.then(ok=>{health.failed=!ok;});}return health;};
const luna = createLunaClient({fetcher:labFetch,enabled:lunaReady,identity});

export function initChat(c) {
  ctx = c; initRecovery({ say: botSay, post, update, near: () => ctx.enterResults({ cat: 'all' }) });
  for(const saved of getMessages()) {
    if(!['me','bot'].includes(saved?.who)||typeof saved.text!=='string')continue;
    items.push({id:++seq,who:saved.who,text:saved.text.slice(0,6000),r:saved.who==='me'?saved.r:null,html:saved.who==='bot'?'<p>'+esc(saved.text.slice(0,6000))+'</p>':null,recoveryReport:saved.recoveryReport});
  }
  render();
}
export function resetChat() { threadEpoch++; luna.reset(); resetSession(); for(const key of Object.keys(told))delete told[key]; items.length = 0; resetRecovery(); render(); }

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
    const where = /\b(taxi|cab)\b/.test(q) ? 'taxi' : /\bmetro\b/.test(q) ? 'metro' : /\b(shop|mall)\b/.test(q) ? 'shop' : null;
    return { intent: 'lost_item', item: m ? m[1].replace(/s$/, '') : 'item', where, conf: m ? 0.92 : 0.7 };
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
  const ep = threadEpoch, typing = post({ who: 'bot', typing: true });
  await wait(520);
  if (ep !== threadEpoch) return null;
  const it = items.find(i => i.id === typing);
  if (!it) return null;
  Object.assign(it, { typing: false, html, ...extra });
  render();
  return typing;
}

const fmtT = d => d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

function render() {
  const list = $('#chatList'); if (!list) return;
  saveMessages(items.filter(it=>!it.typing).map(it=>{
    const box=document.createElement('div');box.innerHTML=it.html||'';
    const text=it.who==='me'?it.text:it.type==='status'?'Demo order timeline paused after refresh. '+it.provider.name+' · AED '+it.total+' (demo)':box.textContent;
    return {who:it.who==='me'?'me':'bot',text,r:it.r||null,recoveryReport:it.recoveryReport||null};
  }));
  list.innerHTML = items.map(it => {
    if (it.who === 'me') return `<div class="msg me"><p>${esc(it.text)}</p>${it.pending ? '<span class="luna">Luna is understanding your request…</span>' : ''}${it.r ? `<span class="luna">${svg('orb', 'ic xs')} ${esc(it.r.via === 'langgraph' ? 'LangGraph · ' + it.r.model : 'Lab router')} · ${esc(it.r.intent)}${it.r.item ? ` · item: ${esc(it.r.item)}` : ''}${it.r.service ? ` · ${esc(it.r.service)}` : ''}${it.r.cat ? ` · ${esc(it.r.cat)}${it.r.sub ? ' › ' + esc(it.r.sub) : ''}` : ''} · ${Math.round(it.r.conf * 100)}%${it.r.ms != null ? ' · ' + (it.r.ms/1000).toFixed(1) + ' s' : ''}${it.r.fallback_reason ? ' · ' + esc(it.r.fallback_reason) : ''}</span>` : ''}</div>`;
    if (it.typing) return `<div class="msg bot typing"><span class="orbdot"></span><span class="orbdot"></span><span class="orbdot"></span></div>`;
    if (it.type === 'status') return statusHTML(it);
    return `<div class="msg bot ${it.wide ? 'wide' : ''}">${it.html}${it.recoveryReport ? `<button class="btn sm" data-restored-report="${it.id}">Review saved report</button>` : ''}</div>`;
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
  text=String(text).trim();if(!text)return;
  if(text.length>600){toast('Keep this message under 600 characters.');return;}
  const ep=threadEpoch, id=post({who:'me',text,pending:true});ctx.showChat();
  const r=await luna.understand(text,route);
  if(!r||ep!==threadEpoch)return;
  update(id,it=>{it.pending=false;it.r=r;});
  const factKeys={area:'area',hotel:'hotel',terminal:'terminal',taxi_plate:'plate',taxi_roof:'roof',deadline:'deadline',pet:'pet',language:'language',other:'other'};
  for(const fact of r.remembered||[])if(factKeys[fact.key])told[factKeys[fact.key]]=fact.value.slice(0,80);
  if(r.remembered?.length)await botSay('<p class="told">You told me: '+r.remembered.map(f=>esc(f.key.replaceAll('_',' '))+': '+esc(f.value)).join(' · ')+'</p>');
  if(ep!==threadEpoch)return;
  switch (r.intent) {
    case 'lost_item': return startRecovery({ item: r.item, where: r.where });
    case 'airport_guide': return r.terminal ? startGuideFlow(r.terminal) : airport();
    case 'service_offers': return offers(r.service,text);
    case 'places_near': {
      await botSay(`<p>Here’s what’s near you, closest first. Opening the map.</p>`);
      await wait(500);
      if(ep!==threadEpoch)return;
      return ctx.enterResults({ ask: text, cat: r.cat, sub: r.sub });
    }
    case 'greeting': return botSay(`<p>Hi! Ask me for a service, a place nearby or help at the airport, or tell me if you’ve lost something.</p>${chips(['Guide me through the airport', 'Home cleaning prices', 'Coffee near me', 'I lost my wallet'])}`);
    case 'smalltalk': return botSay('<p>'+esc(r.reply||'How can I help?')+'</p>');
    case 'thanks': return botSay(`<p>Anytime.</p>`);
    default: return botSay(`<p>${esc(r.clarify || 'I’m not sure I got that. Which of these is closest?')}</p>${chips(['Find a place near me', 'Compare a service', 'I lost something', 'Help at the airport'])}<p class="hint">I’d rather ask than guess.</p>`);
  }
}
const chips = list => `<div class="qchips">${list.map(t => `<button data-say="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;

// ---------------------------------------------------------------- flows
async function offers(id,request) {
  const g = SERVICE_GROUPS.find(x => x.id === id);
  const top = [...g.providers].sort((a, b) => a.from - b.from).slice(0, 3);
  await botSay(`<p>${g.providers.length} providers compete for <b>${esc(g.label.toLowerCase())}</b>. Cheapest first; every offer is the provider’s own published one.</p>
    <div class="mini-rows">${top.map(p => `<div class="mr"><span class="logo" style="background:${p.color}">${esc(p.logo)}</span><span class="mr-t"><b>${esc(p.name)}</b><em>from AED ${p.from.toLocaleString('en-US')} ${esc(p.unit)} (demo) · ${esc(p.eta)} (demo)</em></span>${p.offer ? `<span class="mr-o">${svg('tag', 'ic xs')}</span>` : ''}</div>`).join('')}</div>
    <button class="btn primary sm" data-service-request="${g.id}" data-request-text="${esc(request||'')}">Plan this request</button>
    <button class="btn sm" data-offers="${g.id}">See all ${g.providers.length} offers ${svg('chev', 'ic xs')}</button>`);
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

// ---------------------------------------------------------------- clicks inside the thread
export function wireChat() {
  $('#sheetBody').addEventListener('click', handleRecoveryClick);
  $('#chatList').addEventListener('click', e => {
    if (handleRecoveryClick(e)) return;
    const saved=e.target.closest('[data-restored-report]');if(saved){const it=items.find(i=>i.id===Number(saved.dataset.restoredReport));if(it?.recoveryReport)restoreReport(it.recoveryReport);return;}
    const say = e.target.closest('[data-say]');
    if (say) { handle(say.dataset.say); return; }
    const f = e.target.closest('[data-flow]');
    if (f) {
      const [kind, a, b] = f.dataset.flow.split(':');
      f.closest('.qchips')?.querySelectorAll('button').forEach(x => { x.disabled = true; x.classList.toggle('picked', x === f); });
      post({ who: 'me', text: f.textContent.trim() });
      if (kind === 'guide') startGuideFlow(a);
      return;
    }
    const plan=e.target.closest('[data-service-request]');if(plan){openServiceRequest(plan.dataset.serviceRequest,{request:plan.dataset.requestText});return;}
    const o = e.target.closest('[data-offers]');
    if (o) { ctx.openOffers(o.dataset.offers); return; }
    if (e.target.closest('[data-near]')) { ctx.enterResults({ cat: 'all' }); return; }
    const c = e.target.closest('[data-copy]');
    if (c) { navigator.clipboard?.writeText(c.dataset.copy).then(() => toast('Number copied.'), () => toast('Select the number to copy it.')); return; }
    if (e.target.closest('[data-official]')) { toast('Opens RTA’s official lost-and-found page. Dubai-io doesn’t file anything.'); }
  });
}
