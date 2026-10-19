// Sandbox merchant inbox. Each tap is a real merchant command on the server; the
// user's chat changes only because of these taps. Prices are read-only.
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const DAYS = ['Today', 'Tomorrow'];
let es = null, poll = 0;

async function call(url, options = {}) {
  const r = await fetch(url, { credentials: 'same-origin', ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw Object.assign(new Error(typeof data.detail === 'string' ? data.detail : 'Request failed'), { status: r.status });
  return data;
}

const timePicker = (id, value = 'Tomorrow 10:00') => {
  const [day, hm] = value.split(' ');
  return `<span class="row"><select data-day="${id}">${DAYS.map(d => `<option${d === day ? ' selected' : ''}>${d}</option>`).join('')}</select><input type="time" data-time="${id}" value="${esc(hm)}"></span>`;
};
const picked = id => `${$(`[data-day="${id}"]`).value} ${$(`[data-time="${id}"]`).value}`;

function render(orders) {
  const open = orders.filter(o => !['COMPLETED', 'DECLINED'].includes(o.status));
  const done = orders.filter(o => ['COMPLETED', 'DECLINED'].includes(o.status)).slice(0, 5);
  $('#inbox').innerHTML = !orders.length ? '<p class="empty">No orders yet. Approved orders from Dubai-io appear here instantly.</p>'
    : [...open, ...done].map(o => {
      const lines = o.order.lines.map(l => `${l.qty}× ${esc(l.name)} @ AED ${esc(l.price_aed)}`).join('<br>');
      const f = o.fields;
      const actions = o.status === 'SUBMITTED' ? `<label>Ready time</label>${timePicker(o.id)}<div class="row"><button class="primary" data-cmd="accept" data-id="${o.id}">Accept at fixed price</button><button data-cmd="decline" data-id="${o.id}">Decline</button></div>`
        : o.status === 'ACCEPTED' ? `${o.earlier_request ? `<div class="ask">Customer asks: ready by <b>${esc(o.earlier_request.target)}</b> (same price).</div><label>New ready time</label>${timePicker(o.id, o.earlier_request.target)}<div class="row"><button class="primary" data-cmd="confirm-time" data-id="${o.id}">Confirm this time</button></div>` : ''}
           <div class="row"><button data-cmd="ready" data-id="${o.id}">Mark ready</button><button data-cmd="decline" data-id="${o.id}">Decline</button></div>`
        : o.status === 'READY' ? `<div class="row"><button class="primary" data-cmd="complete" data-id="${o.id}">Mark done</button></div>` : '';
      return `<article class="card"><span class="status">${esc(o.status)}</span>
        <b>${esc(o.evidence?.reference || o.id.slice(0, 6))}</b>
        <div class="lines">${lines}</div>
        <div class="total">Total AED ${esc(o.fixed_total_aed)} · fixed, published</div>
        <div class="meta">${o.order.slot ? `Pickup ${esc(o.order.slot)} · ` : ''}${f.area ? `Area ${esc(f.area)}` : ''}${f.deadline ? ` · Needed by ${esc(f.deadline)}` : ''}${o.ready_at ? ` · Ready ${esc(o.ready_at)}` : ''}</div>
        ${actions}<p class="err" data-err="${o.id}"></p></article>`;
    }).join('');
}

async function command(btn) {
  const { cmd, id } = btn.dataset;
  const body = cmd === 'accept' || cmd === 'confirm-time' ? { ready_at: picked(id) } : cmd === 'decline' ? { reason: 'Declined by the shop' } : {};
  btn.disabled = true;
  try { await call(`/api/merchant/orders/${encodeURIComponent(id)}/${cmd}`, { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(body) }); refresh(); }
  catch (e) { $(`[data-err="${id}"]`).textContent = e.message; btn.disabled = false; }
}

const refresh = () => call('/api/merchant/orders').then(d => render(d.orders)).catch(() => {});

async function ops() {
  try {
    const { triggers } = await call('/api/demo/triggers');
    $('#opsButtons').innerHTML = triggers.map(t => `<button data-trigger="${esc(t.kind)}" title="${esc(t.description)}">${esc(t.kind.replaceAll('_', ' '))}</button>`).join('');
    $('#ops').hidden = false;
  } catch { /* not signed in */ }
}

function live() {
  ops();
  es?.close();
  es = new EventSource('/api/merchant/stream');
  es.onmessage = m => { try { render(JSON.parse(m.data)); } catch { /* ignore */ } };
  es.onerror = () => { es.close(); if (!poll) poll = setInterval(refresh, 1500); };
}

async function start() {
  $('#inbox').addEventListener('click', e => { const b = e.target.closest('[data-cmd]'); if (b) command(b); });
  $('#opsButtons').addEventListener('click', async e => {
    const b = e.target.closest('[data-trigger]'); if (!b) return;
    try { const r = await call('/api/demo/triggers', { method: 'POST', body: JSON.stringify({ kind: b.dataset.trigger }) }); $('#opsMsg').textContent = `${b.dataset.trigger}: ${r.affected} message(s) queued`; }
    catch (err) { $('#opsMsg').textContent = err.message; }
  });
  try {
    render((await call('/api/merchant/orders')).orders);
    live();
  } catch (e) {
    if (e.status !== 401) { $('#inbox').innerHTML = `<p class="empty">${esc(e.message)}</p>`; return; }
    const { providers } = await call('/api/merchant/providers');
    $('#provider').innerHTML = providers.map(p => `<option value="${esc(p.id)}">${esc(p.name)} · ${esc(p.service)}</option>`).join('');
    $('#login').hidden = false;
    $('#login').addEventListener('submit', async ev => {
      ev.preventDefault();
      try { const who = await call('/api/merchant/login', { method: 'POST', body: JSON.stringify({ provider_id: $('#provider').value, pin: $('#pin').value.trim() }) });
        $('#login').hidden = true; $('#title').textContent = who.name; refresh(); live(); }
      catch (err) { $('#loginErr').textContent = err.message; }
    });
  }
}
start();
