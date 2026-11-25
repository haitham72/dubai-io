import React from "react";
import { View } from "react-native";
import { fireEvent, render } from "@testing-library/react-native";
import { CapsuleDock } from "../src/components/CapsuleDock";
import { CompletenessRingCard } from "../src/features/connect/CompletenessRingCard";
import { InitialRevealCard } from "../src/features/connect/InitialRevealCard";
import { GOOGLE_SIGN_IN, completenessPct } from "../src/features/connect/completeness";
import { UserAnalyticsCard } from "../src/features/vault/UserAnalyticsCard";
import { DOCK_TABS } from "../src/lib/types";

function Shell({ sources }: { sources: typeof GOOGLE_SIGN_IN }) {
  return (
    <View>
      <CompletenessRingCard sources={sources} />
      <CapsuleDock tabs={DOCK_TABS} active="today" onTabPress={() => undefined} onVoicePress={() => undefined} />
    </View>
  );
}

test("fresh Google sign-in is 36% and does not block the dock", async () => {
  expect(completenessPct(GOOGLE_SIGN_IN)).toBe(36);
  const view = await render(<Shell sources={GOOGLE_SIGN_IN} />);
  expect(view.getByTestId("completeness-banner").props.children).toBe(
    "Dubai-io knows you 36% · Log in on Dubai-io Desktop on your PC to add more context (+37%)",
  );
  expect(view.getByTestId("explore-app-now").props.disabled).toBeFalsy();
  for (const id of ["today", "chat", "quests", "memory"]) {
    expect(view.getByTestId(`dock-${id}`).props.disabled).toBeFalsy();
  }
  await fireEvent.press(view.getByTestId("explore-app-now"));
  expect(view.getByTestId("dock-today")).toBeTruthy();
});

test("desktop Chrome and AI sessions raise completeness to 73% or more", async () => {
  const connected = { ...GOOGLE_SIGN_IN, chrome: true, aiSessions: true };
  expect(completenessPct(connected)).toBeGreaterThanOrEqual(73);
  const view = await render(<CompletenessRingCard sources={connected} />);
  expect(view.getByText(/knows you 73%/)).toBeTruthy();
});

test("reveal cards show Confirm, Forget, and src evidence", async () => {
  const view = await render(<InitialRevealCard />);
  expect(view.getAllByText("Confirm").length).toBeGreaterThan(0);
  expect(view.getAllByText("Lower").length).toBeGreaterThan(0);
  expect(view.getByText(/src: gmail/)).toBeTruthy();
  expect(view.getByText(/src: youtube:interests/)).toBeTruthy();
  await fireEvent.press(view.getAllByText("Confirm")[0]);
  expect(view.getByText("You told me this is right")).toBeTruthy();
});

test("Rule-9 held-back count and Demo data pill render on analytics", async () => {
  const view = await render(<UserAnalyticsCard demo />);
  expect(view.getByText("Demo data")).toBeTruthy();
  expect(view.getByText(
    "4 sensitive items held back — health, faith, politics, credentials never inferred",
  )).toBeTruthy();
  expect(view.getByText(/\$0 app cost/)).toBeTruthy();
  expect(view.getByText(/Rising 21-Day Interests vs Baseline/)).toBeTruthy();
  expect(view.getByText(/agent:claude-code: 0/)).toBeTruthy();
});
