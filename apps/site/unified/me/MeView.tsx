"use client";

import { useCallback, useEffect, useState } from "react";
import { MapPin, Sparkles, Users, WashingMachine } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { MailResultList } from "../assistant/PlaceCards";
import { TOLD_LABELS, type ToldFact } from "../data/social";
import { useApi } from "../data/use-api";
import { ThemeToggle } from "../shell/Rail";
import { Avatar, Button } from "../ui";
import s from "./me.module.css";

const FACT_ICON: Record<string, LucideIcon> = {
  area: MapPin,
  household: Users,
  services: WashingMachine,
  clothing_size: Sparkles,
};

type Conn = {
  id: string;
  label: string;
  status: string;
  can_connect: boolean;
  account_label?: string | null;
};

type TimelineItem = { id: string; at?: string; text?: string; provenance?: string; kind?: string };
type Hypothesis = { id: string; statement?: string; confidence?: number; status?: string };

export function MeView() {
  const memory = useApi<{ told?: ToldFact[] }>("/api/session/memory");
  const told = memory.data?.told ?? [];
  const [conns, setConns] = useState<Conn[]>([]);
  const [mailBlocker, setMailBlocker] = useState<string | null>(null);
  const [mailItems, setMailItems] = useState<{ id: string; title: string; body: string; provenance?: string; demo?: boolean }[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [noticed, setNoticed] = useState<Hypothesis[]>([]);

  const refreshProfiler = useCallback(async () => {
    try {
      const [c, m, t, h] = await Promise.all([
        fetch("/api/auth/connections", { credentials: "include" }).then((r) => r.json()),
        fetch("/api/mail/needs-reply", { credentials: "include" }).then((r) => r.json()),
        fetch("/api/memory/timeline", { credentials: "include" }).then((r) => r.json()),
        fetch("/api/memory/hypotheses", { credentials: "include" }).then((r) => r.json()),
      ]);
      setConns(c.providers || []);
      setMailItems(m.items || []);
      setMailBlocker(m.blocker || m.status?.blocker || null);
      setTimeline(t.items || []);
      setNoticed(h.items || []);
    } catch {
      /* keep last good */
    }
  }, []);

  useEffect(() => {
    void refreshProfiler();
  }, [refreshProfiler]);

  const connectMail = () => {
    window.open("/api/auth/google/start?caps=mail", "dubaiio-google", "width=520,height=720");
  };

  return (
    <div className={s.page} data-testid="me-screen">
      <div className={s.layout}>
        <div className={s.main}>
          <header className={s.head}>
            <h1>Me</h1>
          </header>

          <div className={s.profile}>
            <Avatar label="You" size={56} />
            <div className={s.profileText}>
              <b>You</b>
              <small>Dubai-io residence companion · temporal profiler</small>
            </div>
          </div>

          <section className={s.section} aria-labelledby="told-title">
            <h2 id="told-title">You told me</h2>
            <p>This helps me give more relevant suggestions.</p>
            {memory.loading ? <div className={s.state}>Loading what you saved…</div> : null}
            {memory.error ? (
              <div className={s.state} role="alert">
                {memory.error}
                <button type="button" className={s.retry} onClick={memory.reload}>
                  Try again
                </button>
              </div>
            ) : null}
            {!memory.loading && !memory.error && told.length === 0 ? (
              <div className={s.card}>
                <div className={s.empty}>
                  Nothing saved yet. Complete onboarding on Assistant home or tell me your area in chat.
                </div>
              </div>
            ) : null}
            {told.length > 0 ? (
              <div className={s.card}>
                {told.map((f) => {
                  const I = FACT_ICON[f.key ?? ""] ?? Sparkles;
                  return (
                    <div key={f.key} className={s.factRow} data-testid={`told-${f.key}`}>
                      <I size={18} strokeWidth={1.75} aria-hidden style={{ color: "var(--accent)", flexShrink: 0 }} />
                      <span className={s.factLabel}>{TOLD_LABELS[f.key ?? ""] ?? f.key}</span>
                      <span className={s.factValue}>{f.value}</span>
                      <span className={s.youTag}>You told me</span>
                    </div>
                  );
                })}
              </div>
            ) : null}
          </section>

          <section className={s.section} aria-labelledby="mail-title" data-testid="me-mail">
            <h2 id="mail-title">Inbox · needs a reply</h2>
            <p>Grok-style scan of job / application mail. Linked into your temporal timeline.</p>
            {mailBlocker && !mailItems.length ? (
              <div className={s.card}>
                <div className={s.empty}>{mailBlocker}</div>
                <div style={{ padding: "0 16px 16px" }}>
                  <Button variant="primary" onClick={connectMail}>Connect Google mail</Button>
                </div>
              </div>
            ) : null}
            {mailItems.length > 0 ? <MailResultList heading="Needs a reply" items={mailItems} /> : null}
          </section>

          <section className={s.section} aria-labelledby="timeline-title">
            <h2 id="timeline-title">Timeline</h2>
            <p>Events from what you told me and connected sources (mail, tasks).</p>
            <div className={s.card} data-testid="me-timeline">
              {timeline.length === 0 ? (
                <div className={s.empty}>No timeline events yet.</div>
              ) : (
                timeline.slice(0, 12).map((ev) => (
                  <div key={ev.id} className={s.factRow}>
                    <span className={s.factLabel}>{ev.kind || "event"}</span>
                    <span className={s.factValue}>{ev.text}</span>
                    <span className={s.youTag}>{ev.provenance || "stored"}</span>
                  </div>
                ))
              )}
            </div>
          </section>

          <section className={s.section} aria-labelledby="noticed-title">
            <h2 id="noticed-title">I noticed</h2>
            <p>Hypotheses only — Confirm / reject later. They never fill forms or send anything.</p>
            <div className={s.card}>
              {noticed.length === 0 ? (
                <div className={s.empty}>
                  Nothing noticed yet. Guesses only reorder suggestions.
                </div>
              ) : (
                noticed.map((h) => (
                  <div key={h.id} className={s.factRow}>
                    <span className={s.factValue}>{h.statement}</span>
                    <span className={s.youTag}>inferred · {Math.round((h.confidence || 0) * 100)}%</span>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>

        <aside className={s.rail} aria-label="Settings">
          <section className={s.panel}>
            <h3>Connections</h3>
            <p>Google identity + optional Gmail read for the inbox profiler.</p>
            <ul style={{ listStyle: "none", margin: "12px 0 0", padding: 0 }}>
              {conns.map((c) => (
                <li key={c.id} style={{ marginBottom: 8, fontSize: "var(--fs-sm)" }}>
                  <b>{c.label}</b> · {c.status}
                  {c.account_label ? ` · ${c.account_label}` : ""}
                  {c.can_connect || c.status !== "connected" ? (
                    <div style={{ marginTop: 8 }}>
                      <Button variant="secondary" onClick={connectMail}>Connect with mail</Button>
                    </div>
                  ) : null}
                </li>
              ))}
              {!conns.length ? (
                <li style={{ fontSize: "var(--fs-sm)", color: "var(--text-2)" }}>
                  OAuth not configured yet — add Google OAuth keys to enable Connect.
                </li>
              ) : null}
            </ul>
            <div style={{ marginTop: 8 }}>
              <Button variant="secondary" onClick={() => void refreshProfiler()}>Refresh profiler</Button>
            </div>
          </section>
          <section className={s.panel}>
            <h3>Appearance</h3>
            <p>Light mode first. Switch theme for this device.</p>
            <div style={{ marginTop: 12 }}>
              <ThemeToggle />
            </div>
          </section>
          <section className={s.panel}>
            <h3>Privacy</h3>
            <p>
              Health, religion, ethnicity, nationality, gender, sexuality and politics are never inferred. Everything stored about you stays visible here.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
