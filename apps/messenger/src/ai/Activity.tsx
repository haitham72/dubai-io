// Messenger AI sidebar, top half: agents still working (collapsible) and finished results as a card stack.
import { useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronRight, X } from "lucide-react";
import { actions, useStore } from "../store";
import type { MessengerTask } from "../types";
import { ICON } from "../ui";
import { relativeTime, Retry, TaskIcon, TaskStatus } from "../updates/common";
import { ai, useAi } from "./state";
import s from "./activity.module.css";

/** Re-render once a second so elapsed times and "5m ago" stay current. */
export function useNow() {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  return now;
}

export function openTask(task: MessengerTask) {
  if (task.unread) actions.updateTask(task.id, { unread: false });
  ai.openTask(task.id);
}

/** Section header that folds its body vertically. */
export function Fold({ title, count, open, onToggle, action }: {
  title: string; count: number; open: boolean; onToggle: () => void; action?: React.ReactNode;
}) {
  return <div className={s.foldHead}>
    <button className={s.foldToggle} aria-expanded={open} onClick={onToggle}>
      {open ? <ChevronDown {...ICON} /> : <ChevronRight {...ICON} />}
      <span>{title}</span><span className={s.count}>{count}</span>
    </button>
    {action}
  </div>;
}

function Agents({ tasks, now }: { tasks: MessengerTask[]; now: number }) {
  const [open, setOpen] = useState(true);
  const current = useAi((st) => st.task);
  const [notice, setNotice] = useState("");
  return <section>
    <Fold title="Agents" count={tasks.length} open={open} onToggle={() => setOpen(!open)} />
    {open && <div className={s.agents}>
      {!tasks.length && <p className={s.idle}>No agents running.</p>}
      {tasks.map((t) => <div key={t.id} className={s.agentWrap}>
        <button className={`${s.agent} ${current === t.id ? s.agentOn : ""}`} onClick={() => openTask(t)}>
          <TaskIcon type={t.type} />
          <span className={s.agentBody}>
            <span className={s.agentTitle}>{t.title}</span>
            {t.status === "running" && t.progress != null
              ? <span className={s.bar}><span style={{ width: `${Math.max(0, Math.min(100, t.progress))}%` }} /></span>
              : <span className={s.agentSub}>{t.subtitle}</span>}
          </span>
          <TaskStatus task={t} now={now} />
        </button>
        {t.status === "failed" && <Retry task={t} notify={setNotice} />}
      </div>)}
      {notice && <p className={s.idle} role="status">{notice}</p>}
    </div>}
  </section>;
}

function Media({ task }: { task: MessengerTask }) {
  if (task.result?.type === "image") return <img className={s.media} src={task.result.imageUrl} alt="" loading="lazy" />;
  if (task.result?.type === "video") return <video className={s.media} src={task.result.videoUrl} muted playsInline preload="metadata" />;
  return null;
}

function ResultCard({ task, now, active, layer = 0, onClick }: {
  task: MessengerTask; now: number; active: boolean; layer?: number; onClick: () => void;
}) {
  return <div className={s.cardWrap} data-layer={layer}>
    <button className={`${s.card} ${active ? s.cardOn : ""}`} onClick={onClick} tabIndex={layer ? -1 : 0} aria-hidden={layer ? true : undefined}>
      <span className={s.cardHead}>
        <TaskIcon type={task.type} />
        <span className={s.cardTitle}><strong>{task.title}</strong><span>{task.subtitle}</span></span>
        <span className={s.time}>{relativeTime(task.completedAt ?? task.startedAt, now)}</span>
      </span>
      <Media task={task} />
      {task.unread && <span className={s.unread} aria-label="Unread" />}
    </button>
    {!layer && <button className={s.dismiss} aria-label={`Remove ${task.title}`} title="Remove"
      onClick={() => { if (ai.get().task === task.id) ai.openTask(null); actions.dismissTask(task.id); }}><X {...ICON} /></button>}
  </div>;
}

function Ready({ tasks, now }: { tasks: MessengerTask[]; now: number }) {
  const [open, setOpen] = useState(true);
  const [fanned, setFanned] = useState(false);
  const current = useAi((st) => st.task);
  const request = useStore((st) => st.updatesRequest);
  useEffect(() => { if (request) { setOpen(true); setFanned(true); } }, [request]);
  const unread = tasks.filter((t) => t.unread).length;
  const toggle = tasks.length > 1 && <button className={s.link} onClick={() => setFanned(!fanned)}>{fanned ? "Stack" : "Show all"}</button>;
  return <section>
    <Fold title={unread ? `Ready · ${unread} new` : "Ready"} count={tasks.length} open={open} onToggle={() => setOpen(!open)} action={open && toggle} />
    {open && (!tasks.length ? <p className={s.idle}>Finished results land here.</p>
      : fanned ? <div className={s.list}>
        {tasks.map((t) => <ResultCard key={t.id} task={t} now={now} active={current === t.id} onClick={() => openTask(t)} />)}
      </div>
      : <>
        <div className={s.stack}>
          {/* Up to two cards peek out under the newest. */}
          {tasks.slice(0, 3).map((t, i) => <ResultCard key={t.id} task={t} now={now} active={!i && current === t.id} layer={i}
            onClick={() => openTask(t)} />)}
        </div>
        {tasks.length > 1 && <button className={s.more} onClick={() => setFanned(true)}>+{tasks.length - 1} more</button>}
      </>)}
  </section>;
}

export function Activity() {
  const all = useStore((st) => st.tasks);
  const now = useNow();
  const { working, done } = useMemo(() => {
    const live = all.filter((t) => !t.dismissed);
    return {
      working: live.filter((t) => t.status !== "completed"),
      done: live.filter((t) => t.status === "completed").sort((a, b) => (b.completedAt ?? b.startedAt) - (a.completedAt ?? a.startedAt)),
    };
  }, [all]);
  return <div className={s.activity}>
    <Agents tasks={working} now={now} />
    <Ready tasks={done} now={now} />
  </div>;
}
