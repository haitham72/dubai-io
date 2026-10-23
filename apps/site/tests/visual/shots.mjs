// Visual gate: node tests/visual/shots.mjs [baseUrl] [outDir]
// Captures /, /?desktop, /?device at 1440x900 (and 390x844 for the plain URL), light and dark, onboarding and home.
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";

const base = process.argv[2] ?? "http://127.0.0.1:3042";
const out = process.argv[3] ?? "../../output/unified-shots/plan1";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch();
const shots = [
  ["", 1440, 900], ["?desktop", 1440, 900], ["?device", 1440, 900], ["", 390, 844],
];
for (const scheme of ["light", "dark"]) {
  for (const flow of ["onboarding", "home"]) {
    for (const [query, w, h] of shots) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: scheme });
      if (flow === "home") await ctx.addInitScript(() => localStorage.setItem("dubaiio.onboarded", "1"));
      const page = await ctx.newPage();
      await page.goto(`${base}/${query}`);
      await page.waitForTimeout(1500);
      const name = `${flow}-${query.replace("?", "") || (w === 390 ? "phone" : "website")}-${w}-${scheme}.png`;
      await page.screenshot({ path: `${out}/${name}` });
      await ctx.close();
    }
  }
}
await browser.close();
