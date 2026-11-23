/** Quests API (vault.py GET /v1/owners/{owner}/quests) with honest states. */
import type { Fetcher } from "../vault/vaultApi";

export type MilestoneState = "done" | "in_progress" | "planned";
export interface Milestone {
  id: string; title: string; state: string; evidence_fact_ids?: string[];
  provenance?: string; as_of?: string; demo_data?: boolean;
  sensitive_cat?: string | null; quarantined?: boolean;
}
export interface QuestGoal {
  id: string; path: string; label: string; status?: string;
  milestones: Milestone[]; counts?: Record<string, number>;
  provenance?: string; as_of?: string; demo_data?: boolean;
}
export interface QuestsData { quests: QuestGoal[]; isDemo: boolean; demoData: boolean }

/**
 * Rule 1: only the whitelisted states are honoured, and `done` requires
 * authoritative evidence (non-empty evidence_fact_ids). Anything else is
 * shown as planned — never fabricated as done.
 */
export function normalizeMilestoneState(m: Milestone): MilestoneState {
  if (m.state === "done" && (m.evidence_fact_ids?.length ?? 0) > 0) return "done";
  if (m.state === "in_progress") return "in_progress";
  return "planned";
}
export function milestoneCounts(milestones: Milestone[]): Record<MilestoneState, number> {
  const counts: Record<MilestoneState, number> = { done: 0, in_progress: 0, planned: 0 };
  milestones.forEach((m) => { counts[normalizeMilestoneState(m)] += 1; });
  return counts;
}
export function milestoneLabel(state: MilestoneState): string {
  return state === "done" ? "Done" : state === "in_progress" ? "In progress" : "Planned";
}

const defaultFetcher: Fetcher = (url) => fetch(url);

export async function loadQuests(
  apiBaseUrl: string, owner: string, fixtures: QuestsData,
  fetcher: Fetcher = defaultFetcher,
): Promise<QuestsData> {
  const url = `${apiBaseUrl.replace(/\/$/, "")}/v1/owners/${encodeURIComponent(owner)}/quests`;
  try {
    const res = await fetcher(url);
    if (!res.ok) throw new Error(`Quests API ${res.status}`);
    const raw = (await res.json()) as { quests?: QuestGoal[]; demo_data?: boolean };
    const quests = (raw.quests ?? []).map((q) => ({
      ...q, milestones: (q.milestones ?? []).filter((m) => !m.quarantined && !m.sensitive_cat),
    }));
    const demo = raw.demo_data === true;
    return { quests, isDemo: demo, demoData: demo };
  } catch {
    return { ...fixtures, isDemo: true, demoData: true };
  }
}
