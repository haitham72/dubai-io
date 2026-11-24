"use client";
import { useEffect, useState } from "react";
import * as realApi from "@/lib/api";
import type { ForgetResult, MemoryConsent } from "@/lib/api";

export interface MemoryApi {
  getMemoryConsent: () => Promise<MemoryConsent>;
  setMemoryConsent: (c: Pick<MemoryConsent, "read_enabled" | "write_enabled" | "allow_interest_export">) => Promise<MemoryConsent>;
  forgetMemory: () => Promise<ForgetResult>;
}

type Flag = "read_enabled" | "write_enabled" | "allow_interest_export";
const TOGGLES: { id: Flag; label: string; hint: string }[] = [
  { id: "read_enabled", label: "Use my interests to order Discover", hint: "Only ranks what you see; nothing is posted or pre-filled." },
  { id: "write_enabled", label: "Remember my public posts and discussions I save", hint: "Only things you authored or chose to save, with provenance." },
  { id: "allow_interest_export", label: "Share interest topics from my other apps with Community", hint: "Topic labels only, never raw text. Off unless you turn it on." },
];

// Status text comes only from the server's response. Nothing here says "saved" before the server says so.
export default function MemoryPanel({ api = realApi }: { api?: MemoryApi }) {
  const [consent, setConsent] = useState<MemoryConsent | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forgot, setForgot] = useState<ForgetResult | null>(null);

  useEffect(() => {
    let live = true;
    api.getMemoryConsent()
      .then((c) => { if (live) setConsent(c); })
      .catch((e: Error) => { if (live) setLoadError(e.message || "Memory status unavailable"); });
    return () => { live = false; };
  }, [api]);

  async function toggle(flag: Flag) {
    if (!consent || busy) return;
    const next = { read_enabled: consent.read_enabled, write_enabled: consent.write_enabled, allow_interest_export: consent.allow_interest_export, [flag]: !consent[flag] };
    setBusy(flag); setError(null);
    try {
      setConsent(await api.setMemoryConsent(next)); // state comes from the server response only
    } catch (e) {
      setError(`Not changed: ${(e as Error).message || "request failed"}`); // toggle keeps its previous state
    } finally { setBusy(null); }
  }

  async function forget() {
    if (busy) return;
    setBusy("forget"); setError(null); setForgot(null);
    try {
      setForgot(await api.forgetMemory());
    } catch (e) {
      setError(`Forget did not complete: ${(e as Error).message || "request failed"}`);
    } finally { setBusy(null); }
  }

  return (
    <article className="card" data-testid="memory-panel">
      <h2>Connected Memory</h2>
      <p className="ai-text">Choose what Community may use. Everything is off until you turn it on, and each switch shows what the server actually has.</p>
      {loadError && <div className="notice" role="alert">Memory status unavailable: {loadError}. Switches are disabled.</div>}
      {!consent && !loadError && <p className="meta">Loading memory status…</p>}
      {TOGGLES.map((t) => {
        const on = consent ? consent[t.id] : false;
        return (
          <div key={t.id} className="toggle-row">
            <span>{t.label}<br /><span className="meta">{t.hint}</span></span>
            <button type="button" role="switch" aria-checked={on} aria-label={t.label} className="action-box" style={{ maxWidth: 90 }}
              disabled={!consent || busy !== null} onClick={() => toggle(t.id)}>
              {busy === t.id ? "Saving…" : consent ? (on ? "On" : "Off") : "—"}
            </button>
          </div>
        );
      })}
      {consent && <p className="meta" data-testid="consent-meta">You told me · as of {consent.as_of || "not set yet"}{consent.default_off ? " · everything is off" : ""}</p>}
      {error && <div className="notice" role="alert">{error}</div>}
      <button type="button" className="action-box" style={{ maxWidth: 220, marginTop: 14 }} disabled={busy !== null} onClick={forget}>
        {busy === "forget" ? "Forgetting…" : "Forget connected memory"}
      </button>
      {forgot && (
        <p className="meta" role="status" data-testid="forget-result">
          Server reports {forgot.records_forgotten} record(s) and {forgot.facts_erased} fact(s) forgotten{forgot.as_of ? `, as of ${forgot.as_of}` : ""}.
        </p>
      )}
      <p className="meta">Forget removes what Community stored through memory. It does not delete your posts.</p>
    </article>
  );
}
