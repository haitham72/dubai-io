"use client";
import { Monitor, Moon, Sun } from "lucide-react";
import { RAIL, type ScreenId } from "../screens";
import { useApp } from "../state";
import s from "./shell.module.css";

export function Brand() {
  return (
    <div className={s.brand}>
      <span className={s.logo}>D</span>
      <span className={s.brandText}>
        <strong>Dubai-io</strong>
        <small>Your personal AI assistant for everyday life in Dubai.</small>
      </span>
    </div>
  );
}

export function Rail({ screen }: { screen: ScreenId }) {
  const { setScreen, openThread } = useApp();
  return (
    <nav className={s.rail} aria-label="Main" data-testid="rail">
      <div className={s.railItems} data-testid="rail-items">
        {RAIL.map(({ id, label, icon: I }) => (
          <button
            key={id}
            className={`${s.railItem} ${screen === id ? s.railItemActive : ""}`}
            aria-current={screen === id ? "page" : undefined}
            onClick={() => { setScreen(id); if (id === "assistant") openThread(null); }}
          >
            <I size={20} strokeWidth={1.75} />
            {label}
          </button>
        ))}
      </div>
    </nav>
  );
}

export function ThemeToggle() {
  const { themePref, setThemePref } = useApp();
  const next = themePref === "system" ? "light" : themePref === "light" ? "dark" : "system";
  const Icon = themePref === "system" ? Monitor : themePref === "light" ? Sun : Moon;
  return (
    <button className={s.themeBtn} onClick={() => setThemePref(next)} aria-label={`Theme: ${themePref}. Switch to ${next}`} title={`Theme: ${themePref}`}>
      <Icon size={16} strokeWidth={1.75} />
      <span>{themePref === "system" ? "System" : themePref === "light" ? "Light" : "Dark"}</span>
    </button>
  );
}
