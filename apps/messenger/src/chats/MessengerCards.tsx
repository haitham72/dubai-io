// How @messenger replies look in a chat: faint border and text, a small Messenger mark — clearly the AI, not a person.
import { useState, type ReactNode } from "react";
import { Mail,
  BellRing, CalendarCheck, CalendarDays, ChevronLeft, ChevronRight, ChevronUp, CloudSun, ExternalLink, MoreHorizontal, Plane, ShieldAlert, ShieldCheck, ShieldQuestion, ShieldX,
  Shuffle, Sparkles, Users, Wallet,
} from "lucide-react";
import { actions } from "../store";
import { ICON, Spinner } from "../ui";
import type { FlightQuery, Message, MessageBody, PlanStep, TripPlan, Verdict } from "../types";
import { anotherPack, choose, contactName, createPlanGroup, updatePlanDates } from "./skills";
import { StickerMedia } from "./StickerMedia";
import s from "./messenger.module.css";

const VERDICT: Record<Verdict, { label: string; icon: typeof ShieldCheck; tone: string }> = {
  true: { label: "True", icon: ShieldCheck, tone: s.good },
  mostly_true: { label: "Mostly true", icon: ShieldCheck, tone: s.good },
  misleading: { label: "Misleading", icon: ShieldAlert, tone: s.warn },
  false: { label: "False", icon: ShieldX, tone: s.bad },
  unverified: { label: "Unverified", icon: ShieldQuestion, tone: s.muted },
};
const plain = (t: string) => t.replace(/\*\*(.+?)\*\*/g, "$1").replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");

function Mark({ label }: { label?: string }) {
  return <span className={s.mark}><Sparkles size={14} strokeWidth={2} />Messenger{label ? ` · ${label}` : ""}</span>;
}

/** Any message written by Messenger. `children` = the normal rendering for media results (image/video/card). */
export function MessengerMessage({ m, children }: { m: Message; children?: ReactNode }) {
  const b = m.body;
  const time = <span className={s.time}>{m.time}</span>;
  if (b.kind === "ai") {
    const v = b.verdict && VERDICT[b.verdict];
    return (
      <div className={s.ai}>
        <Mark label={b.label} />
        {m.replyTo && <span className={s.quote}>“{m.replyTo.text.slice(0, 140)}”</span>}
        {v && <span className={`${s.verdict} ${v.tone}`}><v.icon size={16} strokeWidth={2} />{v.label}</span>}
        <p>{plain(b.text)}</p>
        {!!b.sources?.length && <span className={s.sources}>{b.sources.map((src) => (
          <a key={src.url} href={src.url} target="_blank" rel="noopener noreferrer"><ExternalLink size={12} />{src.domain}</a>
        ))}</span>}
        <span className={s.foot}>{b.status && <span>{b.status}{b.demo ? " · demo" : ""}</span>}{time}</span>
      </div>
    );
  }
  if (b.kind === "choices") return <Choices m={m} b={b} />;
  if (b.kind === "plan") return <Plan m={m} b={b} />;
  return <div className={s.frame}><Mark />{children}</div>;
}

function Choices({ m, b }: { m: Message; b: Extract<MessageBody, { kind: "choices" }> }) {
  const sticker = b.mode === "sticker";
  return (
    <div className={`${s.ai} ${s.wide}`}>
      <Mark label={sticker ? "Stickers" : "Images"} />
      <p>{b.title}</p>
      <div className={sticker ? s.stickerGrid : s.imageGrid}>
        {b.options.map((o, i) => (
          <button key={i} className={`${s.option} ${b.chosen === i ? s.chosen : ""} ${b.chosen !== undefined && b.chosen !== i ? s.faded : ""}`}
            disabled={!o.url || b.chosen !== undefined} onClick={() => choose(m.id, i)} aria-label={o.label ? `Share ${o.label}` : "Share this sticker"}>
            {o.url ? <StickerMedia url={o.url} alt={o.label ?? "Sticker"} /> : <span className={s.skeleton}><Spinner /></span>}
            {o.label && <small>{o.label}</small>}
          </button>
        ))}
      </div>
      <span className={s.foot}>
        {b.chosen !== undefined ? <span>Shared in the chat</span> : b.status ? <span>{b.status}</span> : <span>Tap one to share it</span>}
        {sticker && b.chosen === undefined && <button className={s.link} onClick={() => void anotherPack(m.id)}><Shuffle size={14} />Another pack</button>}
        <span className={s.time}>{m.time}</span>
      </span>
    </div>
  );
}

/* ---------------- trip plan ---------------- */
const STEP_ICON: Record<PlanStep["kind"], typeof Plane> = {
  leave: CalendarCheck, flights: Plane, budget: Wallet, group: Users, reminder: BellRing, email: Mail, weather: CloudSun, dates: CalendarDays,
};

function MiniCalendar({ cal }: { cal: TripPlan["calendar"] }) {
  const first = new Date(cal.year, cal.month - 1, 1);
  const days = new Date(cal.year, cal.month, 0).getDate();
  const lead = (first.getDay() + 6) % 7; // Monday first
  const iso = (d: number) => `${cal.year}-${String(cal.month).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const free = new Set(cal.free);
  return (
    <div className={s.cal} aria-label={`Leave from ${cal.from} to ${cal.to}`}>
      <div className={s.calHead}>{first.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}<span>Nadi · demo connector</span></div>
      <div className={s.calGrid}>
        {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <b key={i}>{d}</b>)}
        {Array.from({ length: lead }, (_, i) => <i key={`x${i}`} />)}
        {Array.from({ length: days }, (_, i) => {
          const d = iso(i + 1);
          const inside = d >= cal.from && d <= cal.to;
          const weekend = [0, 6].includes(new Date(cal.year, cal.month - 1, i + 1).getDay());
          return <span key={d} className={inside ? (free.has(d) ? s.calFree : s.calLeave) : weekend ? s.calWeekend : ""}>{i + 1}</span>;
        })}
      </div>
      <div className={s.legend}><span className={s.calLeave}>Leave</span><span className={s.calFree}>Weekend / holiday</span></div>
    </div>
  );
}

const dayMonth = (iso: string) => new Date(`${iso.slice(0, 10)}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

/** One line per step when collapsed: a short label and its key value. The full title, detail and actions open on tap. */
function brief(step: PlanStep, b: Extract<MessageBody, { kind: "plan" }>): [string, string] {
  switch (step.kind) {
    case "leave": { const l = step.data.leave;
      return ["Leave filed", `${dayMonth(l.from)} – ${dayMonth(l.to)} · ${l.leaveDays} days`]; }
    case "email": return ["Approval email", "Draft"];
    case "flights": {
      const q = step.data.query;
      const cheapest = b.flights?.length ? Math.min(...b.flights.map((f) => f.price)) : null;
      return [`Flights ${q.from} → ${q.to}`, b.flightsState === "loading" ? "Searching…" : cheapest != null ? `from AED ${cheapest.toLocaleString()}` : ""];
    }
    case "budget": return ["Spending money", `AED ${step.data.aed.toLocaleString()}`];
    case "group": return [step.title.replace(/^Create a group with (.+)\?$/, "Group with $1").replace(/^Create a group\?$/, "Group"), b.groupId ? "Created" : ""];
    case "reminder": return ["Booking reminder", step.data.events[0] ? dayMonth(step.data.events[0].start) : ""];
    case "weather": return ["Weather", `${step.data.high}° / ${step.data.low}°`];
    default: return [step.title, ""];
  }
}

function Plan({ m, b }: { m: Message; b: Extract<MessageBody, { kind: "plan" }> }) {
  const p = b.plan;
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className={`${s.ai} ${s.plan}`}>
      <Mark label="Plan" />
      <h3>{p.title}</h3>
      <p>{p.summary}</p>
      <ol className={s.steps}>
        {p.steps.map((step, i) => {
          const I = STEP_ICON[step.kind];
          // The date picker needs an answer, so it never hides behind a tap.
          if (step.kind !== "dates" && open !== i) {
            const [label, value] = brief(step, b);
            return (
              <li key={i}>
                <button className={s.stepLine} onClick={() => setOpen(i)} aria-expanded={false} aria-label={`${label}, show details`}>
                  <span className={s.stepIcon}><I size={16} strokeWidth={2} /></span>
                  <strong>{label}</strong>
                  {value && <span className={s.stepValue}>{value}</span>}
                  <MoreHorizontal size={16} className={s.more} />
                </button>
              </li>
            );
          }
          return (
            <li key={i} className={step.kind === "dates" ? "" : s.stepOpen}>
              <span className={s.stepIcon}><I size={16} strokeWidth={2} /></span>
              <div>
                {step.kind === "dates"
                  ? <strong>{step.title}</strong>
                  : <button className={s.stepTitle} onClick={() => setOpen(null)} aria-expanded>
                      <strong>{step.title}</strong><ChevronUp size={16} className={s.more} />
                    </button>}
                {step.detail && <small>{step.detail}</small>}
                {step.kind === "leave" && <><MiniCalendar cal={p.calendar} /><ChangeDates m={m} /></>}
                {step.kind === "dates" && <DatesForm messageId={m.id} initialFrom={step.data.from ?? ""} initialTo="" />}
                {step.kind === "flights" && <Flights b={b} query={step.data.query} />}
                {step.kind === "group" && (b.groupId
                  ? <button className={s.action} onClick={() => actions.openChat(b.groupId!)}><Users size={16} />Open group</button>
                  : <GroupStep m={m} step={step} />)}
                {step.kind === "reminder" && <button className={s.action} onClick={() => actions.navigate("calendar")}><BellRing size={16} />Open calendar</button>}
                {step.kind === "email" && step.data.draftId && <button className={s.action} onClick={() => actions.openQuick({ kind: "draft", id: step.data.draftId! })}><Mail size={16} />Open draft</button>}
              </div>
            </li>
          );
        })}
      </ol>
      <span className={s.foot}><span>{p.status}</span><span className={s.time}>{m.time}</span></span>
    </div>
  );
}

/** "Select users": who goes in the group. Identified members start checked; names the service could not
 *  match to a contact are shown for confirmation and can never be added straight into a chat. */
function GroupStep({ m, step }: { m: Message; step: Extract<PlanStep, { kind: "group" }> }) {
  const [open, setOpen] = useState(false);
  const [sel, setSel] = useState<string[]>(step.data.members);
  if (!open) {
    return <button className={s.action} onClick={() => { setSel(step.data.members); setOpen(true); }}><Users size={16} />Select users</button>;
  }
  const toggle = (id: string) => setSel((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  return (
    <div className={s.pick}>
      {step.data.members.map((id) => (
        <label key={id}><input type="checkbox" checked={sel.includes(id)} onChange={() => toggle(id)} />{contactName(id) || id}</label>
      ))}
      {(step.data.suggested ?? []).map((n) => <span key={n} className={s.unknown}>{n} · not in contacts</span>)}
      <div className={s.row}>
        <button className={s.action} onClick={() => setOpen(false)}>Cancel</button>
        <button className={s.action} disabled={!sel.length} onClick={() => createPlanGroup(m.id, sel)}><Users size={16} />Create group</button>
      </div>
    </div>
  );
}

const isoDay = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const shortDay = (iso: string) => new Date(`${iso}T00:00:00`).toLocaleDateString("en-GB", { day: "numeric", month: "short" });

/** Tap-to-pick range calendar: the first tap is the start, the second the end (a tap before the start
 *  restarts). Weekends are selectable; the range is kept as picked and only workdays count as leave.
 *  Submitting re-plans with the same people — nobody is asked twice. */
function DatesForm({ messageId, initialFrom, initialTo, onDone }: { messageId: string; initialFrom: string; initialTo: string; onDone?: () => void }) {
  const [from, setFrom] = useState(initialFrom);
  const [to, setTo] = useState(initialTo);
  const [busy, setBusy] = useState(false);
  const today = isoDay(new Date());
  const anchor = new Date(`${from || today}T00:00:00`);
  const [view, setView] = useState({ y: anchor.getFullYear(), m: anchor.getMonth() });
  const first = new Date(view.y, view.m, 1);
  const days = new Date(view.y, view.m + 1, 0).getDate();
  const lead = (first.getDay() + 6) % 7; // Monday first
  const shift = (n: number) => setView(({ y, m }) => ({ y: y + Math.floor((m + n) / 12), m: ((m + n) % 12 + 12) % 12 }));
  const tap = (d: string) => {
    if (!from || to || d < from) { setFrom(d); setTo(""); } else setTo(d);
  };
  const valid = !!from && !!to && to >= from;
  return (
    <div className={s.range}>
      <div className={s.rangeHead}>
        <button aria-label="Previous month" disabled={isoDay(first) <= today} onClick={() => shift(-1)}><ChevronLeft size={16} /></button>
        <span>{first.toLocaleDateString("en-GB", { month: "long", year: "numeric" })}</span>
        <button aria-label="Next month" onClick={() => shift(1)}><ChevronRight size={16} /></button>
      </div>
      <div className={s.rangeGrid}>
        {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <b key={i}>{d}</b>)}
        {Array.from({ length: lead }, (_, i) => <i key={`x${i}`} />)}
        {Array.from({ length: days }, (_, i) => {
          const d = isoDay(new Date(view.y, view.m, i + 1));
          const edge = d === from || d === to;
          const inside = !!from && !!to && d > from && d < to;
          return (
            <button key={d} disabled={d < today} onClick={() => tap(d)}
              className={edge ? s.rangeEdge : inside ? s.rangeIn : ""}>{i + 1}</button>
          );
        })}
      </div>
      <div className={s.rangeFoot}>
        <span>{from ? `${shortDay(from)} – ${to ? shortDay(to) : "pick an end"}` : "Pick a start"}</span>
        {onDone && <button className={s.link} onClick={onDone}>Cancel</button>}
        <button className={s.action} disabled={!valid || busy}
          onClick={() => { setBusy(true); void updatePlanDates(messageId, from, to).finally(() => { setBusy(false); onDone?.(); }); }}>
          {busy ? "Planning…" : "Plan"}
        </button>
      </div>
    </div>
  );
}

/** Change dates on a completed plan: a single quiet link under the calendar; the picker opens inline. */
function ChangeDates({ m }: { m: Message }) {
  const [open, setOpen] = useState(false);
  if (m.body.kind !== "plan" || !m.body.plan.calendar.from) return null;
  if (!open) return <button className={s.link} onClick={() => setOpen(true)}>Change dates</button>;
  return <DatesForm messageId={m.id} initialFrom={m.body.plan.calendar.from} initialTo={m.body.plan.calendar.to} onDone={() => setOpen(false)} />;
}

function Flights({ b, query: q }: { b: Extract<MessageBody, { kind: "plan" }>; query: FlightQuery }) {
  if (b.flightsState === "loading") return <span className={s.inline}><Spinner />Searching flights…</span>;
  if (b.flightsState === "error") return <span className={s.inline}>Flight search is unavailable right now.</span>;
  const query = b.plan.steps.find((s) => s.kind === "flights");
  if (!query || query.kind !== "flights" || !query.data.query.depart) {
    return <span className={s.inline}>Select dates above to search flights.</span>;
  }
  if (!b.flights?.length) return <span className={s.inline}>No flights found for those dates.</span>;
  return (
    <div className={s.flights}>
      {b.flights.map((f) => (
        <span key={f.id}><b>{f.airline} {f.flightNo}</b>{f.fromTime} → {f.toTime} · {f.duration} · {f.stops ? `${f.stops} stop` : "non-stop"}<em>{f.currency} {f.price.toLocaleString()}</em></span>
      ))}
      <button className={s.action} onClick={() => actions.openQuick({ kind: "flights", query: q, flights: b.flights })}><Plane size={16} />All flights</button>
    </div>
  );
}
