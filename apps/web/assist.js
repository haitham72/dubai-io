// How follow-ups happen. Ask: you set each one. Auto: routine reminders and
// check-backs are set for you. Learn: ask, then offer Auto once you keep choosing it.
// No mode sends, shares or pays; those always wait for your approval tap.
import { esc, toast } from './ui.js';
import { api } from './service-workflow.js';

const MODES = [
  ['ask', 'Ask me first', 'You set each reminder and check-back yourself.'],
  ['auto', 'Follow up automatically', 'Reminders for ready orders and check-backs for kept reports are set for you.'],
  ['learn', 'Learn from me', 'Ask for now. After you set reminders a few times, offer to do it automatically.'],
];

export function assistHTML() {
  return `<fieldset class="assist" data-assist><legend>How I follow up</legend>${MODES.map(([id, label, hint]) =>
    `<label><input type="radio" name="assist" value="${id}"><span><b>${esc(label)}</b><small>${esc(hint)}</small></span></label>`).join('')}
    <p class="fine">Sending, sharing or paying always waits for your tap, in every mode.</p></fieldset><div class="assist-routine" data-routine></div>`;
}

export async function mountAssist(root) {
  const box = root.querySelector('[data-assist]'); if (!box) return;
  try { const { mode } = await api('/api/assist'); const input = box.querySelector(`input[value="${mode}"]`); if (input) input.checked = true; }
  catch { box.insertAdjacentHTML('beforeend', '<p role="alert">Your follow-up setting could not load.</p>'); }
  const daily = root.querySelector('[data-routine]');
  const showDaily = r => { daily.innerHTML = r.active ? `<p>Daily brief at ${esc(r.at_time)} · Dubai, until ${esc(new Date(r.expires_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'Asia/Dubai' }))}. Turn it on again from a brief to renew.</p><button class="btn wide" data-routine-off>Stop the daily brief</button>` : '<p>Daily brief is off. Ask “brief me” in chat to turn it on.</p>'; };
  api('/api/routines/brief').then(showDaily).catch(() => {});
  daily.addEventListener('click', async event => {
    if (!event.target.closest('[data-routine-off]')) return;
    try { showDaily(await api('/api/routines/brief', { method: 'PUT', body: JSON.stringify({ active: false, at_time: '08:00' }) })); toast('Daily brief stopped.'); }
    catch (error) { toast(error.message); }
  });
  box.addEventListener('change', async event => {
    const input = event.target.closest('input[name="assist"]'); if (!input) return;
    try { await api('/api/assist', { method: 'PUT', body: JSON.stringify({ mode: input.value }) }); toast(MODES.find(m => m[0] === input.value)[1] + ' is on.'); }
    catch (error) { toast(error.message); }
  });
}

// Learn's one-time offer, as quick replies in chat.
export const offerAutoHTML = () => `<p>You often ask me to remind you when an order is ready. Want me to do that automatically from now on? I still won’t send, share or pay without your tap.</p><div class="rec-choices quick"><button class="btn sm" data-assist-offer="auto">Yes, automatically</button><button class="btn sm" data-assist-offer="keep">Keep asking</button></div>`;
export async function answerOffer(choice) {
  const body = choice === 'auto' ? { mode: 'auto' } : { mode: 'learn', dismiss_offer: true };
  await api('/api/assist', { method: 'PUT', body: JSON.stringify(body) });
  toast(choice === 'auto' ? 'Automatic follow-ups are on. Change it in Me.' : 'I’ll keep asking.');
}
