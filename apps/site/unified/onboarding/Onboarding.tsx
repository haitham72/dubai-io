"use client";
import { useEffect, useState } from "react";
import { Link2, Mail, CalendarDays, MapPin, Send } from "lucide-react";
import { apiGet, apiPut } from "../data/api";
import { greeting } from "../assistant/Home";
import { useApp } from "../state";
import { Button } from "../ui";
import { Orb } from "./Orb";
import s from "./onboarding.module.css";

type Key = "area" | "household" | "services";
const QUESTIONS: { key: Key; ask: string; options: string[]; placeholder: string }[] = [
  { key: "area", ask: "Where in Dubai do you live?", options: ["Dubai Marina", "JLT", "Downtown"], placeholder: "Or type your area" },
  { key: "household", ask: "Who is in your household?", options: ["Just me", "Couple", "Family with kids", "Shared flat"], placeholder: "Or tell me in a few words" },
  { key: "services", ask: "Which services do you use?", options: ["AC repair", "Laundry", "DEWA bills", "Cleaning"], placeholder: "Or type what you use" },
];

type Told = { key: string; value: string }[];

export function Onboarding() {
  const { finishOnboarding } = useApp();
  const [pending, setPending] = useState<Key[] | null>(null); // unanswered question keys, in order
  const [answers, setAnswers] = useState<{ ask: string; value: string }[]>([]);
  const [text, setText] = useState("");
  const [error, setError] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let alive = true;
    apiGet<{ told?: Told | Record<string, unknown> }>("/api/session/memory")
      .then((m) => {
        const saved = new Set(Array.isArray(m.told) ? m.told.map((f) => f.key) : Object.keys(m.told ?? {}));
        if (alive) setPending(QUESTIONS.map((q) => q.key).filter((k) => !saved.has(k)));
      })
      .catch(() => { if (alive) setPending(QUESTIONS.map((q) => q.key)); });
    return () => { alive = false; };
  }, []);

  const current = pending && pending.length ? QUESTIONS.find((q) => q.key === pending[0]) : undefined;

  const answer = async (raw: string) => {
    const value = raw.trim().slice(0, 80);
    if (!current || !value || busy) return;
    setBusy(true);
    setError(false);
    try {
      await apiPut(`/api/session/memory/${current.key}`, { value });
      setAnswers((a) => [...a, { ask: current.ask, value }]);
      setPending((p) => (p ? p.slice(1) : p));
      setText("");
    } catch {
      setError(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.wrap}>
      <div className={s.inner}>
        <Orb />
        <h1 className={s.title}>{greeting(new Date().getHours())}.<br />I&apos;m Dubai-io.</h1>
        {pending === null ? null : (
          <div className={s.chat} role="log" aria-live="polite">
            {answers.map((a) => (
              <div key={a.ask} className={s.turn}>
                <p className={s.q}>{a.ask}</p>
                <p className={s.a}>{a.value}</p>
              </div>
            ))}
            {current ? (
              <div className={s.turn}>
                <p className={s.q}>{current.ask}</p>
                <div className={s.chips}>
                  {current.options.map((o) => (
                    <button key={o} className={s.chip} disabled={busy} onClick={() => void answer(o)}>
                      {current.key === "area" && <MapPin size={16} strokeWidth={1.8} />}
                      {o}
                    </button>
                  ))}
                </div>
                <form className={s.free} onSubmit={(e) => { e.preventDefault(); void answer(text); }}>
                  <input value={text} onChange={(e) => setText(e.target.value)} maxLength={80} placeholder={current.placeholder} aria-label={current.ask} />
                  <button type="submit" aria-label="Save answer" disabled={busy || !text.trim()}><Send size={16} /></button>
                </form>
                {error && <p className={s.error} role="alert" data-testid="onboarding-error">Could not save that. Try again.</p>}
              </div>
            ) : (
              <div className={s.turn}>
                <p className={s.q}>Connect your apps when you are ready.</p>
                <div className={s.connectors}>
                  {[{ name: "Gmail", icon: Mail }, { name: "Calendar", icon: CalendarDays }].map(({ name, icon: I }) => (
                    <div key={name} className={s.connector}>
                      <I size={22} strokeWidth={1.6} />
                      <span>{name}</span>
                      <small>Not available yet</small>
                    </div>
                  ))}
                </div>
                <div><Button icon={Link2} onClick={finishOnboarding}>Later</Button></div>
              </div>
            )}
          </div>
        )}
        <button className={s.skip} onClick={finishOnboarding}>Skip for now</button>
      </div>
    </div>
  );
}
