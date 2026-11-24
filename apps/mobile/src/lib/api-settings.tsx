import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import * as SecureStore from "expo-secure-store";
import { defaultApiBaseUrl, localhostWarning } from "./api";

const STORE_KEY = "dubaiio.apiBaseUrl";

interface ApiSettings {
  apiBaseUrl: string;
  warning: string | null;
  ready: boolean;
  setApiBaseUrl: (url: string) => void;
}

const ApiSettingsContext = createContext<ApiSettings | null>(null);

async function readStoredUrl(): Promise<string | null> {
  try {
    return await SecureStore.getItemAsync(STORE_KEY);
  } catch {
    return null;
  }
}

async function writeStoredUrl(url: string): Promise<void> {
  try {
    await SecureStore.setItemAsync(STORE_KEY, url);
  } catch {
    // Expo Go web and tests have no keychain. The in-memory value still applies.
  }
}

export function ApiSettingsProvider({ children }: { children: React.ReactNode }) {
  const [apiBaseUrl, setUrl] = useState(defaultApiBaseUrl);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    readStoredUrl().then((stored) => {
      if (cancelled) return;
      if (stored && stored.trim()) setUrl(stored.trim().replace(/\/$/, ""));
      setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<ApiSettings>(
    () => ({
      apiBaseUrl,
      warning: localhostWarning(apiBaseUrl),
      ready,
      setApiBaseUrl: (url: string) => {
        const next = url.trim().replace(/\/$/, "");
        setUrl(next);
        void writeStoredUrl(next);
      },
    }),
    [apiBaseUrl, ready],
  );

  return <ApiSettingsContext.Provider value={value}>{children}</ApiSettingsContext.Provider>;
}

export function useApiSettings(): ApiSettings {
  const value = useContext(ApiSettingsContext);
  if (!value) {
    throw new Error("useApiSettings must be used inside ApiSettingsProvider");
  }
  return value;
}

export function useApiSettingsOptional(): ApiSettings | null {
  return useContext(ApiSettingsContext);
}
