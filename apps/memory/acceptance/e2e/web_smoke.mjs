// E6 lane 4: Playwright smoke of the three websites at 390x844 and 1440x900, signed in as synthetic account A.
// usage: node web_smoke.mjs <sessions.json> <screens-dir> <report.json>   (run from a dir where `playwright` is installed)
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const [sessPath, outDir, reportPath] = process.argv.slice(2);
const S = JSON.parse(fs.readFileSync(sessPath, "utf8")).A;
fs.mkdirSync(outDir, { recursive: true });
const sizes = { mobile: { width: 390, height: 844 }, desktop: { width: 1440, height: 900 } };
const sites = [
  { name: "dubaiio", base: "http://localhost:8081", routes: ["/", "/chat", "/memory", "/quests", "/connect"],
    init: (s) => localStorage.setItem("dubaiio.authSession", JSON.stringify({ sessionToken: s.tokens.quest, sessionId: s.ids.quest, userId: s.userId, displayName: s.name, email: null })) },
  { name: "community", base: "http://localhost:3060", routes: ["/", "/communities", "/inbox", "/profile", "/create"],
    init: (s) => localStorage.setItem("dubaiio_community_session", s.tokens.community) },
  { name: "messenger", base: "http://localhost:5173", routes: ["/"],
    init: (s) => sessionStorage.setItem("messenger.session", JSON.stringify({ sessionToken: s.tokens.messenger, userId: s.userId, displayName: s.name, apiBase: "", activeChatId: "" })) },
];
const ctxData = { userId: S.user_id, name: S.display_name, tokens: S.sessions, ids: S.session_ids };
const results = [];
const browser = await chromium.launch();
for (const site of sites) for (const [sz, vp] of Object.entries(sizes)) {
  const ctx = await browser.newContext({ viewport: vp });
  await ctx.addInitScript(`(${site.init.toString()})(${JSON.stringify(ctxData)})`);
  for (const route of site.routes) {
    const page = await ctx.newPage();
    const errors = [], failedReqs = [];
    page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 200)); });
    page.on("pageerror", (e) => errors.push("pageerror: " + String(e).slice(0, 200)));
    page.on("response", (r) => { if (r.status() >= 400) failedReqs.push(`${r.status()} ${r.url().slice(0, 100)}`); });
    let status = null, ok = true, note = "";
    try {
      const resp = await page.goto(site.base + route, { waitUntil: "load", timeout: 60000 });
      status = resp ? resp.status() : null;
      await page.waitForTimeout(3500);
    } catch (e) { ok = false; note = String(e).slice(0, 160); }
    const bodyText = ok ? (await page.evaluate(() => document.body?.innerText || "")).trim() : "";
    const file = `${site.name}-${sz}-${route === "/" ? "home" : route.replace(/\//g, "")}.png`;
    try { await page.screenshot({ path: path.join(outDir, file), fullPage: false }); } catch {}
    const rendered = ok && bodyText.length > 20 && status !== null && status < 400;
    results.push({ site: site.name, size: sz, route, status, rendered, textLen: bodyText.length, consoleErrors: errors.length, errors: errors.slice(0, 4), serverErrors: failedReqs.slice(0, 3), note, shot: file });
    await page.close();
  }
  await ctx.close();
}
await browser.close();
fs.writeFileSync(reportPath, JSON.stringify(results, null, 1));
for (const r of results) console.log(`${r.rendered && r.consoleErrors === 0 ? "PASS" : "FAIL"} ${r.site} ${r.size} ${r.route} http=${r.status} text=${r.textLen} consoleErrors=${r.consoleErrors} ${r.errors[0] || ""}`);
