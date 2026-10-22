// Human copy only. Execution codes remain in records and data-status attributes.
const LABELS = Object.freeze({
  DRAFT: 'Draft', BLOCKED: 'Prepared, not sent', AWAITING_APPROVAL: 'Ready for your approval',
  DISPATCHING: 'Sending request', SUBMITTED: 'Waiting for the shop', ACCEPTED: 'Accepted by the shop',
  READY: 'Ready for collection', COMPLETED: 'Completed', DECLINED: 'Declined by the shop', CANCELLED: 'Cancelled',
  UNKNOWN_STATUS: 'Outcome not yet known', PREPARED_NOT_FILED: 'Prepared, not filed',
});
export function statusLabel(code) { return LABELS[code] || 'Status unavailable'; }
