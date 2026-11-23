import { useEffect } from 'react';
import { CalendarDays, ChevronLeft, ChevronRight, Clock, MapPin, Plane, Plus, Trash2, X } from 'lucide-react';
import { actions, getState, useStore } from '../../store';
import { Button, ICON, IconButton, PageHeader, Segmented, SidebarHeader } from '../../ui';
import { calendars, flightPhoto, holidayEvents, seedEvents, type CalendarKind } from './data';
import { addDays, atHour, dateKey, dayStart, isAllDay, monthDays, monthLabel, onDay, sameDay, timeLabel, timedLayout, weekStart } from './date';
import { calendar, useCalendar, type View } from './state';
import { Editor } from './Editor';
import s from './calendar.module.css';

const weekdays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
type DisplayEvent = ReturnType<typeof holidayEvents>[number] | ReturnType<typeof getState>['events'][number];
const eventStyle = (kind: CalendarKind) => ({ '--event-color': calendars.find(c => c.id === kind)?.color ?? 'var(--blue)' } as React.CSSProperties);
let seeded = false;
function seedOnce() {
  if (seeded) return;
  seeded = true;
  let flag = false;
  try { flag = !!localStorage.getItem('mirsal.calendarSeeded'); } catch { /* storage unavailable */ }
  if (!getState().events.length && !flag) {
    seedEvents(new Date()).forEach(e => actions.addEvent(e));
    try { localStorage.setItem('mirsal.calendarSeeded', '1'); } catch { /* store still works in memory */ }
  }
}
function Sidebar() {
  const st = useCalendar(st => st);
  const today = new Date();
  return <div className={s.sidebar}>
    <SidebarHeader title="Calendar"><IconButton icon={Plus} label="New event" onClick={() => calendar.create()} /></SidebarHeader>
    <div className={s.sidebarBody}>
      <button className={s.newEvent} onClick={() => calendar.create()}><Plus {...ICON} />New Event</button>
      <section className={s.miniCalendar} aria-label="Month picker">
        <header className={s.miniHeader}><strong>{monthLabel(st.picker)}</strong><div className={s.row}><IconButton icon={ChevronLeft} label="Previous mini month" onClick={() => calendar.picker(new Date(st.picker.getFullYear(), st.picker.getMonth() - 1, 1))} /><IconButton icon={ChevronRight} label="Next mini month" onClick={() => calendar.picker(new Date(st.picker.getFullYear(), st.picker.getMonth() + 1, 1))} /></div></header>
        <div className={s.miniGrid}>{weekdays.map(day => <span key={day} className={s.miniWeekday}>{day}</span>)}
          {monthDays(st.picker).map(day => <button key={dateKey(day)} aria-label={`Go to ${dateKey(day)}`} aria-pressed={sameDay(day, st.date)} aria-current={sameDay(day, today) ? 'date' : undefined} className={`${s.miniDay} ${day.getMonth() !== st.picker.getMonth() ? s.muted : ''} ${sameDay(day, st.date) ? s.selectedDay : ''} ${sameDay(day, today) ? s.today : ''}`} onClick={() => { calendar.date(day); calendar.view('week'); }}>{day.getDate()}</button>)}
        </div>
      </section>
      {['My Calendars', 'Other Calendars'].map(group => <section key={group} className={s.calendarGroup}><h2>{group}</h2>{calendars.filter(c => c.group === group).map(c => <label key={c.id} className={s.filterRow} style={eventStyle(c.id)}><input type="checkbox" checked={st.visible.includes(c.id)} onChange={() => calendar.toggle(c.id)} />{c.label}</label>)}</section>)}
      <div className={s.sidebarNote}><Clock {...ICON} /><div>Local time zone<span>{Intl.DateTimeFormat().resolvedOptions().timeZone}</span></div></div>
    </div>
  </div>;
}
function EventButton({ event, compact = false }: { event: DisplayEvent; compact?: boolean }) {
  return <button className={`${s.eventChip} ${compact ? s.compactEvent : ''}`} style={eventStyle(event.calendar)} onClick={() => calendar.detail(event.id)} title={event.title} aria-label={`Open ${event.title}`}>
    {event.calendar === 'flights' && <Plane {...ICON} />}<span>{event.title}</span>
  </button>;
}
function TimeGrid({ date, events, dayView }: { date: Date; events: DisplayEvent[]; dayView: boolean }) {
  const days = dayView ? [dayStart(date)] : Array.from({ length: 7 }, (_, i) => addDays(weekStart(date), i));
  const template = { gridTemplateColumns: `64px repeat(${days.length}, minmax(90px, 1fr))` };
  return <div className={s.timeViewport}>
    <div className={s.timeGrid} style={template}>
      <div className={s.corner} />
      {days.map(day => <button key={dateKey(day)} className={s.dayHeader} onClick={() => { calendar.date(day); calendar.view('day'); }}><span>{weekdays[day.getDay()]}</span><strong className={sameDay(day, new Date()) ? s.todayNumber : ''}>{day.getDate()}</strong></button>)}
      <div className={s.allDayLabel}>All day</div>
      {days.map(day => <div key={dateKey(day)} className={s.allDayCell}>
        <button className={s.addAllDay} aria-label={`Add all-day event ${dateKey(day)}`} onClick={() => calendar.create(day, 0, true)}>+</button>
        {events.filter(e => onDay(e, day) && (isAllDay(e) || new Date(e.end) <= atHour(day, 8) || new Date(e.start) >= atHour(day, 20))).map(e => <EventButton key={e.id} event={e} compact />)}
      </div>)}
      <div className={s.hours}>{Array.from({ length: 13 }, (_, i) => <span key={i} style={{ top: i * 64 }}>{timeLabel(atHour(date, i + 8)).replace(':00', '')}</span>)}</div>
      {days.map(day => <div key={dateKey(day)} className={s.dayColumn}>
        {Array.from({ length: 12 }, (_, i) => <button key={i} className={s.hourSlot} aria-label={`Create event ${dateKey(day)} ${i + 8}:00`} onClick={() => calendar.create(day, i + 8)} />)}
        {timedLayout(events, day).map(item => <button key={item.event.id} className={s.timedEvent} style={{ ...eventStyle(item.event.calendar), top: item.top, height: Math.max(24, item.height - 3), insetInlineStart: `calc(${item.lane / item.lanes * 100}% + 3px)`, width: `calc(${100 / item.lanes}% - 6px)` }} aria-label={`Open ${item.event.title}`} title={`${item.event.title} · ${timeLabel(new Date(item.event.start))} – ${timeLabel(new Date(item.event.end))}`} onClick={() => calendar.detail(item.event.id)}>
          {item.event.calendar === 'flights' && <Plane {...ICON} />}<strong>{item.event.title}</strong><span>{timeLabel(new Date(item.event.start))} – {timeLabel(new Date(item.event.end))}</span><small>{item.event.location}</small>
        </button>)}
      </div>)}
    </div>
  </div>;
}
function MonthGrid({ date, events }: { date: Date; events: DisplayEvent[] }) {
  return <div className={s.monthViewport}><div className={s.monthGrid}>
    {weekdays.map(day => <div key={day} className={s.monthWeekday}>{day}</div>)}
    {monthDays(date).map(day => <div key={dateKey(day)} className={`${s.monthCell} ${day.getMonth() !== date.getMonth() ? s.outsideMonth : ''}`}>
      <div className={s.monthDayTop}><button className={`${s.monthDayNumber} ${sameDay(day, new Date()) ? s.todayNumber : ''}`} aria-label={`View day ${dateKey(day)}`} onClick={() => { calendar.date(day); calendar.view('day'); }}>{day.getDate()}</button><button className={s.monthAdd} aria-label={`Add event ${dateKey(day)}`} onClick={() => calendar.create(day)}><Plus {...ICON} /></button></div>
      <div className={s.monthEvents}>{events.filter(e => onDay(e, day)).map(e => <EventButton key={e.id} event={e} compact />)}</div>
    </div>)}
  </div></div>;
}
function Agenda({ date, events }: { date: Date; events: DisplayEvent[] }) {
  const start = new Date(date.getFullYear(), date.getMonth(), 1), end = new Date(date.getFullYear(), date.getMonth() + 1, 1);
  const listed = events.filter(e => new Date(e.start) < end && new Date(e.end) > start).sort((a, b) => +new Date(a.start) - +new Date(b.start));
  return <div className={s.agenda}>{listed.length ? listed.map(e => <button key={e.id} className={s.agendaEvent} style={eventStyle(e.calendar)} onClick={() => calendar.detail(e.id)}><div className={s.agendaDate}>{new Date(e.start).toLocaleDateString('en-US', { month: 'short', day: 'numeric', weekday: 'short' })}<span>{isAllDay(e) ? 'All day' : timeLabel(new Date(e.start))}</span></div><div><strong>{e.title}</strong><p>{e.location || calendars.find(c => c.id === e.calendar)?.label}</p></div></button>) : <div className={s.empty}><CalendarDays {...ICON} /><h3>No events this month</h3><p>Choose another month or add something to your calendar.</p><Button onClick={() => calendar.create()}>New Event</Button></div>}</div>;
}
function Detail({ event }: { event: DisplayEvent }) {
  return <aside className={s.detail} aria-label="Event details">
    <header className={s.detailHeader}><span>Event details</span><IconButton icon={X} label="Close event details" onClick={() => calendar.detail(null)} /></header>
    {event.calendar === 'flights' && <><img src={flightPhoto} alt="Dubai skyline" className={s.flightPhoto} /><div className={s.flightRoute}><Plane {...ICON} /><div><h3>{event.title}</h3><span>Flight itinerary</span></div></div></>}
    {event.calendar !== 'flights' && <h2 className={s.detailTitle}>{event.title}</h2>}
    <div className={s.detailLine}><CalendarDays {...ICON} /><div>{new Date(event.start).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })}<span>{isAllDay(event) ? `All day · through ${addDays(new Date(event.end), -1).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : `${timeLabel(new Date(event.start))} – ${timeLabel(new Date(event.end))}${!sameDay(new Date(event.start), new Date(event.end)) ? ` · ends ${new Date(event.end).toLocaleDateString()}` : ''}`}</span></div></div>
    {event.location && <div className={s.detailLine}><MapPin {...ICON} /><span>{event.location}</span></div>}
    <div className={s.detailCategory} style={eventStyle(event.calendar)}><i />{calendars.find(c => c.id === event.calendar)?.label}</div>
    {event.notes && <section className={s.notes}><h3>Notes</h3><p>{event.notes}</p></section>}
    {event.calendar === 'flights' && <Button onClick={() => actions.navigate('flights')}>Open Flights</Button>}
    {event.calendar !== 'holidays' ? <div className={s.detailActions}><Button onClick={() => calendar.edit({ eventId: event.id, start: event.start, end: event.end })}>Edit event</Button><button className={s.deleteBtn} onClick={() => { actions.deleteEvent(event.id); calendar.detail(null); }}><Trash2 {...ICON} />Delete event</button></div> : <p className={s.formHint}>Illustrative reminder · read only</p>}
    <div className={s.detailFooter}>Times shown in your device’s local time zone.</div>
  </aside>;
}
function Main() {
  const st = useCalendar(st => st);
  const stored = useStore(st => st.events);
  useEffect(seedOnce, []);
  useEffect(() => {
    const escape = (e: KeyboardEvent) => { if (e.key === 'Escape') { if (calendar.get().form) calendar.closeForm(); else calendar.detail(null); } };
    window.addEventListener('keydown', escape); return () => window.removeEventListener('keydown', escape);
  }, []);
  const all: DisplayEvent[] = [...stored, ...holidayEvents(st.date.getFullYear())];
  const events = all.filter(e => st.visible.includes(e.calendar));
  const detail = events.find(e => e.id === st.detail);
  const shift = (direction: number) => calendar.date(st.view === 'month' || st.view === 'agenda' ? new Date(st.date.getFullYear(), st.date.getMonth() + direction, 1) : addDays(st.date, direction * (st.view === 'day' ? 1 : 7)));
  return <div className={s.main}>
    <PageHeader title={monthLabel(st.date)} subtitle={st.view === 'week' ? `${addDays(weekStart(st.date), 0).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${addDays(weekStart(st.date), 6).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : 'Your schedule, all in one place'}>
      <Segmented<View> options={[{ value: 'day', label: 'Day' }, { value: 'week', label: 'Week' }, { value: 'month', label: 'Month' }, { value: 'agenda', label: 'Agenda' }]} value={st.view} onChange={calendar.view} />
      <IconButton icon={ChevronLeft} label="Previous period" onClick={() => shift(-1)} /><IconButton icon={ChevronRight} label="Next period" onClick={() => shift(1)} /><Button onClick={() => calendar.date(new Date())}>Today</Button>
    </PageHeader>
    <div className={s.workspace}><div className={s.schedule}>
      {st.view === 'week' || st.view === 'day' ? <TimeGrid date={st.date} events={events} dayView={st.view === 'day'} /> : st.view === 'month' ? <MonthGrid date={st.date} events={events} /> : <Agenda date={st.date} events={events} />}
    </div>{detail && <Detail event={detail} />}</div>
    {st.form && <Editor key={`${st.form.eventId ?? 'new'}-${st.form.start}`} form={st.form} />}
  </div>;
}
export const calendarScreen = { Sidebar, Main };
