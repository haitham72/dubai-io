"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet } from "./api";

export interface UseApi<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
  reload: () => void;
}

export function describeApiError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 0) return err.message;
    return err.status >= 500
      ? `The server answered with an error (${err.status}).`
      : err.message.slice(0, 200);
  }
  return "Could not reach Dubai-io. Check your connection.";
}

/** Fetch-on-mount hook with loading / error / retry. Uses the unified session cookie client. */
export function useApi<T>(path: string | null): UseApi<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(path !== null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    if (path === null) {
      setLoading(false);
      return;
    }
    let live = true;
    setLoading(true);
    setError(null);
    apiGet<T>(path)
      .then((value) => {
        if (live) setData(value);
      })
      .catch((err) => {
        if (live) setError(describeApiError(err));
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
