// Task threads: the real /api/today lanes plus three labelled demo threads for a fresh visitor.
// Sidebar groups by product domain (Household / Places / …), not by Grok-style bot channels.

import { classifyDomain, type DomainId, type ServiceCategoryId } from "./domains";

export type Lane = "needs_you" | "running" | "scheduled" | "on_list" | "paused" | "completed";

export interface TodayTask {
  id: string;
  outcome?: string;
  status?: string;
  next_step?: string | null;
  due_at?: string | null;
  updated_at?: string;
  source_status?: string;
}
export type TodayResponse = Partial<Record<Lane, { tasks: TodayTask[]; has_more?: boolean }>>;

export type TaskThread = {
  id: string;
  title: string;
  status: string;
  lane: Lane;
  preview: string;
  at: string;
  unread: boolean;
  demo: boolean;
  domain: DomainId;
  category: ServiceCategoryId | null;
};

/** Open lanes in display order. Completed tasks are history, not open threads. */
const ORDER: Lane[] = ["needs_you", "running", "scheduled", "on_list", "paused"];

export const LANE_LABEL: Record<Lane, string> = {
  needs_you: "Needs you", running: "Running", scheduled: "Scheduled", on_list: "On your list", paused: "Paused", completed: "Done",
};

/** Website demo threads (cursor-plan best-5 + classics) — labelled Demo; never invent provider success. */
export const DEMO_TASKS: TaskThread[] = [
  { id: "demo-taxi", title: "Lost bag in taxi", status: "DEMO", lane: "needs_you", preview: "Let’s track your ride", at: "", unread: true, demo: true, domain: "travel", category: "transport" },
  { id: "demo-khda", title: "School + home shortlist", status: "DEMO", lane: "needs_you", preview: "Year 5 · British · tours", at: "", unread: true, demo: true, domain: "household", category: "schools" },
  { id: "demo-insurance", title: "Clinic on my network", status: "DEMO", lane: "needs_you", preview: "B+ match near JLT", at: "", unread: true, demo: true, domain: "money", category: "insurance" },
  { id: "demo-mamzar", title: "Mamzar Saturday", status: "DEMO", lane: "running", preview: "Plan ready — Yes to all", at: "", unread: false, demo: true, domain: "lifestyle", category: "food" },
  { id: "demo-guests", title: "Guests at 8", status: "DEMO", lane: "needs_you", preview: "Clean + dinner plan", at: "", unread: true, demo: true, domain: "household", category: "cleaning" },
  { id: "demo-gym", title: "Gym renewal", status: "DEMO", lane: "scheduled", preview: "Fitness First Marina", at: "", unread: false, demo: true, domain: "lifestyle", category: "gym" },
  { id: "demo-laundry", title: "Laundry pickup", status: "DEMO", lane: "running", preview: "Driver on the way — example only", at: "", unread: false, demo: true, domain: "lifestyle", category: "laundry" },
  { id: "demo-ac", title: "AC repair", status: "DEMO", lane: "on_list", preview: "Before Friday", at: "", unread: false, demo: true, domain: "household", category: "ac" },
];

function preview(t: TodayTask, lane: Lane): string {
  if (lane === "needs_you") return "needs your approval";
  if (lane === "running") return "waiting for provider";
  if (lane === "scheduled") return "check-back scheduled";
  if (t.next_step) return t.next_step.slice(0, 60);
  return LANE_LABEL[lane].toLowerCase();
}

function threadFromTask(t: TodayTask, lane: Lane): TaskThread {
  const title = t.outcome?.trim() || "Untitled task";
  const guess = classifyDomain([title, t.next_step ?? ""].filter(Boolean).join(" "));
  return {
    id: t.id,
    title,
    status: t.status ?? "",
    lane,
    preview: preview(t, lane),
    at: t.updated_at ?? "",
    unread: lane === "needs_you",
    demo: false,
    domain: guess.domain,
    category: guess.category,
  };
}

export function toThreads(today: TodayResponse, dismissedDemo: string[]): TaskThread[] {
  const seen = new Set<string>();
  const real: TaskThread[] = [];
  for (const lane of ORDER) {
    for (const t of today[lane]?.tasks ?? []) {
      if (!t.id || seen.has(t.id)) continue;
      seen.add(t.id);
      real.push(threadFromTask(t, lane));
    }
  }
  return [...real, ...DEMO_TASKS.filter((d) => !dismissedDemo.includes(d.id))];
}

export function briefing(threads: TaskThread[]): { needsYou?: TaskThread; changed?: TaskThread; due?: TaskThread } {
  const needsYou = threads.find((t) => t.lane === "needs_you");
  const due = threads.find((t) => t.lane === "scheduled");
  const others = threads.filter((t) => t !== needsYou);
  const pool = others.filter((t) => t !== due);
  const candidates = pool.length ? pool : others;
  let changed: TaskThread | undefined;
  for (const t of candidates) if (!changed || Date.parse(t.at || "") > Date.parse(changed.at || "")) changed = t;
  // Date.parse("") is NaN, and NaN > x is false, so ties and demo threads keep the first candidate.
  return { ...(needsYou && { needsYou }), ...(changed && { changed }), ...(due && { due }) };
}

/** "12m", "1h", "2d" since an ISO time; empty for no time. */
export function relTime(iso: string, now = Date.now()): string {
  const then = Date.parse(iso);
  if (!iso || Number.isNaN(then)) return "";
  const min = Math.max(0, Math.round((now - then) / 60000));
  if (min < 60) return `${min}m`;
  if (min < 60 * 24) return `${Math.floor(min / 60)}h`;
  return `${Math.floor(min / 1440)}d`;
}
