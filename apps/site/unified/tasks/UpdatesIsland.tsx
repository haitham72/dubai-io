"use client";
import { LANE_LABEL, type TaskThread } from "../data/tasks";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import s from "./tasks.module.css";

/** The live task: the first needs-you thread, else the first running one. Demo threads are labelled Demo. */
export function liveThread(threads: TaskThread[]): TaskThread | undefined {
  return threads.find((t) => t.lane === "needs_you") ?? threads.find((t) => t.lane === "running");
}

/** `island` sits inside the hardware Dynamic Island (?device); `pill` is the same data as a slim pill on a real phone. */
export function UpdatesIsland({ variant = "island" }: { variant?: "island" | "pill" }) {
  const { threads } = useThreads();
  const { openThread } = useApp();
  const t = liveThread(threads);
  if (!t) return null;
  return (
    <button className={variant === "pill" ? s.pill : s.islandBtn} onClick={() => openThread(t.id)} data-testid={variant === "pill" ? "updates-pill" : undefined}>
      <i className={s.islandDot} />
      <span className={s.islandText}>{t.demo ? "Demo · " : ""}{t.title} · {LANE_LABEL[t.lane]}</span>
    </button>
  );
}
