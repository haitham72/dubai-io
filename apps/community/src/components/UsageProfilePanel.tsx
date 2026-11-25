"use client";

import { useCallback, useEffect, useState } from "react";
import * as realApi from "@/lib/api";
import type { UsageBucket, UsageProfileResult } from "@/lib/api";

export interface UsageApi {
  getUsageProfile: (includeLowered?: boolean) => Promise<UsageProfileResult>;
  lowerUsageTopic: (topicKey: string) => Promise<unknown>;
  restoreUsageTopic: (topicKey: string) => Promise<unknown>;
  recallUsageTopic: (topicKey?: string, query?: string) => Promise<unknown>;
  setUsageSettings: (contextAwareEnabled: boolean) => Promise<{ context_aware_enabled: boolean }>;
}

function isBucketLowered(b: UsageBucket): boolean {
  if (b.status === "lowered") return true;
  if (b.lowered_at) return true;
  return (b.effective_weight ?? b.weight) <= 0.1;
}

function bucketContextSummary(b: UsageBucket): string {
  const parts = [b.time_bucket, b.area_coarse, b.device_class, b.user_state, b.format].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : "General context";
}

export default function UsageProfilePanel({ api = realApi }: { api?: UsageApi }) {
  const [profile, setProfile] = useState<UsageProfileResult | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [recallQuery, setRecallQuery] = useState("");

  const load = useCallback(async () => {
    try {
      const r = await api.getUsageProfile(true);
      setProfile(r);
      setLoadError(null);
    } catch (e) {
      setLoadError((e as Error).message || "Usage profile unavailable");
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleContextAware() {
    if (!profile || busy) return;
    setBusy("settings");
    setError(null);
    setStatus(null);
    try {
      const res = await api.setUsageSettings(!profile.context_aware_enabled);
      setProfile((prev) =>
        prev ? { ...prev, context_aware_enabled: res.context_aware_enabled } : prev,
      );
      setStatus(
        res.context_aware_enabled
          ? "Context-aware adaptation enabled."
          : "Context-aware adaptation paused.",
      );
    } catch (e) {
      setError((e as Error).message || "Could not update setting");
    } finally {
      setBusy(null);
    }
  }

  async function lower(topicKey: string) {
    if (busy) return;
    setBusy(`lower:${topicKey}`);
    setError(null);
    setStatus(null);
    try {
      await api.lowerUsageTopic(topicKey);
      setStatus(`Lowered ${topicKey} to 0.01.`);
      await load();
    } catch (e) {
      setError((e as Error).message || "Could not lower topic");
    } finally {
      setBusy(null);
    }
  }

  async function restore(topicKey: string) {
    if (busy) return;
    setBusy(`restore:${topicKey}`);
    setError(null);
    setStatus(null);
    try {
      await api.restoreUsageTopic(topicKey);
      setStatus(`Restored ${topicKey}.`);
      await load();
    } catch (e) {
      setError((e as Error).message || "Could not restore topic");
    } finally {
      setBusy(null);
    }
  }

  async function recall(topicKey?: string, query?: string) {
    const k = topicKey?.trim();
    const q = query?.trim();
    if ((!k && !q) || busy) return;
    setBusy("recall");
    setError(null);
    setStatus(null);
    try {
      await api.recallUsageTopic(k, q);
      setRecallQuery("");
      setStatus(`Recalled "${k ?? q}" — weight restored immediately.`);
      await load();
    } catch (e) {
      setError((e as Error).message || "Could not recall topic");
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="card" data-testid="usage-profile-panel">
      <h2>How Community adapts to you</h2>
      <p className="ai-text">
        Topic, time, area, and format signals stay editable. Lowering a bucket sets its weight to 0.01 without erasing history, and recalling a topic restores it immediately.
      </p>

      {loadError && (
        <div className="notice" role="alert">
          {loadError}
        </div>
      )}

      {profile && (
        <>
          <div className="toggle-row">
            <span>
              Context-aware adaptation
              <br />
              <span className="meta">
                Use your opt-in time, neighborhood, and movement context to tune For you.
              </span>
            </span>
            <button
              type="button"
              role="switch"
              aria-checked={profile.context_aware_enabled}
              aria-label="Context-aware adaptation"
              className="action-box"
              style={{ maxWidth: 90 }}
              disabled={busy !== null}
              onClick={toggleContextAware}
            >
              {busy === "settings"
                ? "Saving…"
                : profile.context_aware_enabled
                  ? "On"
                  : "Off"}
            </button>
          </div>

          <div className="user-box" style={{ marginTop: 12 }}>
            <label htmlFor="recall-topic-input">Recall topic (D19b)</label>
            <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
              <input
                id="recall-topic-input"
                type="text"
                value={recallQuery}
                onChange={(e) => setRecallQuery(e.target.value)}
                placeholder="e.g. padel or dubaimarina"
                maxLength={80}
              />
              <button
                type="button"
                className="action-box"
                style={{ maxWidth: 140 }}
                disabled={busy !== null || !recallQuery.trim()}
                onClick={() => recall(recallQuery, recallQuery)}
              >
                {busy === "recall" ? "Recalling…" : "Recall topic"}
              </button>
            </div>
          </div>

          {status && (
            <p className="meta" role="status" style={{ color: "#128c9b", fontWeight: 600 }}>
              {status}
            </p>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          {profile.buckets.length === 0 ? (
            <p className="meta" style={{ marginTop: 12 }}>
              No learned context buckets yet. Interact with posts to see how Community adapts.
            </p>
          ) : (
            <div style={{ marginTop: 12 }}>
              {profile.buckets.map((b, idx) => {
                const lowered = isBucketLowered(b);
                const weight = (b.effective_weight ?? b.weight ?? 0).toFixed(2);
                const rowKey = `${b.topic_key}-${b.time_bucket ?? ""}-${b.area_coarse ?? ""}-${idx}`;
                return (
                  <div
                    key={rowKey}
                    className="toggle-row"
                    data-testid="usage-bucket"
                  >
                    <div>
                      <strong>{b.topic_label || b.topic_key}</strong>{" "}
                      <span className="meta">
                        · {lowered ? "Lowered (0.01)" : "Active"} · weight {weight}
                      </span>
                      <br />
                      <span className="meta">{bucketContextSummary(b)}</span>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      {lowered ? (
                        <>
                          <button
                            type="button"
                            className="action-box"
                            style={{ minWidth: 80 }}
                            disabled={busy !== null}
                            onClick={() => restore(b.topic_key)}
                          >
                            Restore
                          </button>
                          <button
                            type="button"
                            className="action-box"
                            style={{ minWidth: 80 }}
                            disabled={busy !== null}
                            onClick={() => recall(b.topic_key, b.topic_key)}
                          >
                            Recall topic
                          </button>
                        </>
                      ) : (
                        <button
                          type="button"
                          className="action-box"
                          style={{ minWidth: 80 }}
                          disabled={busy !== null}
                          onClick={() => lower(b.topic_key)}
                        >
                          Lower
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </article>
  );
}
