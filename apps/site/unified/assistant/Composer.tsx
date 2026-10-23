"use client";
import { useState } from "react";
import { ArrowUp, Plus } from "lucide-react";
import { apiPost } from "../data/api";
import { useApp } from "../state";
import s from "./assistant.module.css";

interface TurnResponse {
  reply?: string;
  answer?: string;
  history?: { role?: string; text?: string }[];
}

/** The assistant's text: the last `luna` history item if the API sends one, else `reply`, else a research `answer`. */
export function lunaReply(res: TurnResponse): string {
  const fromHistory = [...(res.history ?? [])].reverse().find((h) => h.role === "luna" && h.text);
  return (fromHistory?.text ?? res.reply ?? res.answer ?? "").trim();
}

export const UNAVAILABLE = "Assistant unavailable — try again";

/** Draft lives in app state so it survives the desktop/phone layout swap. */
export function Composer() {
  const { draft, setDraft, addMessages, chatThreadId } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menu, setMenu] = useState(false);

  const send = async () => {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiPost<TurnResponse>("/api/luna/turn", { text, thread_id: chatThreadId });
      const reply = lunaReply(res);
      if (!reply) throw new Error("empty reply");
      addMessages([{ role: "user", text }, { role: "assistant", text: reply }]);
      setDraft("");
    } catch {
      // Never a fake reply: keep the draft and say so.
      setError(UNAVAILABLE);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.composerWrap}>
      <div className={s.composer}>
        <textarea
          data-testid="composer-input"
          className={s.composerInput}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }}
          placeholder="Ask Dubai-io anything"
          aria-label="Message Dubai-io"
          rows={2}
        />
        <div className={s.composerBar}>
          <button className={s.plus} aria-label="Add" aria-expanded={menu} onClick={() => setMenu((m) => !m)}><Plus size={20} strokeWidth={1.8} /></button>
          {menu && <div className={s.menu} role="menu"><span className={s.menuItem} role="menuitem" aria-disabled="true">Connect apps — not available yet</span></div>}
          <button className={s.send} onClick={() => void send()} disabled={busy || !draft.trim()} aria-label="Send">
            <ArrowUp size={18} strokeWidth={2.2} />
          </button>
        </div>
      </div>
      {busy && <p className={s.status} role="status">Thinking…</p>}
      {error && <p className={s.error} role="alert" data-testid="composer-error">{error}</p>}
    </div>
  );
}
