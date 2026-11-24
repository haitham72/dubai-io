import { createStore } from '../../storeFactory';
import { addDays, atHour, dayStart } from './date';
import { calendars } from './data';
import type { CalendarKind } from './data';
export type View = 'day' | 'week' | 'month' | 'agenda';
export interface FormState { eventId?: string; start: string; end: string }
interface CalendarState { date: Date; picker: Date; view: View; visible: CalendarKind[]; detail: string | null; form: FormState | null }
/** Phones (and the ?device preview) open on Day — a week doesn't fit. */
function phone() { return window.matchMedia('(max-width: 820px)').matches || new URLSearchParams(window.location.search).has('device'); }
const calendarStore = createStore<CalendarState>({ date: dayStart(new Date()), picker: dayStart(new Date()), view: phone() ? 'day' : 'week', visible: calendars.map(c => c.id), detail: null, form: null });
const getCalendar = calendarStore.get;
const set = calendarStore.set;


export function useCalendar<T>(select: (s: CalendarState) => T) { return calendarStore.use(select); }
export const calendar = {
  get: getCalendar,
  date(date: Date) { set({ date: dayStart(date), picker: date, detail: null }); },
  picker(picker: Date) { set({ picker }); },
  view(view: View) { set({ view, detail: null }); },
  toggle(id: CalendarKind) { const cur = getCalendar(); set({ visible: cur.visible.includes(id) ? cur.visible.filter(c => c !== id) : [...cur.visible, id] }); },
  detail(detail: string | null) { set({ detail }); },
  create(date = getCalendar().date, hour = 9, allDay = false) {
    const start = allDay ? dayStart(date) : atHour(date, hour);
    const end = allDay ? addDays(date, 1) : new Date(start.getTime() + 3600000);
    set({ form: { start: start.toISOString(), end: end.toISOString() }, detail: null });
  },
  edit(form: FormState) { set({ form }); },
  closeForm() { set({ form: null }); },
};
