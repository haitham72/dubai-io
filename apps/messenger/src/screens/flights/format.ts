/** Display-only labels; API query values and date inputs retain their wire format. */
export function flightDate(value: string): string {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return value;
  const date = new Date(`${value}T00:00:00Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0, 10) !== value) return value;
  return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' }).replace(',', '');
}
export const cabinLabel = (value: string) => value ? value[0].toUpperCase() + value.slice(1).toLowerCase() : value;
export const passengerLabel = (count: number) => `${count} passenger${count === 1 ? '' : 's'}`;
export const flightDates = (depart: string, ret?: string) => `${flightDate(depart)}${ret ? ` – ${flightDate(ret)}` : ''}`;
