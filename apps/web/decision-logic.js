// Pure rules for "Needs you" (FIN-01). No DOM, no network: the server's /api/today is the
// authority; this mirrors it so the client never shows a decision the contract does not allow.
// Only three crucial stops qualify: approve a send, unknown send outcome, missed deadline.
export const CRUCIAL = Object.freeze(['approve', 'check', 'deadline']);

// Which crucial stop (if any) an order Action is on right now. Drafts, incomplete or
// unsendable items return null and stay "On your list".
export function decisionKind(action) {
  if (!action) return null;
  if (action.status === 'AWAITING_APPROVAL' && action.execution_available) return 'approve';
  if (action.status === 'UNKNOWN_STATUS') return 'check';
  const dc = action.deadline_check;
  if (action.status === 'ACCEPTED' && dc && !dc.meets && !action.earlier_request) return 'deadline';
  return null;
}

// Keep only well-formed crucial decisions from Today's rows.
export const needsYouRows = tasks => (tasks || []).filter(t => t?.decision && CRUCIAL.includes(t.decision.kind) && t.decision.action_id);

// A card is bound to the revision (and snapshot, for a send) it rendered. Anything else is stale.
export function isStale(shown, fresh) {
  if (!shown || !fresh) return true;
  return shown.revision !== fresh.revision || (shown.snapshot_hash || null) !== (fresh.snapshot_hash || null) || shown.status !== fresh.status;
}

// Approve is allowed only for an approve decision that is still current. Returns the body to
// send, or the reason it was refused (the caller then refreshes the card).
export function approvalFor(shown, fresh) {
  if (decisionKind(fresh) !== 'approve') return { ok: false, reason: 'gone' };
  if (isStale(shown, fresh)) return { ok: false, reason: 'stale' };
  return { ok: true, body: { snapshot_hash: fresh.snapshot_hash, revision: fresh.revision } };
}

export const STALE_MESSAGE = 'This changed while you were looking. Review the current details; nothing was sent.';
