"use client";
import { ChevronRight, Clock, MessageSquareWarning, RefreshCw } from "lucide-react";
import { briefing, type TaskThread } from "../data/tasks";
import { useApp } from "../state";
import { DemoPill } from "../ui";
import s from "./assistant.module.css";

/** Higgsfield l02: “N moving · N needs you” plus up to three briefing cards from the same threads as the sidebar. */
export function BriefingStrip({ threads }: { threads: TaskThread[] }) {
  const { openThread } = useApp();
  const b = briefing(threads);
  const moving = threads.filter((t) => t.lane === "running" || t.lane === "scheduled").length;
  const needs = threads.filter((t) => t.lane === "needs_you").length;
  const anyDemo = threads.some((t) => t.demo);
  const cards = [
    { key: "needs", label: "Needs you", icon: MessageSquareWarning, tone: s.toneRed, t: b.needsYou },
    { key: "changed", label: "Changed", icon: RefreshCw, tone: s.toneGreen, t: b.changed },
    { key: "due", label: "Due", icon: Clock, tone: s.toneAmber, t: b.due },
  ].filter((c): c is typeof c & { t: TaskThread } => !!c.t);
  if (!cards.length) return null;

  const parts: string[] = [];
  if (moving) parts.push(`${moving} moving`);
  if (needs) parts.push(`${needs} need${needs === 1 ? "s" : ""} you`);
  const summary = parts.join(", ") || "On your list";

  return (
    <section className={s.stripWrap} aria-label="Briefing">
      <div className={s.stripHead}>
        <h2 className={s.stripSummary}>
          {summary}
          {anyDemo ? <DemoPill /> : null}
        </h2>
        <button type="button" className={s.stripReview} onClick={() => openThread(cards[0].t.id)}>
          Review <ChevronRight size={14} strokeWidth={2} aria-hidden />
        </button>
      </div>
      <div className={s.strip}>
        {cards.map(({ key, label, icon: I, tone, t }) => (
          <button key={key} className={s.stripCard} data-testid="briefing-card" onClick={() => openThread(t.id)}>
            <span className={`${s.stripIcon} ${tone}`}><I size={20} strokeWidth={2} /></span>
            <span className={s.stripText}>
              <span className={`${s.stripLabel} ${tone}`}>{label}</span>
              <span className={s.stripTitle}><span>{t.title}</span>{t.demo && <DemoPill />}</span>
              <span className={s.stripSub}>{t.preview}</span>
            </span>
            <ChevronRight size={16} className={s.stripChevron} />
          </button>
        ))}
      </div>
    </section>
  );
}
