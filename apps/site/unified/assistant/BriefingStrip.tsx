"use client";
import { ChevronRight, Clock, MessageSquareWarning, RefreshCw } from "lucide-react";
import { briefing, type TaskThread } from "../data/tasks";
import { useApp } from "../state";
import { DemoPill } from "../ui";
import s from "./assistant.module.css";

/** Slim strip of up to three cards: what needs you, what changed, what is due. Built from the same threads as the sidebar. */
export function BriefingStrip({ threads }: { threads: TaskThread[] }) {
  const { openThread } = useApp();
  const b = briefing(threads);
  const cards = [
    { key: "needs", label: "Needs you", icon: MessageSquareWarning, tone: s.toneRed, t: b.needsYou },
    { key: "changed", label: "Changed", icon: RefreshCw, tone: s.toneGreen, t: b.changed },
    { key: "due", label: "Due", icon: Clock, tone: s.toneAmber, t: b.due },
  ].filter((c): c is typeof c & { t: TaskThread } => !!c.t);
  if (!cards.length) return null;
  return (
    <div className={s.strip} aria-label="Briefing">
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
  );
}
