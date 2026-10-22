import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createBrowsingVisit } from '../browsing-visit.js';

test('visits stay stable while active and rotate after idle time in an open tab', () => {
  let at = 0, sequence = 0, saved;
  const storage = { getItem: () => saved, setItem: (k,v) => saved = v };
  const visit = createBrowsingVisit({ storage, now: () => at, uuid: () => 'visit-' + ++sequence });
  assert.equal(visit(), 'visit-1');
  at += 20*60*1000;
  assert.equal(visit(), 'visit-1');
  const resumed = createBrowsingVisit({ storage, now: () => at, uuid: () => 'visit-' + ++sequence });
  assert.equal(resumed(), 'visit-1');
  at += 30*60*1000;
  assert.equal(resumed(), 'visit-2');
});

test('continuous activity still rotates at the maximum visit age', () => {
  let at = 0, sequence = 0;
  // IDs generated in production are strings.
  const textVisit = createBrowsingVisit({ now: () => at, uuid: () => String(++sequence) });
  const first = textVisit();
  for (let n=1; n<72; n++) { at += 20*60*1000; assert.equal(textVisit(), first); }
  at += 20*60*1000;
  assert.notEqual(textVisit(), first);
});

test('old storage formats, blocked storage and clock reversal are safe', () => {
  let at = 100, sequence = 0;
  const storage = { getItem: () => '{"id":"old","at":100}', setItem: () => { throw new Error('blocked'); } };
  const visit = createBrowsingVisit({ storage, now: () => at, uuid: () => 'visit-' + ++sequence });
  assert.equal(visit(), 'visit-1');
  assert.equal(visit(), 'visit-1');
  at = 50;
  assert.equal(visit(), 'visit-2');
});
