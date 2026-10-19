// Recovery facts are user-given; trace results are separate demo fixtures.
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

export function validLastFour(value) {
  return typeof value === 'string' && value.length === 4 && [...value].every(c => c >= '0' && c <= '9');
}

export function simulateTrace(payment, lastFour, cashRun = 0) {
  if (!['card', 'cash'].includes(payment)) throw new Error('Choose card or cash.');
  if (payment === 'card' && !validLastFour(lastFour)) throw new Error('Enter exactly four digits.');
  const matched = payment === 'card' ? lastFour !== '0000' : cashRun % 2 === 0;
  return { matched, provenance: 'demo_fixture', status: matched ? 'READY' : 'UNKNOWN_STATUS', driver: matched ? { name: 'Imran K.', plate: 'DXB-4471', eta: '12 min (demo estimate)' } : null };
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
