// One decision card for every choice that waits on the user: a short context
// line, the exact effect, then one primary action and a first-class Not now.
// Callers pass plain data; buttons carry the caller's own data-* attribute.
import { esc } from './ui.js';

const attrs = a => Object.entries(a || {}).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
const btn = (b, cls) => b ? `<button class="btn ${cls}"${attrs(b.attrs)}${b.disabled ? ' disabled' : ''}>${esc(b.label)}</button>` : '';

export const aed = v => 'AED ' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function decisionHTML({ context = '', amount = null, meta = '', title, rows = [], note = '', primary = null, defer = null, discard = null, fine = '' }) {
  return `<article class="decision">
    ${context ? `<span class="decision-context">${esc(context)}</span>` : ''}
    <div class="decision-head">${amount != null ? `<b class="decision-amount">${esc(aed(amount))}</b>` : ''}${meta ? `<span>${esc(meta)}</span>` : ''}</div>
    <h3 class="decision-title">${esc(title)}</h3>
    ${rows.length ? `<dl class="decision-rows">${rows.map(r => `<div><dt>${esc(r.label)}</dt><dd>${esc(r.value)}</dd></div>`).join('')}</dl>` : ''}
    ${note ? `<p class="decision-note">${esc(note)}</p>` : ''}
    <div class="decision-actions">${btn(primary, 'primary wide')}${btn(defer, 'wide')}</div>
    ${discard ? `<button class="decision-discard"${attrs(discard.attrs)}>${esc(discard.label)}</button>` : ''}
    ${fine ? `<p class="fine">${esc(fine)}</p>` : ''}
  </article>`;
}
