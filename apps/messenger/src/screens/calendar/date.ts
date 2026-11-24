import type { CalendarEvent } from '../../types';
export const dayStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
export const addDays = (d: Date, count: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + count);
export const weekStart = (d: Date) => addDays(d, -d.getDay());
export const monthStart = (d: Date) => new Date(d.getFullYear(), d.getMonth(), 1);
export const sameDay = (a: Date, b: Date) => dayStart(a).getTime() === dayStart(b).getTime();
export const dateKey = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
export const localInput = (d: Date) => `${dateKey(d)}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
export const atHour = (d: Date, hour: number) => new Date(d.getFullYear(), d.getMonth(), d.getDate(), Math.floor(hour), Math.round((hour % 1) * 60));
export const monthDays = (d: Date) => Array.from({ length: 42 }, (_, i) => addDays(weekStart(monthStart(d)), i));
export const monthLabel = (d: Date) => d.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
export const timeLabel = (d: Date) => d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
export const isAllDay = (e: Pick<CalendarEvent, 'start' | 'end'>) => {
  const a = new Date(e.start), b = new Date(e.end);
  return a.getHours() === 0 && a.getMinutes() === 0 && b.getHours() === 0 && b.getMinutes() === 0 && b > a;
};
export const onDay = (e: Pick<CalendarEvent, 'start' | 'end'>, day: Date) => new Date(e.start) < addDays(dayStart(day), 1) && new Date(e.end) > dayStart(day);

/** Assign overlapping intervals separate lanes, including multi-event clusters. */
export function timedLayout<T extends Pick<CalendarEvent, 'start' | 'end'>>(events: T[], day: Date) {
  const lower = atHour(day, 8).getTime(), upper = atHour(day, 20).getTime();
  const items = events.filter(e => !isAllDay(e) && new Date(e.start).getTime() < upper && new Date(e.end).getTime() > lower)
    .map(e => ({ event: e, start: Math.max(lower, new Date(e.start).getTime()), end: Math.min(upper, new Date(e.end).getTime()), lane: 0, lanes: 1 }))
    .sort((a, b) => a.start - b.start || b.end - a.end);
  let cluster: typeof items = [], ends: number[] = [], clusterEnd = 0;
  const flush = () => { cluster.forEach(item => { item.lanes = ends.length; }); cluster = []; ends = []; };
  items.forEach(item => {
    if (cluster.length && item.start >= clusterEnd) flush();
    let lane = ends.findIndex(end => end <= item.start);
    if (lane < 0) lane = ends.length;
    ends[lane] = item.end; item.lane = lane; cluster.push(item); clusterEnd = Math.max(item.end, cluster.length === 1 ? 0 : clusterEnd);
  });
  flush();
  return items.map(item => ({ ...item, top: (item.start - lower) / 3600000 * 64, height: (item.end - item.start) / 3600000 * 64 }));
}
