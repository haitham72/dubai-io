"use client";
// App-level state lives above the layout switch, so crossing the 820 px breakpoint keeps the open thread and the composer draft.
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { ScreenId } from "./screens";

export type Mode = "assistant" | "community";
export type ThemePref = "system" | "light" | "dark";
export type ChatMessage = { id: number; role: "user" | "assistant"; text: string };

interface AppState {
  screen: ScreenId;
  setScreen: (s: ScreenId) => void;
  mode: Mode;
  setMode: (m: Mode) => void;
  threadId: string | null;
  openThread: (id: string | null) => void;
  draft: string;
  setDraft: (v: string) => void;
  messages: ChatMessage[];
  addMessages: (m: Omit<ChatMessage, "id">[]) => void;
  chatThreadId: string;
  onboarded: boolean | null;
  finishOnboarding: () => void;
  themePref: ThemePref;
  setThemePref: (t: ThemePref) => void;
  resolvedTheme: "light" | "dark";
}

const Ctx = createContext<AppState | null>(null);
const THEME_KEY = "dubaiio.theme";
export const ONBOARDED_KEY = "dubaiio.onboarded";

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem(THEME_KEY);
    if (v === "light" || v === "dark" || v === "system") return v;
  } catch { /* storage blocked */ }
  return "system";
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [screen, setScreenRaw] = useState<ScreenId>("assistant");
  const [mode, setMode] = useState<Mode>("assistant");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatThreadId] = useState(() => Math.random().toString(16).slice(2, 18) + Date.now().toString(16));
  const addMessages = useCallback((m: Omit<ChatMessage, "id">[]) => {
    setMessages((cur) => [...cur, ...m.map((x, i) => ({ ...x, id: cur.length + i }))]);
  }, []);
  const [onboarded, setOnboarded] = useState<boolean | null>(null);
  useEffect(() => {
    try { setOnboarded(localStorage.getItem(ONBOARDED_KEY) === "1"); } catch { setOnboarded(true); }
  }, []);
  const finishOnboarding = useCallback(() => {
    setOnboarded(true);
    try { localStorage.setItem(ONBOARDED_KEY, "1"); } catch { /* storage blocked */ }
  }, []);
  const [themePref, setPref] = useState<ThemePref>("system");
  const [systemDark, setSystemDark] = useState(false);

  useEffect(() => {
    setPref(readPref());
    const q = window.matchMedia("(prefers-color-scheme: dark)");
    setSystemDark(q.matches);
    const on = () => setSystemDark(q.matches);
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, []);

  const resolvedTheme = themePref === "system" ? (systemDark ? "dark" : "light") : themePref;
  useEffect(() => {
    document.documentElement.dataset.theme = resolvedTheme;
  }, [resolvedTheme]);

  const setThemePref = useCallback((t: ThemePref) => {
    setPref(t);
    try { localStorage.setItem(THEME_KEY, t); } catch { /* storage blocked */ }
  }, []);
  const setScreen = useCallback((s: ScreenId) => {
    setScreenRaw(s);
    if (s !== "assistant") setThreadId(null);
  }, []);
  const openThread = useCallback((id: string | null) => {
    setThreadId(id);
    if (id) { setScreenRaw("assistant"); setMode("assistant"); }
  }, []);

  const value = useMemo(
    () => ({ screen, setScreen, mode, setMode, threadId, openThread, draft, setDraft, messages, addMessages, chatThreadId, onboarded, finishOnboarding, themePref, setThemePref, resolvedTheme }),
    [screen, setScreen, mode, threadId, openThread, draft, messages, addMessages, chatThreadId, onboarded, finishOnboarding, themePref, setThemePref, resolvedTheme],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useApp outside AppProvider");
  return v;
}
