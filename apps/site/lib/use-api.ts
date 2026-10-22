"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "./api";
import { ensureSession } from "./session";

export interface UseApi<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

/** Fetch-on-mount hook with loading / error / retry states. */
export function useApi<T>(path: string | null): UseApi<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(path !== null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (path === null) {
      setLoading(false);
      return;
    }
    let live = true;
    setLoading(true);
    setError(null);
    ensureSession()
      .then(() => apiGet<T>(path))
      .then((value) => {
        if (live) setData(value);
      })
      .catch((err: unknown) => {
        if (live) setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (live) setLoading(false);
      });
    return () => {
      live = false;
    };
  }, [path, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data, error, loading, reload };
}
