"use client";
import { useMemo, useState } from "react";
import { ArrowUp, Plus } from "lucide-react";
import { apiPost } from "../data/api";
import { classifyDomain, DOMAIN_LABEL } from "../data/domains";
import { detectUserLocation } from "../data/location";
import { placesQueryFromTurn, searchPlaces, wantsNearbyPlaces, type Place } from "../data/places";
import { searchShopping, wantsProductSearch } from "../data/shopping";
import { useApp, type ChatBecause, type ChatProduct, type ChatSource } from "../state";
import s from "./assistant.module.css";

interface TurnResponse {
  reply?: string;
  answer?: string;
  intent?: string;
  category?: string | null;
  subcategory?: string | null;
  query?: string | null;
  products?: ChatProduct[];
  because?: ChatBecause[];
  sources?: ChatSource[];
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
  const guess = useMemo(() => classifyDomain(draft), [draft]);

  const send = async () => {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    const domain = classifyDomain(text).domain;
    try {
      const res = await apiPost<TurnResponse>("/api/luna/turn", { text, thread_id: chatThreadId });
      let reply = lunaReply(res);
      if (!reply) throw new Error("empty reply");

      let places: Place[] | undefined;
      let placesAsOf: string | undefined;
      let placesAttribution: string | undefined;
      let products: ChatProduct[] | undefined = res.intent === "product_search" ? res.products : undefined;
      let because: ChatBecause[] | undefined = res.because;
      let sources: ChatSource[] | undefined =
        res.intent === "info_question" || res.intent === "market_quote" ? res.sources : undefined;

      if (wantsNearbyPlaces(text, res.intent)) {
        try {
          const here = await detectUserLocation();
          const live = await searchPlaces(placesQueryFromTurn(res, text), here);
          places = live.places.slice(0, 6);
          placesAsOf = live.as_of;
          placesAttribution = live.attribution || "Google";
          if (!places.length) {
            reply = `${reply}\n\nNo live places matched near ${here.label} right now.`;
          }
        } catch {
          reply = `${reply}\n\nLive Google Places is unavailable right now — nothing invented.`;
        }
      }

      if (wantsProductSearch(text, res.intent) && !(products && products.length)) {
        try {
          const live = await searchShopping(res.query || text);
          products = live.products.slice(0, 5);
          because = live.because;
          if (products.length && res.intent !== "product_search") {
            reply = live.attribution
              ? `Here are live options across stores (${live.attribution}). Prices as listed now — nothing is bought here.`
              : reply;
          }
          if (!products.length) {
            reply = `${reply}\n\nNo live shopping results matched right now.`;
          }
        } catch {
          reply = `${reply}\n\nLive shopping is unavailable right now — nothing invented.`;
        }
      }

      let mailHeading: string | undefined;
      let mailItems: { id: string; title: string; body: string; provenance?: string; demo?: boolean }[] | undefined;
      if (/\b(email|inbox|job application|missed|needs? a reply|recruiter)\b/i.test(text)) {
        try {
          const mail = await fetch("/api/mail/needs-reply", { credentials: "include" }).then((r) => r.json());
          if (mail.items?.length) {
            mailHeading = mail.heading || "Needs a reply";
            mailItems = mail.items;
            reply = `${reply}\n\nI scanned for application / interview mail worth a reply.`;
          } else if (mail.blocker) {
            reply = `${reply}\n\n${mail.blocker}`;
          }
        } catch {
          reply = `${reply}\n\nMail profiler unavailable right now — nothing invented.`;
        }
      }

      addMessages([
        { role: "user", text, domain },
        {
          role: "assistant",
          text: reply,
          places,
          placesAsOf,
          placesAttribution,
          products,
          because,
          sources,
          mailHeading,
          mailItems,
        },
      ]);
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
          placeholder="Ask Dubai-io or start a task…"
          aria-label="Message Dubai-io"
          rows={2}
        />
        <div className={s.composerBar}>
          <button className={s.plus} aria-label="Add" aria-expanded={menu} onClick={() => setMenu((m) => !m)}><Plus size={20} strokeWidth={1.8} /></button>
          {menu && <div className={s.menu} role="menu"><span className={s.menuItem} role="menuitem" aria-disabled="true">Connect apps — not available yet</span></div>}
          {draft.trim() ? (
            <span className={s.domainChip} data-testid="composer-domain" data-domain={guess.domain} title="Where this ask would live in the sidebar">
              {DOMAIN_LABEL[guess.domain]}
            </span>
          ) : <span />}
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
