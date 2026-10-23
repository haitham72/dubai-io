import assert from 'node:assert/strict';
globalThis.matchMedia = () => ({ matches: false });
globalThis.document = { addEventListener() {} };
const { callRequest } = await import('../social-ui.js');

// Contact call: logs by contact id through POST /api/calls (server resolves the number).
const [path, init] = callRequest({ contactId: 'c1' });
assert.equal(path, '/api/calls');
assert.equal(init.method, 'POST');
assert.deepEqual(JSON.parse(init.body), { contact_id: 'c1' });

// Keypad call: the dialed number is logged through the same endpoint, formatting stripped.
const [kpath, kinit] = callRequest({ number: '+971 (50) 123-4567' });
assert.equal(kpath, '/api/calls');
assert.equal(kinit.method, 'POST');
const kbody = JSON.parse(kinit.body);
assert.equal(kbody.phone, '+971501234567');
assert.equal(kbody.contact_id, undefined);

// A contact id wins over a stray number.
assert.deepEqual(Object.keys(JSON.parse(callRequest({ contactId: 'c1', number: '123' })[1].body)), ['contact_id']);
// Failure path: empty input sends an empty phone; the server rejects it (422) and no tel: URL is built client-side.
assert.equal(JSON.parse(callRequest({})[1].body).phone, '');
console.log('Calls UI: keypad and contact calls both POST /api/calls');
