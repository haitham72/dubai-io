// One decision card for every choice that waits on the user: a short context
// line, the exact effect, then one primary action and a first-class Not now.
// Callers pass plain data; buttons carry the caller's own data-* attribute.
import { esc } from './ui.js';

const attrs = a => Object.entries(a || {}).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
const btn = (b, cls) => b ? `<button class="btn ${cls}"${attrs(b.attrs)}${b.disabled ? ' disabled' : ''}>${esc(b.label)}</button>` : '';

export const aed = v => 'AED ' + Number(v).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const list = (label, items, cls) => items?.length ? `<div class="decision-list ${cls}"><dt>${esc(label)}</dt><dd><ul>${items.map(i => `<li>${esc(i)}</li>`).join('')}</ul></dd></div>` : '';

// kind: approve | check | deadline (data-decision on the card); demo adds the Demo data pill;
// banner is an honest state line (stale refresh, unknown outcome) shown above the title.
export function decisionHTML({ kind = '', context = '', demo = false, amount = null, meta = '', title, banner = null, rows = [], shared = [], never = [], note = '', primary = null, defer = null, discard = null, fine = '' }) {
  return `<article class="decision"${kind ? ` data-decision="${esc(kind)}"` : ''}>
    <div class="decision-top">${context ? `<span class="decision-context">${esc(context)}</span>` : ''}${demo ? '<span class="pill demo sm">Demo data</span>' : ''}</div>
    <div class="decision-head">${amount != null ? `<b class="decision-amount">${esc(aed(amount))}</b>` : ''}${meta ? `<span>${esc(meta)}</span>` : ''}</div>
    <h3 class="decision-title">${esc(title)}</h3>
    ${banner ? `<p class="decision-banner ${esc(banner.tone || '')}" role="status">${esc(banner.text)}</p>` : ''}
    ${rows.length || shared.length || never.length ? `<dl class="decision-rows">${rows.map(r => `<div><dt>${esc(r.label)}</dt><dd>${esc(r.value)}</dd></div>`).join('')}${list('Will be shared', shared, 'shared')}${list('Never shared', never, 'never')}</dl>` : ''}
    ${note ? `<p class="decision-note">${esc(note)}</p>` : ''}
    <div class="decision-actions">${btn(primary, 'primary wide')}${btn(defer, 'wide')}</div>
    ${discard ? `<button class="decision-discard"${attrs(discard.attrs)}>${esc(discard.label)}</button>` : ''}
    ${fine ? `<p class="fine">${esc(fine)}</p>` : ''}
  </article>`;
}
