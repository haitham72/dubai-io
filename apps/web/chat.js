import { labFetch } from './api-client.js';
import { requestContext, selectFocus, selectTaskFocus } from './assistant-context.js';
import { openServiceRequest } from './service-workflow.js';
// io chat. A lab stand-in for Luna: a deterministic intent router (clearly
// labelled "lab router") until the LangGraph service in apps/api replaces it.
// Intents: lost item -> recovery, airport -> guide, service -> competing offers,
// place -> map, greeting, otherwise a clarifying question. Never invents a
// status: reports are "prepared, not filed"; items stay "not recovered".
import { $, svg, esc, toast, told, wait } from './ui.js';
import { CATEGORIES } from './data.js';
import { SERVICE_GROUPS, matchService, byNear, openProvider } from './offers.js';
import { createLunaClient } from './luna-client.js';
import { orderCardHTML, watchOrder, requestEarlier, remindWhenReady } from './orders.js';
import { api } from './service-workflow.js';
import { identity, getMessages, saveMessages, resetSession } from './session-state.js';
import { initRecovery, startRecovery, resetRecovery, handleRecoveryClick, restoreReport } from './recovery.js';
import { taskStateLabel } from './tasks.js';

let ctx = null; // { enterResults, openOffers, startGuide, showChat }
const items = [];
let seq = 0, threadEpoch = 0;
// Luna runs wherever the API answers with a configured model key; one probe, re-tried after a failure.
let health=null, healthAt=0;
const lunaReady=()=>{if(!health||(health.failed&&Date.now()-healthAt>30000)){healthAt=Date.now();health=fetch('/api/health',{signal:AbortSignal.timeout(3000)}).then(r=>r.ok?r.json():null).then(h=>!!h?.openai_key).catch(()=>false);health.then(ok=>{health.failed=!ok;});}return health;};
const luna = createLunaClient({fetcher:labFetch,enabled:lunaReady,identity,context:requestContext});

export function initChat(c) {
  ctx = c; initRecovery({ say: botSay, post, update, near: () => ctx.enterResults({ cat: 'all' }) });
  for(const saved of getMessages()) {
    if(!['me','bot'].includes(saved?.who)||typeof saved.text!=='string')continue;
    if(saved.who==='bot'&&typeof saved.msgId==='string'){items.push({id:++seq,who:'bot',msgId:saved.msgId,msgSource:saved.msgSource,text:saved.text,html:proactiveHTML(saved.msgSource,saved.text.slice(0,600))});continue;}
    if(saved.who==='bot'&&saved.rich&&typeof saved.rich.kind==='string'){const html=richHTML(saved.rich);if(html){items.push({id:++seq,who:'bot',wide:true,rich:saved.rich,text:saved.text,html});continue;}}
    if(saved.who==='bot'&&typeof saved.actionId==='string'){const id=++seq;items.push({id,who:'bot',type:'order',actionId:saved.actionId,action:null,text:saved.text});follow(id,saved.actionId);continue;}
    items.push({id:++seq,who:saved.who,text:saved.text.slice(0,6000),r:saved.who==='me'?saved.r:null,html:saved.who==='bot'?saved.text.slice(0,6000).split(/\n+/).filter(Boolean).map(line=>'<p>'+esc(line)+'</p>').join(''):null,recoveryReport:saved.recoveryReport,taskId:typeof saved.taskId==='string'?saved.taskId:null});
  }
  render();
  followMessages();
}
export function resetChat() { selectFocus(null); threadEpoch++; for(const stop of watchers.values())stop(); watchers.clear(); luna.reset(); resetSession(); for(const key of Object.keys(told))delete told[key]; items.length = 0; resetRecovery(); render(); }

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
  if (/\b(my order|order status|is (it|my \w+) ready|ready yet|has the (shop|laundry|merchant))\b/.test(q)) return { intent: 'order_status', conf: 0.9 };
  if (THANKS.test(q)) return { intent: 'thanks', conf: 0.95 };
  return { intent: 'unclear', conf: 0.3 };
}

// ---------------------------------------------------------------- thread
export function post(it) { it.id = ++seq; items.push(it); render(); return it.id; }
export function update(id, fn) { const it = items.find(i => i.id === id); if (it) { fn(it); render(); } }
export const hasThread = () => items.length > 0;

// Orders render from the server record and follow its change stream across reloads.
const watchers = new Map();
function follow(itemId, actionId) {
  watchers.get(itemId)?.();
  api('/api/actions/' + encodeURIComponent(actionId)).then(a => update(itemId, it => { it.action = a; })).catch(() => update(itemId, it => { it.missing = true; }));
  watchers.set(itemId, watchOrder(actionId, a => update(itemId, it => { it.action = a; })));
}
const proactiveHTML = (source, text) => `<p><span class="upd-pill">${svg(source === 'demo' ? 'spark' : 'clock', 'ic xs')} ${source === 'demo' ? 'Demo trigger' : 'Reminder you asked for'}</span></p><p>${esc(text)}</p>`;
// Proactive messages: delivered by the server outbox (deduped, consented, quiet hours), shown once each.
let messageStream = null;
function followMessages() {
  if (messageStream) return;
  const show = list => { for (const m of list || []) if (!items.some(it => it.msgId === m.id)) post({ who: 'bot', msgId: m.id, msgSource: m.trigger_source, text: m.text, html: proactiveHTML(m.trigger_source, m.text) }); };
  const start = () => { try { messageStream = new EventSource('/api/messages/stream'); messageStream.onmessage = e => { try { show(JSON.parse(e.data)); } catch { /* ignore */ } }; messageStream.onerror = () => { messageStream.close(); setTimeout(() => { messageStream = null; followMessages(); }, 5000); }; } catch { /* no SSE */ } };
  api('/api/session').then(start).catch(() => setTimeout(followMessages, 10000));
}
export function trackOrder(action) { const id = post({ who: 'bot', type: 'order', actionId: action.id, action }); follow(id, action.id); return id; }

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
  const empty = $('#chatEmpty'); if (empty) empty.hidden = items.length > 0;
  saveMessages(items.filter(it=>!it.typing).map(it=>{
    const box=document.createElement('div');box.innerHTML=it.html||'';
    // Preserve block boundaries in the plain-text history; concatenated card
    // labels must not turn into unreadable words after reload. No HTML is saved.
    for(const block of box.querySelectorAll('p,div,li,h1,h2,h3,h4,dt,dd,small')){block.prepend('\n');block.append('\n');}
    const text=it.who==='me'?it.text:it.type==='order'?'Order '+(it.action?.recipient||''):box.textContent.replace(/\n{3,}/g,'\n\n').trim();
    return {who:it.who==='me'?'me':'bot',text,r:it.r||null,recoveryReport:it.recoveryReport||null,...(it.taskId?{taskId:it.taskId}:{}),...(it.type==='order'?{actionId:it.actionId}:{}),...(it.msgId?{msgId:it.msgId,msgSource:it.msgSource,text:it.text}:{}),...(it.rich?{rich:it.rich}:{})};
  }));
  list.innerHTML = items.map(it => {
    if (it.who === 'me') return `<div class="msg me"><p>${esc(it.text)}</p></div>${it.pending ? `<div class="understood pending">${svg('spark', 'ic xs')}<span>Luna is understanding…</span></div>` : ''}${it.r ? understoodHTML(it) : ''}`;
    if (it.typing) return `<div class="msg bot typing"><span class="orbdot"></span><span class="orbdot"></span><span class="orbdot"></span></div>`;
    if (it.type === 'order') return it.missing ? `<div class="msg bot"><p>This order is no longer available on this device.</p></div>` : orderCardHTML(it.action);
    return `<div class="msg bot ${it.wide ? 'wide' : ''} ${it.rich ? 'rich' : ''}">${it.html}${it.taskId ? `<button class="btn sm" data-chat-task="${esc(it.taskId)}">Open task</button>` : ''}${it.recoveryReport ? `<button class="btn sm" data-restored-report="${it.id}">Review saved report</button>` : ''}</div>`;
  }).join('');
  requestAnimationFrame(() => { const s = $('#chatScroll'); if (s) s.scrollTop = s.scrollHeight; });
}

// ---------------------------------------------------------------- entry
export async function handle(text) {
  text=String(text).trim();if(!text)return;
  if(text.length>600){toast('Keep this message under 600 characters.');return;}
  const ep=threadEpoch, id=post({who:'me',text,pending:true});ctx.showChat();
  const taskFocus=requestContext().task_focus;
  const r=await luna.understand(text,taskFocus?()=>({intent:'task_help',conf:1}):route);
  if(!r||ep!==threadEpoch)return;
  update(id,it=>{it.pending=false;it.r=r;});
  const factKeys={area:'area',hotel:'hotel',terminal:'terminal',taxi_plate:'plate',taxi_roof:'roof',deadline:'deadline',pet:'pet',language:'language',other:'other'};
  // Show only facts that are new or changed this turn; known ones are already in "You told me".
  const fresh=(r.remembered||[]).filter(f=>factKeys[f.key]&&told[factKeys[f.key]]!==f.value.slice(0,80));
  for(const fact of fresh)told[factKeys[fact.key]]=fact.value.slice(0,80);
  if(fresh.length)await botSay('<p class="told">You told me: '+fresh.map(f=>esc(f.key.replaceAll('_',' '))+': '+esc(f.value)).join(' · ')+'</p>');
  if(ep!==threadEpoch)return;
  switch (r.intent) {
    case 'lost_item': return startRecovery({ item: r.item, where: r.where });
    case 'airport_guide': return r.terminal ? startGuideFlow(r.terminal) : airport();
    case 'service_offers': return offers(r.service);
    case 'places_near': {
      await botSay(`<p>Here’s what’s near you, closest first. Opening the map.</p>`);
      await wait(500);
      if(ep!==threadEpoch)return;
      return ctx.enterResults({ ask: text, cat: r.cat, sub: r.sub });
    }
    case 'greeting': return botSay(`<p>Hi! I can help with a service, a place nearby or your saved tasks.</p>${chips(['Home cleaning prices', 'Coffee near me', 'I lost my wallet'])}<button class="btn sm" data-chat-task-list>View my tasks</button>`);
    case 'order_status': return orderStatus();
    case 'task_help': return taskHelp(taskFocus,r.reply);
    case 'info_question': case 'market_quote': { const rich = { kind: 'answer', r: { answer: r.answer, reply: r.reply, sources: r.sources, tool: r.tool } }; return botSay(richHTML(rich), { rich }); }
    case 'product_search': { const rich = { kind: 'products', r: { answer: r.answer, products: r.products } }; return botSay(richHTML(rich), { wide: true, rich }); }
    case 'smalltalk': return botSay('<p>'+esc(r.reply||'How can I help?')+'</p>');
    case 'thanks': return botSay(`<p>Anytime.</p>`);
    default: return botSay(`<p>${esc(r.clarify || 'I’m not sure I got that. Which of these is closest?')}</p>${chips(['Find a place near me', 'Compare a service', 'I lost something', 'Help at the airport'])}<p class="hint">I’d rather ask than guess.</p>`);
  }
}
const chips = list => `<div class="qchips">${list.map(t => `<button data-say="${esc(t)}">${esc(t)}</button>`).join('')}</div>`;

async function taskHelp(reference, reply) {
  if(!reference)return botSay('<p>Open a saved task and choose Discuss this task to give me its context.</p><button class="btn sm" data-chat-task-list>View my tasks</button>');
  try {
    const {task}=await api('/api/tasks/'+encodeURIComponent(reference.task_id));
    if(requestContext().task_focus?.task_id===task.id)selectTaskFocus(task);
    if(task.revision!==reference.revision)reply='The task changed. Here are its latest saved details.';
    const at=new Date(task.as_of).toLocaleString('en-GB',{timeZone:'Asia/Dubai',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
    return botSay(`${reply?'<p>'+esc(reply)+'</p>':''}<div class="task-next"><span>${esc(task.outcome)}</span><p>${esc(taskStateLabel(task.status))}</p>${task.next_step?'<p>Next step: '+esc(task.next_step)+'</p>':''}<small>Saved task · ${esc(at)} Dubai time. Review its details to make a change; this conversation has not sent or changed anything.</small></div>`,{taskId:task.id});
  } catch {return botSay('<p>The saved task could not be loaded. Reopen its latest details or clear the task context and try again.</p>');}
}

// ---------------------------------------------------------------- flows
async function offers(id) {
  const rich = { kind: 'offers', id };
  return botSay(richHTML(rich), { wide: true, rich });
}

// Rows card (reference 02-rows): closest first, each row opens its own mini-app.
function offersCardHTML(id) {
  const g = SERVICE_GROUPS.find(x => x.id === id); if (!g) return '';
  const rows = [...g.providers].sort(byNear).slice(0, 3).map(p => `<div class="rc-row">
      <span class="logo lg" style="background:${p.color}">${esc(p.logo)}</span>
      <div class="rc-t"><b>${esc(p.name)}</b><span class="rc-tag">${p.entry ? 'Mini-app' : p.source === 'website' ? 'Website' : 'Marketplace'}</span>
        <span class="rc-meta">AED ${p.from.toLocaleString('en-US')} ${esc(p.unit)} · ${esc(p.eta)}</span><span class="rc-sub">${p.km} km · ★ ${p.rating.toFixed(1)} · demo</span></div>
      ${p.entry ? `<button class="open-btn" data-open-provider="${g.id}|${p.id}">Open ${svg('chev', 'ic xs')}</button>` : ''}</div>`).join('');
  return `<p>${g.providers.length} providers for <b>${esc(g.label.toLowerCase())}</b>, closest first. Prices are each provider’s own published list.</p>
    <div class="rows-card"><div class="rc-head"><span class="rc-ic">${svg(g.glyph, 'ic sm')}</span><div><b>${esc(g.label)}</b><span>Fixed published prices · no bidding</span></div><span class="pill demo">Sandbox partners</span></div>
    ${rows}<p class="rc-foot">${svg('shield', 'ic xs')} Nothing is shared until you approve.</p></div>
    <button class="btn sm" data-offers="${g.id}">See all ${g.providers.length} offers ${svg('chev', 'ic xs')}</button>`;
}

function richHTML(rich) {
  if (rich.kind === 'offers') return offersCardHTML(rich.id);
  if (rich.kind === 'products') return productsHTML(rich.r || {});
  if (rich.kind === 'answer') return answerHTML(rich.r || {});
  return '';
}

const INTENT_LABEL = { lost_item: 'Lost item', airport_guide: 'Airport guide', service_offers: 'Service', places_near: 'Places near you', order_status: 'Order status', task_help: 'Your saved task', info_question: 'Question',
  market_quote: 'Market quote', product_search: 'Shopping', greeting: 'Greeting', smalltalk: 'Chat', thanks: 'Thanks', unclear: 'Not sure yet' };
// "Luna understood: Service · Laundry" (reference 02-rows); tap for the technical line.
function understoodHTML(it) {
  const r = it.r;
  const svc = r.service && SERVICE_GROUPS.find(g => g.id === r.service)?.label;
  const parts = [INTENT_LABEL[r.intent] || r.intent, r.item, svc, r.cat && (r.sub ? r.cat + ' › ' + r.sub : r.cat), r.terminal && 'Terminal ' + r.terminal].filter(Boolean);
  const tech = `${r.via === 'langgraph' ? 'LangGraph · ' + r.model : 'Offline router'} · ${Math.round(r.conf * 100)}%${r.ms != null ? ' · ' + (r.ms / 1000).toFixed(1) + ' s' : ''}${r.fallback_reason ? ' · ' + r.fallback_reason : ''}`;
  return `<button class="understood" data-tech="${it.id}" aria-expanded="${!!it.tech}">${svg('spark', 'ic xs')}<span><em>Luna understood:</em> ${esc(parts.join(' · '))}</span>${svg('chev', 'ic xs')}</button>${it.tech ? `<p class="understood-tech">${esc(tech)}</p>` : ''}`;
}

// Research answers: written only from the listed sources (web search or market data), shown with them.
function answerHTML(r) {
  const at = r.sources?.[0]?.as_of ? new Date(r.sources[0].as_of).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
  const list = (r.sources || []).map(s => `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${s.n ? `[${s.n}] ` : ''}${esc(s.title || s.url)}</a> <span>${esc(s.via)}</span></li>`).join('');
  return `<p>${esc(r.answer || r.reply || 'I couldn’t find that.')}</p>${list ? `<ol class="sources">${list}</ol><p class="hint">${r.tool === 'finnhub' ? 'Market data' : 'Web sources'}${at ? ', checked ' + at : ''}. Sources can be wrong; open them to confirm.</p>` : ''}`;
}

// Product search: live Amazon.ae listings (links, prices, thumbnails). Nothing is bought; a card opens Amazon.
function productsHTML(r) {
  const list = r.products || [];
  if (!list.length) return `<p>${esc(r.answer || 'No products found.')}</p>`;
  const at = list[0].as_of ? new Date(list[0].as_of).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '';
  const card = p => `<a class="prod" href="${esc(p.link)}" target="_blank" rel="noopener noreferrer">
      <span class="prod-img">${p.thumbnail ? `<img src="${esc(p.thumbnail)}" alt="" loading="lazy" referrerpolicy="no-referrer">` : ''}</span>
      <span class="prod-t">${esc(p.title)}</span>
      <span class="prod-m">${p.price ? `<b>${esc(p.price)}</b>` : 'See price'}${p.rating ? ` · ★ ${p.rating}${p.reviews ? ` (${p.reviews.toLocaleString('en-US')})` : ''}` : ''}</span></a>`;
  return `<p>${esc(r.answer)}</p><div class="prod-grid">${list.map(card).join('')}</div>
    <p class="hint">Live from Amazon.ae via SerpAPI${at ? ', ' + at : ''}. Prices may change; nothing is bought here.</p>`;
}

// Status questions are answered from the server's order record, never from model text (rule 1).
async function orderStatus() {
  let orders = [];
  try { orders = (await api('/api/actions')).actions.filter(a => a.capability_id === 'order.request' && a.status !== 'DRAFT' && a.status !== 'AWAITING_APPROVAL'); } catch { /* offline */ }
  if (!orders.length) return botSay('<p>I don’t see an order you’ve sent from this device yet.</p>');
  const latest = orders.sort((a, b) => (b.events.at(-1)?.at || '').localeCompare(a.events.at(-1)?.at || ''))[0];
  await botSay('<p>Here is the latest from the shop’s own updates:</p>');
  trackOrder(latest);
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
      const mem = [told.belt && `belt ${esc(told.belt)}`, told.area && `going to ${esc(told.area)}`, told.plate && `taxi ${esc(told.plate)}${told.roof ? ` (${esc(told.roof)} roof)` : ''}`].filter(Boolean);
      await botSay(`<p>${res.mode === 'Metro' ? 'Enjoy the ride. Keep your Nol card handy.' : res.mode === 'Taxi' ? `Safe ride${told.area ? ' to ' + esc(told.area) : ''}.` : 'You’re through arrivals.'}</p>
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
    const tech = e.target.closest('[data-tech]');
    if (tech) { const it = items.find(i => i.id === Number(tech.dataset.tech)); if (it) { it.tech = !it.tech; render(); } return; }
    const op = e.target.closest('[data-open-provider]');
    if (op) { const [g, pid] = op.dataset.openProvider.split('|'); openProvider(g, pid); return; }
    const rem = e.target.closest('[data-remind]');
    if (rem) { rem.disabled = true; remindWhenReady(rem.dataset.remind).then(() => render()).catch(err => { toast(err.message); rem.disabled = false; }); return; }
    const early = e.target.closest('[data-earlier]');
    if (early) { early.disabled = true; requestEarlier(early.dataset.earlier, early.dataset.target).catch(err => { toast(err.message); early.disabled = false; }); return; }
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
