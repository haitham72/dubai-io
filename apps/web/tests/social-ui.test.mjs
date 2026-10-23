import assert from 'node:assert/strict';
globalThis.matchMedia = () => ({ matches: false });
globalThis.document = { addEventListener() {} };
const { commentTree, avatar, socialRequest, generationText, filterCallPeople } = await import('../social-ui.js');
const comments = [
  { id: 'child', parent_id: 'root', author: { name: 'Kid' }, text: 'nested' },
  { id: 'root', author: { name: 'Parent' }, text: '<script>unsafe</script>' },
  { id: 'orphan', parent_id: 'gone', author: { name: 'Other' }, text: 'orphan' },
  { id: 'a', parent_id: 'b', author: { name: 'A' }, text: 'cycle' },
  { id: 'b', parent_id: 'a', author: { name: 'B' }, text: 'cycle' },
];
const html = commentTree(comments);
assert.ok(html.indexOf('data-comment-id="root"') < html.indexOf('data-comment-id="child"'));
for (const m of comments) assert.equal(html.split(`data-comment-id="${m.id}"`).length - 1, 1);
assert.ok(!html.includes('<script>'));
assert.ok(!avatar({ avatar: 'javascript:alert(1)', name: 'A' }).includes('<img'));
const request = socialRequest();
const first = JSON.parse(request({ text: 'hello' }).body).request_id;
assert.equal(first, JSON.parse(request({ text: 'hello' }).body).request_id);
request.reset();
assert.notEqual(first, JSON.parse(request({ text: 'hello' }).body).request_id);
assert.match(generationText({ generation: { status: 'failed' } }), /unavailable/);
console.log('Social UI: nesting, malformed trees, escaping, retries and failure status passed');

const people = [{ id: 'one', name: 'Amina', phone: '+97150123' }, { id: 'two', name: 'Omar', phone: '+97150456' }];
assert.equal(filterCallPeople(people, ' AMINA ')[0].id, 'one');
assert.equal(filterCallPeople(people, '456')[0].id, 'two');
assert.deepEqual(filterCallPeople(people, 'Amina', new Set(['two'])), []);
assert.equal(filterCallPeople(people, '', new Set(['two'])).length, 1);
console.log('Calls search by name/number and favorites intersection passed');

const { voteBox } = await import('../social-ui.js');
const box = voteBox('p1', 'post', 12, 1);
assert.ok(box.includes('data-votes="p1"') && box.includes('data-kind="post"'));
assert.ok(box.includes('<b>12</b>') && box.includes('data-mine="1"'));
assert.ok(box.includes('data-vote="1"') && box.includes('data-vote="-1"'));
const heated = commentTree([{ id: 'h', author: { name: 'X' }, text: 'rawr', analysis: { harsh: true } }]);
assert.ok(heated.includes('pill warn') && heated.includes('data-votes="h"'));
console.log('Votes and heated badge passed');
