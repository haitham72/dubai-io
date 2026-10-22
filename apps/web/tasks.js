// Manual responsibilities. No model, provider dispatch or background monitor.
import { labFetch } from './api-client.js';
import { esc, svg, toast, closeSheet, reduced } from './ui.js';
import { registerPage, openPage } from './page-host.js';
import { selectTaskFocus } from './assistant-context.js';
import { statusLabel } from './status-labels.js';
import { decisionHTML } from './decision.js';

const labels = { WAITING_USER: 'Waiting for your update', PAUSED: 'Paused', COMPLETED: 'Done · you reported', CANCELLED: 'Cancelled' };
export const taskStateLabel = status => labels[status] || 'Status unavailable';
const active = task => ['WAITING_USER', 'PAUSED'].includes(task.status);
const date = value => value ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dubai', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '';
const localDate = value => value ? new Date(Date.parse(value) + 4 * 3600000).toISOString().slice(0, 16) : '';
const key = () => crypto.randomUUID();
const live = root => root.isConnected && root.closest('#sheet')?.classList.contains('open');
let changed = () => {};

async function request(path, body) {
  const response = await labFetch(path, { ...(body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {}), signal: AbortSignal.timeout(10000) });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'The task could not be saved. Check your entries and try again.');
    error.status = response.status; throw error;
  }
  return response.json();
}

function row(task) {
  const state = task.source_status ? statusLabel(task.source_status) : labels[task.status] || 'Status unavailable';
  return `<button class="task-row" data-open-task="${esc(task.id)}"><span class="task-row-icon">${svg(task.status === 'COMPLETED' ? 'check' : task.status === 'PAUSED' ? 'clock' : 'orb', 'ic sm')}</span><span class="task-row-copy"><b>${esc(task.outcome)}</b>${task.next_step && task.next_step !== 'Add an update when you are ready.' ? `<span>${esc(task.next_step)}</span>` : ''}<small>${esc(state)}</small>${task.due_at ? `<small class="${task.due_state ? 'task-due-flag' : ''}">${task.due_state === 'overdue' ? 'Overdue · ' : task.due_state === 'due_soon' ? 'Due within 24h · ' : 'Due '}${esc(date(task.due_at))} · Dubai time</small>` : ''}</span>${svg('chev', 'ic sm')}</button>`;
}

function fields(task = {}, compact = false) {
  const title = `<label>What would you like to keep track of?<input name="outcome" maxlength="240" required value="${esc(task.outcome || '')}" placeholder="Follow up on my lost bag" autofocus></label>`;
  const optional = `<label>Your next step<input name="next_step" maxlength="300" value="${esc(task.next_step === 'Add an update when you are ready.' ? '' : task.next_step || '')}" placeholder="For example, confirm the route and time"></label>
    <label><span>Due · Dubai time <small class="task-optional">optional</small></span><input type="datetime-local" name="due_at" value="${esc(localDate(task.due_at))}"></label>
    <label><span>Details <small class="task-optional">optional</small></span><textarea name="details" maxlength="1600" rows="3" placeholder="Only the context this task needs">${esc(task.details || '')}</textarea></label>`;
  return title + (compact ? `<details class="task-options"><summary>Add a date or details</summary><div>${optional}</div></details>` : optional);
}

function readFields(form) {
  const data = new FormData(form);
  return { outcome: data.get('outcome').trim(), next_step: data.get('next_step').trim(), details: data.get('details').trim(),
    due_at: data.get('due_at') ? new Date(data.get('due_at') + '+04:00').toISOString() : null };
}

function errorLine(root, message) {
  const el = root.querySelector('[data-task-error]');
  if (el) { el.textContent = message; el.hidden = false; }
}

function wireRows(root) {
  root.addEventListener('click', event => {
    const button = event.target.closest('[data-open-task]');
    if (button) openTask(button.dataset.openTask);
  });
}

registerPage('tasks.new', {
  title: 'A new task', source: 'Saved for you',
  render: () => `<form class="task-form" data-new-task>${fields({}, true)}<p class="task-boundary">This saves a task for your updates. Automatic checks and sending are not active yet.</p><p role="alert" data-task-error hidden></p><button class="btn primary wide" type="submit">Save task</button></form>`,
  mount(root) {
    const form = root.querySelector('form');
    let attempt = null, busy = false;
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (busy) return;
      // A lost response can mean the save succeeded. Retry the exact request/key.
      attempt ||= { ...readFields(form), creation_key: key() };
      busy = true;
      form.querySelectorAll('input,textarea,button').forEach(el => { el.disabled = true; });
      try {
        const result = await request('/api/tasks', attempt);
        changed();
        if (live(root)) openPage('tasks.detail', { id: result.task.id }, { replace: true });
      } catch (error) {
        if (!live(root)) return;
        errorLine(root, error.status ? error.message : 'The save could not be confirmed. Retry this save to avoid creating a duplicate.');
        if (error.status) { attempt = null; form.querySelectorAll('input,textarea').forEach(el => { el.disabled = false; }); }
        form.querySelector('button[type=submit]').textContent = 'Retry save';
      } finally { busy = false; if (live(root)) form.querySelector('button[type=submit]').disabled = false; }
    });
  },
});

registerPage('tasks.list', {
  title: 'All tasks', source: 'Your saved responsibilities',
  render: () => '<div class="task-list-page"><p role="status">Loading your tasks…</p></div>',
  mount(root) {
    let offset = 0, busy = false, items = [], more = null;
    wireRows(root);
    async function load(reset = false) {
      if (busy) return;
      busy = true;
      if (reset) { offset = 0; items = []; }
      root.querySelector('[data-more-tasks]')?.setAttribute('disabled', '');
      try {
        const data = await request('/api/tasks?offset=' + offset);
        if (!root.isConnected) return;
        items.push(...data.tasks); more = data.next_offset;
        root.innerHTML = `<div class="task-list-page">${items.length ? items.map(row).join('') : '<p>You have no saved tasks yet.</p>'}<p role="alert" data-task-error hidden></p>${more != null ? '<button class="btn wide" data-more-tasks>Load more tasks</button>' : ''}<button class="btn wide" data-new-task>New task</button></div>`;
      } catch { if (root.isConnected) root.innerHTML = '<p role="alert">Your tasks could not be loaded. Your saved work has not been replaced.</p><button class="btn wide" data-reload-tasks>Try again</button>'; }
      finally { busy = false; }
    }
    root.addEventListener('click', event => {
      if (event.target.closest('[data-more-tasks]')) { offset = more; load(); }
      if (event.target.closest('[data-reload-tasks]')) load(true);
      if (event.target.closest('[data-new-task]')) openPage('tasks.new');
    });
    root.addEventListener('dubaiio:page-restored', () => load(true));
    load(true);
  },
});

// TAXI-02: staged replies come from the server script and are labelled at every step.
function stagedHTML(data) {
  const t = data.task;
  if (data.linked_item?.capability_id !== 'recovery.rta' || t.status !== 'WAITING_USER') return '';
  const replies = data.events.filter(e => e.kind === 'staged_reply'), chosen = data.events.some(e => e.kind === 'collection_chosen');
  const list = replies.map(e => `<li><span class="rec-pill demo">Staged · demo</span><b>${esc(e.sender)}</b><p>${esc(e.text)}</p><small>${esc(date(e.at))} · Dubai time</small></li>`).join('');
  const next = replies.length < 2 ? `<button class="btn wide" data-task-command="staged_next">Show the next staged reply</button>`
    : chosen ? '<p class="task-boundary">You chose to collect it. It is not recovered until you have it.</p>'
    : decisionHTML({ context: 'Staged demo · lost item', title: 'How do you want it back?', note: 'No delivery service is connected, so delivery is not available.',
        primary: { label: 'I’ll collect it', attrs: { 'data-task-command': 'collect' } }, defer: { label: 'Delivery · not available', attrs: {}, disabled: true } });
  return `<section class="task-staged"><span>Replies · staged demo</span>${list ? `<ol>${list}</ol>` : '<p>No replies yet. Staged replies show how answers would arrive; nobody was contacted.</p>'}${next}</section>`;
}

function detailHTML(data) {
  const t = data.task;
  return `<article class="task-detail"><span class="task-state" data-status="${esc(t.status)}" tabindex="-1" role="status" aria-live="polite" aria-atomic="true">${esc(labels[t.status] || t.status)}</span><h3>${esc(t.outcome)}</h3>
    ${t.due_at ? `<p class="task-due">${svg('cal', 'ic sm')} Due ${esc(date(t.due_at))} · Dubai time · you set this</p>` : ''}
    ${t.details ? `<p class="task-notes">${esc(t.details)}</p>` : ''}
    ${active(t) && t.next_step && t.next_step !== 'Add an update when you are ready.' ? `<section class="task-next"><span>Your next step</span><p>${esc(t.next_step)}</p></section>` : ''}
    ${t.result ? `<section class="task-next"><span>Result · you reported</span><p>${esc(t.result.text)}</p><small>${esc(date(t.result.as_of))} · Dubai time</small></section>` : ''}
    <p class="task-boundary">${t.status === 'CANCELLED' ? 'Tracking stopped. No request was sent from this task.' : 'Saved for your updates. Automatic checks and sending are not active yet.'}</p>
    ${t.source ? `<section class="task-next"><span>Linked ${data.linked_item?.capability_id === 'order.request' ? 'order' : 'request'}</span><p>${esc(data.linked_item ? statusLabel(data.linked_item.status) : 'The linked item is unavailable.')}</p>${data.linked_item ? `<button class="btn wide" data-open-linked-item="${esc(t.source.id)}">Open linked item ${svg('chev', 'ic xs')}</button>` : ''}<small>Tracking does not send, cancel or complete the linked item.</small></section>` : ''}
    ${stagedHTML(data)}
    <button class="btn wide" data-task-chat>Discuss this task ${svg('orb', 'ic sm')}</button>
    <p role="alert" data-task-error hidden></p><div data-task-editor></div>
    ${active(t) ? `<div class="task-actions"><button class="btn" data-task-edit>Edit task</button><button class="btn" data-task-command="${t.status === 'PAUSED' ? 'resume' : 'pause'}">${t.status === 'PAUSED' ? 'Resume' : 'Pause'}</button><button class="btn primary" data-task-complete>Mark done</button><button class="task-cancel" data-task-command="cancel">Cancel task</button></div>` : ''}
    <details class="task-activity"><summary>Activity</summary><ol>${data.events.map(e => `<li><b>${esc({created:'Saved by you',staged_reply:'Staged reply · demo',collection_chosen:'You chose to collect it',edited:'Details edited',paused:'Paused by you',resumed:'Resumed by you',cancelled:'Cancelled by you',completed:'Completion reported by you'}[e.kind] || e.kind)}</b><span>${esc(date(e.at))} · Dubai time</span>${e.fields ? `<small>Changed: ${esc(e.fields.join(', ').replaceAll('_', ' '))}</small>` : ''}</li>`).join('')}</ol>${data.before_seq ? '<button class="btn wide" data-older-events>Earlier activity</button>' : ''}</details>
    <p class="task-updated">Saved by you · updated ${esc(date(t.updated_at))} · Dubai time</p></article>`;
}

registerPage('tasks.detail', {
  title: 'Task', source: 'Your saved responsibility', render: () => '<p class="task-announcement" role="status" aria-live="polite" aria-atomic="true" data-task-announcement></p><div data-task-content><p role="status">Loading task…</p></div>',
  mount(root, context) {
    // Keep the live region mounted while detail content changes, including edits
    // whose state label stays the same. Device screen-reader output needs review.
    const content = root.querySelector('[data-task-content]');
    const announcement = root.querySelector('[data-task-announcement]');
    let data, busy = false, generation = 0, pending = null;
    async function load(focusState = false, message = '') {
      const mine = ++generation;
      try {
        const result = await request('/api/tasks/' + encodeURIComponent(context.id));
        if (root.isConnected && mine === generation) {
          data = result; pending = null; content.innerHTML = detailHTML(data);
          if (focusState && live(root)) {
            root.querySelector('.task-state').focus({ preventScroll: true });
            announcement.textContent = message + ' ' + labels[data.task.status];
          }
        }
      } catch { if (root.isConnected && mine === generation) content.innerHTML = '<p role="alert">This task could not be loaded.</p><button class="btn wide" data-task-reload>Try again</button>'; }
    }
    async function send(kind, extra = {}) {
      if (busy) return;
      pending ||= { kind, ...extra, expected_revision: data.task.revision, command_key: key() };
      busy = true;
      announcement.textContent = '';
      // Re-enable only what this change locked; re-rendered controls keep their own state.
      const locked = [...root.querySelectorAll('button:not([disabled]),input:not([disabled]),textarea:not([disabled])')];
      locked.forEach(el => { el.disabled = true; });
      try {
        const result = await request('/api/tasks/' + encodeURIComponent(context.id) + '/commands', pending);
        changed();
        if (root.isConnected) { data.task = result.task; pending = null; await load(true, kind === 'edit' ? 'Task details updated.' : 'Task updated.'); }
      } catch (error) {
        if (!root.isConnected) return;
        if (error.status === 409) {
          errorLine(root, error.message);
          root.querySelector('[data-task-editor]').innerHTML = '<p>Your edit was not applied. Reload the latest task before trying again.</p><button class="btn wide" data-task-reload>Reload latest task</button>';
          root.querySelector('.task-actions')?.setAttribute('hidden', ''); pending = null;
        } else if (!error.status) {
          errorLine(root, 'The change could not be confirmed. Retry the same change or reload to check the current state.');
          root.querySelector('[data-task-editor]').innerHTML = '<button class="btn wide" data-task-retry>Retry change</button><button class="btn wide" data-task-reload>Reload task</button>';
          root.querySelector('.task-actions')?.setAttribute('hidden', '');
        } else { errorLine(root, error.message); pending = null; }
      } finally { busy = false; locked.forEach(el => { el.disabled = false; }); }
    }
    root.addEventListener('click', async event => {
      if (busy) return;
      if (event.target.closest('[data-task-reload]')) { pending = null; load(); return; }
      if (event.target.closest('[data-task-retry]')) { send(pending.kind); return; }
      if (!data) return;
      if (event.target.closest('[data-open-linked-item]')) { openPage('service.action', { id: data.task.source.id }); return; }
      if (event.target.closest('[data-task-chat]')) {
        selectTaskFocus(data.task); closeSheet(); window.dispatchEvent(new CustomEvent('dubaiio:task-chat')); return;
      }
      const control = event.target.closest('[data-task-command]');
      const editor = root.querySelector('[data-task-editor]');
      if (control) {
        if (control.dataset.taskCommand === 'cancel') {
          editor.innerHTML = '<section class="task-stop"><p>Stop tracking this task?</p><p class="task-boundary">Your history stays available. Nothing will be sent.</p><button class="btn" data-keep-task>Keep task</button><button class="btn primary" data-confirm-cancel>Stop tracking</button></section>';
          root.querySelector('.task-actions').hidden = true;
          editor.querySelector('[data-keep-task]').focus();
        } else send(control.dataset.taskCommand);
        return;
      }
      if (event.target.closest('[data-confirm-cancel]')) { send('cancel'); return; }
      if (event.target.closest('[data-keep-task]')) { content.innerHTML = detailHTML(data); root.querySelector('[data-task-command="cancel"]').focus(); return; }
      if (event.target.closest('[data-task-edit]')) {
        editor.innerHTML = `<form class="task-form" data-edit-task>${fields(data.task)}<button type="submit" class="btn primary wide">Save changes</button><button type="button" class="btn wide" data-edit-close>Keep current details</button></form>`;
        root.querySelector('.task-actions').hidden = true; editor.querySelector('input').focus();
      }
      if (event.target.closest('[data-task-complete]')) {
        editor.innerHTML = '<form class="task-form" data-complete-task><label>What happened?<textarea name="result" maxlength="1000" rows="3" required placeholder="I collected the bag myself"></textarea></label><p class="task-boundary">Recorded as your update, not a provider confirmation.</p><button type="submit" class="btn primary wide">Mark done · my update</button><button type="button" class="btn wide" data-edit-close>Keep task open</button></form>';
        root.querySelector('.task-actions').hidden = true; editor.querySelector('textarea').focus();
      }
      if (event.target.closest('[data-edit-close]')) content.innerHTML = detailHTML(data);
      if (event.target.closest('[data-older-events]')) {
        const button = event.target.closest('button'); button.disabled = true;
        try {
          const earlier = await request(`/api/tasks/${encodeURIComponent(context.id)}/activity?before_seq=${data.before_seq}`);
          if (!root.isConnected) return;
          data.events = [...earlier.events, ...data.events]; data.before_seq = earlier.before_seq;
          content.innerHTML = detailHTML(data); root.querySelector('.task-activity').open = true;
        } catch { if (root.isConnected) { errorLine(root, 'Earlier activity could not be loaded. Try again.'); button.disabled = false; } }
      }
    });
    root.addEventListener('submit', event => {
      event.preventDefault(); if (busy) return;
      if (event.target.matches('[data-edit-task]')) send('edit', { changes: readFields(event.target) });
      if (event.target.matches('[data-complete-task]')) send('complete', { result: new FormData(event.target).get('result').trim() });
    });
    root.addEventListener('keydown', event => {
      if (event.key === 'Escape' && root.querySelector('[data-confirm-cancel]')) {
        event.preventDefault(); event.stopPropagation();
        content.innerHTML = detailHTML(data); root.querySelector('[data-task-command="cancel"]').focus();
      }
    });
    root.addEventListener('dubaiio:page-restored', () => load());
    load(context.focusState === true, context.focusState ? 'Task details updated.' : '');
  },
});

export function openTask(id) { openPage('tasks.detail', { id }); }

registerPage('tasks.review-change', {
  title:'Review task change', source:'Your task · nothing applied yet',
  render:()=>'<p role="status">Preparing the before and after…</p>',
  mount(root,context) {
    let proposal,attempt,busy=false;
    const names={outcome:'Title',next_step:'Next step',details:'Details',due_at:'Due · Dubai time'};
    const display=(field,value)=>value?(field==='due_at'?date(value)+' · Dubai time':value):'Not set';
    request('/api/tasks/'+encodeURIComponent(context.id)+'/prepare-change',{expected_revision:context.expected_revision,changes:context.changes}).then(data=>{
      if(!root.isConnected)return; proposal=data;
      root.innerHTML=Object.keys(data.changes).map(field=>`<section class="task-next"><span>${names[field]}</span><p>Current: ${esc(display(field,data.before[field]))}</p><p>Proposed: ${esc(display(field,data.after[field]))}</p></section>`).join('')+'<p class="task-boundary">This changes your saved task only. The linked request, order and shared details stay as they are.</p><p role="alert" data-task-error hidden></p><button class="btn primary wide" data-apply-task-change>Apply task changes</button><button class="btn wide" data-leave-task-change>Not now</button>';
    }).catch(error=>{if(root.isConnected)root.innerHTML='<p role="alert">'+esc(error.message)+'</p><button class="btn wide" data-leave-task-change>Open latest task</button>';});
    root.addEventListener('click',async event=>{
      if(busy)return;
      if(event.target.closest('[data-leave-task-change]'))return openPage('tasks.detail',{id:context.id},{replace:true});
      if(!proposal||!event.target.closest('[data-apply-task-change]'))return;
      attempt||={kind:'edit',changes:proposal.changes,expected_revision:proposal.expected_revision,command_key:key()};
      busy=true;root.querySelectorAll('button').forEach(button=>button.disabled=true);
      try {
        await request('/api/tasks/'+encodeURIComponent(context.id)+'/commands',attempt);changed();
        if(live(root))openPage('tasks.detail',{id:context.id,focusState:true},{replace:true});
      } catch(error) {
        if(!live(root))return;
        errorLine(root,error.status?error.message:'The save could not be confirmed. Retry the same change, or open the latest task to check.');
        if(error.status){proposal=null;root.querySelector('[data-apply-task-change]').hidden=true;root.querySelector('[data-leave-task-change]').textContent='Open latest task';}
        else root.querySelector('[data-apply-task-change]').textContent='Retry same changes';
      } finally {busy=false;if(root.isConnected)root.querySelectorAll('button').forEach(button=>button.disabled=false);}
    });
  },
});

export function reviewTaskChange(proposal) {
  openPage('tasks.review-change',{id:proposal.task_id,expected_revision:proposal.expected_revision,changes:proposal.changes});
}

export async function trackReport(report) {
  const fields = { description: { value: report.description, provenance: 'user_supplied' } };
  for (const field of report.fields || []) if (field.provenance === 'user_supplied' && field.value) fields[field.key] = { value: field.value, provenance: 'user_supplied' };
  const result = await request('/api/tasks/from-report', { fields });
  changed(); openTask(result.task.id); return result.task;
}

// Duet-style brief: one sentence that splits moving work from what needs you,
// then one line per item. Built only from /api/today; no model text, no status change.
export async function briefHTML() {
  const data = await request('/api/today'), n = data.counts;
  const line = (task, ask, attr) => `<li><button class="brief-line" ${attr}><span class="brief-chip">${esc(task.outcome)}</span> ${esc(ask)}</button></li>`;
  const needs = data.needs_you.tasks.map(t => line(t, t.decision.title + '.', `data-open-decision="${esc(t.decision.action_id)}"`));
  const moving = data.running.tasks.map(t => line(t, statusLabel(t.source_status) + '.', `data-chat-task="${esc(t.id)}"`));
  const list = data.on_list.tasks.map(t => line(t, t.due_at ? 'Due ' + date(t.due_at) + '.' : 'On your list.', `data-chat-task="${esc(t.id)}"`));
  const parts = [n.running && `${n.running} moving`, n.needs_you && `${n.needs_you} ${n.needs_you === 1 ? 'needs' : 'need'} you`].filter(Boolean);
  const head = parts.length ? parts.join(' and ') + '.' : 'Nothing is moving or waiting on you.';
  const rows = [...needs, ...moving, ...list];
  return `<p class="brief-label">${svg('check', 'ic xs')} Your brief · ${esc(new Date(data.as_of).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Dubai' }))}</p><p>${esc(head)}</p>${rows.length ? `<ul class="brief">${rows.join('')}</ul>` : '<p>Your list is empty. Start a task from Services when you need something.</p>'}${data.on_list.has_more ? '<button class="btn sm" data-chat-task-list>All tasks</button>' : ''}`;
}

// Not now on a decision: keep the source on Today's Needs you without approving it.
export async function keepForLater(actionId) {
  const result = await request('/api/tasks/from-action', { action_id: actionId });
  changed(); return result.task;
}

// Source IDs are resolved by the owner on the server. Repeated taps reopen the
// same task, including after an ambiguous response; no action is dispatched.
document.addEventListener('click', async event => {
  const source = event.target.closest('[data-track-action]');
  if (source && !source.disabled) {
    source.disabled = true;
    try { const result = await request('/api/tasks/from-action', { action_id: source.dataset.trackAction }); changed(); openTask(result.task.id); }
    catch (error) { toast(error.message); }
    finally { if (source.isConnected) source.disabled = false; }
  }
  const decision = event.target.closest('[data-open-decision]');
  if (decision) { openPage('service.action', { id: decision.dataset.openDecision }); return; }
  const task = event.target.closest('[data-chat-task]');
  if (task) openTask(task.dataset.chatTask);
  if (event.target.closest('[data-chat-task-list]')) openPage('tasks.list');
});

// A row in Needs you opens the linked source, where the shared decision card lives.
const decisionRow = task => `<button class="task-row has-decision" data-open-decision="${esc(task.decision.action_id)}"><span class="task-row-icon">${svg('orb', 'ic sm')}</span><span class="task-row-copy"><b>${esc(task.outcome)}</b><span class="decision-ask">${esc(task.decision.title)}</span><small>${esc(task.decision.detail)}</small></span>${svg('chev', 'ic sm')}</button>`;

export function createToday(root, startNewTask) {
  let generation = 0, visible = false, summaryGeneration = 0, historyRows = [], nextOffset = null, historyBusy = false;
  const historyObserver = new IntersectionObserver(entries => { if (visible && entries.some(entry => entry.isIntersecting)) loadMoreHistory(); }, { root: root.closest('.home-feed'), rootMargin: '160px' });
  function historyEnd() { dispatchEvent(new CustomEvent('dubaiio:task-history-end', { detail: { exhausted: nextOffset === null } })); }
  function announceSummary(data) { window.dispatchEvent(new CustomEvent('dubaiio:today-summary', { detail: data ? { counts: data.counts, as_of: data.as_of, current_work: data.current_work || [] } : null })); }
  function renderHistory() {
    const host = root.querySelector('[data-task-history]'); if (!host) return;
    const focused = host.contains(document.activeElement) && document.activeElement.closest('[data-open-task]')?.dataset.openTask;
    host.innerHTML = `<header><h2>Task history</h2></header>${historyRows.length ? historyRows.map(row).join('') : '<p class="today-quiet">Your task history will appear here.</p>'}
      ${nextOffset !== null ? '<button class="btn wide" data-more-history>More tasks</button>' : '<p class="today-quiet">You’re up to date.</p>'}<p class="today-refresh-error" data-history-error role="alert" hidden></p>`;
    historyObserver.disconnect();
    const more = host.querySelector('[data-more-history]'); if (more) historyObserver.observe(more);
    if (focused) host.querySelector(`[data-open-task="${CSS.escape(focused)}"]`)?.focus({ preventScroll: true });
    historyEnd();
  }
  async function loadMoreHistory() {
    if (!visible || nextOffset === null || historyBusy) return;
    const mine = generation, offset = nextOffset; historyBusy = true;
    const more = root.querySelector('[data-more-history]'); if (more) { more.disabled = true; more.textContent = 'Loading tasks…'; }
    try {
      const data = await request('/api/tasks?limit=30&offset=' + offset);
      if (mine !== generation || !visible) return;
      const known = new Set(historyRows.map(task => task.id));
      historyRows.push(...data.tasks.filter(task => !known.has(task.id))); nextOffset = data.next_offset; renderHistory();
    } catch {
      if (mine !== generation || !visible) return;
      historyObserver.disconnect(); const error = root.querySelector('[data-history-error]');
      if (error) { error.hidden = false; error.textContent = 'More tasks could not load. Try again before continuing to news.'; }
      if (more?.isConnected) { more.disabled = false; more.textContent = 'Try loading more tasks'; }
    } finally { if (mine === generation) historyBusy = false; }
  }
  async function refreshSummary() {
    const mine = ++summaryGeneration;
    try { const data = await request('/api/today'); if (mine === summaryGeneration) announceSummary(data); }
    catch { if (mine === summaryGeneration) announceSummary(null); }
  }
  async function refresh() {
    if (!visible || !root.isConnected) return;
    const mine = ++generation;
    const cached = !!root.querySelector('.today-header');
    if (!cached) root.innerHTML = '<p class="today-loading" role="status">Loading your day…</p>';
    root.setAttribute('aria-busy', 'true');
    try {
      const retainedCount = historyRows.length;
      const readHistory = async () => {
        let offset = 0, result = {tasks: [], next_offset: null};
        do {
          const page = await request('/api/tasks?limit=30&offset=' + offset);
          result.tasks.push(...page.tasks); result.next_offset = page.next_offset; offset = page.next_offset;
        } while (offset !== null && result.tasks.length < retainedCount && mine === generation && visible);
        return result;
      };
      const [data, history] = await Promise.all([request('/api/today'), readHistory()]);
      if (mine !== generation || !visible || !root.isConnected) return;
      ++summaryGeneration; announceSummary(data);
      const focus = root.contains(document.activeElement) ? document.activeElement.closest('button') : null;
      const attr = focus && ['data-open-decision','data-open-task','data-create-task','data-all-tasks','data-refresh-today','data-start-new-task'].find(name => focus.hasAttribute(name));
      const selector = attr ? `[${attr}="${CSS.escape(focus.getAttribute(attr))}"]` : null;
      const scroll = root.closest('.home-feed'), scrollTop = scroll?.scrollTop || 0;
      const pausedOpen = root.querySelector('.today-paused')?.open;
      const day = new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dubai', weekday: 'long', day: 'numeric', month: 'long' }).format(new Date());
      historyRows = history.tasks; nextOffset = history.next_offset; historyBusy = false;
      root.innerHTML = `<header class="today-header"><p>${esc(day)} · Dubai</p><div><h1>Tasks</h1><button class="today-all" data-all-tasks>History ${svg('chev', 'ic xs')}</button></div></header>
        ${data.needs_you.tasks.length ? `<section class="today-lane"><header><h2>Needs you</h2>${data.needs_you.has_more ? '<button data-all-tasks>See all</button>' : ''}</header>${data.needs_you.tasks.map(decisionRow).join('')}</section>` : ''}
        <section class="today-lane"><header><h2>Running</h2></header>${data.running.tasks.length ? data.running.tasks.map(task => row({...task, source_status: task.source_status})).join('') : '<p class="today-quiet">No tasks are in progress.</p>'}</section>
        <section class="today-lane"><header><h2>Scheduled</h2></header><p class="today-quiet">No scheduled follow-ups. Automatic check-backs are coming next.</p></section>
        <section class="today-lane"><header><h2>On your list</h2>${data.on_list.has_more ? '<button data-all-tasks>See all</button>' : ''}</header>${data.on_list.tasks.length ? data.on_list.tasks.map(row).join('') : '<p class="today-quiet">Nothing to keep track of yet. Add something when you need it.</p>'}</section>
        ${data.paused.count ? `<details class="today-paused"><summary>Paused (${data.paused.count})</summary>${data.paused.tasks.map(row).join('')}${data.paused.has_more ? '<button class="btn wide" data-all-tasks>All paused tasks</button>' : ''}</details>` : ''}
        <section class="today-lane today-completed"><header><h2>Finished</h2>${data.completed.has_more ? '<button data-all-tasks>See all</button>' : ''}</header>${data.completed.tasks.length ? data.completed.tasks.map(row).join('') : '<p class="today-quiet">Completed tasks will stay here.</p>'}</section>
        <button class="today-new-task" data-start-new-task>Start a new task ${svg('arrow', 'ic sm')}</button>
        <button class="today-note" data-create-task>Or keep a note on your list</button>
        <section class="today-lane task-history" data-task-history tabindex="-1"></section>
        <p class="today-refresh-error" role="alert" hidden></p><footer class="today-footer"><span>Updates stay with your tasks.</span><button aria-label="Refresh Today" data-refresh-today>Refresh</button></footer>`;
      renderHistory();
      if (pausedOpen && root.querySelector('.today-paused')) root.querySelector('.today-paused').open = true;
      if (scroll) scroll.scrollTop = scrollTop;
      if (selector) root.querySelector(selector)?.focus({ preventScroll: true });
    } catch {
      if (mine === generation && visible && root.isConnected) {
        const error = root.querySelector('.today-refresh-error');
        if (cached && error) { error.hidden = false; error.textContent = 'The latest update could not load. Showing the previous view; try Refresh again.'; }
        else root.innerHTML = '<div class="today-unavailable"><span class="today-create-icon">' + svg('clock') + '</span><h1>Today is unavailable.</h1><p role="alert">Reconnect and try again to see your latest tasks.</p><button class="btn primary" data-refresh-today>Try again</button></div>';
      }
    } finally {
      if (mine === generation) root.removeAttribute('aria-busy');
    }
  }
  changed = () => { if (visible && root.isConnected) refresh(); else refreshSummary(); window.dispatchEvent(new CustomEvent('dubaiio:tasks-changed')); };
  wireRows(root);
  root.addEventListener('click', event => {
    if (event.target.closest('[data-create-task]')) openPage('tasks.new');
    if (event.target.closest('[data-all-tasks]')) { const history = root.querySelector('[data-task-history]'); history?.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth', block: 'start' }); history?.focus({ preventScroll: true }); }
    if (event.target.closest('[data-more-history]')) loadMoreHistory();
    if (event.target.closest('[data-refresh-today]')) refresh();
    if (event.target.closest('[data-start-new-task]')) startNewTask();
  });
  const controller = { show(value) { const was = visible; visible = value; root.hidden = !value; root.inert = !value; if (value && !was) refresh(); if (!value) { generation++; historyBusy = false; historyObserver.disconnect(); } }, refresh, refreshSummary,
    open() {
      controller.show(true);
      root.closest('.home-feed').scrollTo({ top: root.offsetTop, behavior: reduced ? 'instant' : 'smooth' });
      root.focus({ preventScroll: true });
    } };
  return controller;
}
