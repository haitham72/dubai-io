"use client";

import Link from "next/link";
import { useRef, useState } from "react";
import { FunnelError, funnelStyles as s } from "@/components/funnel";
import { apiPost, describeError, type TaskItem } from "@/lib/api";
import { ensureSession } from "@/lib/session";

const IDEAS = [
  "Get my AC serviced before summer",
  "Find a laundry that presses shirts",
  "Check which bills are due this month",
  "Ask a neighbour about a good vet",
];

const MAX = 240;

function hash(text: string): string {
  let h = 5381;
  for (let i = 0; i < text.length; i++) h = ((h << 5) + h + text.charCodeAt(i)) | 0;
  return (h >>> 0).toString(36);
}

export default function FirstTask() {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [task, setTask] = useState<TaskItem | null>(null);
  // One random id per page load, so a retry of the same text is idempotent
  // (the API replays instead of creating a duplicate).
  const attempt = useRef<string | null>(null);

  const outcome = text.trim();

  async function create() {
    if (!outcome) return;
    setBusy(true);
    setError(null);
    if (!attempt.current) attempt.current = Math.random().toString(36).slice(2, 10);
    try {
      await ensureSession();
      const res = await apiPost<{ task?: TaskItem; replayed?: boolean }>(
        "/api/tasks",
        {
          outcome,
          creation_key: `site-first-task-${attempt.current}-${hash(outcome)}`,
        },
      );
      if (!res?.task?.id) throw new Error("no task in response");
      setTask(res.task);
      try {
        sessionStorage.setItem("dubaiio:firstTask", res.task.id);
      } catch {
        /* storage may be blocked; the dashboard reads the API anyway */
      }
    } catch (err) {
      setError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  if (task) {
    return (
      <>
        <h1>Saved to your list.</h1>
        <p className={s.lede}>
          That is your first task. It stays on your list until you finish or
          change it.
        </p>
        <div className={s.win}>
          <h2>{task.outcome ?? outcome}</h2>
          <p>Nothing was sent to anyone. No provider was contacted.</p>
          <span className={s.status}>Waiting for you</span>
        </div>
        <div className={s.actions}>
          <Link href="/dashboard" className={s.btnPrimary}>
            Continue
          </Link>
        </div>
      </>
    );
  }

  return (
    <>
      <p className={s.step}>One small thing</p>
      <h1>What is one thing you need to get done?</h1>
      <p className={s.lede}>
        Add it as a task. It goes on your list, and nothing is sent to anyone.
      </p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void create();
        }}
      >
        <div className={s.field}>
          <label htmlFor="task">Task</label>
          <input
            id="task"
            className={s.input}
            value={text}
            maxLength={MAX}
            placeholder="Get my AC serviced before summer"
            autoComplete="off"
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        <p className={s.step}>No idea yet? Start from one of these.</p>
        <div className={s.chips}>
          {IDEAS.map((idea) => (
            <button
              type="button"
              key={idea}
              className={s.chip}
              aria-pressed={text === idea}
              onClick={() => setText(idea)}
            >
              {idea}
            </button>
          ))}
        </div>

        {error ? <FunnelError message={error} onRetry={create} busy={busy} /> : null}

        <div className={s.actions}>
          <button type="submit" className={s.btnPrimary} disabled={busy || !outcome}>
            {busy ? "Saving" : "Add task"}
          </button>
          <Link href="/dashboard" className={s.textBtn}>
            Skip for now
          </Link>
        </div>
      </form>
    </>
  );
}
