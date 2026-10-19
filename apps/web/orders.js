// Fixed-price orders through the server action engine. The mini-app can only
// ask; the server rebuilds items and total from its catalog, the user approves
// the exact snapshot once, and every later status comes from a merchant tap
// delivered over /api/actions/{id}/stream. Nothing here simulates a merchant.
import { $, svg, esc, toast, told, openSheet, closeSheet } from './ui.js';
import { api } from './service-workflow.js';

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
  $('#ordReview').innerHTML = `
    <p class="lead">${o.lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')}${o.slot ? ` · pickup ${esc(o.slot)}` : ''}</p>
    <div class="appr">
      <div class="appr-total"><span>Total at their published prices</span><b>${money(a.fixed_total_aed)} (demo)</b></div>
      <h4>Shared with ${esc(a.recipient)}</h4>
      <ul><li>${svg('check', 'ic xs')} The items, total${o.slot ? ' and pickup slot' : ''} above</li>
        ${f.area ? `<li>${svg('check', 'ic xs')} Area: ${esc(f.area.value)} (you told me)</li>` : ''}
        ${f.deadline ? `<li>${svg('check', 'ic xs')} Needed by: ${esc(f.deadline.value)} (you told me)</li>` : ''}</ul>
      <h4>Never shared</h4>
      <ul class="no"><li>${svg('close', 'ic xs')} Your name, number and profile</li><li>${svg('close', 'ic xs')} Anything I noticed about you, and your other orders</li></ul>
    </div>
    ${a.status === 'DRAFT' ? `<p class="hint">Add ${a.missing.map(esc).join(', ')} to continue.</p>` : ''}
    <div class="actions"><button class="btn" id="ordNo">Cancel</button><button class="btn primary" id="ordYes" ${a.status === 'AWAITING_APPROVAL' ? '' : 'disabled'}>Approve and send</button></div>
    <p class="fine">One approval. Prices come from the merchant’s published list (${esc(o.provenance.replace('_', ' '))}, as of ${esc(o.as_of)}), not from the mini-app. The price can’t change after you send; the merchant can accept or decline.</p>`;
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
  const fallback = () => { if (poll || closed) return; poll = setInterval(() => api('/api/actions/' + encodeURIComponent(id)).then(onUpdate).catch(() => {}), 1500); };
  let es = null;
  try { es = new EventSource('/api/actions/' + encodeURIComponent(id) + '/stream'); } catch { fallback(); }
  if (es) {
    es.onmessage = m => { try { onUpdate(JSON.parse(m.data)); } catch { /* ignore a malformed frame */ } };
    es.addEventListener('gone', () => es.close());
    es.onerror = () => { es.close(); fallback(); };
  }
  return () => { closed = true; es?.close(); clearInterval(poll); };
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
  const last = steps[steps.length - 1];
  const dc = a.deadline_check;
  const target = dc && !dc.meets ? earlierThan(dc.deadline) : null;
  const conflict = dc ? (dc.meets
    ? `<p class="told">${svg('check', 'ic xs')} Ready ${esc(dc.ready_at)} meets your ${esc(dc.deadline)} deadline. Confirmed by the shop, not by me.</p>`
    : `<p class="warn">Ready ${esc(dc.ready_at)} misses your ${esc(dc.deadline)} deadline.</p>${a.status === 'ACCEPTED' ? (a.earlier_request ? `<p class="hint">Waiting for ${esc(o.provider)} to answer ${esc(a.earlier_request.target)}.</p>` : target ? `<button class="btn primary sm" data-earlier="${esc(a.id)}" data-target="${esc(target)}">Ask for ${esc(target)}, same price</button>` : '') : ''}`) : '';
  const pending = a.status === 'SUBMITTED' ? `<p class="hint">Waiting for the merchant. No status changes until they tap.</p>` : a.status === 'UNKNOWN_STATUS' ? `<p class="warn">${esc(a.blocked_reason || 'Outcome unknown.')}</p>` : '';
  return `<div class="msg bot wide status" data-order="${esc(a.id)}">
    <div class="st-head"><span class="logo">${esc((o.provider || '?').slice(0, 2).toUpperCase())}</span><div><b>${esc(o.provider || a.recipient)}</b><span>${o.lines.map(l => `${l.qty}× ${esc(l.name)}`).join(', ')} · ${money(a.fixed_total_aed)} (demo)</span></div><span class="pill">Sandbox merchant · live</span></div>
    <ol class="st-steps">${steps.map(x => `<li class="${x === last ? 'now' : ''}"><span class="st-dot"></span><div><b>${esc(x.label)}</b><span><code>${x.code}</code> · ${fmt(x.at)}</span></div></li>`).join('')}</ol>
    ${conflict}${pending}
    <p class="st-ref">${a.evidence ? `Ref ${esc(a.evidence.reference)} · ` : ''}the price can’t change now</p>
  </div>`;
}
