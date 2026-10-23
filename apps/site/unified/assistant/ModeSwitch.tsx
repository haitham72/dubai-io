"use client";
import { Sparkles, Users } from "lucide-react";
import type { Mode } from "../state";
import s from "./assistant.module.css";

const OPTIONS: { value: Mode; label: string; icon: typeof Sparkles }[] = [
  { value: "assistant", label: "Assistant", icon: Sparkles },
  { value: "community", label: "Community", icon: Users },
];

/** Assistant / Community pill, top-centre. One view at a time. */
export function ModeSwitch({ value, onChange }: { value: Mode; onChange: (m: Mode) => void }) {
  return (
    <div className={s.modeSwitch} role="tablist" aria-label="View">
      {OPTIONS.map(({ value: v, label, icon: I }) => (
        <button key={v} role="tab" aria-selected={value === v} className={`${s.modeTab} ${value === v ? s.modeTabActive : ""}`} onClick={() => onChange(v)}>
          <I size={16} strokeWidth={1.9} />
          {label}
        </button>
      ))}
    </div>
  );
}
