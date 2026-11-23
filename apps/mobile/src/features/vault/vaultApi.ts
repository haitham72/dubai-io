/**
 * Memory Vault API client (WP I-B).
 * Shapes mirror apps/memory vault.py: GET /v1/owners/{owner}/vault/subjects,
 * /vault/people, /timeline and /why/{fact_id}. Any fetch failure falls back to
 * synthetic Karim fixtures and is reported as demo data (never hidden).
 */
export type Fetcher = (url: string) => Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>;

export interface SubjectNode {
  id: string; path: string; label: string; kind: string; status: string;
  salience: number; fact_count: number; direct_fact_count?: number;
  provenance?: string; as_of?: string; demo_data?: boolean;
  sensitive_cat?: string | null; quarantined?: boolean; sensitive?: boolean;
  children?: SubjectNode[];
}
export interface VaultEntity {
  id: string; kind: string; name: string; status: string;
  relation_to_user?: string | null; closeness_tier?: "T1" | "T2" | "T3" | null;
  aliases?: string[]; salience?: number; first_seen?: string | null; last_seen?: string | null;
  subjects?: { subject_id: string; subject: string; role?: string | null; fact_count: number; weight?: number }[];
  sensitive_cat?: string | null; quarantined?: boolean; sensitive?: boolean;
}
export interface VaultFact {
  id: string; text: string; subject_id?: string; valid_from?: string;
  provenance?: string; as_of?: string; sensitive_cat?: string | null;
  quarantined?: boolean; sensitive?: boolean;
}
export interface WhyEvidence { id: string; source: string; at: string; author: string; text: string; provenance?: string; as_of?: string; sensitive_cat?: string | null; quarantined?: boolean }
export interface WhyResult {
  fact_id: string; text: string; status?: string; valid_from?: string;
  model: string; cost_badge: string | null; evidence: WhyEvidence[];
  provenance: string; as_of: string; demo_data?: boolean;
}
export interface VaultData {
  themes: SubjectNode[];
  people: VaultEntity[]; places: VaultEntity[]; orgs: VaultEntity[];
  facts: VaultFact[]; isDemo: boolean; demoData: boolean;
}

export const SENSITIVE_CATEGORIES = [
  "health", "religion", "ethnicity_nationality", "gender_sexuality",
  "politics", "third_party_private", "credential", "family_third_party",
] as const;

export function isSensitive(item: { sensitive_cat?: string | null; quarantined?: boolean; sensitive?: boolean }): boolean {
  if (item.quarantined || item.sensitive) return true;
  return !!item.sensitive_cat && (SENSITIVE_CATEGORIES as readonly string[]).includes(item.sensitive_cat);
}

/** Rule 9: drop sensitive/quarantined subjects (recursively) and entities. */
export function filterSubjects(nodes: SubjectNode[]): SubjectNode[] {
  return nodes.filter((n) => !isSensitive(n)).map((n) => ({ ...n, children: filterSubjects(n.children ?? []) }));
}
export function filterEntities<T extends VaultEntity>(items: T[]): T[] {
  return items.filter((e) => !isSensitive(e) && e.status !== "merged");
}
export function filterFacts<T extends VaultFact>(items: T[]): T[] {
  return items.filter((f) => !isSensitive(f));
}

export const THEME_COLORS: Record<string, string> = {
  Career: "#2F80ED", Projects: "#9B51E0", Learning: "#F2994A",
  Gaming: "#EB5757", Travel: "#00B4D8", Health: "#27AE60",
};
export function themeColorFor(label: string): string {
  const head = label.split(/[/\s-]/)[0];
  return THEME_COLORS[label] ?? THEME_COLORS[head] ?? "#C5A059";
}

export interface ConstellationNode { id: string; label: string; x: number; y: number; r: number; color: string; factCount: number }

/** Deterministic golden-angle layout (no Math.random / Date.now). */
export function buildSubjectNodes(themes: SubjectNode[], size = 320): ConstellationNode[] {
  const flat: { node: SubjectNode; theme: string }[] = [];
  const walk = (nodes: SubjectNode[], theme: string) => nodes.forEach((n) => {
    flat.push({ node: n, theme }); walk(n.children ?? [], theme);
  });
  [...themes].sort((a, b) => a.label.localeCompare(b.label)).forEach((t) => walk([t], t.label));
  const center = size / 2;
  return flat.map(({ node, theme }, i) => {
    const angle = i * 2.399963229728653;
    const radius = 14 * Math.sqrt(i + 1);
    return {
      id: node.id, label: node.label,
      x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle),
      r: 5 + Math.sqrt(node.fact_count || 0) * 2, color: themeColorFor(theme),
      factCount: node.fact_count || 0,
    };
  });
}

/** People layout: concentric tiers, T1 innermost ("Inner Circle"). */
export function buildPeopleNodes(people: VaultEntity[], size = 320): ConstellationNode[] {
  const tierRadius: Record<string, number> = { T1: 42, T2: 88, T3: 126 };
  const sorted = [...people].sort((a, b) =>
    (tierRadius[a.closeness_tier ?? "T3"] - tierRadius[b.closeness_tier ?? "T3"]) ||
    a.name.localeCompare(b.name));
  const center = size / 2;
  return sorted.map((p, i) => {
    const angle = i * 2.399963229728653;
    const radius = tierRadius[p.closeness_tier ?? "T3"];
    return {
      id: p.id, label: p.name,
      x: center + radius * Math.cos(angle), y: center + radius * Math.sin(angle),
      r: p.closeness_tier === "T1" ? 10 : 7, color: p.closeness_tier === "T1" ? "#C5A059" : "#2F80ED",
      factCount: (p.subjects ?? []).reduce((sum, s) => sum + s.fact_count, 0),
    };
  });
}

const defaultFetcher: Fetcher = (url) => fetch(url);

async function getJson(fetcher: Fetcher, url: string): Promise<Record<string, unknown>> {
  const res = await fetcher(url);
  if (!res.ok) throw new Error(`Vault API ${res.status} for ${url}`);
  return (await res.json()) as Record<string, unknown>;
}

export async function loadVault(
  apiBaseUrl: string, owner: string,
  fixtures: VaultData,
  fetcher: Fetcher = defaultFetcher,
): Promise<VaultData> {
  const base = `${apiBaseUrl.replace(/\/$/, "")}/v1/owners/${encodeURIComponent(owner)}`;
  try {
    const [subjects, people, timeline] = await Promise.all([
      getJson(fetcher, `${base}/vault/subjects`),
      getJson(fetcher, `${base}/vault/people`),
      getJson(fetcher, `${base}/timeline`).catch(() => ({ items: [] })),
    ]);
    const demo = subjects.demo_data === true || people.demo_data === true;
    return {
      themes: filterSubjects((subjects.themes as SubjectNode[]) ?? []),
      people: filterEntities((people.people as VaultEntity[]) ?? []),
      places: filterEntities((people.places as VaultEntity[]) ?? []),
      orgs: filterEntities((people.orgs as VaultEntity[]) ?? []),
      facts: filterFacts((timeline.items as VaultFact[]) ?? []),
      isDemo: demo, demoData: demo,
    };
  } catch {
    return { ...fixtures, themes: filterSubjects(fixtures.themes),
      people: filterEntities(fixtures.people), places: filterEntities(fixtures.places),
      orgs: filterEntities(fixtures.orgs), facts: filterFacts(fixtures.facts),
      isDemo: true, demoData: true };
  }
}

export async function loadWhy(
  apiBaseUrl: string, owner: string, factId: string,
  fixtureWhy: WhyResult | null,
  fetcher: Fetcher = defaultFetcher,
): Promise<{ why: WhyResult | null; isDemo: boolean; error: string | null }> {
  const url = `${apiBaseUrl.replace(/\/$/, "")}/v1/owners/${encodeURIComponent(owner)}/why/${encodeURIComponent(factId)}`;
  try {
    const raw = await getJson(fetcher, url);
    const why = raw as unknown as WhyResult;
    return { why: { ...why, evidence: (why.evidence ?? []).filter((e) => !isSensitive(e)) },
      isDemo: why.demo_data === true, error: null };
  } catch {
    if (fixtureWhy) {
      return { why: { ...fixtureWhy, evidence: fixtureWhy.evidence.filter((e) => !isSensitive(e)) },
        isDemo: true, error: null };
    }
    return { why: null, isDemo: false, error: "Fact not found or forgotten" };
  }
}
