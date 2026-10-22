import test from 'node:test';
import assert from 'node:assert/strict';
import { createRecommendationCache } from '../recommendation-cache.js';

const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const result = reason => ({ results: [{ id: 'food', reason }] });

test('a corrected profile cannot be repopulated by an older response', async () => {
  const old = deferred();
  const cache = createRecommendationCache(() => old.promise);
  const pending = cache.refresh({});
  cache.invalidate();
  old.resolve(result('stale inference'));
  assert.equal(await pending, false);
  assert.equal(cache.get('food'), undefined);
});

test('newer rankings win even when the old response arrives last', async () => {
  const old = deferred(); let calls = 0;
  const cache = createRecommendationCache(() => ++calls === 1 ? old.promise : result('new explicit preference'));
  const pending = cache.refresh({});
  assert.equal(await cache.refresh({}), true);
  old.resolve(result('old inference'));
  assert.equal(await pending, false);
  assert.equal(cache.get('food').reason, 'new explicit preference');
});

test('a pending correction clears reasons and suspends concurrent ranking loads', async () => {
  let calls = 0;
  const cache = createRecommendationCache(() => { calls++; return result('old inference'); });
  await cache.refresh({});
  cache.pause();
  assert.equal(cache.get('food'), undefined);
  assert.equal(await cache.refresh({}), false);
  assert.equal(calls, 1);
  cache.resume();
  assert.equal(await cache.refresh({}), true);
});

test('a failed load after correction keeps stale reasons cleared', async () => {
  let fail = false;
  const cache = createRecommendationCache(() => { if (fail) throw new Error('offline'); return result('old inference'); });
  await cache.refresh({});
  cache.pause(); fail = true; cache.resume();
  assert.equal(await cache.refresh({}), false);
  assert.equal(cache.get('food'), undefined);
});

test('overlapping corrections stay suspended until both finish', async () => {
  const cache = createRecommendationCache(() => result('fresh preference'));
  cache.pause(); cache.pause(); cache.resume();
  assert.equal(await cache.refresh({}), false);
  cache.resume();
  assert.equal(await cache.refresh({}), true);
});
