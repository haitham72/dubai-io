import React from "react";
import { render, waitFor } from "@testing-library/react-native";
import { QuestsScreen } from "../../src/features/quests/QuestsScreen";
import { KARIM_QUESTS_FIXTURES } from "../../src/features/quests/questsFixtures";
import { normalizeMilestoneState } from "../../src/features/quests/questsApi";

test("fixture quests show honest states and Demo pill", async () => {
  const screen = await render(<QuestsScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" initialData={KARIM_QUESTS_FIXTURES} />);
  expect(screen.getByText("Demo data")).toBeTruthy();
  expect(screen.getByText("Land a product role in Dubai")).toBeTruthy();
  expect(screen.getByText("Done")).toBeTruthy();
  expect(screen.getAllByText("In progress").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Planned").length).toBeGreaterThan(0);
});

test("Rule 1: unknown states and done-without-evidence are never shown as Done", async () => {
  expect(normalizeMilestoneState({ id: "a", title: "x", state: "completed", evidence_fact_ids: ["f1"] })).toBe("planned");
  expect(normalizeMilestoneState({ id: "b", title: "x", state: "done", evidence_fact_ids: [] })).toBe("planned");
  expect(normalizeMilestoneState({ id: "c", title: "x", state: "done", evidence_fact_ids: ["f1"] })).toBe("done");
  const data = { isDemo: false, demoData: false, quests: [{
    id: "g1", path: "career/x", label: "Fabricated goal",
    milestones: [
      { id: "m1", title: "Claimed complete", state: "completed", evidence_fact_ids: ["f1"] },
      { id: "m2", title: "Claimed done no evidence", state: "done", evidence_fact_ids: [] },
    ],
  }] };
  const screen = await render(<QuestsScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" initialData={data} />);
  expect(screen.queryByText("Done")).toBeNull();
  expect(screen.queryByText("Demo data")).toBeNull();
  expect(screen.getByText(/0 done/)).toBeTruthy();
});

test("live quests without demo flag show no Demo pill", async () => {
  const fetcher = async () => ({ ok: true, status: 200, json: async () => ({
    quests: [{ id: "g9", path: "life/x", label: "Live goal", milestones: [
      { id: "m9", title: "Live milestone", state: "done", evidence_fact_ids: ["f9"] },
    ] }], demo_data: false }) });
  const screen = await render(<QuestsScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={fetcher} />);
  await waitFor(() => expect(screen.getByText("Live goal")).toBeTruthy());
  expect(screen.getByText("Done")).toBeTruthy();
  expect(screen.queryByText("Demo data")).toBeNull();
});
