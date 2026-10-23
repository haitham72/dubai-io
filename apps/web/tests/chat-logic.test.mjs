import assert from 'node:assert/strict';
const { recentCalls, createFavorites, resolveFavorites, swipeDecision, searchAction, filterThreads, threadFav, when, SWIPE, FAV_KEY } = await import('../chat-logic.js');

// Recent calls: merged by time desc; demo rows never produce a dial action.
const calls = [{ id: 'c1', contact_id: 'k1', name: 'Amina', phone: '+971501112222', at: '2026-10-20T10:00:00Z' }, { id: 'c2', name: 'Keypad', phone: '+971501234567', at: '2026-10-22T10:00:00Z' }];
const demo = [{ id: 'd1', name: 'Khalo', direction: 'missed', thread_id: 't9', at: '2026-10-21T10:00:00Z', phone: null }, { id: 'd2', name: 'Nobody', direction: 'incoming', thread_id: null, at: '2026-10-23T10:00:00Z', phone: '+9715000' }];
const rows = recentCalls(calls, demo);
assert.deepEqual(rows.map(r => r.key), ['demo:d2', 'call:c2', 'demo:d1', 'call:c1']);
assert.deepEqual(rows[2].action, { type: 'thread', threadId: 't9' });
assert.ok(rows[2].missed); assert.equal(rows[2].label, 'Missed');
assert.equal(rows[0].action.type, 'none', 'demo row without thread does nothing, even if a phone leaks in');
for (const r of rows.filter(x => x.kind === 'demo')) { assert.notEqual(r.action.type, 'dial'); assert.ok(!('number' in r.action) && !('contactId' in r.action)); }
assert.deepEqual(rows[3].action, { type: 'dial', contactId: 'k1' });
assert.deepEqual(rows[1].action, { type: 'dial', number: '+971501234567' });
assert.equal(rows[3].label, 'Started in Dubai-io');
assert.deepEqual(recentCalls(), []);

// Favorites store: add / remove / reorder / threads / bad storage.
const mem = () => { const m = {}; return { getItem: k => m[k] ?? null, setItem: (k, v) => { m[k] = v; }, m }; };
const st = mem(), fav = createFavorites(st);
assert.deepEqual(fav.list(), []);
fav.add('a'); fav.add('b'); fav.add(threadFav('t1')); fav.add('a');
assert.deepEqual(fav.list(), ['a', 'b', 'thread:t1']);
assert.deepEqual(fav.move('b', -1), ['b', 'a', 'thread:t1']);
assert.deepEqual(fav.move('b', -1), ['b', 'a', 'thread:t1'], 'moving the first row up is a no-op');
assert.deepEqual(fav.move('thread:t1', 1), ['b', 'a', 'thread:t1']);
assert.deepEqual(fav.remove('a'), ['b', 'thread:t1']);
assert.equal(fav.toggle('b').includes('b'), false); assert.equal(fav.toggle('b').includes('b'), true);
assert.deepEqual(JSON.parse(st.m[FAV_KEY]), ['thread:t1', 'b']);
assert.deepEqual(createFavorites({ getItem: () => '{oops', setItem() { throw new Error('quota'); } }).list(), []);
assert.doesNotThrow(() => createFavorites({ getItem: () => null, setItem() { throw new Error('quota'); } }).add('x'));
// Old format (plain contact ids) still loads.
assert.deepEqual(createFavorites({ getItem: () => '["k1"]', setItem() {} }).list(), ['k1']);
const res = resolveFavorites(['k1', 'thread:t1', 'gone', 'thread:zz'], [{ id: 'k1', name: 'Amina', phone: '1' }], [{ id: 't1', title: 'Group' }]);
assert.deepEqual(res.map(r => [r.type, r.name]), [['contact', 'Amina'], ['thread', 'Group']]);

// Swipe threshold.
assert.equal(swipeDecision(-10, 0), 'close');
assert.equal(swipeDecision(-SWIPE.reveal, 2), 'reveal');
assert.equal(swipeDecision(-(SWIPE.reveal + 20), 5), 'reveal');
assert.equal(swipeDecision(-SWIPE.full, 0), 'archive');
assert.equal(swipeDecision(30, 0), 'close', 'right swipe never archives');
assert.equal(swipeDecision(-12, 60), 'scroll', 'vertical scroll wins');

// Search: question or no match goes to Ask; a match keeps filtering.
const threads = [{ id: 't1', title: 'Dubai Foodies', last: 'Best karak?', last_author: 'Sara' }, { id: 't2', title: 'Metro', last: 'Delays on red line' }];
assert.equal(filterThreads(threads, 'sara').length, 1);
assert.equal(searchAction('metro', filterThreads(threads, 'metro')), 'none');
assert.equal(searchAction('xyz visa', filterThreads(threads, 'xyz visa')), 'ask');
assert.equal(searchAction('metro?', filterThreads(threads, 'metro?')), 'ask');
assert.equal(searchAction('  ', threads), 'none');
assert.equal(filterThreads(threads, '', new Set([threadFav('t2')])).map(t => t.id).join(), 't2');

// Timestamps.
const now = new Date(2026, 9, 23, 15, 0);
assert.equal(when(new Date(2026, 9, 23, 9, 30), now), '09:30');
assert.equal(when(new Date(2026, 9, 22, 23, 0), now), 'Yesterday');
assert.equal(when(new Date(2026, 9, 20, 8, 0), now), 'Tuesday');
assert.equal(when(new Date(2026, 8, 17, 8, 0), now), '17/09/2026');
assert.equal(when('nope', now), '');
console.log('Chat logic: recent calls, favorites store, swipe, search, timestamps passed');
