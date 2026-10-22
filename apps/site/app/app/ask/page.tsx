"use client";

import { useState } from "react";
import {
  BackLink,
  DemoPill,
  EmptyState,
  SectionCard,
} from "@/components/chrome";
import { ApiError, apiPost } from "@/lib/api";

interface Turn {
  role: "you" | "luna";
  text: string;
}

export default function Ask() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(event?: React.FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    setError(null);
    setTurns((t) => [...t, { role: "you", text }]);
    setBusy(true);
    try {
      const reply = await apiPost<{ text?: string; reply?: string }>(
        "/api/luna/turn",
        { text },
      );
      setTurns((t) => [
        ...t,
        { role: "luna", text: reply.text ?? reply.reply ?? "…" },
      ]);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `Luna is unavailable (${err.status}): ${err.message}`
          : "Luna is unavailable.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Ask</h1>
        <p>
          Ask anything about your day in Dubai. <DemoPill /> Replies follow the
          same rules as everywhere else: provenance on numbers, no invented
          status.
        </p>
      </div>
      <SectionCard title="Conversation">
        {turns.length === 0 ? (
          <EmptyState
            title="Nothing asked yet"
            body="Try: “What needs me today?” — answers come from the live backend, or say so when it is unreachable."
          />
        ) : (
          <ul className="listRows">
            {turns.map((turn, i) => (
              <li
                key={i}
                className="rowCard"
                style={
                  turn.role === "you"
                    ? { background: "var(--band)" }
                    : undefined
                }
              >
                <div className="rowMeta">
                  <span>{turn.role === "you" ? "You" : "Dubai-io"}</span>
                  {turn.role === "luna" ? <DemoPill /> : null}
                </div>
                <p style={{ marginTop: 8 }}>{turn.text}</p>
              </li>
            ))}
          </ul>
        )}
        {error ? (
          <p role="alert" style={{ color: "var(--muted)" }}>
            {error} Your words stay in this box — nothing was sent.
          </p>
        ) : null}
        <form className="inlineForm" onSubmit={send}>
          <label htmlFor="ask-input" className="rowMeta" style={{ display: "none" }}>
            Ask Dubai-io
          </label>
          <input
            id="ask-input"
            className="textInput"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about your day…"
            autoComplete="off"
          />
          <button type="submit" className="btnPrimary" disabled={busy || !draft.trim()}>
            {busy ? "Sending…" : "Send"}
          </button>
        </form>
      </SectionCard>
    </>
  );
}
