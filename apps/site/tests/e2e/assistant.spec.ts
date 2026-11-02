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

test("places_near loads live Google cards (mocked provider)", async ({ page }) => {
  await mockApi(page, {
    turn: (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          reply: "Here are gyms near you.",
          intent: "places_near",
          category: "coffee",
          query: "gym",
        }),
      }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("Gyms near Dubai Marina open now");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("live-places")).toBeVisible();
  await expect(page.getByTestId("live-place").first()).toContainText("Wellfit Marina");
  await expect(page.getByTestId("live-place").first()).toContainText("provider_confirmed");
  await expect(page.getByTestId("live-places")).toContainText("Live from Google");
});

test("product ask loads live shopping cards (mocked provider)", async ({ page }) => {
  await mockApi(page, {
    turn: (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          reply: "Looking for green shirts.",
          intent: "product_search",
          query: "green shirt",
          products: [],
        }),
      }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("I need a green shirt");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("live-products")).toBeVisible();
  await expect(page.getByTestId("live-product").first()).toContainText("Giordano");
  await expect(page.getByTestId("live-product-photo").first()).toBeVisible({ timeout: 8000 });
  await expect(page.getByTestId("because-chips")).toContainText("size XL");
});

test("clothes try-on sheet needs approval then shows AI preview", async ({ page }) => {
  await mockApi(page, {
    turn: (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          reply: "Looking for green shirts.",
          intent: "product_search",
          query: "green shirt",
          products: [],
        }),
      }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("I need a green shirt");
  await page.getByRole("button", { name: "Send" }).click();
  await page.getByTestId("tryon-open").first().click();
  await expect(page.getByTestId("tryon-sheet")).toBeVisible();
  await expect(page.getByTestId("tryon-approval")).toBeVisible();
  await page.getByTestId("tryon-file").setInputFiles({
    name: "me.png",
    mimeType: "image/png",
    buffer: Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
      "base64",
    ),
  });
  await page.getByTestId("tryon-adult").check();
  await page.getByTestId("tryon-approve").check();
  await page.getByTestId("tryon-run").click();
  await expect(page.getByTestId("tryon-result")).toBeVisible();
  await expect(page.getByTestId("tryon-result")).toContainText("Demo data");
});

test("nearby wording still loads Places when Luna returns info_question", async ({ page }) => {
  await mockApi(page, {
    turn: (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          reply: "I can help you look for gyms near Dubai Marina.",
          intent: "info_question",
          answer: "Looking that up.",
        }),
      }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("Gyms near Dubai Marina open now");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("live-place").first()).toContainText("Wellfit Marina");
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
  // Website defaults to light; force system so OS colorScheme still drives the theme.
  await page.addInitScript(() => localStorage.setItem("dubaiio.theme", "system"));
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  const haze = page.getByTestId("home-haze");
  await expect(haze).toBeVisible();
  expect(await haze.evaluate((el) => getComputedStyle(el).animationName)).toBe("none");
  await page.emulateMedia({ colorScheme: "dark" });
  await expect(page.getByTestId("home-haze")).toHaveCount(0);
});

test("domain starters fill the composer and show a live domain chip", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByTestId("domain-starter").first()).toBeVisible();
  await expect(page.getByTestId("domain-starter").filter({ hasText: "Gyms near Marina" })).toHaveAttribute("data-live", "1");
  await page.getByTestId("domain-starter").filter({ hasText: "Gyms near Marina" }).click();
  await expect(page.getByTestId("composer-input")).toHaveValue(/gyms near dubai marina/i);
  await expect(page.getByTestId("composer-domain")).toHaveAttribute("data-domain", "lifestyle");
});

test("Lost bag starter opens the full taxi demo thread", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByTestId("domain-starter").filter({ hasText: "Lost bag in taxi" }).click();
  await expect(page.getByTestId("thread-view")).toBeVisible();
  await expect(page.getByTestId("demo-msg-user")).toContainText(/backpack|taxi/i);
  await expect(page.getByTestId("choice-rideshare")).toBeVisible();
  await expect(page.getByTestId("choice-cash")).toBeVisible();
});

test("KHDA demo loads live schools and opens sites instead of dead Approve", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByTestId("thread-row").filter({ hasText: "School + home" }).click();
  await expect(page.getByTestId("demo-constraints")).toBeVisible();
  await page.getByRole("button", { name: "Find live schools near JLT" }).click();
  await expect(page.getByTestId("live-biz-card").first()).toContainText("Arcadia");
  await page.getByTestId("live-biz-card").first().getByRole("button").first().click();
  await page.getByRole("button", { name: /Plan tour enquiries/ }).click();
  await page.getByTestId("open-school-sites").click();
  await expect(page.getByTestId("demo-status")).toContainText(/Blocked|websites opened/i);
});

test("Gym demo loads live club and offers real membership site", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByTestId("thread-row").filter({ hasText: "Gym renewal" }).click();
  await expect(page.getByTestId("live-biz-card").first()).toContainText("Wellfit Marina");
  await page.getByTestId("choice-renew").click();
  await expect(page.getByTestId("open-gym-site")).toBeEnabled();
});

test("sent messages keep a domain label on the user bubble", async ({ page }) => {
  await mockApi(page, {
    turn: (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ reply: "Noted.", intent: "chat" }) }),
  });
  await page.goto("/");
  await page.getByTestId("composer-input").fill("I need laundry pickup tomorrow");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByTestId("msg-domain")).toHaveText("Lifestyle");
  await expect(page.getByTestId("msg-user")).toContainText("laundry");
});

test("Community switch shows the seeded feed surface", async ({ page }) => {
  await mockApi(page);
  await page.goto("/");
  await page.getByRole("tab", { name: "Community" }).click();
  await expect(page.getByTestId("community-view")).toBeVisible();
  await page.getByRole("tab", { name: "Assistant" }).click();
  await expect(page.getByTestId("composer-input")).toBeVisible();
});
