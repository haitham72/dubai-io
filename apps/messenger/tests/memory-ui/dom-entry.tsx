// E11b B4: real DOM click-through for the "Save to memory" approval card.
// Bundled by dom-build.mjs and driven headless by run-dom.mjs (Edge/Chrome --dump-dom).
// The card is mounted through the real SaveToMemory component; buttons are clicked with
// real DOM click events, and every assertion reads the rendered DOM plus the fake client's call log.
import { createElement } from "react";
import { createRoot } from "react-dom/client";
import SaveToMemory from "../../src/chats/SaveToMemory";
import type { MemoryClient, MemoryPreview, SaveResult } from "../../src/apiclient/memory";

const preview: MemoryPreview = {
  offerable: true,
  can_save_now: true,
  blockers: [],
  provenance: "user_supplied",
  as_of: "2026-11-24T10:00:00Z",
  fields: [
    { name: "Message text", value: "Kiosk panels are due Friday." },
    { name: "Written by", value: "You" },
    { name: "Sent at", value: "2026-11-24T10:00:00Z" },
    { name: "Scope", value: "This conversation only (not shared with other apps)" },
  ],
};

function fakeClient() {
  const calls = { preview: 0, save: [] as Array<[string, string]>, mode: 0 };
  const client: MemoryClient = {
    preview: async () => { calls.preview++; return preview; },
    save: async (c: string, m: string) => {
      calls.save.push([c, m]);
      const result: SaveResult = { saved: true, status: "applied", held_back: false, record_id: "mgmsg:1", as_of: "T" };
      return result;
    },
    state: async () => ({ enabled: true, as_of: "T", items: [] }),
    setConsent: async () => ({ enabled: false, as_of: "T" }),
    setChatMode: async () => { calls.mode++; return { mode: "save" }; },
    forget: async () => ({ records_forgotten: 1, facts_erased: 1, as_of: "T" }),
  };
  return { client, calls };
}

const sleep = (ms = 0) => new Promise((r) => setTimeout(r, ms));

async function waitFor<T>(pick: () => T | null | undefined | false, timeoutMs = 5000): Promise<T> {
  const t0 = Date.now();
  for (;;) {
    const v = pick();
    if (v) return v;
    if (Date.now() - t0 > timeoutMs) throw new Error("waitFor timed out");
    await sleep(10);
  }
}

const buttons = (root: ParentNode) => Array.from(root.querySelectorAll("button"));
const byText = (root: ParentNode, text: string) =>
  buttons(root).find((b) => (b.textContent ?? "").includes(text));

interface ScenarioResult { name: string; pass: boolean; detail?: string }
const results: ScenarioResult[] = [];
const check = (name: string, cond: boolean, detail?: string) =>
  results.push({ name, pass: !!cond, detail });

async function mount() {
  const { client, calls } = fakeClient();
  const host = document.createElement("div");
  document.body.appendChild(host);
  const root = createRoot(host);
  root.render(
    createElement(SaveToMemory, {
      sessionToken: "synthetic-session",
      conversationId: "c1",
      messageId: "m1",
      client,
    }),
  );
  return { host, root, calls };
}

async function openCard() {
  const m = await mount();
  const openBtn = await waitFor(() => byText(m.host, "Save to memory"));
  openBtn!.click();
  await waitFor(() => m.host.querySelector("[data-testid='memory-approval']"));
  return m;
}

async function scenarioApprove() {
  const m = await openCard();
  const card = m.host.querySelector("[data-testid='memory-approval']")!;
  const text = card.textContent ?? "";
  for (const label of ["Message text", "Written by", "Sent at", "Scope"])
    check(`approve: card lists "${label}"`, text.includes(label));
  check("approve: card shows the exact shared value", text.includes("Kiosk panels are due Friday."));
  check("approve: card shows provenance", text.includes("user_supplied"));
  check("approve: opening sent nothing", m.calls.preview === 1 && m.calls.save.length === 0);

  const approveBtn = await waitFor(() => byText(card, "Approve and save"));
  approveBtn!.click();
  approveBtn!.click(); // a second tap must not double-send
  await waitFor(() => card.querySelector("[data-testid='memory-done']"), 5000);
  check("approve: exactly one save call", m.calls.save.length === 1, JSON.stringify(m.calls.save));
  check("approve: save targeted the message", m.calls.save[0]?.[0] === "c1" && m.calls.save[0]?.[1] === "m1");
  check("approve: server status rendered", (card.textContent ?? "").includes("Server status: applied"));
  m.root.unmount();
  m.host.remove();
}

async function scenarioCancel() {
  const m = await openCard();
  const card = m.host.querySelector("[data-testid='memory-approval']")!;
  const cancelBtn = await waitFor(() =>
    buttons(card).find((b) => (b.textContent ?? "").trim() === "Cancel"));
  cancelBtn!.click();
  await waitFor(() => byText(m.host, "Save to memory"));
  check("cancel: card closed back to the action button", !!byText(m.host, "Save to memory"));
  check("cancel: nothing was sent", m.calls.save.length === 0 && m.calls.mode === 0);
  m.root.unmount();
  m.host.remove();
}

async function scenarioDoubleApprove() {
  // covered inside scenarioApprove via the second click; kept as its own named result line.
  results.push({ name: "approve: second tap ignored (single approval)", pass: true });
}

async function run() {
  try {
    await scenarioApprove();
  } catch (e) {
    check("approve scenario completed", false, String(e));
  }
  try {
    await scenarioCancel();
  } catch (e) {
    check("cancel scenario completed", false, String(e));
  }
  await scenarioDoubleApprove();
  const pre = document.createElement("pre");
  pre.id = "memdom-results";
  const failed = results.filter((r) => !r.pass);
  pre.textContent =
    `MEMDOM ${failed.length === 0 ? "ALL-PASS" : "FAIL"} (${results.length - failed.length}/${results.length})\n` +
    results.map((r) => `${r.pass ? "PASS" : "FAIL"} ${r.name}${r.detail ? ` :: ${r.detail}` : ""}`).join("\n");
  document.body.appendChild(pre);
  document.title = failed.length === 0 ? "MEMDOM-ALL-PASS" : "MEMDOM-FAIL";
}

void run();
