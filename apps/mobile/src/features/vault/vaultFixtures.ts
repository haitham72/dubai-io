/** Synthetic Karim Haddad fixtures only (no real data). Shown with a Demo data pill. */
import type { VaultData, WhyResult } from "./vaultApi";

export const KARIM_VAULT_FIXTURES: VaultData = {
  themes: [
    { id: "th-career", path: "career", label: "Career", kind: "theme", status: "active", salience: 9, fact_count: 3, children: [
      { id: "s-interviews", path: "career/interviews", label: "Interviews", kind: "topic", status: "active", salience: 7, fact_count: 3 },
    ] },
    { id: "th-projects", path: "projects", label: "Projects", kind: "theme", status: "active", salience: 8, fact_count: 2 },
    { id: "th-learning", path: "learning", label: "Learning", kind: "theme", status: "candidate", salience: 5, fact_count: 1 },
    { id: "th-family", path: "people-family", label: "People & family", kind: "theme", status: "active", salience: 4, fact_count: 1, provenance: "user_supplied" },
    { id: "th-events", path: "events", label: "Events", kind: "theme", status: "active", salience: 4, fact_count: 2 },
    { id: "th-home", path: "home-money", label: "Home & money", kind: "theme", status: "active", salience: 3, fact_count: 1 },
    { id: "th-travel", path: "travel", label: "Travel", kind: "theme", status: "active", salience: 6, fact_count: 2 },
  ],
  people: [
    { id: "e-sara", kind: "person", name: "Sara Nasser", status: "active", relation_to_user: "colleague", closeness_tier: "T1", salience: 9, subjects: [{ subject_id: "th-projects", subject: "Projects", role: "beta tester", fact_count: 2 }] },
    { id: "e-omar", kind: "person", name: "Omar Farouk", status: "active", relation_to_user: "friend", closeness_tier: "T2", salience: 6, subjects: [{ subject_id: "th-career", subject: "Career", role: "referrer", fact_count: 1 }] },
  ],
  places: [
    { id: "e-qamar", kind: "place", name: "QamarTech Office, Dubai", status: "active", closeness_tier: null, salience: 5, subjects: [] },
  ],
  orgs: [],
  projects: [],
  suggestions: [],
  hiddenByGroup: {},
  error: null,
  facts: [
    { id: "f001", text: "Sara is a beta tester for the Raseef project", subject_id: "th-projects", valid_from: "2026-11-18", provenance: "user_supplied", as_of: "2026-11-18" },
    { id: "f002", text: "Karim interviewed at QamarTech on 18 Nov", subject_id: "s-interviews", valid_from: "2026-11-18", provenance: "inferred", as_of: "2026-11-18" },
  ],
  isDemo: true,
  demoData: true,
};

export const KARIM_WHY_FIXTURE: WhyResult = {
  fact_id: "f001",
  text: "Sara is a beta tester for the Raseef project",
  model: "your Claude",
  cost_badge: "processed on your Claude · $0 app cost",
  evidence: [
    { id: "wab-0001", source: "whatsapp:work", at: "2026-11-18T10:00:00+04:00", author: "Sara Nasser", text: "I tested the Raseef beta today", provenance: "user_supplied", as_of: "2026-11-18T10:00:00+04:00" },
  ],
  provenance: "user_supplied",
  as_of: "2026-11-18",
  demo_data: true,
};
