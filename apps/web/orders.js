// Fixed-price orders through the server action engine. The mini-app can only
// ask; the server rebuilds items and total from its catalog, the user approves
// the exact snapshot once, and every later status comes from a merchant tap
// delivered over /api/actions/{id}/stream. Nothing here simulates a merchant.
import { $, svg, esc, toast, told, openSheet, closeSheet } from './ui.js';
import { api } from './service-workflow.js';
import { statusLabel } from './status-labels.js';

const DAY_RE = /\btoday\b/i;
// "by 9 tomorrow" -> "Tomorrow 09:00"; returns '' when no time is stated.
export function parseDeadline(text) {
  const m = String(text || '').match(/\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b/i);
  if (!m) return '';
  let h = Number(m[1]); const min = m[2] || '00';
  if (m[3]?.toLowerCase() === 'pm' && h < 12) h += 12;
  if (m[3]?.toLowerCase() === 'am' && h === 12) h = 0;
  if (h > 23 || Number(min) > 59) return '';
  return `${DAY_RE.test(text) ? 'Today' : 'Tomorrow'} ${String(h).padStart(2, '0')}:${min}`;
}

const STEP = { SUBMITTED: 'Sent to the merchant inbox', ACCEPTED: 'Merchant accepted at the fixed price', READY: 'Merchant marked it ready', COMPLETED: 'Merchant marked it done', DECLINED: 'Merchant declined' };
const fmt = iso => new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const money = v => 'AED ' + Number(v).toLocaleString('en-US');

// ---------------------------------------------------------------- review + approve
let review = null; // { p, order, draft, seq }
export function reviewOrder(p, payload, onSent) {
  const items = (payload.items || []).slice(0, 20).map(x => ({ id: typeof x.id === 'string' ? x.id : undefined, name: typeof x.name === 'string' ? x.name : undefined, qty: Math.max(1, Math.min(20, x.qty | 0)) }));
  const slot = typeof payload.slot === 'string' ? payload.slot : (String(payload.summary || '').split(' · ')[1] || null);
  review = { p, order: { provider_id: p.id, items, slot }, draft: null, seq: 0, onSent };
  const deadline = parseDeadline(told.deadline);
  const [day, time] = deadline ? deadline.split(' ') : ['Tomorrow', ''];
  openSheet(`
    <h3 id="sheetTitle">Send to ${esc(p.name)}?</h3>
    <form id="ordForm" class="ord-form">
      <label>Area <input id="ordArea" maxlength="80" value="${esc(told.area || '')}" placeholder="e.g. Dubai Marina"></label>
      <label>Needed by <span class="ord-when"><select id="ordDay"><option${day === 'Today' ? ' selected' : ''}>Today</option><option${day === 'Tomorrow' ? ' selected' : ''}>Tomorrow</option></select><input id="ordTime" type="time" value="${esc(time)}"></span></label>
    </form>
    <div id="ordReview" aria-live="polite"><p class="fine">Checking the merchant’s published prices…</p></div>`, () => { review = null; });
  $('#ordForm').addEventListener('change', prepare);
  prepare();
}

function fields() {
  const f = { area: { value: $('#ordArea').value.trim() } };
  const t = $('#ordTime').value;
  if (t) f.deadline = { value: `${$('#ordDay').value} ${t}` };
  return f;
}

async function prepare() {
  const r = review; if (!r) return;
  const n = ++r.seq;
  try {
    const draft = await api('/api/actions/prepare', { method: 'POST', body: JSON.stringify({ capability_id: 'order.request', draft_id: r.draft?.id || null, fields: fields(), order: r.order }) });
    if (review !== r || n !== r.seq) return;
    r.draft = draft; renderReview(draft);
  } catch (err) { if (review === r) $('#ordReview').innerHTML = `<p class="empty">${esc(err.message)}. Nothing was sent.</p>`; }
}

function renderReview(a) {
  const o = a.order, f = a.fields;
  const shared = [`${o.lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')} · total`, o.slot && `pickup ${esc(o.slot)}`,
    f.area && `area: ${esc(f.area.value)} (you told me)`, f.deadline && `needed by ${esc(f.deadline.value)} (you told me)`].filter(Boolean).join(' · ');
  $('#ordReview').innerHTML = `
    <div class="ap-total"><span>Total at ${esc(a.recipient.replace(' (sandbox merchant)', ''))}’s published prices</span><b>${money(a.fixed_total_aed)}</b></div>
    <div class="ap-box"><span class="ap-ic">${svg('arrow', 'ic sm')}</span><div><h5>Will be shared</h5><p>${shared}</p></div></div>
    <div class="ap-box"><span class="ap-ic">${svg('lock', 'ic sm')}</span><div><h5>Never shared</h5><p>Your name · phone number · profile and anything I noticed · other orders</p></div></div>
    ${a.status === 'DRAFT' ? `<p class="hint">Add ${a.missing.map(esc).join(', ')} to continue.</p>` : ''}
    <p class="ap-info">${svg('shield', 'ic xs')} Nothing is sent until you tap. The shop accepts or declines; the price can’t change.</p>
    <div class="ap-actions"><button class="btn primary" id="ordYes" ${a.status === 'AWAITING_APPROVAL' ? '' : 'disabled'}>Approve and send</button><button class="btn" id="ordNo">Cancel</button></div>
    <p class="fine">Prices from the shop’s published list (${esc(o.provenance.replace('_', ' '))}, as of ${esc(o.as_of)}), not from the mini-app. Sandbox merchant.</p>`;
  $('#ordNo').addEventListener('click', () => { closeSheet(); toast('Nothing was sent.'); });
  $('#ordYes').addEventListener('click', approve);
}

async function approve(e) {
  const r = review; if (!r?.draft) return;
  e.target.disabled = true;
  r.key ||= crypto.randomUUID();
  try {
    const sent = await api(`/api/actions/${encodeURIComponent(r.draft.id)}/approve`, { method: 'POST', headers: { 'Idempotency-Key': r.key }, body: JSON.stringify({ snapshot_hash: r.draft.snapshot_hash, revision: r.draft.revision }) });
    closeSheet();
    r.onSent(sent);
  } catch (err) { toast(err.message); if (e.target.isConnected) e.target.disabled = false; }
}

// ---------------------------------------------------------------- live status
// EventSource first; a 1.5 s poll takes over if the stream breaks.
export function watchOrder(id, onUpdate) {
  let poll = 0, closed = false;
  let previous = null;
  const receive = action => { if (closed) return; onUpdate(action); const version = JSON.stringify([action.status, action.revision, action.ready_at, action.earlier_request]); if (previous !== version) { previous = version; dispatchEvent(new CustomEvent('dubaiio:source-changed', { detail: { id } })); } };
  const fallback = () => { if (poll || closed) return; poll = setInterval(() => api('/api/actions/' + encodeURIComponent(id)).then(receive).catch(() => {}), 1500); };
  let es = null;
  try { es = new EventSource('/api/actions/' + encodeURIComponent(id) + '/stream'); } catch { fallback(); }
  if (es) {
    es.onmessage = m => { try { receive(JSON.parse(m.data)); } catch { /* ignore a malformed frame */ } };
    es.addEventListener('gone', () => es.close());
    es.onerror = () => { es.close(); fallback(); };
  }
  return () => { closed = true; es?.close(); clearInterval(poll); };
}

// Per-browser memory of reminders already set (the server dedupes regardless).
const REMINDED = 'dubaiio.reminded';
const reminded = () => { try { return JSON.parse(localStorage.getItem(REMINDED) || '{}'); } catch { return {}; } };
export async function remindWhenReady(id) {
  const r = await api('/api/reminders', { method: 'POST', body: JSON.stringify({ action_id: id }) });
  try { localStorage.setItem(REMINDED, JSON.stringify({ ...reminded(), [id]: r.scheduled_for })); } catch { /* private mode */ }
  return r;
}

export async function requestEarlier(id, target) {
  return api(`/api/actions/${encodeURIComponent(id)}/request-earlier`, { method: 'POST', body: JSON.stringify({ target }) });
}

// "Tomorrow 09:00" -> "Tomorrow 08:30": 30 minutes of slack before the deadline.
export function earlierThan(deadline) {
  const [day, hm] = String(deadline).split(' ');
  let [h, m] = hm.split(':').map(Number); m -= 30; if (m < 0) { m += 60; h -= 1; }
  return h < 0 ? null : `${day} ${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

export function orderCardHTML(a) {
  if (!a) return `<div class="msg bot"><p>Loading your order…</p></div>`;
  const o = a.order || { lines: [], provider: a.recipient };
  const steps = a.events.flatMap(e => e.kind === 'adapter_result' && e.status === 'SUBMITTED' ? [{ at: e.at, label: STEP.SUBMITTED, code: 'SUBMITTED' }]
    : e.kind === 'status' ? [{ at: e.at, label: STEP[e.to] + (e.ready_at ? ` · ready ${e.ready_at}` : '') + (e.reason ? ` · ${e.reason}` : ''), code: e.to }]
    : e.kind === 'earlier_requested' ? [{ at: e.at, label: `You asked for ${e.target}, same price`, code: 'REQUEST' }]
    : e.kind === 'ready_time' ? [{ at: e.at, label: `Merchant set ready time to ${e.to}`, code: 'READY_TIME' }] : []);
  const dc = a.deadline_check;
  const target = dc && !dc.meets ? earlierThan(dc.deadline) : null;
  const conflict = dc ? (dc.meets
    ? `<p class="told">${svg('check', 'ic xs')} Ready ${esc(dc.ready_at)} meets your ${esc(dc.deadline)} deadline. Confirmed by the shop, not by me.</p>`
    : `<p class="warn">Ready ${esc(dc.ready_at)} misses your ${esc(dc.deadline)} deadline.</p>${a.status === 'ACCEPTED' ? (a.earlier_request ? `<p class="hint">Waiting for ${esc(o.provider)} to answer ${esc(a.earlier_request.target)}.</p>` : target ? `<button class="btn primary sm" data-earlier="${esc(a.id)}" data-target="${esc(target)}">Ask for ${esc(target)}, same price</button>` : '') : ''}`) : '';
  const set = reminded()[a.id];
  const remind = !['ACCEPTED', 'READY'].includes(a.status) || !a.ready_at || (dc && !dc.meets) ? ''
    : set ? `<p class="hint">${svg('clock', 'ic xs')} Reminder set for ${esc(new Date(set).toLocaleString('en-GB', { weekday: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Dubai' }))} (quiet hours 23:00–07:00 respected)</p>`
    : `<button class="btn sm" data-remind="${esc(a.id)}">${svg('clock', 'ic xs')} Remind me before it’s ready</button>`;
  const pending = a.status === 'UNKNOWN_STATUS' ? `<p class="warn">${esc(a.blocked_reason || 'Outcome unknown.')}</p>` : '';
  const done = ['COMPLETED', 'DECLINED', 'CANCELLED'].includes(a.status);
  const waiting = a.status === 'SUBMITTED' ? 'Waiting for the shop to accept…' : a.status === 'ACCEPTED' ? 'Waiting for the shop to mark it ready…' : a.status === 'READY' ? 'Ready for pickup; waiting for the shop to mark it done…' : '';
  const title = a.status === 'DECLINED' ? `${esc(o.provider)} declined` : a.status === 'COMPLETED' ? `Done at ${esc(o.provider)}`
    : ['SUBMITTED', 'ACCEPTED', 'READY'].includes(a.status) ? `Order sent to ${esc(o.provider)}` : `Order with ${esc(o.provider)}`;
  return `<div class="msg bot wide status" data-order="${esc(a.id)}">
    <div class="st-head"><span class="st-ic ${a.status === 'DECLINED' ? 'bad' : ''}">${svg(a.status === 'DECLINED' ? 'close' : 'check', 'ic sm')}</span>
      <div><b>${title}</b><span>${o.lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')} · ${money(a.fixed_total_aed)} · sandbox merchant</span></div><span class="st-pill" data-status="${esc(a.status)}">${esc(statusLabel(a.status))}</span></div>
    <ol class="st-steps">${steps.map(x => `<li class="done"><span class="st-dot">${svg('check', 'ic xs')}</span><div><b>${esc(x.label)}</b><span>${fmt(x.at)}</span></div></li>`).join('')}${waiting && !done ? `<li class="now"><span class="st-dot"></span><div><b>${waiting}</b><span>No status changes until the shop taps</span></div></li>` : ''}</ol>
    ${conflict}${pending}${remind}
    <button class="btn sm" data-track-action="${esc(a.id)}">Keep track of this ${svg('chev', 'ic xs')}</button>
    <p class="st-ref">${a.evidence ? `Ref ${esc(a.evidence.reference)} · ` : ''}the price can’t change now</p>
  </div>`;
}
