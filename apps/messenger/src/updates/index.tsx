// Messenger AI entry in the Chats list: a quiet row with live status. Results and agents live in the Messenger AI workspace.
import { useEffect, useMemo } from "react";
import { actions, useStore } from "../store";
import { Badge, ListRow } from "../ui";
import { ai } from "../ai/state";
import { relativeTime } from "./common";
import s from "./updates.module.css";

/** Orb with a ring only while agents run: real progress when known, otherwise a slow arc. */
function Orb({ running, progress }: { running: boolean; progress: number | null }) {
  const r = 22, c = 2 * Math.PI * r;
  return <span className={s.orb}>
    {running && <svg className={`${s.ring} ${progress == null ? s.ringSpin : ""}`} viewBox="0 0 48 48" aria-hidden>
      <circle cx="24" cy="24" r={r} className={s.ringTrack} />
      <circle cx="24" cy="24" r={r} className={s.ringFill} strokeDasharray={c}
        strokeDashoffset={progress == null ? c * 0.72 : c * (1 - progress / 100)} />
    </svg>}
  </span>;
}

export function MessengerAiRow() {
  const all = useStore((st) => st.tasks);
  const screen = useStore((st) => st.screen);
  const tasks = useMemo(() => all.filter((t) => !t.dismissed), [all]);
  // Shared result links (#update=<id>) open that result in Messenger AI.
  useEffect(() => {
    const openShared = () => {
      const id = new URLSearchParams(window.location.hash.slice(1)).get("update");
      if (id && tasks.some((t) => t.id === id)) { actions.updateTask(id, { unread: false }); ai.openTask(id); actions.navigate("ai"); }
    };
    openShared();
    window.addEventListener("hashchange", openShared);
    return () => window.removeEventListener("hashchange", openShared);
    // Resolve shared links once on mount, then only when the URL hash changes.
  }, []);
  const running = tasks.filter((t) => t.status === "running" || t.status === "queued");
  const known = running.filter((t) => t.progress != null);
  const progress = running.length && known.length === running.length
    ? known.reduce((sum, t) => sum + (t.progress ?? 0), 0) / known.length : null;
  const done = tasks.filter((t) => t.status === "completed").sort((a, b) => (b.completedAt ?? 0) - (a.completedAt ?? 0));
  const unread = tasks.filter((t) => t.unread).length;
  const latest = done[0];
  const status = [running.length ? `${running.length} working` : "", latest ? latest.title : "Ask anything"].filter(Boolean).join(" · ");
  return <div className={s.entry}>
    <ListRow selected={screen === "ai"} onClick={() => actions.openUpdates()}
      leading={<Orb running={running.length > 0} progress={progress} />}
      title="Messenger AI" subtitle={status}
      trailing={<>
        {latest && <span>{relativeTime(latest.completedAt ?? latest.startedAt, Date.now())}</span>}
        {unread > 0 && <Badge>{unread > 9 ? "9+" : unread}</Badge>}
      </>} />
  </div>;
}
