import { expect, test } from "@playwright/test";
import { EMPTY_TODAY, lane, mockApi } from "./helpers";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("dubaiio.onboarded", "1"));
  await page.setViewportSize({ width: 1440, height: 900 });
});

for (const [hour, word] of [[9, "Good morning"], [14, "Good afternoon"], [20, "Good evening"]] as const) {
  test(`greets "${word}" at ${hour}:00`, async ({ page }) => {
    await mockApi(page);
    await page.clock.setFixedTime(new Date(2026, 9, 23, hour, 0, 0));
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toContainText(word);
  });
}

test("sending shows the mocked Luna reply and clears the draft", async ({ page }) => {
  await mockApi(page, {
    turn: (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ reply: "Hi, how can I help?", intent: "chat" }) }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("hello");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("msg-assistant").last()).toHaveText("Hi, how can I help?");
  await expect(page.getByTestId("msg-user").last()).toHaveText("hello");
  await expect(page.getByTestId("composer-input")).toHaveValue("");
});

test("history-shaped replies use the last luna item", async ({ page }) => {
  await mockApi(page, {
    turn: (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ history: [{ role: "user", text: "hello" }, { role: "luna", text: "From history" }] }) }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("hello");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("msg-assistant").last()).toHaveText("From history");
});

test("a 503 shows an honest error, no fake reply, and keeps the draft", async ({ page }) => {
  await mockApi(page, {
    turn: (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "OPENAI_API_KEY is not set" }) }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("hello");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("composer-error")).toHaveText("Assistant unavailable — try again");
  await expect(page.getByTestId("composer-input")).toHaveValue("hello");
  await expect(page.getByTestId("msg-assistant")).toHaveCount(0);
});

test("briefing strip renders three cards from /api/today", async ({ page }) => {
  await mockApi(page, {
    today: {
      ...EMPTY_TODAY,
      needs_you: lane([{ id: "n1", outcome: "Approve AC visit", status: "WAITING_USER", updated_at: "2026-10-23T08:00:00+04:00" }]),
      running: lane([{ id: "r1", outcome: "Pressing order", status: "WAITING_USER", updated_at: "2026-10-23T09:30:00+04:00" }]),
      scheduled: lane([{ id: "s1", outcome: "Renew Salik tag", status: "WAITING_USER", updated_at: "2026-10-21T08:00:00+04:00" }]),
    },
  });
  await page.goto("/");
  const cards = page.getByTestId("briefing-card");
  await expect(cards).toHaveCount(3);
  await expect(cards.nth(0)).toContainText("Needs you");
  await expect(cards.nth(0)).toContainText("Approve AC visit");
  await expect(cards.nth(1)).toContainText("Changed");
  await expect(cards.nth(1)).toContainText("Pressing order");
  await expect(cards.nth(2)).toContainText("Due");
  await expect(cards.nth(2)).toContainText("Renew Salik tag");
  await expect(cards.locator("[data-testid=demo-pill]")).toHaveCount(0);
});

test("empty today briefs from the three labelled demo tasks", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByTestId("briefing-card")).toHaveCount(3);
  await expect(page.getByTestId("briefing-card").locator("[data-testid=demo-pill]")).toHaveCount(3);
});

test("home haze is present in light, absent in dark, and static", async ({ page }) => {
  await mockApi(page);
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  const haze = page.getByTestId("home-haze");
  await expect(haze).toBeVisible();
  expect(await haze.evaluate((el) => getComputedStyle(el).animationName)).toBe("none");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.getByTestId("home-haze")).toHaveCount(0);
});

test("Community switch shows the placeholder until plan 3", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("tab", { name: "Community" }).click();
  await expect(page.getByText("Coming in plan 3")).toBeVisible();
  await page.getByRole("tab", { name: "Assistant" }).click();
  await expect(page.getByTestId("composer-input")).toBeVisible();
});
