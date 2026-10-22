"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionCard,
} from "@/components/chrome";
import { ApiError, apiPost, type ChatThread } from "@/lib/api";
import { useApi } from "@/lib/use-api";

type Segment = "all" | "unread" | "groups" | "communities";
type CallTab = "calls" | "contacts" | "keypad" | "favorites";

interface Contact {
  id: string;
  name: string;
  phone: string;
  favorite?: boolean;
}

interface CallEntry {
  id: string;
  name: string;
  phone: string;
  at: string;
}

function Threads() {
  const [segment, setSegment] = useState<Segment>("all");
  const { data, error, loading, reload } = useApi<{ threads?: ChatThread[] }>(
    "/api/chats",
  );
  const threads = useMemo(() => {
    const all = data?.threads ?? [];
    if (segment === "unread") return all.filter((t) => (t.unread ?? 0) > 0);
    if (segment === "groups")
      return all.filter((t) => t.kind === "group");
    if (segment === "communities")
      return all.filter((t) => t.kind === "community");
    return all;
  }, [data, segment]);

  const segments: Array<[Segment, string]> = [
    ["all", "All"],
    ["unread", "Unread"],
    ["groups", "Groups"],
    ["communities", "Communities"],
  ];

  return (
    <SectionCard
      title="Threads"
      action={
        <button type="button" className="chip" onClick={reload}>
          Refresh
        </button>
      }
    >
      <div className="chipRow" role="group" aria-label="Thread segments">
        {segments.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className="chip"
            aria-pressed={segment === key}
            onClick={() => setSegment(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {loading ? <LoadingState label="Loading threads…" /> : null}
      {error ? (
        <ErrorState message={`Threads unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {threads.length === 0 && !loading && !error ? (
        <EmptyState
          title="No threads here"
          body={
            segment === "all"
              ? "Join a community in Feed and it will open a thread here."
              : "Nothing in this segment yet."
          }
        />
      ) : (
        <ul className="listRows">
          {threads.map((thread) => (
            <li key={thread.id} className="rowCard">
              <h3>
                <Link href={`/app/chat/${encodeURIComponent(thread.id)}`}>
                  {thread.title ?? thread.id}
                </Link>
              </h3>
              {thread.kind === "community" || thread.kind === "group" ? (
                <div className="rowMeta">
                  <DemoPill />
                </div>
              ) : null}
              <div className="rowMeta">
                {(thread.unread ?? 0) > 0 ? (
                  <span>{thread.unread} unread</span>
                ) : null}
                <Link href={`/app/chat/${encodeURIComponent(thread.id)}`}>
                  Open →
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

function CallsPanel() {
  const [tab, setTab] = useState<CallTab>("calls");
  const [query, setQuery] = useState("");
  const contacts = useApi<{ contacts?: Contact[] }>("/api/contacts");
  const calls = useApi<{ calls?: CallEntry[] }>("/api/calls");
  const [notice, setNotice] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [digits, setDigits] = useState("");

  const tabs: Array<[CallTab, string]> = [
    ["calls", "Calls"],
    ["contacts", "Contacts"],
    ["keypad", "Keypad"],
    ["favorites", "Favorites"],
  ];

  const q = query.trim().toLowerCase();
  const filtered = (contacts.data?.contacts ?? []).filter(
    (c) =>
      !q ||
      c.name.toLowerCase().includes(q) ||
      c.phone.replace(/[^0-9+]/g, "").includes(q.replace(/[^0-9+]/g, "")),
  );
  const favorites = filtered.filter((c) => c.favorite);

  async function addContact(event?: React.FormEvent) {
    event?.preventDefault();
    if (!name.trim() || !phone.trim()) return;
    setNotice(null);
    try {
      await apiPost("/api/contacts", { name: name.trim(), phone: phone.trim() });
      setName("");
      setPhone("");
      setNotice("Contact saved on this device session.");
      contacts.reload();
    } catch (err) {
      setNotice(
        err instanceof ApiError ? `Could not save (${err.status})` : "Could not save.",
      );
    }
  }

  async function startCall(contactId: string, tel?: string) {
    setNotice(null);
    try {
      const result = await apiPost<{ tel?: string }>("/api/calls", {
        contact_id: contactId,
      });
      calls.reload();
      const number = result.tel ?? tel;
      setNotice(
        number
          ? `Logged. Opening your dialer — the phone app places the call, Dubai-io never claims it connected.`
          : "Call logged.",
      );
      if (number && typeof window !== "undefined") window.location.href = number;
    } catch (err) {
      setNotice(
        err instanceof ApiError ? `Could not log (${err.status})` : "Could not log.",
      );
    }
  }

  return (
    <SectionCard title="Calls">
      <form
        className="inlineForm"
        onSubmit={(e) => e.preventDefault()}
        role="search"
      >
        <input
          className="textInput"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search contacts…"
          aria-label="Search contacts"
        />
      </form>
      <div className="chipRow" role="group" aria-label="Calls tabs">
        {tabs.map(([key, label]) => (
          <button
            key={key}
            type="button"
            className="chip"
            aria-pressed={tab === key}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "calls" ? (
        <>
          {calls.loading ? <LoadingState label="Loading call log…" /> : null}
          {calls.error ? (
            <ErrorState message={`Call log unavailable: ${calls.error}`} onRetry={calls.reload} />
          ) : null}
          {(calls.data?.calls ?? []).length === 0 && !calls.loading && !calls.error ? (
            <EmptyState
              title="No calls yet"
              body="Calls you start from a contact are logged here. This log never reads your phone's call history."
            />
          ) : (
            <ul className="listRows">
              {(calls.data?.calls ?? []).map((call) => (
                <li key={call.id} className="rowCard">
                  <h3>{call.name}</h3>
                  <div className="rowMeta">
                    <span>{call.phone}</span>
                    <span>{call.at}</span>
                    <span>started in Dubai-io</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}

      {tab === "contacts" || tab === "favorites" ? (
        <>
          {contacts.loading ? <LoadingState label="Loading contacts…" /> : null}
          {contacts.error ? (
            <ErrorState
              message={`Contacts unavailable: ${contacts.error}`}
              onRetry={contacts.reload}
            />
          ) : null}
          {(tab === "favorites" ? favorites : filtered).length === 0 &&
          !contacts.loading &&
          !contacts.error ? (
            <EmptyState
              title={tab === "favorites" ? "No favorites" : "No contacts"}
              body={
                tab === "favorites"
                  ? "Mark contacts as favorites in the prototype to pin them here."
                  : "Add your first contact below — contacts live in this session."
              }
            />
          ) : (
            <ul className="listRows">
              {(tab === "favorites" ? favorites : filtered).map((contact) => (
                <li key={contact.id} className="rowCard">
                  <h3>{contact.name}</h3>
                  <div className="rowMeta">
                    <span>{contact.phone}</span>
                    {contact.favorite ? <span>★ favorite</span> : null}
                  </div>
                  <div className="chipRow">
                    <a className="chip" href={`tel:${contact.phone.replace(/[^+0-9]/g, "")}`}>
                      Dial via phone app
                    </a>
                    <button
                      type="button"
                      className="chip"
                      onClick={() => startCall(contact.id, `tel:${contact.phone.replace(/[^+0-9]/g, "")}`)}
                    >
                      Log &amp; call
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
          {tab === "contacts" ? (
            <form className="inlineForm" onSubmit={addContact}>
              <input
                className="textInput"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Name"
                aria-label="Contact name"
                maxLength={80}
              />
              <input
                className="textInput"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+971 …"
                aria-label="Contact phone"
                inputMode="tel"
              />
              <button type="submit" className="btnPrimary">
                Add
              </button>
            </form>
          ) : null}
        </>
      ) : null}

      {tab === "keypad" ? (
        <>
          <p style={{ color: "var(--muted)" }}>
            Type a number, then open it in your phone app. Dubai-io dials
            nothing itself.
          </p>
          <form
            className="inlineForm"
            onSubmit={(e) => e.preventDefault()}
          >
            <input
              className="textInput"
              value={digits}
              onChange={(e) => setDigits(e.target.value)}
              placeholder="+971 4 …"
              aria-label="Number to dial"
              inputMode="tel"
            />
            <a
              className="btnPrimary"
              style={{ textDecoration: "none" }}
              href={`tel:${digits.replace(/[^+0-9]/g, "")}`}
            >
              Dial
            </a>
          </form>
        </>
      ) : null}

      {notice ? (
        <p role="status" style={{ color: "var(--muted)" }}>
          {notice}
        </p>
      ) : null}
    </SectionCard>
  );
}

export default function Chat() {
  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Chat</h1>
        <p>
          Threads, groups and communities — the assistant stays pinned at the
          top of Ask. <DemoPill /> Group members are demo personas.
        </p>
      </div>
      <Threads />
      <CallsPanel />
    </>
  );
}
