// Floating card for voice commands that wait on the person: "Sending to Sara Ali… Undo" and paid actions' Confirm.
// Floats over whatever screen the command opened (overlays never resize the chat).
import { useEffect, useState } from "react";
import { CalendarPlus, CircleCheck, Send, Sparkles, Undo2, X } from "lucide-react";
import { actions } from "../store";
import { ICON } from "../ui";
import { commands, useCommands, type PendingCommand, type MeetingDraft } from "./commands";
import s from "./commands.module.css";

function Countdown({ until }: { until: number }) {
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 250); return () => clearInterval(t); }, []);
  return <span className={s.count}>{Math.max(0, Math.ceil((until - Date.now()) / 1000))}s</span>;
}

function Row({ p }: { p: PendingCommand }) {
  if (p.kind === "undo") {
    return (
      <div className={s.card} role="status">
        <Send {...ICON} />
        <p>{p.label}</p>
        {p.until && <Countdown until={p.until} />}
        <button className={s.secondary} onClick={() => commands.undo(p.id)}><Undo2 {...ICON} />Undo</button>
        <button className={s.primary} onClick={() => commands.commit(p.id)}>Send now</button>
      </div>
    );
  }
  return (
    <div className={s.card} role="alertdialog" aria-label={p.label}>
      <Sparkles {...ICON} />
      <p>{p.label}<small>Uses paid credits</small></p>
      <button className={s.secondary} aria-label="Cancel" onClick={() => commands.decline(p.id)}><X {...ICON} /></button>
      <button className={s.primary} onClick={() => commands.confirm(p.id)}><CircleCheck {...ICON} />Confirm</button>
    </div>
  );
}

export function CommandCard() {
  const { pending, note, drafts } = useCommands((c) => c);
  if (!pending.length && !note && !drafts.length) return null;
  return (
    <div className={s.stack}>
      {pending.map((p) => <Row key={p.id} p={p} />)}
      {drafts[0] && <Meeting key={drafts[0].id} draft={drafts[0]} count={drafts.length} />}
      {note && <div className={s.note} role="status">{note}</div>}
    </div>
  );
}

function Meeting({ draft, count }: { draft: MeetingDraft; count: number }) {
  const a = draft.args;
  const [title, setTitle] = useState(a.title || "Meeting");
  const [date, setDate] = useState(a.date || "");
  const [start, setStart] = useState(a.startTime || "");
  const [end, setEnd] = useState(a.endTime || "");
  const [location, setLocation] = useState(a.location || "");
  return <form className={`${s.card} ${s.meeting}`} aria-label="Meeting draft" onSubmit={e => {
    e.preventDefault();
    const endInput = e.currentTarget.elements.namedItem("end") as HTMLInputElement;
    endInput.setCustomValidity(end <= start ? "Choose an end time after the start time." : "");
    if (!e.currentTarget.reportValidity()) return;
    actions.addEvent({ title: title.trim(), start: `${date}T${start}:00`, end: `${date}T${end}:00`, calendar: "personal", location: location.trim(),
      notes: [a.name ? `Planned with ${a.name}; invitation not sent.` : "Personal meeting draft.", a.context].filter(Boolean).join("\n") });
    commands.closeDraft(draft.id);
  }}>
    <header><CalendarPlus {...ICON} /><strong>Meeting draft{count > 1 ? ` · 1 of ${count}` : ""}</strong>
      <button type="button" className={s.secondary} aria-label="Discard meeting draft" onClick={() => commands.closeDraft(draft.id)}><X {...ICON} /></button></header>
    <p>{a.name ? `You and ${a.name}` : "Participants not specified"}<small>Review the details, then save to your calendar. No invitation is sent.</small></p>
    {a.context && <blockquote>{a.context}</blockquote>}
    <label>Title<input required pattern=".*\S.*" value={title} onChange={e => setTitle(e.target.value)} /></label>
    <label>Date<input required type="date" value={date} onChange={e => setDate(e.target.value)} /></label>
    <div className={s.times}><label>Start<input required type="time" value={start} onChange={e => {
      (e.target.form?.elements.namedItem("end") as HTMLInputElement | null)?.setCustomValidity(""); setStart(e.target.value);
    }} /></label>
      <label>End<input required name="end" type="time" value={end} onChange={e => { e.target.setCustomValidity(""); setEnd(e.target.value); }} /></label></div>
    <label>Place or meeting link<input required pattern=".*\S.*" value={location} onChange={e => setLocation(e.target.value)} placeholder="Add the place or branch" /></label>
    <button className={s.primary} type="submit"><CalendarPlus {...ICON} />Save to calendar</button>
  </form>;
}
