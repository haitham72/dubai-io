// Founder ops dashboard (S1 health, S2 ML/jobs). Plain ES module, real data only.
const POLL_MS = 15000;
const KEY = "dubaiio_ops_token";

const store = {
  get() { try { return sessionStorage.getItem(KEY) || ""; } catch { return ""; } },
  set(v) { try { sessionStorage.setItem(KEY, v); } catch { /* storage blocked: token lives for this page only */ } },
};
let token = store.get();

function ensureToken(force = false) {
  if (!token || force) {
    const entered = window.prompt("Ops token (OPS_TOKEN on the server):");
    if (entered) { token = entered.trim(); store.set(token); }
  }
  document.getElementById("token-state").textContent = token ? "token set for this tab" : "no token";
  return Boolean(token);
}

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}
const pill = (state) => el("span", `pill ${state}`, state);
const when = (iso) => { const d = new Date(iso); return isNaN(d) ? "time unknown" : d.toLocaleTimeString(); };

async function getJson(path) {
  const res = await fetch(path, { headers: { "X-Ops-Token": token }, cache: "no-store" });
  if (res.status === 404) throw { kind: "off", msg: "Ops is disabled on the server (OPS_TOKEN is not set) or the token is missing." };
  if (res.status === 403) throw { kind: "token", msg: "Token missing or invalid. Use Set token." };
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch { /* no body */ }
    throw { kind: "http", msg: `HTTP ${res.status}${detail ? `: ${detail}` : ""}` };
  }
  return res.json();
}

function showError(body, err) {
  body.replaceChildren(el("div", "err", err && err.msg ? err.msg : "Backend unreachable — state is unknown, not healthy."));
}

function renderHealth(body, d) {
  const frag = document.createDocumentFragment();
  const sum = el("div", "summary");
  sum.append("Overall ", pill(d.state), el("span", "note", ` as of ${when(d.as_of)}`));
  frag.append(sum);
  const api = el("div", "row");
  const top = el("div", "row-top"); top.append(el("span", "name", "API"), el("span", "pill ok", "up"));
  api.append(top, el("div", "meta", `version ${d.api.version} · uptime ${Math.round(d.api.uptime_s)} s · as of ${when(d.api.as_of)}`));
  frag.append(api);
  for (const dep of d.dependencies) {
    const row = el("div", "row");
    const t = el("div", "row-top"); t.append(el("span", "name", dep.name), pill(dep.state));
    row.append(t, el("div", "meta", `probed: ${dep.probed} · ${when(dep.as_of)}`));
    if (dep.detail) row.append(el("div", "meta", dep.detail));
    frag.append(row);
  }
  body.replaceChildren(frag);
}

function block(title, b, renderValue) {
  const row = el("div", "row");
  const t = el("div", "row-top"); t.append(el("span", "name", title), pill(b.state));
  row.append(t);
  if (b.state === "ok" && b.value !== null && renderValue) row.append(el("div", "meta", renderValue(b.value)));
  if (b.reason) row.append(el("div", "meta", b.reason));
  row.append(el("div", "meta", `as of ${when(b.as_of)}`));
  return row;
}

function renderMl(body, d) {
  const frag = document.createDocumentFragment();
  frag.append(
    block("Queue depth", d.queue, (v) => `${v.queue}: ${v.messages} message(s)`),
    block("Active jobs", d.active_jobs, (v) => `${v} running`),
    block("Failed jobs", d.failed_jobs, (v) => `${v.count} failed`),
  );
  if (d.failed_jobs.state === "ok") {
    const jobs = d.failed_jobs.value.jobs;
    const list = el("div", "kv");
    for (const j of jobs) list.append(el("span", "", j.job_id), el("span", "", j.category));
    if (jobs.length) frag.append(list);
  }
  const s = d.sentiment;
  const row = el("div", "row");
  const t = el("div", "row-top"); t.append(el("span", "name", "Sentiment (labelled comments)"), pill(s.state));
  row.append(t);
  if (s.state === "empty") {
    row.append(el("div", "meta", s.hint));
  } else {
    const kv = el("div", "kv");
    for (const [w, c] of Object.entries(s.windows)) {
      kv.append(el("span", "", w), el("span", "", `neg ${c.negative} · neu ${c.neutral} · pos ${c.positive}`));
    }
    row.append(kv);
  }
  row.append(el("div", "meta", `as of ${when(s.as_of)}`));
  frag.append(row, block("RAG hybrid vs keyword fallback", d.rag));
  body.replaceChildren(frag);
}

function panel(id, path, render) {
  const body = document.getElementById(`${id}-body`);
  let timer = null;
  async function load() {
    if (!ensureToken()) { showError(body, { msg: "Token missing. Use Set token." }); return; }
    try { render(body, await getJson(path)); }
    catch (err) { showError(body, err); }
  }
  function schedule() {
    clearTimeout(timer);
    if (!document.hidden) timer = setTimeout(async () => { await load(); schedule(); }, POLL_MS);
  }
  document.getElementById(`${id}-refresh`).addEventListener("click", () => load());
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) clearTimeout(timer); else { load(); schedule(); }
  });
  return { start() { load(); schedule(); }, load };
}

const panels = [panel("health", "/api/ops/health", renderHealth), panel("ml", "/api/ops/ml", renderMl)];
document.getElementById("token-btn").addEventListener("click", () => { ensureToken(true); panels.forEach((p) => p.load()); });
ensureToken();
panels.forEach((p) => p.start());
