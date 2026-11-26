"use client";

import { useEffect, useState } from "react";
import * as realApi from "@/lib/api";
import type {
  ForgetResult,
  LowerMemoryResult,
  MemoryConsent,
  MemoryConsentInput,
} from "@/lib/api";

export interface MemoryApi {
  getMemoryConsent: () => Promise<MemoryConsent>;
  setMemoryConsent: (c: MemoryConsentInput) => Promise<MemoryConsent>;
  forgetMemory: () => Promise<ForgetResult>;
  lowerCommunityMemory?: () => Promise<LowerMemoryResult>;
}

type Flag =
  | "read_enabled"
  | "remember_saved_discussions"
  | "remember_public_posts"
  | "allow_interest_export";

const TOGGLES: { id: Flag; label: string; hint: string }[] = [
  {
    id: "read_enabled",
    label: "Use my interests to order Discover",
    hint: "Only ranks what you see; nothing is posted or pre-filled.",
  },
  {
    id: "remember_saved_discussions",
    label: "Remember my saved discussions",
    hint: "Only bookmarks and discussions you explicitly choose to save.",
  },
  {
    id: "remember_public_posts",
    label: "Remember my public posts",
    hint: "Only public posts you authored, with provenance. Private groups are excluded.",
  },
  {
    id: "allow_interest_export",
    label: "Share interest topics from my other apps with Community",
    hint: "Topic labels only, never raw text. Off unless you turn it on.",
  },
];

function flagValue(consent: MemoryConsent | null, flag: Flag): boolean {
  if (!consent) return false;
  if (flag === "remember_saved_discussions") {
    return consent.remember_saved_discussions ?? consent.write_enabled ?? false;
  }
  if (flag === "remember_public_posts") {
    return consent.remember_public_posts ?? consent.write_enabled ?? false;
  }
  return !!consent[flag];
}

// Status text comes only from the server's response. Nothing here says "saved" before the server says so.
export default function MemoryPanel({ api = realApi }: { api?: MemoryApi }) {
  const [consent, setConsent] = useState<MemoryConsent | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lowered, setLowered] = useState<LowerMemoryResult | null>(null);
  const [forgot, setForgot] = useState<ForgetResult | null>(null);

  useEffect(() => {
    let live = true;
    api
      .getMemoryConsent()
      .then((c) => {
        if (live) setConsent(c);
      })
      .catch((e: Error) => {
        if (live) setLoadError(e.message || "Memory status unavailable");
      });
    return () => {
      live = false;
    };
  }, [api]);

  async function toggle(flag: Flag) {
    if (!consent || busy) return;
    const savedOn =
      flag === "remember_saved_discussions"
        ? !flagValue(consent, "remember_saved_discussions")
        : flagValue(consent, "remember_saved_discussions");
    const postsOn =
      flag === "remember_public_posts"
        ? !flagValue(consent, "remember_public_posts")
        : flagValue(consent, "remember_public_posts");
    const next: MemoryConsentInput = {
      read_enabled:
        flag === "read_enabled" ? !consent.read_enabled : consent.read_enabled,
      remember_saved_discussions: savedOn,
      remember_public_posts: postsOn,
      write_enabled: savedOn || postsOn,
      allow_interest_export:
        flag === "allow_interest_export"
          ? !consent.allow_interest_export
          : consent.allow_interest_export,
    };
    setBusy(flag);
    setError(null);
    try {
      setConsent(await api.setMemoryConsent(next));
    } catch (e) {
      setError(`Not changed: ${(e as Error).message || "request failed"}`);
    } finally {
      setBusy(null);
    }
  }

  async function lowerWeights() {
    if (busy) return;
    const fn = api.lowerCommunityMemory ?? realApi.lowerCommunityMemory;
    setBusy("lower");
    setError(null);
    setLowered(null);
    try {
      setLowered(await fn());
    } catch (e) {
      setError(`Lower weight did not complete: ${(e as Error).message || "request failed"}`);
    } finally {
      setBusy(null);
    }
  }

  async function forget() {
    if (busy) return;
    setBusy("forget");
    setError(null);
    setForgot(null);
    try {
      setForgot(await api.forgetMemory());
    } catch (e) {
      setError(`Lower Community memory did not complete: ${(e as Error).message || "request failed"}`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="card" data-testid="memory-panel">
      <h2>Connected Memory</h2>
      <p className="ai-text">
        Choose what Community may use. Everything is off until you turn it on, and each switch shows what the server actually has.
      </p>
      {loadError && (
        <div className="notice" role="alert">
          Memory status unavailable: {loadError}. Switches are disabled.
        </div>
      )}
      {!consent && !loadError && <p className="meta">Loading memory status…</p>}
      {TOGGLES.map((t) => {
        const on = flagValue(consent, t.id);
        return (
          <div key={t.id} className="toggle-row">
            <span>
              {t.label}
              <br />
              <span className="meta">{t.hint}</span>
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={on}
              aria-label={t.label}
              className="action-box"
              style={{ maxWidth: 90 }}
              disabled={!consent || busy !== null}
              onClick={() => toggle(t.id)}
            >
              {busy === t.id ? "Saving…" : consent ? (on ? "On" : "Off") : "—"}
            </button>
          </div>
        );
      })}
      {consent && (
        <p className="meta" data-testid="consent-meta">
          You told me · as of {consent.as_of || "not set yet"}
          {consent.default_off ? " · everything is off" : ""}
        </p>
      )}
      {error && (
        <div className="notice" role="alert">
          {error}
        </div>
      )}
      <div className="actions" style={{ marginTop: 14, flexWrap: "wrap" }}>
        <button
          type="button"
          className="action-box"
          style={{ maxWidth: 230 }}
          disabled={busy !== null}
          onClick={lowerWeights}
        >
          {busy === "lower" ? "Lowering…" : "Lower weight on preferences"}
        </button>
        <button
          type="button"
          className="action-box"
          style={{ maxWidth: 260 }}
          disabled={busy !== null}
          onClick={forget}
        >
          {busy === "forget" ? "Clearing…" : "Lower Community memory"}
        </button>
      </div>
      {lowered && (
        <p className="meta" role="status" data-testid="lower-memory-result">
          Preference weights lowered to {lowered.w_min ?? 0.01}
          {lowered.weights_lowered != null ? ` across ${lowered.weights_lowered} item(s)` : ""}
          {lowered.as_of ? `, as of ${lowered.as_of}` : ""}. You can still recall any topic explicitly.
        </p>
      )}
      {forgot && (
        <p className="meta" role="status" data-testid="forget-result">
          Server reports {forgot.records_forgotten} record(s) and {forgot.facts_erased} fact(s) cleared from the Community memory source
          {forgot.as_of ? `, as of ${forgot.as_of}` : ""}.
        </p>
      )}
      <p className="meta">
        Lower weight reduces preference influence to 0.01 without erasing history. Lower Community memory clears Community-sourced records only — account deletion is Delete my data under identity settings.
      </p>
    </article>
  );
}
