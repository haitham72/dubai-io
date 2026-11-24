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

const CLUSTERS = ["Career", "Learning", "Projects", "People & family", "Events", "Home & money", "Travel"];

test("graph DTO renders 7 clusters and falls back when the route is missing", async () => {
  const graph = async (url: string) => {
    if (url.includes("view=subjects")) return okJson({
      demo_data: false,
      nodes: CLUSTERS.map((label, i) => ({ id: `c${i}`, kind: "cluster", label, group: label, fact_count: i + 1, provenance: "inferred" })),
      counts: { hidden_by_group: { career: 3 } },
    })();
    if (url.includes("view=people")) return okJson({
      demo_data: false,
      nodes: [
        { id: "owner", kind: "owner", label: "Karim Haddad" },
        { id: "omar", kind: "person", label: "Omar Farouk", tier: "T1", provenance: "user_supplied", subtitle: "friend" },
        { id: "layla", kind: "person", label: "Layla Haddad", tier: null, closeness_suggested: "T1", provenance: "inferred" },
        { id: "cafe", kind: "place", label: "Alserkal Cafe", place_type: "restaurant", provenance: "inferred" },
      ],
      counts: { hidden_by_group: {} },
    })();
    return okJson({ items: [] })();
  };
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={graph} />);
  await waitFor(() => expect(screen.getByText("Career")).toBeTruthy());
  for (const label of CLUSTERS) expect(screen.getAllByText(label).length).toBeGreaterThan(0);
  expect(screen.getByText("+3 more")).toBeTruthy();
  expect(screen.queryByText("Demo data")).toBeNull();
  expect(screen.queryByText(/You told me/)).toBeNull();
  await fireEvent.press(screen.getByText("People & Places"));
  expect(screen.getByText("T1 Inner Circle")).toBeTruthy();
  expect(screen.getAllByText(/You told me Omar Farouk/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/I noticed Layla Haddad/).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Alserkal Cafe · restaurant/).length).toBeGreaterThan(0);
  expect(screen.queryByText(/✓ Layla/)).toBeNull();
});

test("missing graph route falls back to subjects and people", async () => {
  const fetcher = async (url: string) => {
    if (url.includes("/vault/graph")) return { ok: false, status: 404, json: async () => ({}) };
    if (url.includes("vault/subjects")) return okJson({ themes: [
      { id: "t1", path: "career", label: "Career", kind: "theme", status: "active", salience: 1, fact_count: 2, provenance: "user_supplied" },
    ], demo_data: false })();
    if (url.includes("vault/people")) return okJson({ people: [
      { id: "p1", kind: "person", name: "Sara", status: "active", closeness_tier: "T1", provenance: "user_supplied" },
    ], places: [], orgs: [], demo_data: false })();
    return okJson({ items: [] })();
  };
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={fetcher} />);
  await waitFor(() => expect(screen.getByText("Career")).toBeTruthy());
  expect(screen.queryByText("Demo data")).toBeNull();
});

test("401 is shown and does not fall back to demo fixtures", async () => {
  const fetcher = async () => ({ ok: false, status: 401, json: async () => ({}) });
  const screen = await render(<VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={fetcher} />);
  await waitFor(() => expect(screen.getByText("Sign-in required")).toBeTruthy());
  expect(screen.queryByText("Demo data")).toBeNull();
  expect(screen.queryByText("Career")).toBeNull();
});

test("suggestion Confirm posts the tier and demo fixtures are explicit", async () => {
  const posts: string[] = [];
  const graph = async (url: string) => {
    if (url.includes("view=subjects")) return okJson({ demo_data: false, nodes: [{ id: "c", kind: "cluster", label: "Career", fact_count: 1 }], counts: { hidden_by_group: {} } })();
    if (url.includes("view=people")) return okJson({
      demo_data: false,
      nodes: [{ id: "layla", kind: "person", label: "Layla Haddad", closeness_suggested: "T1", provenance: "inferred" }],
      counts: { hidden_by_group: {} },
    })();
    return okJson({ items: [] })();
  };
  const screen = await render(
    <VaultScreen apiBaseUrl="http://192.168.1.10:8000" owner="karim" fetcher={graph} poster={async (url) => { posts.push(url); return { ok: true, status: 200 }; }} />,
  );
  await waitFor(() => expect(screen.getByText("Career")).toBeTruthy());
  await fireEvent.press(screen.getByText("People & Places"));
  expect(screen.queryByText("T1 Inner Circle")).toBeNull();
  await fireEvent.press(screen.getByTestId("confirm-layla"));
  expect(posts[0]).toContain("/vault/people/layla/tier");
  expect(screen.queryByText("Demo data")).toBeNull();
});
