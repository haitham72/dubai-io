import type { CalendarEvent } from '../../types';
import { img } from '../../ui';
import { addDays, atHour, weekStart } from './date';
export type CalendarKind = CalendarEvent['calendar'] | 'holidays';
export const calendars: { id: CalendarKind; label: string; color: string; group: string }[] = [
  { id: 'personal', label: 'Personal', color: 'var(--blue)', group: 'My Calendars' },
  { id: 'work', label: 'Work', color: 'var(--purple)', group: 'My Calendars' },
  { id: 'travel', label: 'Travel', color: 'var(--success)', group: 'My Calendars' },
  { id: 'family', label: 'Family', color: 'var(--warning)', group: 'My Calendars' },
  { id: 'holidays', label: 'Holidays', color: 'var(--danger)', group: 'Other Calendars' },
  { id: 'flights', label: 'Flights', color: 'var(--blue)', group: 'Other Calendars' },
];
export const flightPhoto = img('photo-1512453979798-5ea266f8880c', 800);
export function seedEvents(today: Date): Omit<CalendarEvent, 'id'>[] {
  const base = weekStart(today);
  const event = (offset: number, hour: number, duration: number, title: string, calendar: CalendarEvent['calendar'], location: string, notes = '') => ({
    title, calendar, location, notes, start: atHour(addDays(base, offset), hour).toISOString(), end: atHour(addDays(base, offset), hour + duration).toISOString(),
  });
  return [
    event(0, 10, 1, 'Coffee & weekly reset', 'personal', 'Alserkal Avenue, Dubai'),
    event(1, 9, 1, 'Team sync', 'work', 'Messenger HQ', 'Review this week’s priorities and project milestones.'),
    event(1, 12, 1, 'Lunch with Omar', 'family', 'Zabeel'),
    event(1, 15, 1, 'Weekly planning', 'work', 'Zoom'),
    event(2, 10, 1, 'Product review', 'personal', 'Meeting room 2'),
    event(2, 16, 1, 'Roadmap update', 'work', 'Messenger HQ'),
    event(3, 0, 24, 'Travel preparation', 'travel', 'Dubai', 'Pack bags and review the itinerary.'),
    event(3, 9, 1, 'Client call', 'work', 'Zoom'),
    event(4, 8.5, 7.25, 'DXB → LHR · EK 007', 'flights', 'Dubai International Airport', 'Demo itinerary · Emirates EK 007 · Terminal 3 · 1 adult · Economy. Times shown in your device’s local time.'),
    event(5, 10, 1, 'Design review', 'work', 'Meeting room 1'),
    event(5, 15, 1, 'Hotel check-in', 'travel', 'Hilton London'),
    event(6, 12, 2, 'Family time', 'family', 'Home'),
  ];
}
export const holidayEvents = (year: number) => [{
  id: `holiday-${year}`, title: 'Holiday planning reminder', calendar: 'holidays' as const,
  start: new Date(year, 11, 2).toISOString(), end: new Date(year, 11, 3).toISOString(),
  location: 'UAE', notes: 'Illustrative reminder for travel planning. Confirm official holiday dates separately.',
}];
