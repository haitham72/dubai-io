"use client";
// Task threads from /api/today. Polls every 20 s while the tab is visible and stops while hidden.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiGet } from "./api";
import { toThreads, type TaskThread, type TodayResponse } from "./tasks";

export const DISMISS_KEY = "dubaiio.dismissedDemo";
export const POLL_MS = 20_000;

interface ThreadsState {
  threads: TaskThread[];
  dismissDemo: (id: string) => void;
  loaded: boolean;
  error: string | null;
}
const Ctx = createContext<ThreadsState | null>(null);

function readDismissed(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(DISMISS_KEY) ?? "[]");
    return Array.isArray(v) ? v.filter((x) => typeof x === "string") : [];
  } catch { return []; }
}

export function ThreadsProvider({ children }: { children: ReactNode }) {
  const [today, setToday] = useState<TodayResponse>({});
  const [dismissed, setDismissed] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setDismissed(readDismissed()), []);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const data = await apiGet<TodayResponse>("/api/today");
        if (alive) { setToday(data ?? {}); setError(null); }
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Could not load tasks");
      } finally {
        if (alive) setLoaded(true);
      }
    };
    void load();
    const timer = window.setInterval(() => { if (document.visibilityState === "visible") void load(); }, POLL_MS);
    const onVisible = () => { if (document.visibilityState === "visible") void load(); };
    document.addEventListener("visibilitychange", onVisible);
    return () => { alive = false; window.clearInterval(timer); document.removeEventListener("visibilitychange", onVisible); };
  }, []);

  const dismissDemo = useCallback((id: string) => {
    setDismissed((cur) => {
      const next = cur.includes(id) ? cur : [...cur, id];
      try { localStorage.setItem(DISMISS_KEY, JSON.stringify(next)); } catch { /* storage blocked */ }
      return next;
    });
  }, []);

  const threads = useMemo(() => toThreads(today, dismissed), [today, dismissed]);
  const value = useMemo(() => ({ threads, dismissDemo, loaded, error }), [threads, dismissDemo, loaded, error]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useThreads(): ThreadsState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useThreads outside ThreadsProvider");
  return v;
}
