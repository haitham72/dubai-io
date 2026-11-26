"use client";

import { useCallback, useEffect, useState } from "react";
import * as realApi from "@/lib/api";
import type { MuteKind, SafetyState } from "@/lib/api";

export interface SafetyApi {
  getSafety: () => Promise<SafetyState>;
  unblockUser: (handle: string) => Promise<void>;
  unmuteTarget: (kind: MuteKind, target: string) => Promise<void>;
}

export default function SafetyPanel({ api = realApi }: { api?: SafetyApi }) {
  const [safety, setSafety] = useState<SafetyState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSafety(await api.getSafety());
      setLoadError(null);
    } catch (e) {
      setLoadError((e as Error).message || "Safety list unavailable");
    }
  }, [api]);

  useEffect(() => {
    void load();
  }, [load]);

  async function unblock(handle: string) {
    if (busy) return;
    setBusy(`unblock:${handle}`);
    setError(null);
    try {
      await api.unblockUser(handle);
      setSafety((prev) =>
        prev
          ? { ...prev, blocked: prev.blocked.filter((b) => b.handle !== handle) }
          : prev,
      );
    } catch (e) {
      setError((e as Error).message || "Could not unblock user");
    } finally {
      setBusy(null);
    }
  }

  async function unmute(kind: string, target: string) {
    if (busy) return;
    setBusy(`unmute:${kind}:${target}`);
    setError(null);
    try {
      await api.unmuteTarget(kind as MuteKind, target);
      setSafety((prev) =>
        prev
          ? {
              ...prev,
              mutes: prev.mutes.filter((m) => !(m.kind === kind && m.target === target)),
            }
          : prev,
      );
    } catch (e) {
      setError((e as Error).message || "Could not unmute");
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="card" data-testid="safety-panel">
      <h2>Blocked &amp; Muted</h2>
      <p className="ai-text">
        People, communities, or hashtags you block or mute are filtered from your feed, search, discovery, and inbox.
      </p>
      {loadError && <p className="meta">{loadError}</p>}
      {error && (
        <div className="error" role="alert">
          {error}
        </div>
      )}
      {safety && safety.blocked.length === 0 && safety.mutes.length === 0 && (
        <p className="meta">No blocked accounts or muted topics.</p>
      )}
      {safety && safety.blocked.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <strong style={{ fontSize: 13 }}>Blocked accounts</strong>
          {safety.blocked.map((b) => (
            <div key={b.handle} className="toggle-row">
              <span>
                @{b.handle}
                {b.display_name ? ` (${b.display_name})` : ""}
              </span>
              <button
                type="button"
                className="action-box"
                style={{ maxWidth: 110 }}
                disabled={busy !== null}
                onClick={() => unblock(b.handle)}
              >
                Unblock
              </button>
            </div>
          ))}
        </div>
      )}
      {safety && safety.mutes.length > 0 && (
        <div style={{ marginTop: 12 }}>
          <strong style={{ fontSize: 13 }}>Muted targets</strong>
          {safety.mutes.map((m) => (
            <div key={`${m.kind}:${m.target}`} className="toggle-row">
              <span>
                {m.kind === "tag" ? `#${m.target}` : m.target}{" "}
                <span className="meta">({m.kind})</span>
              </span>
              <button
                type="button"
                className="action-box"
                style={{ maxWidth: 110 }}
                disabled={busy !== null}
                onClick={() => unmute(m.kind, m.target)}
              >
                Unmute
              </button>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
