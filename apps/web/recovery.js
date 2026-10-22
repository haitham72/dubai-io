import { statusLabel } from './status-labels.js';
import { trackReport } from './tasks.js';
import { openRecoveryRequest } from './service-workflow.js';
// C6: user-given reports and explicitly simulated card/cash trace paths.
import { $, svg, esc, toast, closeSheet, told, reduced } from './ui.js';
import { registerPage, openPage } from './page-host.js';
import { saveDraft } from './session-state.js';
import { REPORT_FIELDS, tripFields, simulateTrace, prepareReport, reportText } from './recovery-state.js';

let ctx, active = null, epoch = 0, actionSeq = 0, cashRuns = 0;
const actions = new Map(), timers = new Map();
const demoPill = '<span class="rec-pill demo">Simulated trace · demo data</span>';
const taxiArt = '<svg class="taxi-art" viewBox="0 0 300 150" role="img" aria-label="Illustrative cream taxi, fictional plate"><rect width="300" height="150" rx="18" fill="#E7F1F6"/><path d="M0 105h300v45H0z" fill="#CFDCE5"/><path d="M65 76l26-34h95l31 34 29 12v28H45V91z" fill="#EAD9B5" stroke="#806F55" stroke-width="2"/><path d="M93 47h88l22 29H73z" fill="#8FB5C8"/><path d="M140 48v28" stroke="#EAD9B5" stroke-width="5"/><rect x="122" y="31" width="47" height="13" rx="4" fill="#F4D06F"/><circle cx="88" cy="116" r="17" fill="#34414A"/><circle cx="210" cy="116" r="17" fill="#34414A"/><circle cx="88" cy="116" r="8" fill="#D4DEE4"/><circle cx="210" cy="116" r="8" fill="#D4DEE4"/><rect x="128" y="90" width="57" height="14" rx="3" fill="#fff"/><text x="156" y="100" text-anchor="middle" fill="#34414A" font-size="9" font-family="sans-serif">DXB-4471</text></svg>';

export function initRecovery(c) { ctx = c; }
function cancelPending() { epoch++; for (const [id, done] of timers) { clearTimeout(id); done(false); } timers.clear(); }
export function resetRecovery() { cancelPending(); active = null; actions.clear(); cashRuns = 0; }
const live = s => active === s && s.epoch === epoch;
function pause(ms, s) { return new Promise(done => { const id = setTimeout(() => { timers.delete(id); done(live(s)); }, reduced ? 0 : ms); timers.set(id, done); }); }
function button(label, fn, cls = '', persistent = false) {
  const id = 'recovery-' + (++actionSeq), owner = active;
  actions.set(id, { fn, owner, persistent });
  return `<button class="btn ${cls}" data-recovery="${id}">${label}</button>`;
}
export function handleRecoveryClick(e) {
  const b = e.target.closest('[data-recovery]'); if (!b) return false;
  const a = actions.get(b.dataset.recovery);
  if (!a || (!a.persistent && !live(a.owner))) { toast('This flow has changed. Start a new request in the chat.'); return true; }
  Promise.resolve(a.fn(b)).catch(() => toast('That step could not finish. Try again.'));
  return true;
}
registerPage('recovery.detail', { title: c => c.title, source: 'Dubai-io · lost item', render: c => '<div class="rec-sheet">' + c.body + '</div>' });
function sheet(title, body, options) { return openPage('recovery.detail', { title, body }, options); }
function reportButton(s, label = 'Prepare RTA report') { return button(svg('globe', 'ic sm') + ' ' + label, () => openReport(s), 'sm'); }
async function keepTrackReport(report, control) {
  control.disabled = true;
  try { await trackReport(report); }
  catch (error) { toast(error.message); }
  finally { if (control.isConnected) control.disabled = false; }
}
const itemName = s => s.item === 'item' ? 'something' : 'your ' + s.item;

export async function startRecovery({ item = 'item', where = null } = {}) {
  cancelPending();
  const s = active = { epoch, item, where, fields: tripFields(told), report: null, tracing: false, receipt: told.receipt || null };
  if (where) return chooseWhere(s, where);
  await ctx.say(`<p>I’m sorry you lost ${esc(itemName(s))}. Where did you last have it?</p><div class="rec-choices">${button(svg('taxi', 'ic sm') + ' In a taxi', () => chooseWhere(s, 'taxi'), 'sm')}${button(svg('train', 'ic sm') + ' On the Metro', () => chooseWhere(s, 'metro'), 'sm')}${button(svg('store', 'ic sm') + ' In a shop', () => chooseWhere(s, 'shop'), 'sm')}${button('Not sure', () => chooseWhere(s, 'unsure'), 'sm')}</div>`);
}
async function chooseWhere(s, where) {
  if (!live(s)) return; s.where = where;
  if (where === 'shop' || where === 'unsure') {
    await ctx.say(`<p>${where === 'shop' ? 'Start with the shop or its customer service desk.' : 'Let’s retrace the last place you used it and the transport you took.'}</p><div class="rec-choices">${button('Check the taxi', () => chooseWhere(s, 'taxi'), 'sm')}${button('Check the Metro', () => chooseWhere(s, 'metro'), 'sm')}${button(svg('map', 'ic sm') + ' Nearby places', () => ctx.near(), 'sm')}</div>`); return;
  }
  if (where === 'metro') {
    s.fields = REPORT_FIELDS.map(([key, label]) => ({ key, label, value: null, provenance: null }));
    await ctx.say(`<p>Let’s prepare the details you know for RTA’s official channel.</p>${reportButton(s)}`); return;
  }
  s.fields = tripFields(told);
  const saved = s.fields.filter(f => f.value);
  if (saved.length) {
    await ctx.say(`<div class="rec-memory"><span class="rec-pill told">You told me</span><h3>Your saved taxi details</h3><dl>${saved.map(f => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value)}</dd></div>`).join('')}</dl><div class="rec-choices">${reportButton(s)}</div></div>`, { wide: true });
  } else await paymentChoice(s);
}
async function paymentChoice(s) {
  if (!live(s)) return;
  await ctx.say(`<p>How did you pay? You can try either demo path, or go straight to the report.</p><div class="rec-card"><div class="rec-title"><span class="rec-icon">${svg('taxi')}</span><h3>How did you pay?</h3></div>${demoPill}<div class="rec-pay">${button('Paid by card', () => cardForm(s), 'primary')}${button('Paid cash', () => trace(s, 'cash'), 'primary')}</div>${reportButton(s, 'Prepare a report instead')}</div>`, { wide: true });
}
function cardForm(s) {
  sheet('Trace by card', `${demoPill}<p class="rec-intro">Only the last four digits. The receipt stays in this browser.</p><form id="recCardForm" class="rec-form"><label for="recLast4">Last four digits</label><input id="recLast4" name="last4" inputmode="numeric" maxlength="4" pattern="[0-9]{4}" required placeholder="e.g. 4242" autocomplete="off"><label for="recReceipt">Receipt photo (optional)</label><input id="recReceipt" type="file" accept="image/*"><p id="recCardError" class="rec-error" role="alert"></p><button class="btn primary wide" type="submit">Run simulated trace</button><p class="rec-fine">Demo: 0000 gives no match. Other four-digit values select a fictional trip. No payment network is contacted.</p></form>`);
  $('#recCardForm').addEventListener('submit', e => {
    e.preventDefault(); if (!live(s) || s.tracing) return;
    const last4 = $('#recLast4').value.trim(), file = $('#recReceipt').files[0];
    if (last4.length !== 4 || ![...last4].every(x => x >= '0' && x <= '9')) { $('#recCardError').textContent = 'Enter exactly four digits.'; return; }
    if (file && (!file.type.startsWith('image/') || file.size > 8 * 1024 * 1024)) { $('#recCardError').textContent = 'Choose an image smaller than 8 MB.'; return; }
    if (file) { if (told.receipt?.url) URL.revokeObjectURL(told.receipt.url); s.receipt = told.receipt = { name: file.name, url: URL.createObjectURL(file) }; }
    e.target.querySelector('button[type="submit"]').disabled = true;
    closeSheet(); trace(s, 'card', last4);
  });
}
async function trace(s, payment, last4 = null) {
  if (!live(s) || s.tracing) return; s.tracing = true;
  const result = simulateTrace(payment, last4, payment === 'cash' ? cashRuns++ : 0);
  s.payment = payment; s.fields.find(f => f.key === 'payment').value = payment;
  s.fields.find(f => f.key === 'payment').provenance = 'user_supplied';
  const id = ctx.post({ wide: true, html: `<div class="rec-card"><div class="rec-title"><span class="rec-icon">${svg('taxi')}</span><h3>${payment === 'cash' ? 'Airport taxi team' : 'Taxi receipt trace'}</h3></div>${demoPill}<p>Waiting for a simulated reply.</p><span class="rec-code" data-status="UNKNOWN_STATUS">${esc(statusLabel('UNKNOWN_STATUS'))}</span><ol class="rec-progress"><li class="on">Requested</li><li>Checking</li><li>Reply</li></ol>${button('Stop demo trace', () => { cancelPending(); active = null; ctx.update(id, m => { m.html = '<p>Demo trace stopped. Nothing was sent.</p>'; }); }, 'sm')}</div>` });
  if (!await pause(1700, s)) return;
  s.tracing = false; s.result = result;
  if (!result.matched) {
    ctx.update(id, m => { m.html = `<div class="rec-card"><div class="rec-title"><span class="rec-icon">${svg('taxi')}</span><h3>No matching trip</h3></div>${demoPill}<p>The demo trace found no match. Add the details you know to the report.</p><span class="rec-code" data-status="UNKNOWN_STATUS">${esc(statusLabel('UNKNOWN_STATUS'))}</span>${reportButton(s)}</div>`; }); return;
  }
  ctx.update(id, m => { m.html = driverCard(s); });
}
function driverCard(s) {
  const d = s.result.driver;
  return `<div class="rec-card"><div class="rec-title"><span class="rec-icon">${svg('taxi')}</span><h3>Matched in the demo</h3></div>${demoPill}<div class="rec-driver-preview">${taxiArt}<div><span class="rec-avatar">${svg('person', 'ic lg')}</span><b>${esc(d.name)} (demo)</b><small>Taxi #${esc(d.plate)} · fictional</small></div></div><div class="rec-driver-status"><span class="rec-dot"></span><div><b>Driver en route (simulated)</b><span>${esc(d.eta)} to the Terminal 3 rank</span></div></div><div class="rec-choices">${button(svg('person', 'ic sm') + ' Driver details', () => driverSheet(s), 'primary sm')}${reportButton(s, 'Prepare report anyway')}</div><p class="rec-fine">A fictional provider reply, not a real match. Your item stays not recovered.</p></div>`;
}
function driverSheet(s) {
  const d = s.result.driver;
  sheet('Taxi #' + d.plate, `${taxiArt}<div class="rec-driver-name"><span class="rec-avatar">${svg('person', 'ic lg')}</span><div><h3>${esc(d.name)} (demo)</h3><p>Fictional driver · illustrated taxi</p></div></div><div class="rec-driver-status"><span class="rec-dot"></span><div><b>Driver en route (simulated)</b><span>${esc(d.eta)} · Terminal 3 rank</span></div></div>${demoPill}<div class="rec-sheet-actions">${button(svg('orb', 'ic sm') + ' Message driver (demo)', () => driverChat(s), 'primary wide')}${reportButton(s, 'Prepare RTA report')}</div><p class="rec-fine">No real driver is contacted. This fixture never becomes a saved trip fact.</p>`);
}
function driverChat(s) {
  sheet('Driver chat · demo', `${demoPill}<div id="recDriverThread" class="rec-driver-chat"><p><b>Imran K. (demo)</b><br>I’m checking the car. This is a fictional reply.</p></div><form id="recDriverForm" class="rec-form"><label for="recDriverMessage">Your message (local demo only)</label><input id="recDriverMessage" maxlength="200" required placeholder="Describe where you left it"><button class="btn primary wide">Send in demo</button></form>`);
  $('#recDriverForm').addEventListener('submit', e => { e.preventDefault(); if (!live(s)) return; const input = $('#recDriverMessage'), value = input.value.trim(); if (!value) return; $('#recDriverThread').insertAdjacentHTML('beforeend', `<p class="me">${esc(value)}</p><p><b>Imran K. (demo)</b><br>I’ll check that spot. Simulated reply; your item is not recovered.</p>`); input.value = ''; });
}
function openReport(s) {
  if (!live(s)) return;
  const fields = s.where === 'metro' ? s.fields.filter(f => ['when', 'from', 'to'].includes(f.key)) : s.fields;
  sheet('Lost item report', `<span class="rec-pill draft">Not filed yet</span><section class="rec-report-trip"><div class="rec-title"><h3>Trip</h3>${fields.some(f => f.value) ? '<span class="rec-pill told">You told me</span>' : '<span class="rec-pill draft">Add what you know</span>'}</div><dl>${fields.map(f => f.value ? `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value)}</dd></div>` : `<div class="missing"><label for="rec-${f.key}">${esc(f.label)}</label><input id="rec-${f.key}" data-rec-field="${f.key}" maxlength="160" placeholder="Add if you know"></div>`).join('')}</dl>${s.receipt ? `<div class="rec-receipt"><span>Receipt photo · you supplied</span><span>${s.receipt.url ? `<img src="${esc(s.receipt.url)}" alt="Your receipt preview">` : ''}${esc(s.receipt.name)}</span></div>` : ''}</section><form id="recReportForm" class="rec-form"><label for="recDescription">Describe the ${esc(s.item)}</label><textarea id="recDescription" maxlength="160" required placeholder="Colour, size and what was inside">${esc(s.report?.description || '')}</textarea><p id="recReportError" class="rec-error" role="alert"></p><button class="btn primary wide">Prepare report</button></form><p class="rec-fine">Missing details stay missing. The official channel may ask for them. This draft is never filed automatically.</p>`);
  $('#recReportForm').addEventListener('submit', e => {
    e.preventDefault(); if (!live(s)) return;
    const values = Object.fromEntries([...$('#sheetBody').querySelectorAll('[data-rec-field]')].map(el => [el.dataset.recField, el.value]));
    try { s.report = prepareReport(s.item, s.fields, $('#recDescription').value, values); s.fields = s.report.fields; } catch(err) { $('#recReportError').textContent = err.message; return; }
    e.target.querySelector('button').disabled = true;
    saveDraft('recovery', {item:s.item,where:s.where,report:s.report});
    reportReady(s);
    ctx.post({ wide: true, recoveryReport:{item:s.item,where:s.where,report:s.report}, html: `<div class="rec-card"><div class="rec-title"><span class="rec-icon">${svg('check')}</span><h3>Report prepared</h3></div><span class="rec-code" data-status="PREPARED_NOT_FILED">${esc(statusLabel('PREPARED_NOT_FILED'))}</span><p>${esc(s.report.description)}</p><p class="rec-fine">Not filed · not recovered.</p>${button('View report', () => reportReady(s), 'sm', true)}${button('Keep track of this', b => keepTrackReport(s.report, b), 'sm', true)}</div>` });
  });
}
async function copyReport(report) {
  const value = reportText(report);
  if (navigator.clipboard?.writeText) { try { await navigator.clipboard.writeText(value); toast('Report copied. Nothing was filed.'); return; } catch { /* LAN fallback below */ } }
  const box = $('#recCopyText'); if (box) { box.hidden = false; box.value = value; box.focus(); box.select(); toast('Select and copy the report text.'); }
}
function reportReady(s) {
  const report = s.report;
  sheet('Report ready', `<div class="rec-ready"><span class="rec-icon">${svg('check')}</span><div><h3>Prepared, not filed</h3><span class="rec-code" data-status="PREPARED_NOT_FILED">${esc(statusLabel('PREPARED_NOT_FILED'))}</span></div></div><p class="rec-intro">${esc(report.description)}</p><section class="rec-report-trip"><dl>${report.fields.filter(f => s.where !== 'metro' || ['when', 'from', 'to'].includes(f.key)).map(f => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value || 'Not given')}</dd></div>`).join('')}</dl></section><p class="rec-not-recovered">Your item is not recovered.</p><div class="rec-sheet-actions">${button('Keep track of this', b => keepTrackReport(report, b), 'primary wide', true)}${button(svg('globe', 'ic sm') + ' Continue with this report', () => openRecoveryRequest(report), 'wide', true)}<a class="btn wide" href="tel:8009090">${svg('phone', 'ic sm')} Call RTA · 800 9090</a><details class="rec-external"><summary>Manual alternatives</summary>${button(svg('wallet', 'ic sm') + ' Copy report', () => copyReport(report), 'wide', true)}</details><textarea id="recCopyText" class="rec-copy" readonly hidden aria-label="Report text to copy"></textarea></div><p class="rec-fine">Continue keeps this report as a saved request. The RTA reporting integration is not connected; nothing has been filed.</p>`, { replace: true });
}

export function restoreReport(record) {
  if(!record?.report||!Array.isArray(record.report.fields))return;
  cancelPending();
  const report=prepareReport(record.item,record.report.fields,record.report.description);
  const s=active={epoch,item:report.item,where:['taxi','metro','shop'].includes(record.where)?record.where:null,fields:report.fields,report,tracing:false,receipt:null};
  reportReady(s);
}
