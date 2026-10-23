"use client";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { BriefingStrip } from "./BriefingStrip";
import { HeroSkyline } from "./Skyline";
import { Composer } from "./Composer";
import s from "./assistant.module.css";

export function greeting(hour: number): string {
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
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
            <HeroSkyline />
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
