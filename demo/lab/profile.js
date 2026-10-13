// Temporal profile math (ARCHITECTURE.md §12.3), the JS twin of the future
// Python profiler. Both must pass fixtures/profile-vectors.json.
//
// Each hypothesis is a Beta(alpha, beta) belief. Between pieces of evidence,
// alpha and beta decay toward the prior with the facet's half-life, so old
// evidence fades. Confidence = alpha / (alpha + beta).

export const PRIOR = 1;
export const SURFACE_CONF = 0.7;   // in-context "I noticed" chip threshold
export const SURFACE_MIN_EVIDENCE = 2;
const DAY = 86400000;

export function decay(value, days, halfLifeDays) {
  if (days <= 0) return value;
  return PRIOR + (value - PRIOR) * Math.pow(0.5, days / halfLifeDays);
}

export function confidence(alpha, beta) {
  return alpha / (alpha + beta);
}

// Replays one hypothesis' evidence up to asOf (ms). Pure.
export function belief(evidence, asOf, halfLifeDays) {
  let alpha = PRIOR, beta = PRIOR, last = null, n = 0;
  for (const e of evidence) {
    if (e.t > asOf) break;
    if (last !== null) {
      const d = (e.t - last) / DAY;
      alpha = decay(alpha, d, halfLifeDays);
      beta = decay(beta, d, halfLifeDays);
    }
    if (e.w >= 0) alpha += e.w; else beta += -e.w;
    last = e.t; n += 1;
  }
  if (last !== null) {
    const d = (asOf - last) / DAY;
    alpha = decay(alpha, d, halfLifeDays);
    beta = decay(beta, d, halfLifeDays);
  }
  return { alpha, beta, conf: confidence(alpha, beta), n, last };
}

// overrides: { [hypId]: 'confirmed' | 'rejected' | 'forgotten' }
export function profileAt(episodes, hypotheses, asOf, overrides = {}) {
  const eps = episodes
    .map(e => ({ ...e, t: Date.parse(e.at) }))
    .filter(e => e.t <= asOf)
    .sort((a, b) => a.t - b.t);

  // Told facts: latest value per key wins; earlier values become "Changed".
  const told = new Map();
  const changed = [];
  for (const e of eps) {
    if (e.kind !== 'told') continue;
    const prev = told.get(e.key);
    if (prev && prev.value !== e.value) {
      changed.push({ key: e.key, from: prev.value, to: e.value, at: e.at });
    }
    told.set(e.key, { key: e.key, value: e.value, at: e.at, provenance: 'user_supplied' });
  }

  const noticed = [];
  const confirmed = [];
  for (const h of hypotheses) {
    const status = overrides[h.id];
    if (status === 'forgotten') continue;
    const evidence = eps
      .flatMap(e => (e.ev || []).filter(x => x.h === h.id).map(x => ({ t: e.t, w: x.w, text: e.text, at: e.at })));
    if (!evidence.length) continue;
    const b = belief(evidence, asOf, h.halfLifeDays);
    const item = {
      ...h, ...b, evidence,
      provenance: status === 'confirmed' ? 'user_supplied' : 'inferred',
      surfaced: b.conf >= SURFACE_CONF && b.n >= SURFACE_MIN_EVIDENCE,
    };
    if (status === 'confirmed') confirmed.push(item);
    else if (status === 'rejected') changed.push({ key: h.id, label: h.label, rejected: true, at: null });
    else noticed.push(item);
  }
  noticed.sort((a, b) => b.conf - a.conf);
  return { told: [...told.values()], confirmed, noticed, changed };
}

// Tier rule (ARCHITECTURE.md §12.1): may this item be used for `use`?
// use: 'rerank' | 'prefill' | 'approval' | 'proactive' | 'status'
export function allowed(item, use) {
  const told = item.provenance === 'user_supplied';
  if (use === 'status') return false;
  if (use === 'rerank') return true;
  return told; // prefill, approval, proactive need a told/confirmed fact
}
