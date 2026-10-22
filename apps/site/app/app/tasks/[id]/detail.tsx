"use client";

import { useState } from "react";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import { ApiError, apiPost, type TaskItem } from "@/lib/api";
import { useApi } from "@/lib/use-api";

const COMMANDS = ["complete", "pause", "cancel"] as const;

export default function Detail({ id }: { id: string }) {
  const { data, error, loading, reload } = useApi<TaskItem>(
    `/api/tasks/${encodeURIComponent(id)}`,
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function run(command: string) {
    setBusy(command);
    setNotice(null);
    try {
      await apiPost(`/api/tasks/${encodeURIComponent(id)}/commands`, {
        kind: command,
        expected_revision: (data as { revision?: number })?.revision ?? 1,
        command_key: `${command}-${Date.now()}`,
      });
      setNotice(`Command ${command} recorded.`);
      reload();
    } catch (err) {
      setNotice(
        err instanceof ApiError
          ? `Command failed (${err.status}): ${err.message}`
          : "Command failed.",
      );
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Task</h1>
      </div>
      {loading ? <LoadingState label="Loading task…" /> : null}
      {error ? (
        <ErrorState message={`Task unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {data ? (
        <SectionCard
          title={data.title ?? id}
          action={<Provenance value="user_supplied" />}
        >
          {"detail" in data && data.detail ? <p>{data.detail}</p> : null}
          <div className="rowMeta">
            {data.status ? <span>{data.status}</span> : null}
            {data.due_at ? <span>due {data.due_at}</span> : null}
            {data.decision?.action_id ? (
              <a href={`/app/decisions/${data.decision.action_id}`}>
                Open decision →
              </a>
            ) : null}
          </div>
          <div className="chipRow" role="group" aria-label="Task commands">
            {COMMANDS.map((command) => (
              <button
                key={command}
                type="button"
                className="chip"
                disabled={busy !== null}
                onClick={() => run(command)}
              >
                {busy === command ? "Working…" : command}
              </button>
            ))}
          </div>
          {notice ? (
            <p role="status" style={{ color: "var(--muted)" }}>
              {notice}
            </p>
          ) : null}
        </SectionCard>
      ) : !loading && !error ? (
        <EmptyState title="Task not found" body="It may have been removed." />
      ) : null}
    </>
  );
}
