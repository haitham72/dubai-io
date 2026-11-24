import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { actions, getState } from '../../store';
import type { CalendarEvent } from '../../types';
import { Button, IconButton } from '../../ui';
import { calendars } from './data';
import { addDays, isAllDay, localInput } from './date';
import { calendar, type FormState } from './state';
import s from './calendar.module.css';

export function Editor({ form }: { form: FormState }) {
  const existing = getState().events.find(e => e.id === form.eventId);
  const [title, setTitle] = useState(existing?.title ?? '');
  const [start, setStart] = useState(localInput(new Date(form.start)));
  const [end, setEnd] = useState(localInput(new Date(form.end)));
  const [allDay, setAllDay] = useState(isAllDay(form));
  const [kind, setKind] = useState<CalendarEvent['calendar']>(existing?.calendar ?? 'work');
  const [location, setLocation] = useState(existing?.location ?? '');
  const [notes, setNotes] = useState(existing?.notes ?? '');
  const [error, setError] = useState('');
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const prior = document.activeElement as HTMLElement;
    dialog.current?.querySelector<HTMLInputElement>('input')?.focus();
    return () => { if (prior?.isConnected) prior.focus(); };
  }, []);
  const save = (e: React.FormEvent) => {
    e.preventDefault();
    const first = new Date(allDay ? `${start.slice(0, 10)}T00:00` : start);
    const last = new Date(allDay ? `${end.slice(0, 10)}T00:00` : end);
    if (!title.trim()) { setError('Give this event a title.'); return; }
    if (!Number.isFinite(first.getTime()) || !Number.isFinite(last.getTime()) || last <= first) { setError('End must be after start.'); return; }
    const event = { title: title.trim(), start: first.toISOString(), end: last.toISOString(), calendar: kind, location: location.trim(), notes: notes.trim() };
    const id = form.eventId ?? actions.addEvent(event);
    if (form.eventId) actions.updateEvent(id, event);
    // Keep saved events visible, including events moved to another week or calendar.
    if (!calendar.get().visible.includes(kind)) calendar.toggle(kind);
    calendar.date(first); calendar.closeForm(); calendar.detail(id);
  };
  return <div className={s.backdrop} onMouseDown={e => { if (e.target === e.currentTarget) calendar.closeForm(); }}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-labelledby="event-editor-title" className={s.editor} onKeyDown={e => {
      if (e.key === 'Escape') { e.stopPropagation(); calendar.closeForm(); }
      if (e.key === 'Tab') {
        const controls = Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, input, select, textarea') ?? []).filter(el => !el.hasAttribute('disabled'));
        const first = controls[0], last = controls[controls.length - 1];
        if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
        else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
      }
    }}>
      <header className={s.editorHeader}><h2 id="event-editor-title">{form.eventId ? 'Edit event' : 'New event'}</h2><IconButton icon={X} label="Close event form" onClick={calendar.closeForm} /></header>
      <form onSubmit={save} className={s.form}>
        <label>Event title<input required maxLength={160} value={title} onChange={e => setTitle(e.target.value)} placeholder="Add a title" /></label>
        <label className={s.checkbox}><input type="checkbox" checked={allDay} onChange={e => {
          setAllDay(e.target.checked);
          if (e.target.checked) { const date = new Date(`${start.slice(0, 10)}T00:00`); setStart(localInput(date)); setEnd(localInput(addDays(date, 1))); }
        }} />All-day event</label>
        <div className={s.formPair}>
          <label>Start<input type={allDay ? 'date' : 'datetime-local'} required value={allDay ? start.slice(0, 10) : start} onChange={e => setStart(allDay ? `${e.target.value}T00:00` : e.target.value)} /></label>
          <label>{allDay ? 'End (exclusive)' : 'End'}<input type={allDay ? 'date' : 'datetime-local'} required value={allDay ? end.slice(0, 10) : end} onChange={e => setEnd(allDay ? `${e.target.value}T00:00` : e.target.value)} /></label>
        </div>
        <p className={s.formHint}>{allDay ? 'Ends at midnight on the end date.' : 'Times use your device’s local time zone.'}</p>
        <label>Calendar<select value={kind} onChange={e => setKind(e.target.value as CalendarEvent['calendar'])}>{calendars.filter(c => c.id !== 'holidays').map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
        <label>Location<input value={location} onChange={e => setLocation(e.target.value)} placeholder="Add a location" /></label>
        <label>Notes<textarea value={notes} onChange={e => setNotes(e.target.value)} rows={3} placeholder="Details, reminders or a travel itinerary" /></label>
        {error && <div role="alert" className={s.error}>{error}</div>}
        <div className={s.formFooter}><Button onClick={calendar.closeForm}>Cancel</Button><button type="submit" className={s.primary}>{form.eventId ? 'Save changes' : 'Create event'}</button></div>
      </form>
    </div>
  </div>;
}
