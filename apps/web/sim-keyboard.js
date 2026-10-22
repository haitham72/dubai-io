// Preview only: an iPhone-style keyboard for desktop review, so Ask behaves like
// it does on a phone (composer and chat ride above the keyboard). Real touch
// devices keep their own keyboard; #nokbd turns this off. Physical typing still works.
import { esc } from './ui.js';

const HEIGHT = 291;
const ROWS = {
  abc: ['qwertyuiop', 'asdfghjkl', '⇧zxcvbnm⌫', ['123', 'space', 'return']],
  num: ['1234567890', '-/:;()$&@"', '#+=.,?!\'⌫', ['ABC', 'space', 'return']],
};

export function initSimKeyboard(app, input, form) {
  const desktop = matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (!desktop || location.hash.includes('nokbd')) return;
  let layer = 'abc', shift = false;
  const pad = document.createElement('div');
  pad.className = 'sim-keyboard'; pad.hidden = true; pad.setAttribute('aria-hidden', 'true');
  app.append(pad);

  const key = (k, extra = '') => {
    const label = k === 'space' ? 'space' : k === 'return' ? 'return' : k === '⇧' ? '⇧' : shift && k.length === 1 ? k.toUpperCase() : k;
    const wide = { space: 'space', return: 'action', '123': 'mod', ABC: 'mod', '⇧': 'mod', '⌫': 'mod' }[k] || '';
    return `<button type="button" tabindex="-1" class="${wide} ${extra}" data-key="${esc(k)}">${esc(label)}</button>`;
  };
  function render() {
    pad.innerHTML = ROWS[layer].map(row => `<div>${[...(Array.isArray(row) ? row : [...row])].map(k => key(k, k === '⇧' && shift ? 'on' : '')).join('')}</div>`).join('') + '<span class="sim-keyboard-tag">Preview keyboard</span>';
  }
  function insert(text) {
    const start = input.selectionStart ?? input.value.length, end = input.selectionEnd ?? start;
    input.setRangeText(text, start, end, 'end');
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function show(open) {
    pad.hidden = !open;
    app.classList.toggle('sim-keyboard-open', open);
    app.classList.toggle('keyboard-open', open);
    app.style.setProperty('--keyboard-inset', open ? HEIGHT + 'px' : '0px');
  }

  // Keys never take focus, so the caret stays in the composer.
  pad.addEventListener('pointerdown', event => {
    event.preventDefault();
    const k = event.target.closest('[data-key]')?.dataset.key; if (!k) return;
    if (k === '⌫') { const s = input.selectionStart, e = input.selectionEnd; if (s !== e) input.setRangeText('', s, e, 'end'); else if (s > 0) input.setRangeText('', s - 1, s, 'end'); input.dispatchEvent(new Event('input', { bubbles: true })); return; }
    if (k === '⇧') { shift = !shift; render(); return; }
    if (k === '123' || k === 'ABC') { layer = k === '123' ? 'num' : 'abc'; render(); return; }
    if (k === 'space') { insert(' '); return; }
    if (k === 'return') { form.requestSubmit(); return; }
    insert(shift ? k.toUpperCase() : k);
    if (shift) { shift = false; render(); }
  });
  input.addEventListener('focus', () => { layer = 'abc'; shift = !input.value; render(); show(true); });
  input.addEventListener('blur', () => show(false));
  render();
}
