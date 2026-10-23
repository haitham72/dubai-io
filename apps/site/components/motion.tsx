"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { Phone, type ScreenId } from "./phone";
import styles from "./motion.module.css";

function reduced(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Fades its children in once when they scroll into view. Server render is
 * fully visible; the hidden state is only applied after mount for content
 * below the fold, so no-JS and reduced-motion users see everything.
 */
export function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "hidden" | "shown">("idle");

  useEffect(() => {
    const el = ref.current;
    if (!el || reduced()) return;
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 0.92) return; // already in view
    setState("hidden");
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setState("shown");
          io.disconnect();
        }
      },
      { threshold: 0.12 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={`${styles.reveal} ${className}`}
      data-state={state}
      style={{ transitionDelay: state === "shown" ? `${delay}ms` : undefined }}
    >
      {children}
    </div>
  );
}

/** Slow vertical drift for the hero phone, driven by scroll position. */
export function Drift({
  children,
  amount = 60,
  className = "",
}: {
  children: ReactNode;
  amount?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || reduced()) return;
    let frame = 0;
    const update = () => {
      frame = 0;
      const progress = Math.min(1, Math.max(0, window.scrollY / 700));
      el.style.transform = `translate3d(0, ${(-progress * amount).toFixed(1)}px, 0)`;
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [amount]);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}

export interface StoryStep {
  id: ScreenId;
  title: string;
  body: string;
}

/**
 * "How it works": one sticky phone whose screen follows the step in view.
 * Below 900px each step carries its own phone instead (CSS toggles).
 */
export function Story({ steps }: { steps: StoryStep[] }) {
  const [active, setActive] = useState<ScreenId>(steps[0].id);
  const refs = useRef<Array<HTMLLIElement | null>>([]);

  useEffect(() => {
    const els = refs.current.filter(Boolean) as HTMLLIElement[];
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setActive(entry.target.getAttribute("data-step") as ScreenId);
          }
        }
      },
      { rootMargin: "-42% 0px -42% 0px" },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  return (
    <div className={styles.story}>
      <div className={styles.sticky} aria-hidden="true">
        <Phone screen={active} layers />
      </div>
      <ol className={styles.steps}>
        {steps.map((step, i) => (
          <li
            key={step.id}
            data-step={step.id}
            data-active={step.id === active}
            ref={(el) => {
              refs.current[i] = el;
            }}
            className={styles.step}
          >
            <p className={styles.stepNo} aria-hidden="true">
              {i + 1}
            </p>
            <h3>{step.title}</h3>
            <p>{step.body}</p>
            <div className={styles.inlinePhone}>
              <Phone screen={step.id} />
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
