// Photo collection → annotation queue → search. Talks to /api/photos over HTTP (Postgres stays behind the API).
// The queue lives in the LOCAL Postgres (Docker `messenger-pg`, served by `npm run dev`); only finished rows are
// migrated to production (Supabase) at the end, so annotation never touches the Supabase quota.
//
//   node scripts/photos.mjs setup                                    create the table (local)
//   node scripts/photos.mjs seed <folder> [--collection faz3]        add images (local)
//   node scripts/photos.mjs work [--worker laptop] [--base-url http://localhost:1234/v1] [--model qwen3.5-4b] [--batch 10] [--api-key KEY]
//   node scripts/photos.mjs status                                   progress by status/worker
//   node scripts/photos.mjs migrate [--to https://messenger-demo.vercel.app]   copy finished rows to production, then embed there
//   node scripts/photos.mjs search "sheikh zayed" [--api https://messenger-demo.vercel.app]
//
// Run `work` on as many machines as you like (LM Studio here, vLLM in the cloud — any OpenAI-compatible vision endpoint):
// each claims 10 images, annotates them, claims the next 10… until the queue is empty. Crashed claims return after 10 min.
// Cloud workers reach this PC's queue through a tunnel:  cloudflared tunnel --url http://localhost:5173  → MESSENGER_API=<https://….trycloudflare.com>
// Env (.env or shell): PHOTOS_TOKEN (required for everything but status/search), MESSENGER_API (default http://localhost:5173).
import { readdir } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { basename } from "node:path";
import { hostname } from "node:os";

if (existsSync(".env")) for (const line of readFileSync(".env", "utf8").split(/\r?\n/)) {
  const m = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=(.*)$/); if (m && !process.env[m[1]]) process.env[m[1]] = m[2].trim();
}
const [cmd, ...rest] = process.argv.slice(2);
const opt = (name, fallback) => { const i = rest.indexOf(`--${name}`); return i >= 0 ? rest[i + 1] : fallback; };
const positional = rest.filter((a, i) => !a.startsWith("--") && !rest[i - 1]?.startsWith("--"));
const API = (opt("api", process.env.MESSENGER_API ?? "http://localhost:5173")).replace(/\/$/, "");
const TOKEN = process.env.PHOTOS_TOKEN;

async function api(action, payload, method = payload ? "POST" : "GET", query = "", base = API) {
  // If the queue API is briefly unreachable (dev server restarting, tunnel hiccup), wait and retry instead of dying.
  let res;
  for (let attempt = 1; ; attempt++) {
    try {
      res = await fetch(`${base}/api/photos?action=${action}${query}`, {
        method, headers: { "Content-Type": "application/json", ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}) },
        body: method === "POST" ? JSON.stringify(payload ?? {}) : undefined,
      });
      break;
    } catch (err) {
      if (attempt >= 60) throw err;
      if (attempt === 1) console.log(`  … queue API unreachable (${err.cause?.code ?? err.message}), retrying`);
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
  if (res.status === 409) return res.json(); // e.g. complete: the claim expired and was reassigned — not an error to retry
  if (!res.ok) throw new Error(`${action}: ${res.status} ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

/* ---------- filename → context ---------- */
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const FIX = { shk: "Sheikh", ksa: "Saudi Arabia", uae: "UAE", fitar: "Fitr", natioanl: "National" };
/** "faz3-2021-eid-ul-fitar-12-05-eid-2021.jpg" → {account, year, event, date, extra} ({account}-{year}-{event}-{dd-mm}-{rest}). */
function parseName(file) {
  const stem = basename(file, extname(file)).toLowerCase();
  const words = (s) => s.split("-").filter((w) => w && !/^[0-9a-f]{6,}$/.test(w) && !/^\d{5,}$/.test(w)).map((w) => FIX[w] ?? w).join(" ");
  const m = stem.match(/^([a-z0-9]+)-(\d{4})-(.+?)-(\d{2})-(\d{2})(?:-(.*))?$/);
  if (!m) return { account: stem.split("-")[0], year: null, event: words(stem), date: null, extra: "" };
  const [, account, year, event, dd, mm, extra = ""] = m;
  const month = MONTHS[Number(mm) - 1] ?? mm;
  return { account, year: Number(year), event: words(event), date: `${Number(dd)} ${month} ${year}`, extra: words(extra) };
}

/* ---------- annotation (any OpenAI-compatible vision endpoint) ---------- */
const FIELDS = {
  caption: "1–2 sentences in English describing what is visible, using the filename context for the occasion",
  caption_ar: "the same caption in Arabic",
  people: "array — named people only when the filename or visible text supports it; otherwise short descriptions",
  objects: "array of notable objects",
  scene: "the setting, e.g. 'desert at sunset', 'majlis', 'stadium'",
  text_in_image: "readable text/calligraphy in the image, verbatim; empty string if none",
  tags: "array of 8–15 search keywords in English and Arabic (occasion, people, objects, colours, mood)",
};

async function annotate({ file, meta, url }, { baseUrl, model, apiKey }) {
  // Images live on the CDN now — the queue carries a URL, never base64. Download here for the vision model.
  const img = Buffer.from(await (await fetch(url)).arrayBuffer()).toString("base64");
  const prompt =
    `Filename: ${file}\nParsed from the filename (trust it for the account, occasion and date — the image may not show them):\n` +
    `- account: ${meta.account}\n- year: ${meta.year ?? "unknown"}\n- occasion/event: ${meta.event}\n- date: ${meta.date ?? "unknown"}\n` +
    (meta.extra ? `- extra words in the filename: ${meta.extra}\n` : "") +
    `This is a social-media post from that account. Describe it for a bilingual photo search index. ` +
    `Do not invent names that neither the filename nor visible text supports.\n\nReply with only a JSON object with these keys:\n` +
    Object.entries(FIELDS).map(([k, d]) => `- "${k}": ${d}`).join("\n");
  const res = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}) },
    body: JSON.stringify({
      // Ask for thinking off (LM Studio: reasoning_effort, vLLM/Qwen: enable_thinking). Some models (Qwen 3.5 4B) still
      // reason, so leave room for it — a short budget is what produced empty answers.
      model, temperature: 0.2, max_tokens: 4096,
      reasoning_effort: "none", chat_template_kwargs: { enable_thinking: false },
      messages: [
        { role: "system", content: "You catalogue images for a bilingual (English/Arabic) photo search engine. Answer only with the requested JSON." },
        { role: "user", content: [{ type: "text", text: prompt }, { type: "image_url", image_url: { url: `data:image/jpeg;base64,${img}` } }] },
      ],
    }),
  });
  if (!res.ok) throw new Error(`model ${res.status}: ${(await res.text()).slice(0, 160)}`);
  const message = (await res.json()).choices?.[0]?.message ?? {};
  // the JSON is in the answer; if the model put it in its reasoning instead, take it from there
  const content = [message.content, message.reasoning_content, message.reasoning].find((t) => typeof t === "string" && t.includes("{")) ?? "";
  if (!content) throw new Error("empty answer (raise max_tokens or turn thinking off)");
  const out = JSON.parse(content.slice(content.indexOf("{"), content.lastIndexOf("}") + 1));
  for (const k of ["people", "objects", "tags"]) out[k] = Array.isArray(out[k]) ? out[k].map(String) : out[k] ? [String(out[k])] : [];
  for (const k of ["caption", "caption_ar", "scene", "text_in_image"]) out[k] = String(out[k] ?? "");
  return out;
}

/* ---------- commands ---------- */
if (cmd === "setup") console.log(await api("setup", {}));

else if (cmd === "seed") {
  const folder = positional[0];
  if (!folder) throw new Error("usage: seed <folder> [--collection name]");
  const files = (await readdir(folder)).filter((f) => /\.(jpe?g|png|webp)$/i.test(f)).sort();
  let added = 0;
  for (const f of files) {
    const r = await api("seed", { file: f, meta: parseName(f), collection: opt("collection", "default") });
    if (r.added) added++;
    process.stdout.write(`\rseeded ${added} new / ${files.length}`);
  }
  console.log();
}

else if (cmd === "work") {
  const cfg = { baseUrl: opt("base-url", "http://localhost:1234/v1").replace(/\/$/, ""), model: opt("model", "qwen3.5-4b"), apiKey: opt("api-key", process.env.WORKER_API_KEY) };
  const worker = opt("worker", `${hostname()}-${cfg.model}`);
  const n = Number(opt("batch", "10"));
  console.log(`worker ${worker} · ${cfg.model} @ ${cfg.baseUrl} · batches of ${n} from ${API}`);
  let total = 0;
  for (;;) {
    const batch = await api("claim", { worker, n });
    if (!batch.length) break;
    console.log(`claimed ${batch.length}`);
    for (const job of batch) {
      const t = Date.now();
      try {
        const result = await annotate(job, cfg);
        const saved = await api("complete", { file: job.file, worker, model: cfg.model, result });
        if (saved.ok === false) { console.log(`  · skipped ${job.file}: ${saved.reason}`); continue; }
        total++;
        console.log(`  ✓ ${((Date.now() - t) / 1000).toFixed(1)}s ${job.file}\n      ${result.caption}`);
      } catch (err) {
        await api("complete", { file: job.file, worker, error: String(err.message ?? err) }).catch(() => {});
        console.log(`  ✗ ${job.file}: ${err.message ?? err}`);
      }
    }
  }
  console.log(`queue empty · ${total} annotated by ${worker}`);
}

else if (cmd === "migrate") {
  const to = opt("to", "https://messenger-demo.vercel.app").replace(/\/$/, "");
  if (to === API) throw new Error("--to must be a different deployment than the source");
  let after = "", moved = 0;
  for (;;) {
    const rows = await api("export", undefined, "GET", `&n=20&after=${encodeURIComponent(after)}`);
    if (!rows.length) break;
    for (const r of rows) { await api("import", r, "POST", "", to); moved++; after = r.file; }
    process.stdout.write(`\rmigrated ${moved}`);
  }
  console.log(`\nembedding on ${to}…`, await api("embed", {}, "POST", "", to));
}
else if (cmd === "embed") console.log(await api("embed", {}));
else if (cmd === "status") console.table(await api("status"));
else if (cmd === "search") {
  const { mode, count, results } = await api("search", undefined, "GET", `&q=${encodeURIComponent(positional.join(" "))}&k=${opt("k", "8")}`);
  console.log(`${mode} · ${count} results`);
  for (const r of results) console.log(`${r.score.toFixed(3)} [${r.why.join("+")}] ${r.file}\n       ${r.caption}\n       ${r.url}`);
}
else console.log("commands: setup | seed <folder> | work | status | migrate | embed | search <query>");
