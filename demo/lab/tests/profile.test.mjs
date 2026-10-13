// Run: node demo/lab/tests/profile.test.mjs
import { readFileSync } from 'node:fs';
import { decay, belief, allowed, profileAt } from '../profile.js';
import { EPISODES, HYPOTHESES } from '../data.js';

const v = JSON.parse(readFileSync(new URL('../fixtures/profile-vectors.json', import.meta.url)));
const DAY = 86400000;
let fail = 0, pass = 0;
const close = (a, b) => Math.abs(a - b) < 1e-5;
const check = (ok, msg) => { if (ok) pass++; else { fail++; console.error('FAIL', msg); } };

for (const c of v.decay) {
  const got = decay(c.value, c.days, c.half_life);
  check(close(got, c.expect), `decay ${JSON.stringify(c)} -> ${got}`);
}
for (const c of v.belief) {
  const ev = c.evidence.map(([d, w]) => ({ t: d * DAY, w }));
  const b = belief(ev, c.as_of * DAY, c.half_life);
  for (const k of ['alpha', 'beta', 'conf', 'n']) {
    check(close(b[k], c.expect[k]), `belief "${c.name}" ${k}: got ${b[k]}, want ${c.expect[k]}`);
  }
}
for (const c of v.tiers) {
  check(allowed({ provenance: c.provenance }, c.use) === c.expect, `tier ${c.provenance}/${c.use}`);
}

// Property: confidence never rises while no new evidence arrives.
const ev = [{ t: 0, w: 2 }, { t: DAY, w: 2 }];
let prev = 1;
for (let d = 1; d <= 400; d += 7) {
  const c = belief(ev, d * DAY, 90).conf;
  check(c <= prev + 1e-12, `monotonic decay at day ${d}`);
  prev = c;
}

// Property: ingesting the same episode twice is idempotent once deduped by `at`+text.
const dedup = [...new Map([...EPISODES, ...EPISODES].map(e => [e.at + e.text, e])).values()];
const asOf = Date.parse('2026-10-13T23:00:00');
check(JSON.stringify(profileAt(dedup, HYPOTHESES, asOf)) === JSON.stringify(profileAt(EPISODES, HYPOTHESES, asOf)), 'idempotent ingestion');

// Scenario: the scripted timeline surfaces exactly the expected hypotheses on 13 Oct.
const p = profileAt(EPISODES, HYPOTHESES, asOf);
const surfaced = p.noticed.filter(h => h.surfaced).map(h => h.id).sort();
check(JSON.stringify(surfaced) === JSON.stringify(['eat_out_friday', 'order_in_weeknight', 'price_unless_deadline', 'specialty_coffee']), `surfaced on 13 Oct: ${surfaced}`);
check(p.told.find(t => t.key === 'area').value === 'Dubai Marina', 'area superseded to Dubai Marina');
check(p.changed.some(c => c.from === 'JLT' && c.to === 'Dubai Marina'), 'change JLT -> Dubai Marina recorded');
check(!p.noticed.find(h => h.id === 'haircut_4w').surfaced, 'one haircut is not enough to surface the routine');

// Overrides: confirmed moves to told tier; forgotten disappears.
const o = profileAt(EPISODES, HYPOTHESES, asOf, { order_in_weeknight: 'confirmed', eat_out_friday: 'forgotten' });
check(o.confirmed[0]?.provenance === 'user_supplied' && allowed(o.confirmed[0], 'prefill'), 'confirmed becomes user_supplied');
check(!o.noticed.some(h => h.id === 'eat_out_friday') && !o.confirmed.some(h => h.id === 'eat_out_friday'), 'forgotten is gone');

console.log(`${pass} passed, ${fail} failed`);
for (const h of p.noticed) console.log(`  ${h.surfaced ? '*' : ' '} ${h.conf.toFixed(3)} n=${h.n} ${h.label}`);
process.exit(fail ? 1 : 0);
