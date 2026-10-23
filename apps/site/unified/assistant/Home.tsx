"use client";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { BriefingStrip } from "./BriefingStrip";
import { Composer } from "./Composer";
import s from "./assistant.module.css";

export function greeting(hour: number): string {
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

function Skyline() {
  return (
    <svg className={s.skyline} viewBox="0 0 180 90" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 86h172" />
      <path d="M12 86V58h10v28M22 66h8v20M30 86V50h9v36" />
      <path d="M72 86V54l6-14 3-28 3 28 6 14v32M81 12V4" />
      <path d="M98 86V60h8v26M108 86V46c8-6 14 0 14 6v34" />
      <path d="M126 86c0-20 8-34 22-40M148 46v40" />
      <path d="M160 86V70M160 70c-6-2-10-6-12-10M160 70c6-2 10-6 12-10M160 70c-2-7 0-12 4-16M160 70c2-7 0-12-4-16" />
    </svg>
  );
}

export function Home() {
  const { messages } = useApp();
  const { threads } = useThreads();
  const hour = new Date().getHours();
  const talking = messages.length > 0;

  return (
    <div className={s.home}>
      <div className={`${s.body} ${talking ? s.bodyTalking : ""}`}>
        {talking ? (
          <div className={s.messages} role="log" aria-live="polite">
            {messages.map((m) => (
              <p key={m.id} className={m.role === "user" ? s.msgUser : s.msgAssistant} data-testid={`msg-${m.role}`}>{m.text}</p>
            ))}
          </div>
        ) : (
          <div className={s.hero}>
            <Skyline />
            <h1 className={s.greeting}>{greeting(hour)}</h1>
            <p className={s.lede}>Ask me anything about Dubai — from places and transport to work, schools, events and more.</p>
          </div>
        )}
        <Composer />
        {!talking && <BriefingStrip threads={threads} />}
      </div>
    </div>
  );
}
