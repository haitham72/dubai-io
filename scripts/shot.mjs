// Screenshot a nav screen at 1920x1080 with headless Chrome, and report console errors.
// usage: node scripts/shot.mjs http://localhost:<port> /tmp/out.png "<Nav label>" ["<JS to run after, e.g. clicking>"]
// Then LOOK at the png (open it / read it as an image). "Done" means the screenshot looks right.
import { spawn } from "node:child_process";
const port = 9300 + (process.pid % 600);
const [url, out, nav, extra] = process.argv.slice(2);
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  [`--headless=new`, `--remote-debugging-port=${port}`, "--window-size=1920,1080", "--hide-scrollbars",
   `--user-data-dir=/tmp/mirsal-shot-${process.pid}`, "about:blank"], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let ws;
for (let i = 0; i < 40 && !ws; i++) {
  await sleep(250);
  try {
    const list = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    const page = list.find((t) => t.type === "page");
    if (page) ws = new WebSocket(page.webSocketDebuggerUrl);
  } catch {}
}
await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pending = new Map(); const errors = [];
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m.result); pending.delete(m.id); }
  if (m.method === "Runtime.exceptionThrown") errors.push(m.params.exceptionDetails.exception?.description ?? "exception");
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") errors.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
});
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
await send("Page.navigate", { url });
await sleep(2500);
if (nav) await send("Runtime.evaluate", { expression: `[...document.querySelectorAll('nav button')].find(b => b.textContent.trim().startsWith(${JSON.stringify(nav)}))?.click()` });
await sleep(3500);
if (extra) { await send("Runtime.evaluate", { expression: extra, awaitPromise: true }); await sleep(2500); }
const { data } = await send("Page.captureScreenshot", { format: "png" });
(await import("node:fs")).writeFileSync(out, Buffer.from(data, "base64"));
console.log("saved", out, errors.length ? "\nCONSOLE ERRORS:\n" + errors.join("\n") : "(no console errors)");
ws.close(); chrome.kill();
