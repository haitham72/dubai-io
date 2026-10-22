"use client";

import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import { ApiError, apiPost, type ChatMessage } from "@/lib/api";
import { useApi } from "@/lib/use-api";
import { useState } from "react";

export default function ThreadDetail({ threadId }: { threadId: string }) {
  const { data, error, loading, reload } = useApi<{
    messages?: ChatMessage[];
    thread?: { title?: string };
  }>(`/api/chats/${encodeURIComponent(threadId)}/messages`);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function send(event?: React.FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    setSending(true);
    setNotice(null);
    try {
      await apiPost(`/api/chats/${encodeURIComponent(threadId)}/messages`, {
        text,
      });
      setNotice("Sent. Demo personas may reply; they are not real people.");
      reload();
    } catch (err) {
      setNotice(
        err instanceof ApiError
          ? `Could not send (${err.status}): ${err.message}`
          : "Could not send.",
      );
    } finally {
      setSending(false);
    }
  }

  const messages = data?.messages ?? [];

  return (
    <>
      <div className="appHead">
        <BackLink href="/app/chat" label="Chat" />
        <h1>{data?.thread?.title ?? "Thread"}</h1>
        <p>
          <DemoPill /> Messages from anyone but you are demo personas — not
          real people, not authoritative facts.
        </p>
      </div>
      {loading ? <LoadingState label="Loading messages…" /> : null}
      {error ? (
        <ErrorState message={`Thread unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {!loading && !error && messages.length === 0 ? (
        <EmptyState title="No messages yet" body="Say hello below." />
      ) : null}
      {messages.length > 0 ? (
        <SectionCard title="Messages">
          <ul className="listRows">
            {messages.map((message, i) => {
              const mine = message.mine ?? message.author === "You";
              return (
                <li
                  key={message.id ?? i}
                  className="rowCard"
                  style={mine ? { background: "var(--band)" } : undefined}
                >
                  <div className="rowMeta">
                    <span>{message.author ?? "Someone"}</span>
                    {message.created_at ?? message.at ? (
                      <span>{message.created_at ?? message.at}</span>
                    ) : null}
                    {!mine ? <DemoPill /> : null}
                    <Provenance value={message.provenance} />
                  </div>
                  <p style={{ marginTop: 8 }}>{message.text}</p>
                </li>
              );
            })}
          </ul>
        </SectionCard>
      ) : null}
      {notice ? (
        <p role="status" style={{ color: "var(--muted)" }}>
          {notice}
        </p>
      ) : null}
      <form className="inlineForm" onSubmit={send}>
        <input
          className="textInput"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Write a message…"
          aria-label="Write a message"
          maxLength={500}
        />
        <button
          type="submit"
          className="btnPrimary"
          disabled={sending || !draft.trim()}
        >
          {sending ? "Sending…" : "Send"}
        </button>
      </form>
    </>
  );
}
