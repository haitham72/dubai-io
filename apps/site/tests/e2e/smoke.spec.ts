import { expect, test } from "@playwright/test";

test("home responds 200", async ({ page }) => {
  const res = await page.goto("/");
  expect(res?.status()).toBe(200);
});
