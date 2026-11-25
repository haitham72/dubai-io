// E11b B4: drive the bundled DOM click-through test in a real headless browser.
// Uses the OS Edge/Chrome binary with --headless --dump-dom (no npm dependencies).
// The page runs the scenarios on load and writes PASS/FAIL lines into #memdom-results.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const html = join(here, "dom-test.html");

const candidates = [
  process.env.MEMDOM_BROWSER,
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
].filter(Boolean);
const browser = candidates.find((p) => existsSync(p));
if (!browser) {
  console.error("MEMDOM-SKIP: no Edge/Chrome binary found (set MEMDOM_BROWSER)");
  process.exit(0); // environment without a browser: report as skip, not failure
}

const profile = join(here, ".memdom-profile");
const res = spawnSync(
  browser,
  [
    "--headless=new",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
    `--user-data-dir=${profile}`,
    "--virtual-time-budget=20000",
    "--dump-dom",
    `file:///${html.replaceAll("\\", "/")}`,
  ],
  { encoding: "utf8", timeout: 120000, maxBuffer: 64 * 1024 * 1024 },
);

const out = `${res.stdout ?? ""}\n${res.stderr ?? ""}`;
const m = out.match(/<pre id="memdom-results">([\s\S]*?)<\/pre>/);
if (!m) {
  console.error("MEMDOM-FAIL: no results block in dumped DOM");
  console.error(out.slice(-4000));
  process.exit(1);
}
const text = m[1].replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
console.log(text);
process.exit(text.includes("MEMDOM ALL-PASS") ? 0 : 1);
