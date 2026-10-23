"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { FunnelError, funnelStyles as s } from "@/components/funnel";
import { apiGet, describeError, type TaskItem } from "@/lib/api";
import { ensureSession } from "@/lib/session";

interface Fact {
  key?: string;
  value?: string;
}

const LABELS: Record<string, string> = {
  area: "Area",
  household: "Household",
  services: "Services",
};

function statusLabel(status?: string): string {
  if (status === "WAITING_USER") return "Waiting for you";
  if (!status) return "Status unknown";
  return status.replace(/_/g, " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
}

/**
 * Where the Dubai-io app lives. Cookies are shared across ports on one host,
 * so the same anonymous session carries over. Override for deployments.
 */
function appUrl(): string {
  const fixed = process.env.NEXT_PUBLIC_PWA_URL;
  if (fixed) return fixed;
  return `${window.location.protocol}//${window.location.hostname}:8030/`;
}

export default function Handoff() {
  const [facts, setFacts] = useState<Fact[] | null>(null);
  const [tasks, setTasks] = useState<TaskItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);
  const [href, setHref] = useState("/app");

  useEffect(() => {
    setHref(appUrl());
  }, []);

  useEffect(() => {
    let live = true;
    setError(null);
    ensureSession()
      .then(() =>
        Promise.all([
          apiGet<{ told?: Fact[] }>("/api/session/memory"),
          apiGet<{ tasks?: TaskItem[] }>("/api/tasks?limit=5"),
        ]),
      )
      .then(([memory, list]) => {
        if (!live) return;
        setFacts(memory.told ?? []);
        setTasks(list.tasks ?? []);
      })
      .catch((err: unknown) => {
        if (live) setError(describeError(err));
      });
    return () => {
      live = false;
    };
  }, [nonce]);

  const loading = !error && (facts === null || tasks === null);

  return (
    <>
      <h1>You are set up.</h1>
      <p className={s.lede}>
        Here is what Dubai-io has so far. Open the app to keep going: chat,
        services, the feed and your calls.
      </p>

      {error ? (
        <FunnelError message={error} onRetry={() => setNonce((n) => n + 1)} />
      ) : null}

      {loading ? <p className={s.lede}>Loading what you saved</p> : null}

      {facts ? (
        <section aria-label="You told me">
          <p className={s.step}>You told me</p>
          {facts.length > 0 ? (
            <ul className={s.saved}>
              {facts.map((f) => (
                <li key={f.key}>
                  <span>{LABELS[f.key ?? ""] ?? f.key}</span>
                  <span>{f.value}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className={s.panel}>
              <h2>Nothing saved yet</h2>
              <p>
                You skipped setup. Anything you tell the assistant in the app
                shows up here and in the app, where you can edit or forget it.{" "}
                <Link href="/setup">Answer the three questions</Link>
              </p>
            </div>
          )}
        </section>
      ) : null}

      {tasks ? (
        <section aria-label="Your tasks">
          <p className={s.step}>Your tasks</p>
          {tasks.length > 0 ? (
            <ul className={s.saved}>
              {tasks.map((t) => (
                <li key={t.id}>
                  <span>{t.outcome ?? t.title}</span>
                  <span>{statusLabel(t.status)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className={s.panel}>
              <h2>No tasks yet</h2>
              <p>
                Tasks you add appear here and on your Home in the app.{" "}
                <Link href="/first-win">Add your first task</Link>
              </p>
            </div>
          )}
        </section>
      ) : null}

      <div className={s.actions} style={{ marginTop: 16 }}>
        <a href={href} className={s.btnPrimary}>
          Open Dubai-io
        </a>
        <Link href="/app" className={s.textBtn}>
          Open the in-site preview instead
        </Link>
      </div>
    </>
  );
}
