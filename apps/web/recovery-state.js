// Recovery facts are user-given. Staged replies live on the saved task (server script).
export const REPORT_FIELDS = [
  ['when', 'Date and time'], ['from', 'Pickup'], ['to', 'Drop-off'],
  ['plate', 'Taxi plate'], ['roof', 'Roof colour'], ['fare', 'Trip fare'],
  ['payment', 'Payment method'], ['booking', 'Booking reference'],
];
const text = v => typeof v === 'string' && v.trim() ? v.trim().slice(0, 160) : null;

export function tripFields(memory = {}) {
  const trip = memory.trip || {};
  const date = trip.at instanceof Date ? trip.at : null;
  const when = date && Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Dubai', dateStyle: 'medium', timeStyle: 'short' }).format(date) : text(trip.when);
  const values = { when, from: text(trip.from), to: text(trip.to), plate: text(memory.plate), roof: text(memory.roof), fare: text(trip.fare), payment: text(trip.payment), booking: text(trip.booking) };
  return REPORT_FIELDS.map(([key, label]) => ({ key, label, value: values[key] || null, provenance: values[key] ? 'user_supplied' : null }));
}

export function prepareReport(item, fields, description, values = {}) {
  const desc = text(description);
  if (!desc) throw new Error('Describe the item before preparing the report.');
  const safeFields = REPORT_FIELDS.map(([key, label]) => {
    const existing = fields.find(f => f.key === key);
    // Typed values supersede a saved field only when explicitly provided.
    const value = Object.hasOwn(values, key) ? text(values[key]) : existing?.provenance === 'user_supplied' ? text(existing.value) : null;
    return { key, label, value, provenance: value ? 'user_supplied' : null };
  });
  return { item: text(item) || 'item', description: desc, fields: safeFields, status: 'PREPARED_NOT_FILED', filed: false, recovered: false };
}

export function reportText(report) {
  return ['Lost item: ' + report.description, ...report.fields.map(f => f.label + ': ' + (f.value || 'Not given')), 'Prepared in Dubai-io. Not filed. Not recovered.'].join('\n');
}
