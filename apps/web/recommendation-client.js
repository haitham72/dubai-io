import { api } from './service-workflow.js';
import { esc } from './ui.js';

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
let homeRanks = new Map(), refreshEpoch = 0;
export const homeRank = id => homeRanks.get(id);
export async function refreshRecommendations(cases) {
  const epoch = ++refreshEpoch;
  const candidates = cases.filter(c => CASE_TOPICS[c.id]).map(c => ({ id: c.id, topics: CASE_TOPICS[c.id] }));
  try {
    const data = await api('/api/recommendations', { method: 'POST', body: JSON.stringify({ session_id: visit.id, surface: 'home', candidates }) });
    if (epoch === refreshEpoch) homeRanks = new Map(data.results.map(r => [r.id, r]));
  } catch { /* Discovery remains usable when the optional recommender is unavailable. */ }
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

export async function renderInterests(el, onChange) {
  if (!el) return;
  el.innerHTML = '<p>Loading your live interests…</p>';
  try {
    const data = await api('/api/profile/interests?session_id=' + encodeURIComponent(visit.id));
    if (!el.isConnected) return;
    const rows = data.interests.filter(i => i.scope === 'long_term');
    el.innerHTML = '<h4>Live interests</h4><p class="fine">From your choices, separate from the timeline below. Inferences only reorder suggestions. Forgotten interests stay paused until you resume learning.</p><ul class="list">' +
      (rows.map(i => '<li class="fact"><div><b>' + esc(i.label) + '</b><span class="src">' +
        (i.status === 'confirmed' ? 'You confirmed' : i.status === 'active' ? 'I noticed · ' + i.evidence_count + ' distinct choices · inferred' : esc(i.status)) +
        '</span></div><div class="acts">' + (['rejected','forgotten'].includes(i.status) ? '<button data-interest="' + esc(i.topic) + '" data-control="resume">Resume learning</button>' :
          ['confirm','reject','forget'].map((a,n) => '<button data-interest="' + esc(i.topic) + '" data-control="' + a + '">' + ['Confirm','Not true','Forget'][n] + '</button>').join('')) + '</div></li>').join('') || '<li>No interests learned yet. Explore a few places to start.</li>') + '</ul>';
    el.querySelectorAll('[data-interest]').forEach(button => button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await api('/api/profile/interests/' + encodeURIComponent(button.dataset.interest), { method: 'PUT', body: JSON.stringify({ action: button.dataset.control }) });
        homeRanks.clear(); onChange?.(); await renderInterests(el, onChange);
      } catch { button.disabled = false; button.textContent = 'Try again'; }
    }));
  } catch { if (el.isConnected) el.textContent = 'Live interests are unavailable. Try opening this screen again.'; }
}
