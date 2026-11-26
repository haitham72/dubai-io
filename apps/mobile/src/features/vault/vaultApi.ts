/**
 * Memory Vault API client (WP I-B + E2 authenticated /api/vault/* gateway).
 * All requests go through apps/api (/api/vault/*) with X-App-Session — never :8040 directly.
 */
export type Fetcher = (
  url: string,
  init?: RequestInit,
) => Promise<{ ok: boolean; status: number; json: () => Promise<unknown> }>;

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
  provenance?: string; place_type?: string | null;
  subjects?: { subject_id: string; subject: string; role?: string | null; fact_count: number; weight?: number }[];
  sensitive_cat?: string | null; quarantined?: boolean; sensitive?: boolean;
}
export interface VaultFact {
  lowered?: boolean;
  weight?: number;
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
export interface VaultSuggestion {
  id: string; name: string; suggested: "T1" | "T2" | "T3";
}
export interface VaultData {
  themes: SubjectNode[];
  people: VaultEntity[]; places: VaultEntity[]; orgs: VaultEntity[];
  projects: VaultEntity[];
  facts: VaultFact[];
  suggestions: VaultSuggestion[];
  hiddenByGroup: Record<string, number>;
  isDemo: boolean; demoData: boolean;
  error: string | null;
}

export interface GraphNode {
  id: string; kind: string; label: string; subtitle?: string | null; group?: string;
  tier?: "T1" | "T2" | "T3" | null;
  closeness_suggested?: "T1" | "T2" | "T3" | null;
  fact_count?: number; provenance?: string; place_type?: string | null;
}
export interface GraphDto {
  view?: string; demo_data?: boolean; provenance?: string;
  nodes?: GraphNode[];
  counts?: { hidden_by_group?: Record<string, number> };
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

export const CLUSTER_LABELS = [
  "Career", "Learning", "Projects", "People & family", "Events", "Home & money", "Travel",
] as const;

export const THEME_COLORS: Record<string, string> = {
  Career: "#2F80ED",
  Learning: "#F2994A",
  Projects: "#9B51E0",
  "People & family": "#C5A059",
  Events: "#EB5757",
  "Home & money": "#27AE60",
  Travel: "#00B4D8",
};
const GROUP_TO_LABEL: Record<string, string> = {
  career: "Career", learning: "Learning", projects: "Projects",
  "people-family": "People & family", events: "Events",
  "home-money": "Home & money", travel: "Travel",
};
export function themeColorFor(label: string): string {
  const mapped = GROUP_TO_LABEL[label] ?? label;
  const head = mapped.split(/[/\s-]/)[0];
  return THEME_COLORS[mapped] ?? THEME_COLORS[head] ?? "#C5A059";
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

const defaultFetcher: Fetcher = (url, init) => fetch(url, init);

async function getJson(fetcher: Fetcher, url: string, init?: RequestInit): Promise<Record<string, unknown>> {
  const res = await fetcher(url, init);
  if (!res.ok) throw new VaultStatusError(res.status);
  return (await res.json()) as Record<string, unknown>;
}

function emptyVault(error: string | null): VaultData {
  return {
    themes: [], people: [], places: [], orgs: [], projects: [], facts: [],
    suggestions: [], hiddenByGroup: {}, isDemo: false, demoData: false, error,
  };
}

function asGraph(body: unknown): GraphDto | null {
  if (!body || typeof body !== "object" || !Array.isArray((body as GraphDto).nodes)) return null;
  return body as GraphDto;
}

function clusterThemes(graph: GraphDto): SubjectNode[] {
  const clusters = (graph.nodes ?? []).filter((node) => node.kind === "cluster");
  return clusters.map((node) => ({
    id: node.id,
    path: node.group ?? node.id,
    label: node.label,
    kind: "theme",
    status: "active",
    salience: 0,
    fact_count: node.fact_count ?? 0,
    provenance: node.provenance,
  }));
}

function peopleFromGraph(graph: GraphDto): Pick<VaultData, "people" | "places" | "orgs" | "projects" | "suggestions"> {
  const people: VaultEntity[] = [];
  const places: VaultEntity[] = [];
  const orgs: VaultEntity[] = [];
  const projects: VaultEntity[] = [];
  const suggestions: VaultSuggestion[] = [];
  for (const node of graph.nodes ?? []) {
    if (node.kind === "owner") continue;
    const entity: VaultEntity = {
      id: node.id,
      kind: node.kind,
      name: node.label,
      status: "active",
      relation_to_user: node.subtitle ?? null,
      closeness_tier: node.tier ?? null,
      provenance: node.provenance,
      place_type: node.place_type ?? null,
    };
    if (node.kind === "person") {
      people.push(entity);
      if (node.closeness_suggested) {
        suggestions.push({ id: node.id, name: node.label, suggested: node.closeness_suggested });
      }
    } else if (node.kind === "place") places.push(entity);
    else if (node.kind === "project") projects.push(entity);
    else if (node.kind === "org") orgs.push(entity);
  }
  return { people, places, orgs, projects, suggestions };
}

export function graphToVault(subjects: GraphDto, people: GraphDto, facts: VaultFact[]): VaultData {
  const fromPeople = peopleFromGraph(people);
  const hidden = {
    ...(subjects.counts?.hidden_by_group ?? {}),
    ...(people.counts?.hidden_by_group ?? {}),
  };
  const demo = subjects.demo_data === true || people.demo_data === true;
  return {
    themes: filterSubjects(clusterThemes(subjects)),
    people: filterEntities(fromPeople.people),
    places: filterEntities(fromPeople.places),
    orgs: filterEntities(fromPeople.orgs),
    projects: filterEntities(fromPeople.projects),
    suggestions: fromPeople.suggestions,
    facts: filterFacts(facts),
    hiddenByGroup: hidden,
    isDemo: demo,
    demoData: demo,
    error: null,
  };
}

class VaultStatusError extends Error {
  constructor(readonly status: number) {
    super(status === 401 || status === 403 ? "Sign-in required" : `Vault API ${status}`);
  }
}

async function readBody(fetcher: Fetcher, url: string, init?: RequestInit): Promise<{ missing: boolean; body: unknown }> {
  const res = await fetcher(url, init);
  if (res.status === 404) return { missing: true, body: null };
  if (!res.ok) throw new VaultStatusError(res.status);
  return { missing: false, body: await res.json() };
}

function authInit(sessionToken?: string | null): RequestInit | undefined {
  return sessionToken ? { headers: { "X-App-Session": sessionToken } } : undefined;
}

export async function loadVault(
  apiBaseUrl: string, _owner: string,
  fixtures: VaultData,
  fetcher: Fetcher = defaultFetcher,
  options?: { demo?: boolean; sessionToken?: string | null; loweredOnly?: boolean },
): Promise<VaultData> {
  if (options?.demo) {
    return { ...fixtures, isDemo: true, demoData: true, error: null };
  }
  const cleanBase = apiBaseUrl.replace(/\/$/, "");
  if (!cleanBase) {
    return emptyVault("Connect to your API server");
  }
  if (!options?.sessionToken && fetcher === defaultFetcher) {
    return emptyVault("Sign-in required");
  }
  const base = `${cleanBase}/api/vault`;
  const init = authInit(options?.sessionToken);
  try {
    const [subjectRes, peopleRes, timeline] = await Promise.all([
      readBody(fetcher, `${base}/graph?view=subjects`, init),
      readBody(fetcher, `${base}/graph?view=people`, init),
      getJson(fetcher, `${base}/timeline${options?.loweredOnly ? "?lowered=true" : ""}`, init).catch(() => ({ items: [] })),
    ]);
    const subjectGraph = subjectRes.missing ? null : asGraph(subjectRes.body);
    const peopleGraph = peopleRes.missing ? null : asGraph(peopleRes.body);
    const facts = filterFacts((timeline.items as VaultFact[]) ?? []);
    if (subjectGraph && peopleGraph) return graphToVault(subjectGraph, peopleGraph, facts);
    if (subjectRes.missing || peopleRes.missing || !subjectGraph || !peopleGraph) {
      const [subjects, people] = await Promise.all([
        getJson(fetcher, `${base}/subjects`, init),
        getJson(fetcher, `${base}/people`, init),
      ]);
      const demo = subjects.demo_data === true || people.demo_data === true;
      return {
        themes: filterSubjects((subjects.themes as SubjectNode[]) ?? []),
        people: filterEntities((people.people as VaultEntity[]) ?? []),
        places: filterEntities((people.places as VaultEntity[]) ?? []),
        orgs: filterEntities((people.orgs as VaultEntity[]) ?? []),
        projects: filterEntities((people.projects as VaultEntity[]) ?? []),
        suggestions: [],
        facts,
        hiddenByGroup: {},
        isDemo: demo,
        demoData: demo,
        error: null,
      };
    }
    return emptyVault(null);
  } catch (err) {
    const message = err instanceof Error ? err.message : "Vault unavailable";
    return emptyVault(message);
  }
}

export async function loadWhy(
  apiBaseUrl: string, _owner: string, factId: string,
  fixtureWhy: WhyResult | null,
  fetcher: Fetcher = defaultFetcher,
  options?: { demo?: boolean; sessionToken?: string | null; loweredOnly?: boolean },
): Promise<{ why: WhyResult | null; isDemo: boolean; error: string | null }> {
  if (options?.demo && fixtureWhy) {
    return { why: { ...fixtureWhy, evidence: fixtureWhy.evidence.filter((e) => !isSensitive(e)) },
      isDemo: true, error: null };
  }
  const url = `${apiBaseUrl.replace(/\/$/, "")}/api/vault/why/${encodeURIComponent(factId)}`;
  try {
    const raw = await getJson(fetcher, url, authInit(options?.sessionToken));
    const why = raw as unknown as WhyResult;
    return { why: { ...why, evidence: (why.evidence ?? []).filter((e) => !isSensitive(e)) },
      isDemo: why.demo_data === true, error: null };
  } catch {
    if (options?.demo && fixtureWhy) {
      return { why: { ...fixtureWhy, evidence: fixtureWhy.evidence.filter((e) => !isSensitive(e)) },
        isDemo: true, error: null };
    }
    return { why: null, isDemo: false, error: "Fact not found or forgotten" };
  }
}
