"use client";
import type { ReactNode } from "react";
import type { ScreenId } from "../screens";
import { Brand, Rail, ThemeToggle } from "./Rail";
import s from "./shell.module.css";

/** Desktop layout: left column (brand, rail, task threads) + main. */
export function Shell({ screen, sidebar, main }: { screen: ScreenId; sidebar: ReactNode; main: ReactNode }) {
  return (
    <div className={s.app}>
      <aside className={s.left}>
        <Brand />
        <Rail screen={screen} />
        <div className={s.sidebar}>{sidebar}</div>
        <div className={s.leftFoot}><ThemeToggle /></div>
      </aside>
      <main className={s.main}>{main}</main>
    </div>
  );
}
