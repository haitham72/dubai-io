// History: a timeline of everything Mirsal did, grouped by day, with filters and a detail panel.
import { useEffect, useMemo, useRef, useState } from "react";
import { createStore } from "../../storeFactory";
import {
  ArrowRight, CloudSun, FileText, Image as ImageIcon, Mail, MessageSquare, Plane, Trash2, Video,
} from "lucide-react";
import { actions } from "../../store";
import { Button, ICON, IconButton, PageHeader, SearchField, SidebarHeader } from "../../ui";
import type { ScreenId } from "../../types";
import { days, entries as seed, filters, stats, type Entry, type Filter, type Kind } from "./data";
import s from "./history.module.css";

/* Shared between Sidebar and Main; module-level so it survives leaving the screen. */
interface HistoryState { query: string; filter: Filter; selected: string | null; list: Entry[] }
const historyStore = createStore<HistoryState>({ query: "", filter: "all", selected: seed[0].id, list: seed });
const set = historyStore.set;
const useHistory = <T,>(pick: (st: HistoryState) => T) => historyStore.use(pick);

const kindIcon: Record<Kind, typeof Plane> = { image: ImageIcon, flight: Plane, research: FileText, email: Mail, weather: CloudSun, video: Video };
const kindLabel: Record<Kind, string> = { image: "Image", flight: "Flight", research: "Research", email: "Email", weather: "Weather", video: "Video" };

function matches(e: Entry, filter: Filter, query: string) {
  if (filter !== "all" && e.kind !== filter) return false;
  const q = query.trim().toLowerCase();
  return !q || `${e.title} ${e.summary} ${e.source}`.toLowerCase().includes(q);
}

function Sidebar() {
  const query = useHistory((st) => st.query);
  const list = useHistory((st) => st.list);
  const bySource = useMemo(() => {
    const counts = new Map<string, number>();
    list.forEach((e) => counts.set(e.source, (counts.get(e.source) ?? 0) + 1));
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  }, [list]);
  return <div className={s.sidebar}>
    <SidebarHeader title="History" />
    <div className={s.sidePad}><SearchField placeholder="Search history" value={query} onChange={(q) => set({ query: q })} /></div>
    <div className={s.sideScroll}>
      <h2 className={s.sideLabel}>This month</h2>
      <div className={s.stats}>
        {stats.map((x) => <div key={x.id} className={s.stat}>
          <strong>{x.value}</strong><span>{x.label}</span><small>{x.delta}</small>
        </div>)}
      </div>
      <h2 className={s.sideLabel}>Where you asked</h2>
      {bySource.map(([source, n]) => <button key={source} className={s.sourceRow} onClick={() => set({ query: source, filter: "all" })}>
        <MessageSquare {...ICON} /><span>{source}</span><small>{n}</small>
      </button>)}
    </div>
  </div>;
}

function Main() {
  const query = useHistory((st) => st.query);
  const filter = useHistory((st) => st.filter);
  const selected = useHistory((st) => st.selected);
  const list = useHistory((st) => st.list);
  const [toast, setToast] = useState<string | null>(null);
  const timer = useRef<number>();
  useEffect(() => () => window.clearTimeout(timer.current), []);
  const notify = (text: string) => { setToast(text); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setToast(null), 2400); };
  const shown = list.filter((e) => matches(e, filter, query));
  const current = list.find((e) => e.id === selected) ?? null;
  return <div className={s.main}>
    <PageHeader title="History" subtitle="Everything Mirsal did for you" />
    <div className={s.chips} role="tablist" aria-label="Filter history">
      {filters.map((f) => <button key={f.id} role="tab" aria-selected={filter === f.id}
        className={`${s.chip} ${filter === f.id ? s.chipOn : ""}`} onClick={() => set({ filter: f.id })}>
        {f.label}<span className={s.chipCount}>{f.id === "all" ? list.length : list.filter((e) => e.kind === f.id).length}</span>
      </button>)}
      {query && <button className={s.clear} onClick={() => set({ query: "" })}>Clear “{query}”</button>}
    </div>
    <div className={s.split}>
      <div className={s.timeline}>
        {!shown.length && <p className={s.empty}>Nothing matches. Try another filter or search.</p>}
        {days.map((day) => {
          const items = shown.filter((e) => e.day === day);
          if (!items.length) return null;
          return <section key={day} className={s.day}>
            <h3 className={s.dayLabel}>{day}</h3>
            {items.map((e) => <EntryRow key={e.id} e={e} active={e.id === selected} onClick={() => set({ selected: e.id })} />)}
          </section>;
        })}
      </div>
      {current && <Detail key={current.id} e={current} notify={notify} onDelete={() => {
        const rest = list.filter((x) => x.id !== current.id);
        set({ list: rest, selected: rest.find((x) => matches(x, filter, query))?.id ?? null });
        notify("Removed from history.");
      }} />}
    </div>
    {toast && <div className={s.toast} role="status">{toast}</div>}
  </div>;
}

function EntryRow({ e, active, onClick }: { e: Entry; active: boolean; onClick: () => void }) {
  const I = kindIcon[e.kind];
  return <button className={`${s.entry} ${active ? s.entryActive : ""}`} onClick={onClick} aria-pressed={active}>
    <span className={`${s.kindIcon} ${s[e.kind]}`}><I {...ICON} /></span>
    <span className={s.entryBody}>
      <span className={s.entryTop}><strong>{e.title}</strong><time>{e.time}</time></span>
      <span className={s.entrySummary}>{e.summary}</span>
      <span className={s.entrySource}>{kindLabel[e.kind]}{e.source !== kindLabel[e.kind] && ` · ${e.source}`}</span>
    </span>
    {e.image && <img className={s.thumb} src={e.image.replace("w=1200", "w=240")} alt="" loading="lazy" />}
    {e.route && <span className={s.routeChip}><b>{e.route.from}</b><Plane size={14} strokeWidth={ICON.strokeWidth} /><b>{e.route.to}</b></span>}
    {e.weather && <span className={s.weatherChip}>{e.weather.temp}°</span>}
    {e.doc && !e.image && <span className={s.docChip}><FileText size={14} strokeWidth={ICON.strokeWidth} />{e.doc.pages} pages</span>}
  </button>;
}

const openIn: Record<Kind, [string, ScreenId]> = {
  image: ["Open in Mirsal AI", "ai"], video: ["Open in Mirsal AI", "ai"], flight: ["Open Flights", "flights"],
  research: ["Open Research", "research"], email: ["Open Mail", "mail"], weather: ["Open Weather", "weather"],
};

function Detail({ e, notify, onDelete }: { e: Entry; notify: (t: string) => void; onDelete: () => void }) {
  const I = kindIcon[e.kind];
  const useInChat = () => {
    if (e.kind === "image" && e.image) actions.sendToChat({ kind: "image", url: e.image, caption: e.title });
    else if (e.kind === "flight") actions.sendToChat({ kind: "card", icon: "flight", title: e.title, subtitle: e.summary });
    else if (e.kind === "research") actions.sendToChat({ kind: "card", icon: "research", title: e.title, subtitle: e.summary });
    else if (e.kind === "email") actions.sendToChat({ kind: "card", icon: "mail", title: e.mail?.subject ?? e.title, subtitle: `To ${e.mail?.to}` });
    else actions.sendToChat({ kind: "text", text: `${e.title}: ${e.summary}` });
  };
  return <aside className={s.detail} aria-label="History detail">
    <header className={s.detailHead}>
      <span className={`${s.kindIcon} ${s[e.kind]}`}><I {...ICON} /></span>
      <div className={s.detailTitle}><h3>{e.title}</h3><p>{e.day} · {e.time} · {e.source}</p></div>
      <IconButton icon={Trash2} label="Remove from history" onClick={onDelete} />
    </header>
    <div className={s.detailBody}>
      {e.image && <img className={s.detailImage} src={e.image} alt={e.title} />}
      {e.prompt && <div className={s.block}><h4>Prompt</h4><p>{e.prompt}</p></div>}
      {e.route && <div className={s.routeCard}>
        <div className={s.routeEnds}><strong>{e.route.from}</strong><span className={s.routeLine}><Plane {...ICON} /></span><strong>{e.route.to}</strong></div>
        <dl className={s.facts}>
          <dt>Date</dt><dd>{e.route.date}</dd><dt>Best fare</dt><dd>{e.route.price}</dd>
          <dt>Airline</dt><dd>{e.route.airline}</dd><dt>Route</dt><dd>{e.route.stops}</dd>
        </dl>
      </div>}
      {e.doc && <div className={s.block}>
        <h4>Key findings</h4>
        <ol className={s.findings}>{e.doc.findings.map((f) => <li key={f}>{f}</li>)}</ol>
        <p className={s.meta}>{e.doc.pages} pages · {e.doc.insights} insights · {e.doc.sources} sources</p>
      </div>}
      {e.mail && <div className={s.block}>
        <dl className={s.facts}><dt>To</dt><dd>{e.mail.to}</dd><dt>Subject</dt><dd>{e.mail.subject}</dd></dl>
        <p className={s.mailBody}>{e.mail.body}</p>
      </div>}
      {e.weather && <div className={s.weatherCard}>
        <span className={s.bigTemp}>{e.weather.temp}°</span>
        <span><strong>{e.weather.city}</strong><br />{e.weather.cond} · H {e.weather.hi}° / L {e.weather.lo}°</span>
      </div>}
    </div>
    <footer className={s.detailActions}>
      <Button variant="primary" onClick={() => { useInChat(); notify("Shared in chat."); }}>Use in chat</Button>
      <Button icon={ArrowRight} onClick={() => actions.navigate(openIn[e.kind][1])}>{openIn[e.kind][0]}</Button>
    </footer>
  </aside>;
}

export const historyScreen = { Sidebar, Main };
