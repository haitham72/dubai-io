// E6 lane 5: launch each Electron shell once with Playwright's Electron support; check the window loads its URL and that
// off-origin navigation (location change + window.open) is blocked. shell.openExternal is stubbed so no OS browser opens.
// usage: node electron_smoke.mjs <report.json> <desktopMainJs>  (run from a dir where `playwright` is installed)
import { _electron as electron } from "playwright";
import fs from "node:fs";
import path from "node:path";

const [reportPath, desktopMain] = process.argv.slice(2);
const ROOT = "G:/Haitham/VsCode/contest-e6/apps";
const shells = [
  { name: "community-desktop", exe: `${ROOT}/community/desktop/node_modules/electron/dist/electron.exe`, args: [`${ROOT}/community/desktop/dist-electron/main.js`], env: { COMMUNITY_URL: "http://localhost:3060" }, base: "http://localhost:3060" },
  { name: "messenger-desktop", exe: `${ROOT}/messenger/desktop/node_modules/electron/dist/electron.exe`, args: [`${ROOT}/messenger/desktop/build/electron/main.js`], env: { MESSENGER_URL: "http://localhost:5173" }, base: "http://localhost:5173" },
  { name: "dubaiio-desktop", exe: `${ROOT}/desktop/node_modules/electron/dist/electron.exe`, args: [desktopMain], env: { DUBAI_DESKTOP_BOOT: "1" }, base: null },
];
const results = [];
for (const s of shells) {
  const r = { shell: s.name, started: false, loadedUrl: null, urlOk: null, offOriginBlocked: null, windowOpenBlocked: null, externalHandoffs: 0, notes: [] };
  let app;
  try {
    app = await electron.launch({ executablePath: s.exe, args: s.args, env: { ...process.env, ...s.env }, timeout: 60000 });
    r.started = true;
    const page = await app.firstWindow({ timeout: 60000 });
    await page.waitForLoadState("load", { timeout: 60000 }).catch(() => r.notes.push("load state timeout"));
    await page.waitForTimeout(3000);
    r.loadedUrl = page.url();
    r.urlOk = s.base ? r.loadedUrl.startsWith(s.base) : null;
    await app.evaluate(({ shell }) => { globalThis.__ext = []; shell.openExternal = async (u) => { globalThis.__ext.push(u); }; });
    const before = page.url();
    await page.evaluate(() => { location.href = "https://example.com/e6-offorigin"; }).catch(() => {});
    await page.waitForTimeout(3000);
    const after = page.url();
    r.offOriginBlocked = after === before && !after.includes("example.com");
    r.afterUrl = after;
    const winsBefore = app.windows().length;
    await page.evaluate(() => { window.open("https://example.com/e6-popup", "_blank"); }).catch(() => {});
    await page.waitForTimeout(2000);
    r.windowOpenBlocked = app.windows().length === winsBefore;
    r.externalHandoffs = await app.evaluate(() => (globalThis.__ext || []).length);
  } catch (e) { r.notes.push(String(e).slice(0, 300)); }
  finally { try { await app?.close(); } catch {} }
  results.push(r);
  console.log(JSON.stringify(r));
}
fs.writeFileSync(reportPath, JSON.stringify(results, null, 1));
