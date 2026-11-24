/** Quests API (/api/vault/quests) with honest states and explicit demo gate. */
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
export interface QuestsData {
  quests: QuestGoal[];
  isDemo: boolean;
  demoData: boolean;
  error?: string | null;
}

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

const defaultFetcher: Fetcher = (url, init) => fetch(url, init);

export async function loadQuests(
  apiBaseUrl: string, _owner: string, fixtures: QuestsData,
  fetcher: Fetcher = defaultFetcher,
  options?: { demo?: boolean; sessionToken?: string | null },
): Promise<QuestsData> {
  if (options?.demo) {
    return { ...fixtures, isDemo: true, demoData: true, error: null };
  }
  const cleanBase = apiBaseUrl.replace(/\/$/, "");
  if (!cleanBase) {
    return { quests: [], isDemo: false, demoData: false, error: "Connect to your API server" };
  }
  if (!options?.sessionToken && fetcher === defaultFetcher) {
    return { quests: [], isDemo: false, demoData: false, error: "Sign-in required" };
  }
  const url = `${cleanBase}/api/vault/quests`;
  const init: RequestInit | undefined = options?.sessionToken
    ? { headers: { "X-App-Session": options.sessionToken } }
    : undefined;
  try {
    const res = await fetcher(url, init);
    if (!res.ok) {
      return {
        quests: [],
        isDemo: false,
        demoData: false,
        error: res.status === 401 || res.status === 403 ? "Sign-in required" : `Quests API ${res.status}`,
      };
    }
    const raw = (await res.json()) as { quests?: QuestGoal[]; demo_data?: boolean };
    const quests = (raw.quests ?? []).map((q) => ({
      ...q, milestones: (q.milestones ?? []).filter((m) => !m.quarantined && !m.sensitive_cat),
    }));
    const demo = raw.demo_data === true;
    return { quests, isDemo: demo, demoData: demo, error: null };
  } catch {
    return { quests: [], isDemo: false, demoData: false, error: "Quests unavailable" };
  }
}
