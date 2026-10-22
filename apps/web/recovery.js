import { statusLabel } from './status-labels.js';
import { resultHTML } from './result.js';
import { trackReport } from './tasks.js';
import { openRecoveryRequest } from './service-workflow.js';
// C6/TAXI-02: user-given reports; replies are staged on the saved task, never simulated here.
import { $, svg, esc, toast, closeSheet, told } from './ui.js';
import { registerPage, openPage } from './page-host.js';
import { saveDraft } from './session-state.js';
import { REPORT_FIELDS, tripFields, prepareReport, reportText } from './recovery-state.js';

let ctx, active = null, epoch = 0, actionSeq = 0;
const actions = new Map();

export function initRecovery(c) { ctx = c; }
function cancelPending() { epoch++; }
export function resetRecovery() { cancelPending(); active = null; actions.clear(); }
const live = s => active === s && s.epoch === epoch;
function actionId(fn, persistent = false) {
  const id = 'recovery-' + (++actionSeq);
  actions.set(id, { fn, owner: active, persistent });
  return id;
}
function button(label, fn, cls = '', persistent = false) {
  return `<button class="btn ${cls}" data-recovery="${actionId(fn, persistent)}">${label}</button>`;
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
  const s = active = { epoch, item, where, fields: tripFields(told), report: null, receipt: told.receipt || null };
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
  await receiptChoice(s);
}
// TAXI-02: receipt first, as quick replies. Nothing is traced or contacted here.
async function receiptChoice(s) {
  if (!live(s)) return;
  await ctx.say(`<p>Do you have the taxi receipt? It usually shows the plate and the trip time.</p><div class="rec-choices quick">${button('I have a receipt', () => receiptForm(s), 'sm')}${button('Paid cash, no receipt', () => confirmTrip(s, 'cash'), 'sm')}${button('Not sure', () => confirmTrip(s, null), 'sm')}</div>`);
}
function receiptForm(s) {
  const value = key => esc(s.fields.find(f => f.key === key)?.value || '');
  sheet('From your receipt', `<p class="rec-intro">Type only what the receipt shows. Leave the rest empty. The photo stays in this browser.</p><form id="recReceiptForm" class="rec-form">${[['plate', 'Taxi plate'], ['when', 'Date and time'], ['fare', 'Trip fare'], ['booking', 'Booking reference']].map(([k, l]) => `<label for="recr-${k}">${l}</label><input id="recr-${k}" data-receipt-field="${k}" maxlength="80" value="${value(k)}" autocomplete="off">`).join('')}<label for="recReceipt">Receipt photo (optional)</label><input id="recReceipt" type="file" accept="image/*"><p id="recReceiptError" class="rec-error" role="alert"></p><button class="btn primary wide" type="submit">Use these details</button></form>`);
  $('#recReceiptForm').addEventListener('submit', e => {
    e.preventDefault(); if (!live(s)) return;
    const file = $('#recReceipt').files[0];
    if (file && (!file.type.startsWith('image/') || file.size > 8 * 1024 * 1024)) { $('#recReceiptError').textContent = 'Choose an image smaller than 8 MB.'; return; }
    if (file) { if (told.receipt?.url) URL.revokeObjectURL(told.receipt.url); s.receipt = told.receipt = { name: file.name, url: URL.createObjectURL(file) }; }
    for (const el of $('#sheetBody').querySelectorAll('[data-receipt-field]')) {
      const f = s.fields.find(x => x.key === el.dataset.receiptField), v = el.value.trim();
      if (v) { f.value = v.slice(0, 160); f.provenance = 'user_supplied'; }
    }
    closeSheet(); confirmTrip(s, 'receipt');
  });
}
// Cash or unknown: confirm route and time before anything is prepared. Unknown stays unknown.
async function confirmTrip(s, payment) {
  if (!live(s)) return;
  if (payment) { const f = s.fields.find(x => x.key === 'payment'); f.value = payment === 'cash' ? 'Cash' : 'Receipt'; f.provenance = 'user_supplied'; }
  const trip = s.fields.filter(f => ['when', 'from', 'to'].includes(f.key));
  if (!trip.some(f => f.value)) return openReport(s);
  await ctx.say(`<div class="rec-memory"><span class="rec-pill told">You told me</span><h3>Is this the trip?</h3><dl>${trip.map(f => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value || 'Unknown')}</dd></div>`).join('')}</dl><div class="rec-choices quick">${button('Yes, that’s the trip', () => openReport(s), 'sm')}${button('Change the trip', () => { for (const f of trip) { f.value = null; f.provenance = null; } openReport(s); }, 'sm')}</div></div>`, { wide: true });
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
    ctx.post({ wide: true, recoveryReport:{item:s.item,where:s.where,report:s.report}, html: resultHTML({ context: 'Lost item report · ' + statusLabel('PREPARED_NOT_FILED'), title: s.report.description, verdict: 'Ready for RTA’s official channel. Nothing is filed and your item is not recovered.', status: 'PREPARED_NOT_FILED',
      open: { label: 'View report', attrs: { 'data-recovery': actionId(() => reportReady(s), true) } }, keep: { attrs: { 'data-recovery': actionId(b => keepTrackReport(s.report, b), true) } } }) });
  });
}
async function copyReport(report) {
  const value = reportText(report);
  if (navigator.clipboard?.writeText) { try { await navigator.clipboard.writeText(value); toast('Report copied. Nothing was filed.'); return; } catch { /* LAN fallback below */ } }
  const box = $('#recCopyText'); if (box) { box.hidden = false; box.value = value; box.focus(); box.select(); toast('Select and copy the report text.'); }
}
function reportReady(s) {
  const report = s.report;
  sheet('Report ready', `<div class="rec-ready"><span class="rec-icon">${svg('check')}</span><div><h3>Prepared, not filed</h3><span class="rec-code" data-status="PREPARED_NOT_FILED">${esc(statusLabel('PREPARED_NOT_FILED'))}</span></div></div><p class="rec-intro">${esc(report.description)}</p><section class="rec-report-trip"><dl>${report.fields.filter(f => s.where !== 'metro' || ['when', 'from', 'to'].includes(f.key)).map(f => `<div><dt>${esc(f.label)}</dt><dd>${esc(f.value || 'Not given')}</dd></div>`).join('')}</dl></section><p class="rec-not-recovered">Your item is not recovered.</p><div class="rec-sheet-actions">${button('Keep on Today', b => keepTrackReport(report, b), 'primary wide', true)}${button(svg('globe', 'ic sm') + ' Continue with this report', () => openRecoveryRequest(report), 'wide', true)}<a class="btn wide" href="tel:8009090">${svg('phone', 'ic sm')} Call RTA · 800 9090</a><details class="rec-external"><summary>Manual alternatives</summary>${button(svg('wallet', 'ic sm') + ' Copy report', () => copyReport(report), 'wide', true)}</details><textarea id="recCopyText" class="rec-copy" readonly hidden aria-label="Report text to copy"></textarea></div><p class="rec-fine">Continue keeps this report as a saved request. The RTA reporting integration is not connected; nothing has been filed.</p>`, { replace: true });
}

export function restoreReport(record) {
  if(!record?.report||!Array.isArray(record.report.fields))return;
  cancelPending();
  const report=prepareReport(record.item,record.report.fields,record.report.description);
  const s=active={epoch,item:report.item,where:['taxi','metro','shop'].includes(record.where)?record.where:null,fields:report.fields,report,receipt:null};
  reportReady(s);
}
