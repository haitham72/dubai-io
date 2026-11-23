import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { VaultScreen } from "../../src/features/vault/VaultScreen";
import { KARIM_VAULT_FIXTURES } from "../../src/features/vault/vaultFixtures";

jest.mock("react-native-svg", () => {
  const ReactLib = require("react");
  const { View } = require("react-native");
  const Svg = (p: Record<string, unknown>) => ReactLib.createElement(View, p, (p as { children?: unknown }).children as never);
  const Circle = (p: Record<string, unknown>) => ReactLib.createElement(View, p);
  return { __esModule: true, default: Svg, Circle };
});

const okJson = (body: unknown) => async () => ({ ok: true, status: 200, json: async () => body });

const WHY = {
  fact_id: "f001", text: "Sara is a beta tester for the Raseef project",
  model: "your Claude", cost_badge: "processed on your Claude · $0 app cost",
  evidence: [{ id: "wab-0001", source: "whatsapp:work", at: "2026-11-18T10:00:00+04:00", author: "Sara", text: "I tested the Raseef beta today", provenance: "user_supplied", as_of: "2026-11-18" }],
  provenance: "user_supplied", as_of: "2026-11-18", demo_data: false,
};

test("subjects/people toggle, T1 badge and Demo pill on fixtures", async () => {
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" initialData={KARIM_VAULT_FIXTURES} />);
  expect(screen.getByText("Demo data")).toBeTruthy();
  expect(screen.getByText("Career")).toBeTruthy();
  await fireEvent.press(screen.getByText("People & Places"));
  expect(screen.getByText("T1 Inner Circle")).toBeTruthy();
  expect(screen.getAllByText(/Sara Nasser/).length).toBeGreaterThan(0);
  await fireEvent.press(screen.getByText("Subjects"));
  expect(screen.getByText("Projects")).toBeTruthy();
});

test("tap a verified fact opens Why sheet with your Claude badge, provenance and as_of", async () => {
  const fetcher = async (url: string) => {
    if (url.includes("/why/")) return { ok: true, status: 200, json: async () => WHY };
    throw new Error("unexpected");
  };
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" initialData={KARIM_VAULT_FIXTURES} fetcher={fetcher} />);
  await fireEvent.press(screen.getByText(/Sara is a beta tester/));
  await waitFor(() => expect(screen.getByText(/your Claude/)).toBeTruthy());
  expect(screen.getByText(/processed on your Claude/)).toBeTruthy();
  expect(screen.getByText(/provenance: user_supplied/)).toBeTruthy();
  expect(screen.getByText(/as_of: 2026-11-18/)).toBeTruthy();
  expect(screen.getByText(/I tested the Raseef beta today/)).toBeTruthy();
});

test("Rule 9: sensitive subjects and people never render", async () => {
  const payload = (url: string) => {
    if (url.includes("vault/subjects")) return okJson({ themes: [
      { id: "t1", path: "career", label: "Career", kind: "theme", status: "active", salience: 1, fact_count: 2 },
      { id: "t2", path: "health", label: "Diabetes care", kind: "theme", status: "active", salience: 1, fact_count: 1, sensitive_cat: "health", quarantined: true },
      { id: "t3", path: "faith", label: "Prayer routine", kind: "theme", status: "active", salience: 1, fact_count: 1, sensitive_cat: "religion" },
    ], demo_data: false })();
    if (url.includes("vault/people")) return okJson({ people: [
      { id: "p1", kind: "person", name: "Sara", status: "active", closeness_tier: "T1" },
      { id: "p2", kind: "person", name: "MumHidden", status: "active", sensitive_cat: "health", quarantined: true },
    ], places: [], orgs: [], demo_data: false })();
    return okJson({ items: [], demo_data: false })();
  };
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={payload} />);
  await waitFor(() => expect(screen.getByText("Career")).toBeTruthy());
  expect(screen.queryByText(/Diabetes/)).toBeNull();
  expect(screen.queryByText(/Prayer/)).toBeNull();
  expect(screen.queryByText("Demo data")).toBeNull(); // live payload, demo_data=false
  await fireEvent.press(screen.getByText("People & Places"));
  expect(screen.getAllByText(/Sara/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/MumHidden/)).toBeNull();
});
