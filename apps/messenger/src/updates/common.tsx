import { useState } from "react";
import { retryTask } from "../ai/runAction";
import { CalendarHeart, Check, CircleAlert, FileSignature, FileText, Image, Mail, Plane, Video } from "lucide-react";
import type { MessengerTask, TaskType } from "../types";
import { ICON, Spinner } from "../ui";
import s from "./updates.module.css";

export const taskIcons = { image: Image, flight: Plane, research: FileText, email: Mail, video: Video, esign: FileSignature, event: CalendarHeart };
export function TaskIcon({ type }: { type: TaskType }) {
  const Icon = taskIcons[type];
  return <span className={s.taskIcon}><Icon {...ICON} /></span>;
}
export function relativeTime(timestamp: number, now: number) {
  const minutes = Math.max(0, Math.floor((now - timestamp) / 60_000));
  if (!minutes) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)}h ago`;
  return `${Math.floor(minutes / 1440)}d ago`;
}
export function TaskStatus({ task, now }: { task: MessengerTask; now: number }) {
  if (task.status === "failed") return <span className={s.failed}><CircleAlert {...ICON} /> Failed</span>;
  if (task.status === "queued") return <span className={s.status}>Queued <Spinner /></span>;
  if (task.status === "running") {
    const seconds = Math.max(0, Math.floor((now - task.startedAt) / 1000));
    const progress = task.progress == null ? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
      : `${Math.max(0, Math.min(100, Math.round(task.progress)))}%`;
    return <span className={s.status}>{progress} <Spinner /></span>;
  }
  return <span className={s.status}>{relativeTime(task.completedAt ?? task.startedAt, now)} <Check {...ICON} className={s.ready} /></span>;
}
export function Retry({ task, notify }: { task: MessengerTask; notify: (text: string) => void }) {
  const [starting, setStarting] = useState(false);
  return <button className={s.retry} disabled={starting} onClick={async () => {
    setStarting(true);
    try {
      const retried = await retryTask(task);
      notify(retried ? "Retry started." : "Retry is unavailable for this demo task.");
    } catch (err) {
      notify(`Couldn't retry: ${err instanceof Error ? err.message : String(err)}`);
    } finally { setStarting(false); }
  }}>{starting ? "Retrying…" : "Retry"}</button>;
}
