"use client";
import { AlertCircle, CheckCircle2, Clock, ListTodo, Loader, PauseCircle, type LucideIcon } from "lucide-react";
import { relTime, type Lane } from "../data/tasks";
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

export function ThreadList({ title = "Task threads" }: { title?: string }) {
  const { threads, error, loaded } = useThreads();
  const { threadId, openThread } = useApp();
  return (
    <section aria-label={title} className={s.list}>
      <h2 className={s.listTitle}>{title}</h2>
      {threads.map((t) => {
        const I = LANE_ICON[t.lane];
        return (
          <button key={t.id} data-testid="thread-row" className={`${s.row} ${threadId === t.id ? s.rowActive : ""}`} onClick={() => openThread(t.id)}>
            <span className={`${s.rowIcon} ${LANE_TONE[t.lane]}`}><I size={18} strokeWidth={2} /></span>
            <span className={s.rowText}>
              <span className={s.rowTitle}>{t.title}{t.demo && <DemoPill />}</span>
              <span className={s.rowSub}>{t.preview}</span>
            </span>
            <span className={s.rowMeta}>
              <span>{relTime(t.at)}</span>
              {t.unread && <i className={s.dot} aria-label="Unread" />}
            </span>
          </button>
        );
      })}
      {loaded && error && <p className={s.note} role="status">Could not refresh tasks. Showing what was loaded.</p>}
      {threads.length === 0 && <p className={s.note}>No open tasks.</p>}
    </section>
  );
}
