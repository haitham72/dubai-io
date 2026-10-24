import test from 'node:test';
import assert from 'node:assert/strict';
import { decisionKind, needsYouRows, isStale, approvalFor, CRUCIAL } from '../decision-logic.js';

const order = o => ({ id: 'a1', revision: 3, snapshot_hash: 'h'.repeat(64), execution_available: true, ...o });

test('only the three crucial stops are decisions', () => {
  assert.equal(decisionKind(order({ status: 'AWAITING_APPROVAL' })), 'approve');
  assert.equal(decisionKind(order({ status: 'UNKNOWN_STATUS' })), 'check');
  assert.equal(decisionKind(order({ status: 'ACCEPTED', deadline_check: { meets: false } })), 'deadline');
  assert.deepEqual([...CRUCIAL], ['approve', 'check', 'deadline']);
});

test('unsendable, incomplete, met or already-asked items stay on the list', () => {
  assert.equal(decisionKind(order({ status: 'AWAITING_APPROVAL', execution_available: false })), null);
  assert.equal(decisionKind(order({ status: 'DRAFT' })), null);
  assert.equal(decisionKind(order({ status: 'ACCEPTED', deadline_check: { meets: true } })), null);
  assert.equal(decisionKind(order({ status: 'ACCEPTED', deadline_check: { meets: false }, earlier_request: { target: 'x' } })), null);
  assert.equal(decisionKind(order({ status: 'READY' })), null);
  assert.equal(decisionKind(null), null);
  const rows = needsYouRows([{ decision: { kind: 'approve', action_id: 'a' } }, { decision: { kind: 'remind', action_id: 'b' } }, { decision: { kind: 'check' } }, {}]);
  assert.equal(rows.length, 1);
});

test('approval binds the rendered revision and snapshot', () => {
  const shown = order({ status: 'AWAITING_APPROVAL' });
  assert.deepEqual(approvalFor(shown, { ...shown }), { ok: true, body: { snapshot_hash: shown.snapshot_hash, revision: 3 } });
});

test('stale approval is refused and never builds a body', () => {
  const shown = order({ status: 'AWAITING_APPROVAL' });
  const edited = { ...shown, revision: 4, snapshot_hash: 'x'.repeat(64) };
  assert.equal(isStale(shown, edited), true);
  assert.deepEqual(approvalFor(shown, edited), { ok: false, reason: 'stale' });
  assert.deepEqual(approvalFor(shown, { ...shown, status: 'UNKNOWN_STATUS' }), { ok: false, reason: 'gone' });
  assert.deepEqual(approvalFor(shown, null), { ok: false, reason: 'gone' });
});
