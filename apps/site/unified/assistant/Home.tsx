"use client";
import { Home as HomeIcon, MapPin, Wrench } from "lucide-react";
import { DOMAIN_LABEL, type DomainId } from "../data/domains";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { BriefingStrip } from "./BriefingStrip";
import { HeroSkyline } from "./Skyline";
import { Composer } from "./Composer";
import s from "./assistant.module.css";

export function greeting(hour: number): string {
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

const STARTERS = [
  { domain: "household", icon: HomeIcon, title: "Household", hint: "Bills, AC, schools, insurance", ask: "Remind me about my DEWA bill" },
  { domain: "places", icon: MapPin, title: "Places & trips", hint: "Near me, outings, parking", ask: "Coffee near me in Dubai Marina" },
  { domain: "services", icon: Wrench, title: "Services", hint: "Laundry, cleaning, car wash", ask: "I need a shirt pressed by tomorrow" },
] as const;

export function Home() {
  const { messages, setDraft } = useApp();
  const { threads } = useThreads();
  const hour = new Date().getHours();
  const talking = messages.length > 0;

  return (
    <div className={s.home}>
      <div className={`${s.body} ${talking ? s.bodyTalking : ""}`}>
        {talking ? (
          <div className={s.messages} role="log" aria-live="polite">
            {messages.map((m) => (
              <div key={m.id} className={m.role === "user" ? s.msgUserWrap : s.msgAssistantWrap}>
                {m.role === "user" && m.domain && (
                  <span className={s.msgDomain} data-testid="msg-domain">{DOMAIN_LABEL[m.domain as DomainId]}</span>
                )}
                <p className={m.role === "user" ? s.msgUser : s.msgAssistant} data-testid={`msg-${m.role}`}>{m.text}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className={s.hero}>
            <HeroSkyline />
            <h1 className={s.greeting}>{greeting(hour)}</h1>
            <p className={s.lede}>Ask me anything about Dubai — home, places, services and work. I keep related tasks under one domain in the sidebar.</p>
            <div className={s.starters} aria-label="Try asking">
              {STARTERS.map(({ domain, icon: I, title, hint, ask }) => (
                <button
                  key={domain}
                  type="button"
                  className={s.starter}
                  data-testid="domain-starter"
                  data-domain={domain}
                  onClick={() => setDraft(ask)}
                >
                  <span className={s.starterIcon}><I size={18} strokeWidth={2} /></span>
                  <span className={s.starterText}>
                    <b>{title}</b>
                    <small>{hint}</small>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
        <Composer />
        {!talking && <BriefingStrip threads={threads} />}
      </div>
    </div>
  );
}
