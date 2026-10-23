"use client";
import type { ReactNode } from "react";
import { useApp } from "../state";
import { ModeSwitch } from "./ModeSwitch";
import { BackdropSkyline } from "./Skyline";
import s from "./assistant.module.css";

/** Assistant main area: the Assistant / Community switch on top, content below. The haze sits only behind the home hero. */
export function AssistantFrame({ haze, children }: { haze?: boolean; children: ReactNode }) {
  const { mode, setMode, resolvedTheme } = useApp();
  return (
    <div className={s.frame}>
      {haze && resolvedTheme === "light" && <div className={s.haze} data-testid="home-haze" aria-hidden="true" />}
      {haze && <BackdropSkyline />}
      <div className={s.top}><ModeSwitch value={mode} onChange={setMode} /></div>
      {children}
    </div>
  );
}
