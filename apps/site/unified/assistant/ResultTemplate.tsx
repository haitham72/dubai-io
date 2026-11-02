"use client";
/**
 * Grok Bot–style result blocks: section heading → icon + bold title → plain summary body → actions.
 * Used for places, shopping, mail, and research — one visual grammar everywhere.
 */
import type { ReactNode } from "react";
import s from "./assistant.module.css";

export type ResultProvider = "google" | "shopping" | "mail" | "place" | "web" | "demo";

export type ResultItem = {
  id: string;
  title: string;
  body: string;
  provider?: ResultProvider;
  meta?: string;
  provenance?: string;
  media?: string | null;
  actions?: ReactNode;
  /** Optional Playwright hooks (e.g. live-place / live-product). */
  testId?: string;
};

const PROVIDER_MARK: Record<ResultProvider, string> = {
  google: "G",
  shopping: "S",
  mail: "M",
  place: "P",
  web: "W",
  demo: "D",
};

export function ResultSection({
  heading,
  items,
  foot,
  testId = "result-section",
}: {
  heading: string;
  items: ResultItem[];
  foot?: string;
  testId?: string;
}) {
  if (!items.length) return null;
  return (
    <section className={s.resultSection} data-testid={testId} aria-label={heading}>
      <h3 className={s.resultHeading}>{heading}</h3>
      <ul className={s.resultList}>
        {items.map((item) => {
          const provider = item.provider || "web";
          const media = item.media?.startsWith("https://") || item.media?.startsWith("/api/") ? item.media : null;
          return (
            <li key={item.id} className={`${s.resultItem} ${media ? "" : s.resultItemText}`} data-testid={item.testId || "result-item"}>
              {media ? (
                <img className={s.resultMedia} src={media} alt="" data-testid={item.testId ? `${item.testId}-photo` : undefined} />
              ) : null}
              <div className={s.resultMain}>
                <div className={s.resultTitleRow}>
                  <span className={s.resultIcon} data-provider={provider} aria-hidden>
                    {PROVIDER_MARK[provider]}
                  </span>
                  <strong className={s.resultTitle}>{item.title}</strong>
                </div>
                <p className={s.resultBody}>{item.body}</p>
                {(item.meta || item.provenance) && (
                  <p className={s.resultMeta}>
                    {[item.meta, item.provenance].filter(Boolean).join(" · ")}
                  </p>
                )}
                {item.actions ? <div className={s.resultActions}>{item.actions}</div> : null}
              </div>
            </li>
          );
        })}
      </ul>
      {foot ? <p className={s.liveFoot}>{foot}</p> : null}
    </section>
  );
}
