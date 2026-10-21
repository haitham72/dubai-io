import { api } from './service-workflow.js';
import { esc } from './ui.js';
import { createRecommendationCache } from './recommendation-cache.js';

// One browsing visit, independent of chat threads. No external Google profile.
let visit;
try {
  const previous = JSON.parse(sessionStorage.getItem('dubaiio.visit') || 'null');
  visit = previous && Date.now() - previous.at < 86400000 ? previous : { id: crypto.randomUUID(), at: Date.now() };
  sessionStorage.setItem('dubaiio.visit', JSON.stringify(visit));
} catch { visit = { id: crypto.randomUUID() }; }
export const browsingSession = () => visit.id;
export const topicFor = (cat, sub) => ({ food: sub === 'Seafood' ? 'food.seafood' : 'food.restaurants', coffee: 'food.cafes',
  pets: sub === 'Grooming' ? 'pets.grooming' : sub === 'Boarding' ? 'pets.boarding' : 'pets.care',
  laundry: 'services.laundry', 'home-help': 'services.cleaning', 'fix-it': 'services.repairs', clothing: 'shopping.clothing' })[cat] || null;

const CASE_TOPICS = { C1: ['services.cleaning'], C13: ['food.restaurants', 'food.seafood'], C12: ['pets.care','pets.grooming','pets.boarding'],
  C4: ['services.laundry'], C8: ['services.repairs'], C2: ['shopping.clothing'], C11: ['food.cafes'] };
const homeRanks = createRecommendationCache(body => api('/api/recommendations', { method: 'POST', body: JSON.stringify(body) }));
export const homeRank = id => homeRanks.get(id);
export async function refreshRecommendations(cases) {
  const candidates = cases.filter(c => CASE_TOPICS[c.id]).map(c => ({ id: c.id, topics: CASE_TOPICS[c.id] }));
  await homeRanks.refresh({ session_id: visit.id, surface: 'home', candidates });
}
export async function observe(kind, topic, entityId) {
  if (!topic) return;
  try {
    await api('/api/recommendation-events', { method: 'POST', body: JSON.stringify({ events: [{
      event_key: crypto.randomUUID(), session_id: visit.id, kind, topic, entity_id: entityId,
    }] }) });
    return true;
  } catch { return false; }
}

const dateLabel = value => new Date(value).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
const evidenceLabels = { category: 'Explored this category', detail: 'Opened an option', choose: 'Chose an option', save: 'Saved an option', less_like_this: 'Asked for fewer like this' };
function evidenceHTML(e) {
  const placeId = e.entity_id?.startsWith('g:') ? e.entity_id.slice(2) : null;
  // Maps URLs resolve a permitted place ID without storing a listing snapshot:
  // https://developers.google.com/maps/documentation/urls/get-started#search-action
  const link = placeId && /^[A-Za-z0-9_-]+$/.test(placeId) ? ' <a href="https://www.google.com/maps/search/?api=1&amp;query=Place&amp;query_place_id=' + encodeURIComponent(placeId) + '" target="_blank" rel="noopener noreferrer">View place in Google Maps</a>' : '';
  return '<li>' + esc(evidenceLabels[e.kind] || 'Explored an option') + ' · <time datetime="' + esc(e.at) + '">' + esc(dateLabel(e.at)) + '</time>' + link + '</li>';
}
function scopeHTML(row) {
  const session = row.scope === 'session';
  const state = row.learning_state === 'ready' ? 'Can influence suggestions' : row.learning_state === 'confirmed' ? 'You confirmed' : row.learning_state === 'paused' ? 'Learning paused' : 'Still learning';
  return '<div class="interest-scope"><b>' + (session ? 'This visit' : 'Across visits') + '</b><span class="src">' + esc(state) +
    (row.status === 'active' ? ' · ' + Math.round(row.confidence * 100) + '% inferred confidence · ' + row.evidence_count + ' distinct options' : '') + '</span>' +
    (row.status === 'active' ? '<small>Fades with a ' + (session ? '30-minute' : '30-day') + ' half-life. Expires ' + esc(dateLabel(row.expires_at)) + '.</small>' : '') +
    (row.evidence?.length ? '<details><summary>Recent evidence</summary><ul class="interest-evidence">' + row.evidence.map(evidenceHTML).join('') + '</ul></details>' : '') + '</div>';
}
const buttonsHTML = row => ['rejected','forgotten'].includes(row.status)
  ? '<button data-interest="' + esc(row.topic) + '" data-control="resume">Resume learning</button>'
  : ['confirm','edit','reject','forget'].map((action,n) => '<button data-interest="' + esc(row.topic) + '" data-control="' + action + '">' + ['Confirm','Edit','Not true','Forget'][n] + '</button>').join('');

export async function renderInterests(el, onChange) {
  if (!el) return;
  const renderId = crypto.randomUUID();
  el.dataset.interestRender = renderId;
  el.innerHTML = '<p>Loading your live interests…</p>';
  try {
    const data = await api('/api/profile/interests?session_id=' + encodeURIComponent(visit.id));
    if (!el.isConnected || el.dataset.interestRender !== renderId) return;
    const rows = data.interests.filter(i => i.scope === 'long_term');
    el.innerHTML = '<h4>Live interests</h4><p class="fine">From your choices, separate from the timeline below. Inferences only reorder suggestions. Edit explicitly confirms your replacement; old evidence is removed. Forgotten interests stay paused until you resume learning.</p><ul class="list">' +
      (rows.map(i => '<li class="fact interest" data-interest-row="' + esc(i.topic) + '"><h5>' + esc(i.label) + '</h5><span class="src">' +
        (i.status === 'confirmed' ? 'You confirmed this preference' : i.status === 'active' ? 'I noticed · inferred from your choices' : esc(i.status) + ' · learning paused') + '</span>' +
        (data.interests.find(s => s.scope === 'session' && s.topic === i.topic) ? scopeHTML(data.interests.find(s => s.scope === 'session' && s.topic === i.topic)) : '') + scopeHTML(i) +
        '<div class="acts">' + buttonsHTML(i) + '</div><div data-edit-interest></div><p class="interest-error" role="alert"></p></li>').join('') || '<li>No interests learned yet. Explore a few places to start.</li>') + '</ul>';
    async function save(topic, body, row) {
      homeRanks.pause();
      onChange?.({ refresh: false });
      row.querySelectorAll('button,select').forEach(control => control.disabled = true);
      row.querySelector('.interest-error').textContent = '';
      let saved = false;
      try {
        await api('/api/profile/interests/' + encodeURIComponent(topic), { method: 'PUT', body: JSON.stringify(body) });
        saved = true;
      } catch {
        if (el.dataset.interestRender === renderId) {
          row.querySelectorAll('button,select').forEach(control => control.disabled = false);
          row.querySelector('.interest-error').textContent = 'Could not verify the change. Try again or reopen to check its status.';
        }
      } finally {
        homeRanks.resume();
      }
      if (saved) {
        onChange?.({ refresh: true });
        await renderInterests(el, onChange);
      }
    }
    el.querySelectorAll('[data-interest]').forEach(button => button.addEventListener('click', async () => {
      const topic = button.dataset.interest, row = button.closest('[data-interest-row]');
      if (button.dataset.control !== 'edit') { await save(topic, { action: button.dataset.control }, row); return; }
      const host = row.querySelector('[data-edit-interest]');
      host.innerHTML = '<form class="interest-editor"><label>Replace with<select aria-label="Replacement interest">' + Object.entries(data.topics).filter(([key]) => key !== topic).map(([key,label]) => '<option value="' + esc(key) + '">' + esc(label) + '</option>').join('') + '</select></label><p class="fine">Save confirms your selection and removes the old evidence.</p><div class="acts"><button type="submit">Save interest</button><button type="button" data-cancel-edit>Cancel</button></div></form>';
      host.querySelector('select').focus();
      host.querySelector('[data-cancel-edit]').addEventListener('click', () => { host.innerHTML = ''; button.focus(); });
      host.querySelector('form').addEventListener('submit', async e => { e.preventDefault(); await save(topic, { action: 'edit', replacement_topic: host.querySelector('select').value }, row); });
    }));
  } catch { if (el.isConnected && el.dataset.interestRender === renderId) el.textContent = 'Live interests are unavailable. Try opening this screen again.'; }
}
