import { expect, test } from "@playwright/test";
import { EMPTY_TODAY, lane, mockApi } from "./helpers";

const REAL_TODAY = {
  ...EMPTY_TODAY,
  needs_you: lane([{ id: "t1", outcome: "Approve AC visit", status: "WAITING_USER", updated_at: "2026-10-23T08:00:00+04:00" }]),
  running: lane([{ id: "t2", outcome: "Pressing order", status: "WAITING_USER", updated_at: "2026-10-23T09:30:00+04:00", source_status: "SUBMITTED" }]),
};

const TASKS = {
  t1: {
    task: { id: "t1", outcome: "Approve AC visit", status: "WAITING_USER", next_step: "Approve the visit window", updated_at: "2026-10-23T08:00:00+04:00" },
    events: [
      { seq: 1, kind: "created", at: "2026-10-23T07:00:00+04:00", actor: "user" },
      { seq: 2, kind: "edited", at: "2026-10-23T07:30:00+04:00", actor: "user", fields: ["details"] },
      { seq: 3, kind: "staged_reply", at: "2026-10-23T08:00:00+04:00", actor: "staged", provenance: "demo_fixture", sender: "AC Co (demo)", text: "We can come at 5 pm." },
    ],
  },
};

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("dubaiio.onboarded", "1"));
  await page.setViewportSize({ width: 1440, height: 900 });
});

test("sidebar lists real threads first, then demo threads with Demo pills", async ({ page }) => {
  await mockApi(page, { today: REAL_TODAY, tasks: TASKS });
  await page.goto("/");
  const rows = page.getByTestId("thread-row");
  await expect(rows).toHaveCount(5);
  await expect(rows.nth(0)).toContainText("Approve AC visit");
  await expect(rows.nth(1)).toContainText("Pressing order");
  await expect(rows.nth(2)).toContainText("AC repair");
  await expect(rows.nth(0).getByTestId("demo-pill")).toHaveCount(0);
  await expect(rows.nth(2).getByTestId("demo-pill")).toHaveCount(1);
});

test("opening a real thread renders its activity entries in order", async ({ page }) => {
  await mockApi(page, { today: REAL_TODAY, tasks: TASKS });
  await page.goto("/");
  await expect(page.getByTestId("thread-row")).toHaveCount(5);
  await page.getByTestId("thread-row").first().click();
  const entries = page.getByTestId("activity-entry");
  await expect(entries).toHaveCount(3);
  await expect(entries.nth(0)).toContainText("Task created");
  await expect(entries.nth(1)).toContainText("Details edited");
  await expect(entries.nth(2)).toContainText("We can come at 5 pm.");
  await expect(entries.nth(2).getByTestId("demo-pill")).toHaveCount(1);
  await expect(page.getByTestId("thread-view")).toContainText("Approve the visit window");
});

test("a thread that cannot load says so instead of inventing content", async ({ page }) => {
  await mockApi(page, { today: REAL_TODAY, tasks: {} });
  await page.goto("/");
  await expect(page.getByTestId("thread-row")).toHaveCount(5);
  await page.getByTestId("thread-row").first().click();
  await expect(page.getByTestId("thread-error")).toHaveText("This task could not be loaded.");
});

test("dismissing a demo thread removes it and survives reload", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByTestId("thread-row")).toHaveCount(3);
  await page.getByTestId("thread-row").filter({ hasText: "AC repair" }).click();
  await expect(page.getByTestId("thread-view").getByTestId("demo-pill")).toBeVisible();
  await page.getByRole("button", { name: "Dismiss demo" }).click();
  await expect(page.getByTestId("thread-row")).toHaveCount(2);
  await expect(page.getByTestId("thread-row").filter({ hasText: "AC repair" })).toHaveCount(0);
  expect(await page.evaluate(() => localStorage.getItem("dubaiio.dismissedDemo"))).toBe('["demo-ac"]');
  await page.reload();
  await expect(page.getByTestId("thread-row")).toHaveCount(2);
});

test("Updates island shows the first needs-you thread on the phone", async ({ page }) => {
  await mockApi(page, { today: REAL_TODAY, tasks: TASKS });
  await page.goto("/?device");
  await expect(page.getByTestId("dynamic-island")).toContainText("Approve AC visit");
  await expect(page.getByTestId("dynamic-island")).toContainText("Needs you");
});

test("Updates island marks demo content as Demo", async ({ page }) => {
  await mockApi(page);
  await page.goto("/?device");
  await expect(page.getByTestId("dynamic-island")).toContainText("Demo");
  await expect(page.getByTestId("dynamic-island")).toContainText("AC repair");
});

test("polls /api/today every 20 s while visible and stops while hidden", async ({ page }) => {
  let today = 0;
  await mockApi(page, { onRequest: (_m, url) => { if (url === "/api/today") today++; } });
  await page.clock.install();
  await page.goto("/");
  await expect.poll(() => today).toBeGreaterThanOrEqual(1);
  const first = today;
  expect(first).toBeGreaterThanOrEqual(1);
  await page.clock.runFor(21_000);
  await expect.poll(() => today).toBeGreaterThan(first);
  await page.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const atHide = today;
  await page.clock.runFor(25_000);
  await page.waitForTimeout(300);
  expect(today).toBe(atHide);
});
