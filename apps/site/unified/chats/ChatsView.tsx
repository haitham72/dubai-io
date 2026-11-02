"use client";

import { useMemo, useState } from "react";
import { formatWhen, isDemoProvenance, type ChatMessage, type ChatThread } from "../data/social";
import { useApi } from "../data/use-api";
import { Avatar, DemoPill, ListRow, SearchField } from "../ui";
import s from "./chats.module.css";

type Filter = "all" | "unread" | "groups" | "communities";

function ThreadMessages({ threadId }: { threadId: string }) {
  const { data, error, loading, reload } = useApi<{
    thread?: { title?: string; kind?: string };
    messages?: ChatMessage[];
  }>(`/api/chats/${encodeURIComponent(threadId)}/messages`);

  const messages = data?.messages ?? [];
  const demoThread = data?.thread?.kind === "group" || data?.thread?.kind === "community";

  if (loading) {
    return <div className={s.state} role="status">Loading messages…</div>;
  }
  if (error) {
    return (
      <div className={s.state} role="alert">
        {error}
        <button type="button" className={s.retry} onClick={reload}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <>
      <header className={s.threadHead}>
        <h2>{data?.thread?.title ?? "Conversation"}</h2>
        <p>
          {demoThread ? (
            <>
              <DemoPill /> Demo personas — not real people or authoritative facts.
            </>
          ) : (
            "Messages in this thread."
          )}
        </p>
      </header>
      <div className={s.messages} role="log" aria-live="polite">
        {messages.length === 0 ? (
          <div className={s.emptyPane}>
            <strong>No messages yet</strong>
            <span>Say hello when sending is wired on desktop.</span>
          </div>
        ) : (
          messages.map((m, i) => {
            const mine = m.mine ?? m.author === "You";
            return (
              <div key={m.id ?? i} style={{ alignSelf: mine ? "flex-end" : "flex-start", maxWidth: "72%" }}>
                {!mine ? (
                  <div className={s.bubbleMeta}>
                    <span>{m.author ?? "Someone"}</span>
                    {isDemoProvenance(m.provenance) ? <DemoPill /> : null}
                    {m.at || m.created_at ? <span>{formatWhen(m.at ?? m.created_at)}</span> : null}
                  </div>
                ) : null}
                <div className={`${s.bubble} ${mine ? s.bubbleMine : s.bubbleTheirs}`}>{m.text}</div>
              </div>
            );
          })
        )}
      </div>
    </>
  );
}

export function ChatsView() {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const { data, error, loading, reload } = useApi<{ threads?: ChatThread[] }>("/api/chats");

  const threads = useMemo(() => {
    let list = data?.threads ?? [];
    if (filter === "unread") list = list.filter((t) => (t.unread ?? 0) > 0);
    if (filter === "groups") list = list.filter((t) => t.kind === "group");
    if (filter === "communities") list = list.filter((t) => t.kind === "community");
    const q = query.trim().toLowerCase();
    if (q) list = list.filter((t) => (t.title ?? t.id).toLowerCase().includes(q) || (t.last ?? "").toLowerCase().includes(q));
    return list;
  }, [data, filter, query]);

  const filters: [Filter, string][] = [
    ["all", "All"],
    ["unread", "Unread"],
    ["groups", "Groups"],
    ["communities", "Communities"],
  ];

  return (
    <div className={s.page} data-testid="chats-view">
      <div className={s.layout}>
        <div className={s.listPane}>
          <div className={s.listHead}>
            <h1>Chats</h1>
            <SearchField placeholder="Search chats…" value={query} onChange={setQuery} />
          </div>
          <div className={s.filters} role="group" aria-label="Filter chats">
            {filters.map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={`${s.filter} ${filter === id ? s.filterActive : ""}`}
                aria-pressed={filter === id}
                onClick={() => setFilter(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <div className={s.list}>
            {loading ? <div className={s.state}>Loading threads…</div> : null}
            {error ? (
              <div className={s.state} role="alert">
                {error}
                <button type="button" className={s.retry} onClick={reload}>
                  Try again
                </button>
              </div>
            ) : null}
            {!loading && !error && threads.length === 0 ? (
              <div className={s.state}>
                No chats here yet. Join a community in the feed to open a group thread.
              </div>
            ) : null}
            {threads.map((t) => (
              <ListRow
                key={t.id}
                selected={selected === t.id}
                onClick={() => setSelected(t.id)}
                leading={<Avatar label={(t.title ?? "?").slice(0, 2)} size={48} />}
                title={
                  <>
                    {t.title ?? t.id}
                    {t.kind === "group" || t.kind === "community" ? <> <DemoPill /></> : null}
                  </>
                }
                subtitle={t.last ? `${t.last_author ? `${t.last_author}: ` : ""}${t.last}` : "No messages yet"}
                trailing={
                  <>
                    {t.at ? <span className={s.rowTime}>{formatWhen(t.at)}</span> : null}
                    {(t.unread ?? 0) > 0 ? <span className={s.unread}>{t.unread}</span> : null}
                  </>
                }
              />
            ))}
          </div>
        </div>
        <div className={s.threadPane}>
          {selected ? (
            <ThreadMessages threadId={selected} />
          ) : (
            <div className={s.emptyPane}>
              <strong>Select a chat</strong>
              <span>Pick a conversation from the list to read messages.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
