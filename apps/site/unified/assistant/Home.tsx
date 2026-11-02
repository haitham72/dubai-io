"use client";
import { DOMAIN_LABEL, type DomainId } from "../data/domains";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { BriefingStrip } from "./BriefingStrip";
import { HeroSkyline } from "./Skyline";
import { Composer } from "./Composer";
import { BecauseChips, MailResultList, PlaceCards, ProductList, SourceList } from "./PlaceCards";
import s from "./assistant.module.css";

export function greeting(hour: number): string {
  return hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}

/** Starters — live API pills + demo utterances that match sidebar demo threads. */
const CATEGORY_PILLS = [
  { domain: "lifestyle" as const, title: "Green shirt", ask: "I need a green shirt", live: true },
  { domain: "lifestyle" as const, title: "Gyms near Marina", ask: "Gyms near Dubai Marina open now", live: true },
  { domain: "travel" as const, title: "Lost bag in taxi", ask: "I left my bag in a taxi last night" },
  { domain: "household" as const, title: "School shortlist", ask: "Year 5 British curriculum — shortlist schools and a home with a sane school run" },
  { domain: "lifestyle" as const, title: "Mamzar Saturday", ask: "Saturday Mamzar with the kids — toys and a hot meal when we get back" },
  { domain: "money" as const, title: "Clinic near me", ask: "Ear pain — which nearby clinic does my insurance cover?" },
  { domain: "household" as const, title: "Guests at 8", ask: "Guests at 8 — flat ready and light dinner" },
  { domain: "lifestyle" as const, title: "I wear XL", ask: "I wear size XL" },
];

export function Home() {
  const { messages, setDraft, openThread } = useApp();
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
                {m.role === "assistant" && m.places && m.places.length > 0 && (
                  <PlaceCards places={m.places} asOf={m.placesAsOf} attribution={m.placesAttribution} />
                )}
                {m.role === "assistant" && m.products && m.products.length > 0 && (
                  <ProductList products={m.products} because={m.because} />
                )}
                {m.role === "assistant" && !(m.products && m.products.length) && m.because && m.because.length > 0 && (
                  <BecauseChips because={m.because} />
                )}
                {m.role === "assistant" && m.sources && m.sources.length > 0 && <SourceList sources={m.sources} />}
                {m.role === "assistant" && m.mailItems && m.mailItems.length > 0 && (
                  <MailResultList heading={m.mailHeading || "Needs a reply"} items={m.mailItems} />
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className={s.hero}>
            <HeroSkyline />
            <h1 className={s.greeting}>{greeting(hour)}</h1>
            <p className={s.lede}>
              Open a <strong>Demo</strong> thread in the sidebar for full journeys, or ask live for places and shopping.
            </p>
          </div>
        )}
        <Composer />
        {!talking && (
          <div className={s.pills} aria-label="Try asking">
            {CATEGORY_PILLS.map(({ domain, title, ask, live }) => (
              <button
                key={title}
                type="button"
                className={s.pill}
                data-testid="domain-starter"
                data-domain={domain}
                data-live={live ? "1" : undefined}
                onClick={() => {
                  const match = threads.find((t) => t.demo && t.title.toLowerCase().includes(title.split(" ")[0].toLowerCase()));
                  // Prefer opening the matching demo thread when one exists (taxi / school / mamzar / clinic / guests).
                  if (!live && match) openThread(match.id);
                  else setDraft(ask);
                }}
              >
                {title}
              </button>
            ))}
          </div>
        )}
        {!talking && <BriefingStrip threads={threads} />}
      </div>
    </div>
  );
}
