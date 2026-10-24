import test from 'node:test';
import assert from 'node:assert/strict';
import { tripFields, prepareReport, reportText, confirmTripFields } from '../recovery-state.js';
test('cash: typed route and time are confirmed as user_supplied, other fields untouched', () => {
  const out = confirmTripFields(tripFields(), { from: ' DXB T3 ', to: 'Business Bay', when: 'Today 20:40', plate: 'ignored' });
  assert.equal(out.find(f => f.key === 'from').value, 'DXB T3');
  assert.ok(out.filter(f => ['when', 'from', 'to'].includes(f.key)).every(f => f.provenance === 'user_supplied'));
  assert.equal(out.find(f => f.key === 'plate').value, null);
});
test('not sure: "I don’t remember" leaves route and time unknown, never invented', () => {
  const out = confirmTripFields(tripFields({ trip: { from: 'DXB T3', to: 'JLT', when: 'Yesterday' } }), null);
  assert.ok(out.filter(f => ['when', 'from', 'to'].includes(f.key)).every(f => f.value === null && f.provenance === null));
});

test('saved trip facts preserve values and Dubai time', () => {
  const fields = tripFields({ plate: '12345', roof: 'red', trip: { from: 'DXB T3', to: 'Business Bay', at: new Date('2026-10-12T20:40:00Z') } });
  assert.equal(fields.find(f => f.key === 'plate').value, '12345');
  assert.match(fields.find(f => f.key === 'when').value, /00:40/);
  assert.equal(fields.find(f => f.key === 'to').value, 'Business Bay');
  assert.ok(fields.filter(f => f.value).every(f => f.provenance === 'user_supplied'));
});
test('missing facts never become demo taxi details', () => {
  const empty = tripFields();
  assert.ok(empty.every(f => f.value === null));
  const report = prepareReport('bag', empty, 'Black backpack');
  assert.ok(report.fields.every(f => f.value === null));
  assert.ok(!reportText(report).includes('DXB-4471'));
});
test('preparing a report requires an actual description', () => {
  assert.throws(() => prepareReport('bag', tripFields(), '  '), /Describe/);
});
test('hypotheses and fixtures cannot prefill a report', () => {
  const fields = [{ key: 'plate', value: 'DXB-4471', provenance: 'demo_fixture' }, { key: 'to', value: 'JLT', provenance: 'inferred' }];
  const report = prepareReport('bag', fields, 'Backpack');
  assert.equal(report.fields.find(f => f.key === 'plate').value, null);
  assert.equal(report.fields.find(f => f.key === 'to').value, null);
});
test('explicitly typed known fields are used; unknown fields are dropped', () => {
  const report = prepareReport('wallet', tripFields(), 'Brown wallet', { plate: ' 9876 ', bank_card: 'do not store', status: 'FILED' });
  assert.equal(report.fields.find(f => f.key === 'plate').value, '9876');
  assert.ok(!report.fields.some(f => f.key === 'bank_card'));
  assert.equal(report.status, 'PREPARED_NOT_FILED');
  assert.equal(report.filed, false);
  assert.equal(report.recovered, false);
});
test('copyable report is plain text and includes missing-field and status truth', () => {
  const report = prepareReport('bag', tripFields(), 'Bag <red>');
  const text = reportText(report);
  assert.ok(text.includes('Bag <red>'));
  assert.ok(text.includes('Taxi plate: Not given'));
  assert.ok(text.includes('Not filed. Not recovered.'));
});
