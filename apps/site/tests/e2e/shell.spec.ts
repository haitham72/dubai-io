import { expect, test } from "@playwright/test";
import { mockApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await mockApi(page);
  // skip onboarding for shell tests
  await page.addInitScript(() => localStorage.setItem("dubaiio.onboarded", "1"));
});

test("desktop width shows the six rail labels in order", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await expect(page.getByTestId("rail-items").locator("button")).toHaveText(["Assistant", "Chats", "Services", "Maps", "Dashboard", "Me"]);
  await expect(page.getByTestId("tabbar")).toHaveCount(0);
});

test("phone width shows Home/Chat/Services/Feed + Ask tabs", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByTestId("tabbar").locator("button")).toHaveText(["Home", "Chat", "Services", "Feed", "Ask"]);
  await expect(page.getByTestId("rail-items")).toHaveCount(0);
});

test("?device shows the iPhone frame", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?device");
  await expect(page.getByTestId("device-frame")).toBeVisible();
  await expect(page.getByTestId("tabbar")).toBeVisible();
});

test("?desktop shows the Mac window", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/?desktop");
  await expect(page.getByTestId("mac-window")).toBeVisible();
  await expect(page.getByTestId("rail-items")).toBeVisible();
});

test("non-home screens say which plan builds them", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByTestId("rail-items").getByRole("button", { name: "Services" }).click();
  await expect(page.getByText("Coming in plan 4")).toBeVisible();
});

test("resizing 1440 to 390 keeps the typed composer draft", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("pressed shirts tonight");
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByTestId("tabbar")).toBeVisible();
  await expect(page.getByTestId("composer-input")).toHaveValue("pressed shirts tonight");
});
