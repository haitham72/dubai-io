// Live profile inputs: episodes from what the user did on this device, plus persisted
// Confirm / Not true / Forget. Beliefs are computed by profile.js (same math as the tests).
// Fixture history stays visibly labelled as demo data and is never sent to the server.
import { EPISODES } from './data.js';
import { api } from './service-workflow.js';

let live = [], overrides = {};

export async function loadProfile() {
  try { const p = await api('/api/profile'); live = p.episodes; overrides = p.overrides || {}; } catch { /* offline: fixture only */ }
  return overrides;
}

export function profileEpisodes() {
  return [...EPISODES.map(e => ({ ...e, text: e.text + ' · demo history' })), ...live.map(e => ({ ...e, text: e.text + ' · on this device' }))];
}


export async function setOverride(h, status) {
  await api('/api/profile/overrides/' + encodeURIComponent(h), { method: 'PUT', body: JSON.stringify({ status }) });
  overrides[h] = status;
  if (status === 'forgotten') live = live.map(e => ({ ...e, ev: (e.ev || []).filter(x => x.h !== h) })).filter(e => e.ev.length);
}

// One observation; the server allowlists hypotheses and weights and drops duplicates.
export async function recordEpisode(kind, text, ev, dedupeKey) {
  try {
    const r = await api('/api/profile/episodes', { method: 'POST', body: JSON.stringify({ kind, text, ev, dedupe_key: dedupeKey }) });
    if (r.recorded) live.push({ at: new Date().toISOString(), kind, text, ev, source: 'this_device' });
  } catch { /* the profile is optional; the action already succeeded */ }
}
