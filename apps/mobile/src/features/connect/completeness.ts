/** Deterministic context weights from gamified-onboarding-and-analytics.md §3. */

export interface CompletenessSources {
  gmail: boolean;
  calendar: boolean;
  youtubeApi: boolean;
  whatsapp: boolean;
  youtubeWatch: boolean;
  chrome: boolean;
  aiSessions: boolean;
}

export const COMPLETENESS_WEIGHTS = {
  gmail: 14,
  calendar: 10,
  youtubeApi: 12,
  whatsapp: 15,
  youtubeWatch: 12,
  chrome: 18,
  aiSessions: 19,
} as const;

export const GOOGLE_SIGN_IN: CompletenessSources = {
  gmail: true,
  calendar: true,
  youtubeApi: true,
  whatsapp: false,
  youtubeWatch: false,
  chrome: false,
  aiSessions: false,
};

export function completenessPct(sources: CompletenessSources): number {
  let total = 0;
  (Object.keys(COMPLETENESS_WEIGHTS) as (keyof CompletenessSources)[]).forEach((key) => {
    if (sources[key]) total += COMPLETENESS_WEIGHTS[key];
  });
  return Math.min(100, total);
}

export function desktopGapPct(sources: CompletenessSources): number {
  return (sources.chrome ? 0 : COMPLETENESS_WEIGHTS.chrome)
    + (sources.aiSessions ? 0 : COMPLETENESS_WEIGHTS.aiSessions);
}

export function completenessBanner(sources: CompletenessSources): string {
  const pct = completenessPct(sources);
  const gap = desktopGapPct(sources);
  if (gap > 0) {
    return `Dubai-io knows you ${pct}% · Log in on Dubai-io Desktop on your PC to add more context (+${gap}%)`;
  }
  return `Dubai-io knows you ${pct}%`;
}

export const PC_SETUP_LINK = "https://dubai-io.local/pair/karim";

export interface RevealFact {
  id: string;
  theme: string;
  text: string;
  src: string;
  asOf: string;
}

export const REVEAL_FACTS: RevealFact[] = [
  {
    id: "rev-learning",
    theme: "Learning & Ideas",
    text: "Interface typography notes are an active interest",
    src: "youtube:interests",
    asOf: "2026-11-18",
  },
  {
    id: "rev-career",
    theme: "Career & Craft",
    text: "A product-role search is open in Dubai",
    src: "gmail",
    asOf: "2026-11-17",
  },
  {
    id: "rev-events",
    theme: "Events",
    text: "A design review is on the calendar this week",
    src: "calendar",
    asOf: "2026-11-18",
  },
];

export const LIFE_SPINES = [
  { id: "career", label: "Career & Craft", count: 4 },
  { id: "projects", label: "Projects", count: 3 },
  { id: "learning", label: "Learning & Ideas", count: 6 },
  { id: "people", label: "People & Inner Circle", count: 2 },
  { id: "home", label: "Home & Money", count: 1 },
  { id: "events", label: "Events", count: 2 },
  { id: "travel", label: "Travel & Places", count: 1 },
] as const;

export const RISING_INTEREST = "Rising 21-Day Interests vs Baseline: interface typography +18%";

export const SIGNAL_MIX = [
  { source: "gmail", count: 4 },
  { source: "youtube:interests", count: 3 },
  { source: "whatsapp", count: 0 },
  { source: "browser", count: 0 },
  { source: "agent:claude-code", count: 0 },
  { source: "agent:codex", count: 0 },
  { source: "ai:chatgpt", count: 0 },
  { source: "takeout:*", count: 0 },
] as const;

/** Synthetic count of items the Rule-9 filter held back. Never the items themselves. */
export const RULE9_HELD_BACK = 4;

export const OWNER_HOOK_FACTS = 0;
