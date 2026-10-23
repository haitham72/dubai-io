"use client";
import { Sparkles } from "lucide-react";
import s from "./onboarding.module.css";

/** The orb that wakes up. Motion is CSS only and disabled under prefers-reduced-motion. */
export function Orb() {
  return (
    <div className={s.orb} data-testid="orb" aria-hidden="true">
      <Sparkles size={34} strokeWidth={1.6} />
    </div>
  );
}
