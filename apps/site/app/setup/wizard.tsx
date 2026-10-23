"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { FunnelError, funnelStyles as s } from "@/components/funnel";
import { apiPut, describeError } from "@/lib/api";
import { ensureSession } from "@/lib/session";

const QUESTIONS = [
  {
    key: "area",
    title: "Where in Dubai do you live?",
    help: "Used to prepare local tasks, like which pickup area to put on an order.",
    label: "Area or neighbourhood",
    placeholder: "Dubai Marina",
    chips: ["Dubai Marina", "JLT", "Downtown", "Business Bay", "JVC", "Al Barsha"],
  },
  {
    key: "household",
    title: "Who is in your household?",
    help: "Helps it pick the right size of service, like a one-bedroom clean or pet care.",
    label: "Household",
    placeholder: "2 adults, 1 child, 1 dog",
    chips: ["Just me", "2 adults", "2 adults, 1 child", "2 adults, 1 dog"],
  },
  {
    key: "services",
    title: "Which bills and services do you handle?",
    help: "So reminders and tasks can name the right ones. Nothing is connected or paid.",
    label: "Services you use",
    placeholder: "DEWA, Salik, du",
    chips: ["DEWA", "Salik", "du", "etisalat", "Empower"],
  },
] as const;

const MAX = 80;
const SHORT: Record<string, string> = { area: "Area", household: "Household", services: "Services" };

export default function SetupWizard() {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const [values, setValues] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Array<[string, string]>>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const q = QUESTIONS[index];
  const value = values[q.key] ?? "";
  const trimmed = value.trim();

  function next() {
    setError(null);
    if (index + 1 >= QUESTIONS.length) router.push("/first-win");
    else setIndex(index + 1);
  }

  async function save() {
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      await ensureSession();
      await apiPut(`/api/session/memory/${q.key}`, { value: trimmed });
      setSaved((prev) => [...prev.filter(([k]) => k !== SHORT[q.key]), [SHORT[q.key], trimmed]]);
      setBusy(false);
      next();
    } catch (err) {
      setError(describeError(err));
      setBusy(false);
    }
  }

  function addChip(chip: string) {
    if (q.key === "services") {
      const parts = value
        .split(",")
        .map((p) => p.trim())
        .filter(Boolean);
      if (parts.includes(chip)) return;
      const joined = [...parts, chip].join(", ");
      if (joined.length <= MAX) setValues({ ...values, [q.key]: joined });
    } else {
      setValues({ ...values, [q.key]: chip });
    }
  }

  return (
    <>
      <p className={s.step}>
        Question {index + 1} of {QUESTIONS.length}
      </p>
      <h1>{q.title}</h1>
      <p className={s.lede}>{q.help}</p>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <div className={s.field}>
          <label htmlFor="answer">{q.label}</label>
          <input
            id="answer"
            className={s.input}
            value={value}
            maxLength={MAX}
            placeholder={q.placeholder}
            autoComplete="off"
            onChange={(e) => setValues({ ...values, [q.key]: e.target.value })}
          />
          <span className={s.count}>
            {value.length} / {MAX}
          </span>
        </div>

        <div className={s.chips} role="group" aria-label="Quick picks">
          {q.chips.map((chip) => (
            <button
              type="button"
              key={chip}
              className={s.chip}
              aria-pressed={value.split(",").map((p) => p.trim()).includes(chip)}
              onClick={() => addChip(chip)}
            >
              {chip}
            </button>
          ))}
        </div>

        <div className={s.panel}>
          <h2>Where this goes</h2>
          <p>
            It is saved as a fact under <strong>You told me</strong>. You can
            edit or forget it in the app at any time.
          </p>
        </div>

        {error ? <FunnelError message={error} onRetry={save} busy={busy} /> : null}

        <div className={s.actions}>
          <button
            type="submit"
            className={s.btnPrimary}
            disabled={busy || !trimmed}
          >
            {busy ? "Saving" : index + 1 >= QUESTIONS.length ? "Save and continue" : "Save and next"}
          </button>
          <button type="button" className={s.textBtn} onClick={next} disabled={busy}>
            Skip this question
          </button>
        </div>
      </form>

      {saved.length > 0 ? (
        <section aria-label="Saved so far" style={{ marginTop: 40 }}>
          <p className={s.step}>Saved so far, as You told me</p>
          <ul className={s.saved}>
            {saved.map(([k, v]) => (
              <li key={k}>
                <span>{k}</span>
                <span>{v}</span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </>
  );
}
