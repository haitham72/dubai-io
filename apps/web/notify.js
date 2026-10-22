// Duet-style "your task is done" notification. Fired only by an authoritative
// source change (a merchant tap) or an explicit, labelled demo preview.
// In view: a banner at the top of the app. Tab in the background and the user
// allowed it: a system notification that brings them back to the task.
import { esc, svg, reduced } from './ui.js';

let host = null, hideTimer = 0;
const supported = () => 'Notification' in window;
export const notificationsAllowed = () => supported() && Notification.permission === 'granted';

export async function allowNotifications() {
  if (!supported()) return 'unsupported';
  return Notification.permission === 'default' ? Notification.requestPermission() : Notification.permission;
}

export function notify({ title, body, demo = false, onOpen }) {
  if (document.hidden && notificationsAllowed()) {
    const n = new Notification(title, { body: (demo ? 'Demo · ' : '') + body, tag: 'dubaiio-' + title });
    n.onclick = () => { window.focus(); n.close(); onOpen?.(); };
    return;
  }
  host ||= Object.assign(document.createElement('div'), { className: 'notify-host' });
  if (!host.isConnected) document.querySelector('#app').append(host);
  host.innerHTML = `<button class="notify" role="status" aria-live="polite"><span class="notify-icon">${svg('orb', 'ic sm')}</span><span class="notify-copy"><span class="notify-head"><b>Dubai-io</b>${demo ? '<em>Demo</em>' : ''}<small>now</small></span><b class="notify-title">${esc(title)}</b><span>${esc(body)}</span></span></button>`;
  host.classList.remove('out'); host.classList.add('in');
  const close = () => { host.classList.remove('in'); host.classList.add('out'); };
  host.firstElementChild.addEventListener('click', () => { close(); onOpen?.(); }, { once: true });
  clearTimeout(hideTimer); hideTimer = setTimeout(close, reduced ? 8000 : 6000);
}

// Source changes worth interrupting for, in the user's words.
const MOMENTS = {
  COMPLETED: ['Task done', 'Marked done by the shop.'],
  READY: ['Ready for you', 'The shop marked it ready.'],
  DECLINED: ['Needs you', 'The shop declined. Open it to choose what next.'],
};
const seen = new Map();
export function sourceMoment(task, action, onOpen) {
  const before = seen.get(action.id); seen.set(action.id, action.status);
  if (!before || before === action.status || !MOMENTS[action.status]) return;  // never on first sight
  const [title, line] = MOMENTS[action.status];
  notify({ title: `${title}: ${task.outcome}`, body: line, onOpen });
}
