import { useMemo, useSyncExternalStore } from "react";
import { createMemoryClient, type MemoryClient } from "../apiclient/memory";
import { Button } from "../ui";
import { createApprovalFlow, type FlowState } from "./memoryFlow";

/** The approval card. It lists exactly which fields would be shared with memory; nothing is sent before "Approve". */
export function ApprovalCard({ state, onApprove, onCancel, onAllow }: { state: FlowState; onApprove: () => void; onCancel: () => void; onAllow: () => void }) {
  const p = state.preview;
  const blockers = p?.blockers ?? [];
  return (
    <div role="dialog" aria-label="Save to memory" data-testid="memory-approval">
      <strong>Save this message to memory?</strong>
      {state.phase === "loading" && <p>Checking with the server…</p>}
      {p && !p.offerable && <p role="status">{blockers.find((b) => b.code === "held_back")?.message ?? "Held back."}</p>}
      {p && p.offerable && <>
        <p>These fields will be shared with memory:</p>
        <ul>{p.fields.map((f) => <li key={f.name}><strong>{f.name}:</strong> {f.value}</li>)}</ul>
        {p.provenance && <p>Provenance: {p.provenance} · as of {p.as_of}</p>}
        {blockers.map((b) => <p key={b.code} role="status">{b.message}</p>)}
        {blockers.some((b) => b.code === "ai_default_off") && <Button onClick={onAllow}>Allow memory in this chat</Button>}
      </>}
      {state.phase === "done" && state.result && <p role="status" data-testid="memory-done">Server status: {state.result.status} (as of {state.result.as_of}).</p>}
      {state.phase === "error" && <p role="alert">{state.error}</p>}
      {state.phase !== "done" && <>
        {p?.offerable && <Button onClick={onApprove} disabled={state.phase !== "ready" || !p.can_save_now}>{state.phase === "saving" ? "Saving…" : "Approve and save"}</Button>}
        <Button onClick={onCancel}>Cancel</Button>
      </>}
      {state.phase === "done" && <Button onClick={onCancel}>Close</Button>}
    </div>
  );
}

/** Per-message action. Only for signed-in real-mode text messages that a person wrote. */
export default function SaveToMemory({ sessionToken, conversationId, messageId, client }: { sessionToken: string; conversationId: string; messageId: string; client?: MemoryClient }) {
  const flow = useMemo(
    () => createApprovalFlow(client ?? createMemoryClient(sessionToken), conversationId, messageId),
    [client, sessionToken, conversationId, messageId],
  );
  const state = useSyncExternalStore(flow.subscribe, flow.get, flow.get);
  if (state.phase === "closed") return <Button onClick={flow.open}>Save to memory</Button>;
  return <ApprovalCard state={state} onApprove={flow.approve} onCancel={flow.cancel} onAllow={flow.allowInThisChat} />;
}
