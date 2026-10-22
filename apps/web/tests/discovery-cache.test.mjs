import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createDiscoveryCache } from '../discovery-cache.js';

const deferred = () => { let resolve; const promise = new Promise(r => resolve = r); return { promise, resolve }; };
test('snapshots remain stable until deliberate refresh', async () => {
  let calls = 0;
  const cache = createDiscoveryCache(() => ({ places: ['place-' + ++calls] }));
  await cache.refresh('food', {});
  assert.equal(await cache.refresh('food', {}), false);
  assert.deepEqual(cache.get('food').places, ['place-1']);
  await cache.refresh('food', {}, true);
  assert.deepEqual(cache.get('food').places, ['place-2']);
});

test('a correction invalidates saved and in-flight place explanations', async () => {
  const pending = deferred();
  const cache = createDiscoveryCache(() => pending.promise);
  const loaded = cache.refresh('food', {});
  cache.pause();
  assert.equal(cache.get('food'), undefined);
  assert.equal(await cache.refresh('food', {}), false);
  cache.resume();
  pending.resolve({ places: ['stale seafood reason'] });
  assert.equal(await loaded, false);
  assert.equal(cache.get('food'), undefined);
});

test('an older request cannot overwrite a newer refresh of the same context', async () => {
  const old = deferred();
  let calls = 0;
  const cache = createDiscoveryCache(() => ++calls === 1 ? old.promise : { places: ['fresh'] });
  const pending = cache.refresh('food', {});
  await cache.refresh('food', {}, true);
  old.resolve({ places: ['old'] });
  assert.equal(await pending, false);
  assert.deepEqual(cache.get('food').places, ['fresh']);
});

test('failures remain retryable and overlapping corrections stay paused', async () => {
  let fail = true;
  const cache = createDiscoveryCache(() => { if (fail) throw Error('offline'); return { places: [] }; });
  await cache.refresh('food', {});
  assert.equal(cache.get('food').status, 'error');
  cache.pause(); cache.pause(); cache.resume();
  assert.equal(await cache.refresh('food', {}, true), false);
  cache.resume(); fail = false;
  await cache.refresh('food', {}, true);
  assert.equal(cache.get('food').status, 'ok');
});

test('only a bounded number of transient listing snapshots is retained', async () => {
  const cache = createDiscoveryCache(() => ({ places: [] }));
  for (let i=0; i<17; i++) await cache.refresh('context-'+i, {});
  assert.equal(cache.get('context-0'), undefined);
  assert.equal(cache.get('context-16').status, 'ok');
});
