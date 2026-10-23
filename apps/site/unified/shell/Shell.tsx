"use client";
import { useState, type ReactNode } from "react";
import { ChevronRight, Plus } from "lucide-react";
import type { ScreenId } from "../screens";
import { useApp } from "../state";
import { Brand, Rail } from "./Rail";
import s from "./shell.module.css";

/** Desktop layout: floating left card (brand, rail, task threads, profile, connect apps) + main. */
export function Shell({ screen, sidebar, main }: { screen: ScreenId; sidebar: ReactNode; main: ReactNode }) {
  const { setScreen, openThread } = useApp();
  const [connectors, setConnectors] = useState(false);
  return (
    <div className={s.app}>
      <aside className={s.left}>
        <Brand />
        <Rail screen={screen} />
        <div className={s.sidebar}>{sidebar}</div>
        <div className={s.leftFoot}>
          {connectors && (
            <div className={s.pop} role="dialog" aria-label="Connectors" data-testid="connectors-panel">
              <strong>Connectors</strong>
              <p>Gmail and Calendar: Not available yet.</p>
            </div>
          )}
          <button className={s.profile} onClick={() => { openThread(null); setScreen("me"); }}>
            <span className={s.initial}>Y</span>
            <span className={s.profileText}><b>You</b><small>View profile</small></span>
            <ChevronRight size={16} />
          </button>
          <button className={s.connect} aria-expanded={connectors} onClick={() => setConnectors((c) => !c)}>
            Connect apps <Plus size={16} />
          </button>
        </div>
      </aside>
      <main className={s.main}>{main}</main>
    </div>
  );
}
