"use client";
import { AlertCircle, CheckCircle2, Clock, ListTodo, Loader, PauseCircle, type LucideIcon } from "lucide-react";
import { DOMAIN_LABEL, groupByDomain } from "../data/domains";
import { relTime, type Lane, type TaskThread } from "../data/tasks";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { DemoPill } from "../ui";
import s from "./tasks.module.css";

const LANE_ICON: Record<Lane, LucideIcon> = {
  needs_you: AlertCircle, running: Loader, scheduled: Clock, on_list: ListTodo, paused: PauseCircle, completed: CheckCircle2,
};
const LANE_TONE: Record<Lane, string> = {
  needs_you: s.toneRed, running: s.toneAccent, scheduled: s.toneAmber, on_list: s.toneGrey, paused: s.toneGrey, completed: s.toneGreen,
};

function ThreadRow({ t }: { t: TaskThread }) {
  const { threadId, openThread } = useApp();
  const I = LANE_ICON[t.lane];
  return (
    <button
      data-testid="thread-row"
      data-domain={t.domain}
      className={`${s.row} ${threadId === t.id ? s.rowActive : ""}`}
      onClick={() => openThread(t.id)}
    >
      <span className={`${s.rowIcon} ${LANE_TONE[t.lane]}`}><I size={18} strokeWidth={2} /></span>
      <span className={s.rowText}>
        <span className={s.rowTitle}><span>{t.title}</span>{t.demo && <DemoPill />}</span>
        <span className={s.rowSub}>{t.preview}</span>
      </span>
      <span className={s.rowMeta}>
        <span>{relTime(t.at)}</span>
        {t.unread && <i className={s.dot} aria-label="Unread" />}
      </span>
    </button>
  );
}

export function ThreadList({ title = "Task threads" }: { title?: string }) {
  const { threads, error, loaded, dismissedCount, restoreDemos } = useThreads();
  const groups = groupByDomain(threads);
  return (
    <section aria-label={title} className={s.list} data-testid="thread-list">
      <h2 className={s.listTitle}>{title}</h2>
      {groups.map((g) => (
        <div key={g.domain} className={s.domainGroup} data-testid="domain-group" data-domain={g.domain}>
          <h3 className={s.domainTitle}>{DOMAIN_LABEL[g.domain]}</h3>
          {g.items.map((t) => <ThreadRow key={t.id} t={t} />)}
        </div>
      ))}
      {dismissedCount > 0 && (
        <button type="button" className={s.pill} data-testid="restore-demos" onClick={restoreDemos}>
          Restore {dismissedCount} demo{dismissedCount === 1 ? "" : "s"}
        </button>
      )}
      {loaded && error && <p className={s.note} role="status">Could not refresh tasks. Showing what was loaded.</p>}
      {threads.length === 0 && <p className={s.note}>No open tasks.{dismissedCount ? " Restore demos above." : ""}</p>}
    </section>
  );
}
