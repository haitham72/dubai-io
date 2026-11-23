import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const out = path.resolve("..", "..", "docs", "submissions", "community", "review", "v2");
await mkdir(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage();
await page.addInitScript(() => {
  const hide = () => document.querySelectorAll("nextjs-portal").forEach((n) => n.remove());
  new MutationObserver(hide).observe(document.documentElement, { childList: true, subtree: true });
});

async function shot(width, height, file, ready) {
  await page.setViewportSize({ width, height });
  await page.goto("http://localhost:3060/", { waitUntil: "networkidle" });
  await page.waitForSelector(ready);
  await page.screenshot({ path: path.join(out, file), fullPage: false });
}

await shot(390, 844, "feed-phone.png", "text=JLT Residents");
await shot(1440, 900, "feed-desktop.png", "text=Ask Dubai-io privately");
await browser.close();
console.log("captured", out);
