/** Synthetic Karim Haddad quest fixtures (Demo data). */
import type { QuestsData } from "./questsApi";

export const KARIM_QUESTS_FIXTURES: QuestsData = {
  quests: [
    {
      id: "goal-career", path: "career/job-search", label: "Land a product role in Dubai", status: "active",
      milestones: [
        { id: "ms1", title: "Interview at QamarTech", state: "done", evidence_fact_ids: ["f002"] },
        { id: "ms2", title: "Prepare portfolio walkthrough", state: "in_progress", evidence_fact_ids: ["f001"] },
        { id: "ms3", title: "Negotiate offer", state: "planned", evidence_fact_ids: [] },
      ],
    },
    {
      id: "goal-race", path: "life/half-marathon", label: "Run a half marathon", status: "candidate",
      milestones: [
        { id: "ms4", title: "Run 10k comfortably", state: "in_progress", evidence_fact_ids: ["f001"] },
        { id: "ms5", title: "Race day", state: "planned", evidence_fact_ids: [] },
      ],
    },
  ],
  isDemo: true,
  demoData: true,
};
