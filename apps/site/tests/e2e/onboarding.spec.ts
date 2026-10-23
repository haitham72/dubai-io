import { expect, test } from "@playwright/test";
import { mockApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
});

test("first visit shows the orb and asks where you live; answering saves and advances", async ({ page }) => {
  const puts: string[] = [];
  await mockApi(page, { onRequest: (m, url, body) => { if (m === "PUT") puts.push(`${url} ${body}`); } });
  await page.goto("/");
  await expect(page.getByTestId("orb")).toBeVisible();
  await expect(page.getByText("Where in Dubai do you live?")).toBeVisible();
  await page.getByRole("button", { name: "Dubai Marina" }).click();
  await expect(page.getByText("Who is in your household?")).toBeVisible();
  expect(puts).toEqual(['/api/session/memory/area {"value":"Dubai Marina"}']);
});

test("reload mid-flow resumes at the next unanswered question and never re-asks saved facts", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Dubai Marina" }).click();
  await expect(page.getByText("Who is in your household?")).toBeVisible();
  await page.reload();
  await expect(page.getByText("Who is in your household?")).toBeVisible();
  await expect(page.getByText("Where in Dubai do you live?")).toHaveCount(0);
});

test("saved facts are skipped on a fresh visit", async ({ page }) => {
  await mockApi(page, { memory: { area: "JLT", household: "Just me" } });
  await page.goto("/");
  await expect(page.getByText("Which services do you use?")).toBeVisible();
  await expect(page.getByText("Where in Dubai do you live?")).toHaveCount(0);
});

test("a failed save keeps the question and says so", async ({ page }) => {
  await mockApi(page);
  await page.route("**/api/session/memory/area", (route) => route.fulfill({ status: 500, contentType: "application/json", body: '{"detail":"boom"}' }));
  await page.goto("/");
  await page.getByRole("button", { name: "JLT" }).click();
  await expect(page.getByTestId("onboarding-error")).toHaveText("Could not save that. Try again.");
  await expect(page.getByText("Where in Dubai do you live?")).toBeVisible();
});

test("connectors step says Not available yet and Later finishes", async ({ page }) => {
  await mockApi(page, { memory: { area: "JLT", household: "Just me", services: "Laundry" } });
  await page.goto("/");
  await expect(page.getByText("Gmail")).toBeVisible();
  await expect(page.getByText("Not available yet")).toHaveCount(2);
  await page.getByRole("button", { name: "Later" }).click();
  await expect(page.getByTestId("composer-input")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("dubaiio.onboarded"))).toBe("1");
});

test("Skip lands on the composer and sets the flag; later visits do not onboard", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Skip" }).click();
  await expect(page.getByTestId("composer-input")).toBeVisible();
  expect(await page.evaluate(() => localStorage.getItem("dubaiio.onboarded"))).toBe("1");
  await page.reload();
  await expect(page.getByTestId("composer-input")).toBeVisible();
  await expect(page.getByTestId("orb")).toHaveCount(0);
});

test("reduced motion: the orb has no running animation", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mockApi(page);
  await page.goto("/");
  const orb = page.getByTestId("orb");
  await expect(orb).toBeVisible();
  expect(await orb.evaluate((el) => getComputedStyle(el).animationName)).toBe("none");
});
