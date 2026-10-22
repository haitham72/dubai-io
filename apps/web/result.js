// One result card for finished work (a prepared report, an order outcome):
// context, title, verdict first, when it was updated, then Open and Keep on Today.
// Keeping uses the existing task link; it never approves, files or sends.
import { esc, svg } from './ui.js';

const attrs = a => Object.entries(a || {}).map(([k, v]) => ` ${k}="${esc(v)}"`).join('');
export const updatedAt = iso => new Date(iso || Date.now()).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Dubai' });

export function resultHTML({ context = '', title, verdict = '', updated = null, status = '', open = null, keep = null }) {
  return `<article class="result"${status ? ` data-status="${esc(status)}"` : ''}>
    ${context ? `<span class="result-context">${esc(context)}</span>` : ''}
    <h3 class="result-title">${esc(title)}</h3>
    ${verdict ? `<p class="result-verdict">${esc(verdict)}</p>` : ''}
    <footer class="result-foot"><span>Updated ${esc(updatedAt(updated))}</span>
      ${keep ? `<button class="result-keep"${attrs(keep.attrs)} aria-label="Keep on Today">${svg('keep', 'ic sm')}<span>Keep on Today</span></button>` : ''}
      ${open ? `<button class="result-open"${attrs(open.attrs)} aria-label="${esc(open.label || 'Open')}">${svg('chev', 'ic sm')}</button>` : ''}</footer>
  </article>`;
}
