import { expect, test } from "@playwright/test";
import { mockApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  await page.addInitScript(() => localStorage.setItem("dubaiio.onboarded", "1"));
});

test("profile row opens Me, where the theme control lives", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: /View profile/ }).click();
  await expect(page.getByTestId("me-screen")).toBeVisible();
  await page.getByTestId("me-screen").getByRole("button", { name: /Theme/ }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
});

test("Connect apps opens a Not available yet panel", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByRole("button", { name: /Connect apps/ }).click();
  await expect(page.getByTestId("connectors-panel")).toContainText("Not available yet");
});

test("composer plus menu offers no fake attach", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  const box = await page.getByTestId("composer-input").locator("xpath=../..").boundingBox();
  expect(box!.height).toBeGreaterThanOrEqual(110);
  await page.getByRole("button", { name: "Add" }).click();
  await expect(page.getByRole("menuitem")).toHaveText("Connect apps — not available yet");
  await expect(page.getByRole("menuitem")).toHaveCount(1);
});

for (const [w, h] of [[1440, 900], [390, 844]] as const) {
  test(`briefing titles are not truncated at ${w}`, async ({ page }) => {
    await page.setViewportSize({ width: w, height: h });
    await page.goto("/");
    const titles = page.getByTestId("briefing-card").locator("span:has(> span)").filter({ hasText: /pickup|repair|bill/ });
    await expect(page.getByTestId("briefing-card")).toHaveCount(3);
    const clipped = await page.getByTestId("briefing-card").evaluateAll((cards) =>
      cards.flatMap((c) => [...c.querySelectorAll("span")].filter((e) => e.scrollWidth > e.clientWidth + 1).map((e) => e.textContent)));
    expect(clipped).toEqual([]);
    void titles;
  });
}
