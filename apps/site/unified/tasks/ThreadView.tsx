"use client";
import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";
import { apiGet } from "../data/api";
import { DOMAIN_LABEL, DOMAIN_ORDER, type DomainId } from "../data/domains";
import { LANE_LABEL, relTime, type TaskThread } from "../data/tasks";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { Button, DemoPill } from "../ui";
import { DemoBody } from "./demos";
import s from "./tasks.module.css";

interface TaskEvent {
  seq: number;
  kind: string;
  at?: string;
  actor?: string;
  text?: string;
  sender?: string;
  provenance?: string;
  fields?: string[];
  [k: string]: unknown;
}
interface Detail {
  task: { id: string; outcome?: string; next_step?: string | null; status?: string };
  events?: TaskEvent[];
  before_seq?: number | null;
}

/** One line per recorded event. Only what the API recorded; no invented stages. */
export function describeEvent(e: TaskEvent): string {
  switch (e.kind) {
    case "created": return "Task created";
    case "edited": return `Details edited${e.fields?.length ? `: ${e.fields.join(", ")}` : ""}`;
    case "paused": return "Task paused";
    case "resumed": return "Task resumed";
    case "cancelled": return "Task cancelled";
    case "completed": return "Marked complete";
    case "check_back_set": return "Check-back scheduled";
    case "check_back_cleared": return "Check-back cleared";
    case "collection_chosen": return "Collection chosen";
    case "staged_reply": return `${e.sender ? `${e.sender}: ` : ""}${e.text ?? ""}`.trim();
    default: return e.kind.replace(/_/g, " ");
  }
}

function Header({ title, lane, demo, onBack }: { title: string; lane?: string; demo?: boolean; onBack: () => void }) {
  return (
    <header className={s.viewHead}>
      <button className={s.back} onClick={onBack} aria-label="Back to assistant"><ArrowLeft size={18} /></button>
      <div className={s.viewTitle}>
        <h1>{title}{demo && <DemoPill />}</h1>
        {lane && <span>{lane}</span>}
      </div>
    </header>
  );
}

function MoveDomain({ id, current }: { id: string; current: DomainId }) {
  const { moveThreadDomain } = useThreads();
  return (
    <label className={s.moveDomain}>
      <span>Move to</span>
      <select
        data-testid="move-domain"
        aria-label="Move thread to domain"
        value={current}
        onChange={(e) => moveThreadDomain(id, e.target.value as DomainId)}
      >
        {DOMAIN_ORDER.map((d) => (
          <option key={d} value={d}>{DOMAIN_LABEL[d]}</option>
        ))}
      </select>
    </label>
  );
}

function DemoThread({ thread }: { thread: TaskThread }) {
  const { openThread } = useApp();
  const { dismissDemo } = useThreads();
  return (
    <div className={s.view} data-testid="thread-view">
      <Header
        title={thread.title}
        lane={`${DOMAIN_LABEL[thread.domain]} · ${LANE_LABEL[thread.lane]} · example`}
        demo
        onBack={() => openThread(null)}
      />
      <div className={s.entries}>
        <DemoBody id={thread.id} />
        <MoveDomain id={thread.id} current={thread.domain} />
        <div><Button onClick={() => { dismissDemo(thread.id); openThread(null); }}>Dismiss demo</Button></div>
      </div>
    </div>
  );
}

function RealThread({ id, fallback }: { id: string; fallback?: TaskThread }) {
  const { openThread } = useApp();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [failed, setFailed] = useState(false);
  const [older, setOlder] = useState<TaskEvent[]>([]);
  const [before, setBefore] = useState<number | null>(null);

  useEffect(() => {
    let alive = true;
    setDetail(null); setFailed(false); setOlder([]);
    apiGet<Detail>(`/api/tasks/${encodeURIComponent(id)}`)
      .then((d) => { if (alive) { setDetail(d); setBefore(d.before_seq ?? null); } })
      .catch(() => { if (alive) setFailed(true); });
    return () => { alive = false; };
  }, [id]);

  const loadOlder = async () => {
    if (before == null) return;
    try {
      const more = await apiGet<{ events: TaskEvent[]; before_seq: number | null }>(`/api/tasks/${encodeURIComponent(id)}/activity?before_seq=${before}`);
      setOlder((cur) => [...more.events, ...cur]);
      setBefore(more.before_seq ?? null);
    } catch { setFailed(true); }
  };

  const title = detail?.task.outcome ?? fallback?.title ?? "Task";
  const events = [...older, ...(detail?.events ?? [])];
  const lane = fallback
    ? `${DOMAIN_LABEL[fallback.domain]} · ${LANE_LABEL[fallback.lane]}`
    : undefined;
  return (
    <div className={s.view} data-testid="thread-view">
      <Header title={title} lane={lane} onBack={() => openThread(null)} />
      <div className={s.entries}>
        {failed && <p className={s.entry} data-testid="thread-error">This task could not be loaded.</p>}
        {!detail && !failed && <p className={s.note} role="status">Loading…</p>}
        {detail?.task.next_step && <p className={s.next}><strong>Next step</strong> {detail.task.next_step}</p>}
        {fallback && <MoveDomain id={id} current={fallback.domain} />}
        {before != null && <div><Button variant="ghost" onClick={() => void loadOlder()}>Load earlier</Button></div>}
        {events.map((e) => (
          <div key={e.seq} className={s.entry} data-testid="activity-entry">
            <span>{describeEvent(e)}</span>
            {e.provenance === "demo_fixture" && <DemoPill />}
            {e.at && <time className={s.when}>{relTime(e.at)} ago</time>}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ThreadView({ id }: { id: string }) {
  const { threads } = useThreads();
  const thread = threads.find((t) => t.id === id);
  if (thread?.demo) return <DemoThread thread={thread} />;
  return <RealThread id={id} fallback={thread} />;
}
