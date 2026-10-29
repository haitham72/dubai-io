import type { DomainId } from "./domains";
import type { TaskThread } from "./tasks";

export const DOMAIN_OVERRIDE_KEY = "dubaiio.domainOverrides";

export function readDomainOverrides(): Record<string, DomainId> {
  try {
    const raw = JSON.parse(localStorage.getItem(DOMAIN_OVERRIDE_KEY) ?? "{}");
    if (!raw || typeof raw !== "object") return {};
    const out: Record<string, DomainId> = {};
    for (const [id, domain] of Object.entries(raw as Record<string, unknown>)) {
      if (
        typeof id === "string" &&
        (domain === "household" || domain === "places" || domain === "services" || domain === "work" || domain === "general")
      ) {
        out[id] = domain;
      }
    }
    return out;
  } catch {
    return {};
  }
}

export function writeDomainOverrides(map: Record<string, DomainId>): void {
  try {
    localStorage.setItem(DOMAIN_OVERRIDE_KEY, JSON.stringify(map));
  } catch {
    /* storage blocked */
  }
}

/** Apply user moves on top of keyword classification. */
export function applyDomainOverrides(threads: TaskThread[], overrides: Record<string, DomainId>): TaskThread[] {
  return threads.map((t) => {
    const domain = overrides[t.id];
    return domain && domain !== t.domain ? { ...t, domain, category: t.category } : t;
  });
}
