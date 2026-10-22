"use client";

import { useState } from "react";
import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionCard,
} from "@/components/chrome";
import { ApiError, apiPost } from "@/lib/api";
import { useApi } from "@/lib/use-api";

interface ActionDetail {
  id?: string;
  status?: string;
  recipient?: string;
  revision?: number;
  snapshot_hash?: string;
  fixed_total_aed?: number | null;
  execution_available?: boolean;
  evidence?: unknown;
  fields?: Record<string, { value?: string }>;
}

export default function Detail({ actionId }: { actionId: string }) {
  const { data, error, loading, reload } = useApi<ActionDetail>(
    `/api/actions/${encodeURIComponent(actionId)}`,
  );
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function approve(action: ActionDetail) {
    if (!action.snapshot_hash || !action.revision) {
      setNotice("This decision has no approval snapshot — reload first.");
      return;
    }
    setBusy(true);
    setNotice(null);
    try {
      const key =
        typeof crypto !== "undefined" && "randomUUID" in crypto
          ? crypto.randomUUID()
          : `key-${Date.now()}`;
      const result = await apiPost(
        `/api/actions/${encodeURIComponent(actionId)}/approve`,
        { snapshot_hash: action.snapshot_hash, revision: action.revision },
        { headers: { "Idempotency-Key": key } },
      );
      setNotice(
        `Approved revision ${action.revision}. Server response: ${JSON.stringify(result).slice(0, 200)}`,
      );
      reload();
    } catch (err) {
      setNotice(
        err instanceof ApiError
          ? err.status === 409
            ? "This decision changed since it was shown. Reload and review the latest revision before approving."
            : `Approval failed (${err.status}): ${err.message}`
          : "Approval failed.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>
          Decision <DemoPill />
        </h1>
        <p>
          Approve sends exactly the revision shown below — nothing more. Status
          only ever comes from an authoritative event, never from this page.
        </p>
      </div>
      {loading ? <LoadingState label="Loading decision…" /> : null}
      {error ? (
        <ErrorState message={`Decision unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {data ? (
        <SectionCard title={data.recipient ? `With ${data.recipient}` : "Decision"}>
          <div className="rowMeta">
            {data.status ? <span>status: {data.status}</span> : null}
            {typeof data.revision === "number" ? (
              <span>revision {data.revision}</span>
            ) : null}
            {typeof data.fixed_total_aed === "number" ? (
              <span>AED {data.fixed_total_aed.toFixed(2)} (fixed)</span>
            ) : null}
          </div>
          {data.fields ? (
            <ul className="listRows" style={{ marginTop: 12 }}>
              {Object.entries(data.fields).map(([name, field]) => (
                <li key={name} className="rowCard">
                  <h3>{name}</h3>
                  <p>{field?.value ?? "—"}</p>
                </li>
              ))}
            </ul>
          ) : null}
          <div className="chipRow">
            <button
              type="button"
              className="btnPrimary"
              disabled={busy || !data.execution_available}
              onClick={() => approve(data)}
            >
              {busy ? "Approving…" : "Approve this revision"}
            </button>
          </div>
          {!data.execution_available ? (
            <p style={{ color: "var(--muted)" }}>
              Not currently approvable (status: {data.status ?? "unknown"}).
              Prepared-but-unsendable items stay quietly on the list.
            </p>
          ) : null}
          {notice ? (
            <p role="status" style={{ color: "var(--muted)" }}>
              {notice}
            </p>
          ) : null}
        </SectionCard>
      ) : !loading && !error ? (
        <EmptyState
          title="Decision not found"
          body="It may have been discarded or belong to another session."
        />
      ) : null}
    </>
  );
}
