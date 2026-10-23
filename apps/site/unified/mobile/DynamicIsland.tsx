"use client";
import type { ReactNode } from "react";
import s from "./mobile.module.css";

/** The hardware island of the ?device frame. `children` (the live task, Task 6) renders inside it. */
export function DynamicIsland({ children }: { children?: ReactNode }) {
  return (
    <div className={`${s.island} ${children ? s.islandLive : ""}`} data-testid="dynamic-island">
      {children}
    </div>
  );
}
