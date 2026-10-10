// Dubai-io clickable demo (arc v2). Scripted, no backend, no LLM.
// The "Under the hood" panel shows what a real build would do at each step.
// Rules this file enforces: no invented defaults for blank inputs, no status without a merchant event,
// the host rebuilds every total from the price list, and the bridge uses explicit origins.
(() => {
  const D = window.DEMO;
  const $ = (s) => document.querySelector(s);
  const chat = $("#chat");
  const BASE_MERCHANTS = D.merchants.length;     // merchants added at run time (onboarding) are dropped on restart
  const state = {};
  let epoch = 0;                                  // bumped on restart so stale async chains never touch the new chat
  let reqSeq = 4800, idemSeq = 0;

  // ---------- helpers ----------
  const sleep = (ms) => new Promise((resolve) => { const e = epoch; setTimeout(() => { if (e === epoch) resolve(); }, ms); });
  const typing = (ms = 500) => sleep(ms);
  const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);
  const pad = (n) => String(n).padStart(2, "0");
  const fmt = (min) => { const m = ((min % 1440) + 1440) % 1440; return pad(Math.floor(m / 60)) + ":" + pad(m % 60); };
  const toMin = (hhmm) => { const m = /^(\d{1,2}):(\d{2})$/.exec(hhmm || ""); return m ? Number(m[1]) * 60 + Number(m[2]) : NaN; };
  const aed = (cents) => "AED " + (cents / 100).toFixed(2);
  const now = () => fmt(state.clock);
  const terminalLabel = () => D.terminals[state.terminal];
  const demoPill = `<span class="pill demo">Demo data</span>`;
  const youPill = `<span class="pill user">You told me</span>`;
  const examplePill = `<span class="pill demo">Demo example</span>`;
  const merchantPill = `<span class="pill trig">Merchant update</span>`;

  function paintClock() { $("#clock").textContent = state.weekday + " " + now(); }
  function setClock(min) { state.clock = min; paintClock(); }
  function advance(n) { setClock(state.clock + n); }

  // Raw log + key events. big() writes to both; the key-event view is what the stage shows.
  function log(kind, text, obj) {
    const el = document.createElement("div");
    el.className = "entry";
    el.innerHTML = `<span class="ts">${new Date().toTimeString().slice(0, 8)}</span> <span class="kind k-${kind}">${kind}</span> ${esc(text)}` +
      (obj ? `<div class="detail">${esc(JSON.stringify(obj))}</div>` : "");
    $("#log").prepend(el);
  }
  function big(text, detail) {
    log("action", "KEY EVENT: " + text, detail);
    const el = document.createElement("div");
    el.className = "ev";
    el.innerHTML = `<span class="t">${now()}</span><b>${esc(text)}</b>` + (detail ? `<div class="d">${esc(typeof detail === "string" ? detail : JSON.stringify(detail))}</div>` : "");
    $("#keylog").prepend(el);
  }
  const scroll = () => { const s = $("#screen-companion"); s.scrollTop = s.scrollHeight; };

  function bot(html, meta) {
    const el = document.createElement("div");
    el.className = "msg bot";
    el.innerHTML = html + `<span class="meta">${meta || now()}</span>`;
    chat.append(el); scroll(); return el;
  }
  function user(text) {
    const el = document.createElement("div");
    el.className = "msg user";
    el.innerHTML = esc(text) + `<span class="meta">${now()} ✓✓</span>`;
    chat.append(el); scroll();
  }
  function card(html, cls) {
    const el = document.createElement("div");
    el.className = "card" + (cls ? " " + cls : ""); el.innerHTML = html;
    chat.append(el); scroll(); return el;
  }
  function chips(list) {
    const wrap = document.createElement("div");
    wrap.className = "chips";
    list.forEach(([label, fn]) => {
      const b = document.createElement("button");
      b.className = "chip"; b.textContent = label;
      b.onclick = () => { wrap.querySelectorAll("button").forEach((x) => (x.disabled = true)); user(label); fn(); };
      wrap.append(b);
    });
    chat.append(wrap); scroll(); return wrap;
  }

  // ---------- memory (user-given only) ----------
  function remember(key, value, prov = "user_supplied") {
    state.memory[key] = { value, prov };
    log("memory", `saved "${key}"`, { value, provenance: prov });
    renderMemory();
  }
  function renderMemory() {
    const keys = Object.keys(state.memory);
    $("#memoryList").innerHTML = keys.length
      ? keys.map((k) => `<div class="row"><div>${esc(k)}<div class="k">${esc(state.memory[k].value)}</div></div>${state.memory[k].prov === "user_supplied" ? youPill : examplePill}</div>`).join("")
      : `<div class="empty">Nothing yet.</div>`;
  }

  // ---------- tabs ----------
  function showTab(t) {
    document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b.dataset.tab === t));
    document.querySelectorAll(".screen").forEach((s) => s.classList.toggle("active", s.id === "screen-" + t));
    $("#composer").style.display = t === "companion" ? "flex" : "none";
    if (t === "companion") scroll();
  }
  document.querySelectorAll(".tab").forEach((b) => (b.onclick = () => showTab(b.dataset.tab)));

  // ---------- airport journey ----------
  function schematic(active) {
    const rows = D.zones.map((z, i) => {
      const y = 8 + i * 34, on = i === active, done = i < active;
      return `<rect x="6" y="${y}" width="80" height="26" rx="8" fill="${on ? "#0A9CC2" : done ? "#E8F8EC" : "#F2F2F7"}" stroke="${on ? "#0A9CC2" : "#E5E5EA"}"/>
        <text x="46" y="${y + 17}" text-anchor="middle" font-size="9.5" font-weight="${on ? 600 : 400}" font-family="-apple-system,Segoe UI,sans-serif" fill="${on ? "#fff" : done ? "#1E8E3E" : "#3C3C43"}">${done ? "✓ " : ""}${z}</text>` +
        (i < D.zones.length - 1 ? `<line x1="46" y1="${y + 26}" x2="46" y2="${y + 34}" stroke="#D1D1D6" stroke-width="2"/>` : "");
    }).join("");
    return `<svg viewBox="0 0 92 214" role="img" aria-label="Illustrative airport flow">${rows}</svg>`;
  }

  let journeyCard = null;
  function renderStep(i) {
    state.step = i;
    const s = D.airportSteps[i];
    log("agent", `journey step → ${s.id}`, { step: i + 1, of: D.airportSteps.length, position_source: "user_confirmed" });
    const prog = D.airportSteps.map((_, k) => `<span class="${k <= i ? "on" : ""}"></span>`).join("");
    const extras = s.extra === "needs" ? `<button class="btn small ghost" data-x="needs">What do I need?</button>`
      : s.extra === "belt" ? `<button class="btn small ghost" data-x="belt">Save my belt number</button>` : "";
    const html = `
      <div class="card-head"><div><h3>DXB arrival guide</h3><div class="sub">${esc(terminalLabel())} (from your flight) · step ${i + 1} of ${D.airportSteps.length}</div></div>
      <div class="pills"><span class="pill demo">Demo data</span></div></div>
      <div class="journey">${schematic(s.zone)}
        <div><div class="step-title">${s.title}</div><div class="step-body">${s.body}</div>
        <div class="btn-row">${i < D.airportSteps.length - 1 ? `<button class="btn small" data-x="next">Done, next ✓</button>` : `<button class="btn small" data-x="ride">Compare rides</button>`}
        <button class="btn small ghost" data-x="lost">I'm lost</button>${extras}</div></div></div>
      ${i === 0 ? `<button class="map-thumb" data-x="map" aria-label="Open airport map"><span class="pin"></span><span class="cap">${esc(terminalLabel())} from your flight · tap for map</span></button>` : ""}
      <div class="progress">${prog}</div>
      <div class="foot"><span>Steps confirmed by you, no indoor GPS</span><button class="btn small ghost" data-x="map" style="padding:4px 10px;font-size:12px">Airport maps</button></div>`;
    if (!journeyCard) journeyCard = card(html); else { journeyCard.innerHTML = html; chat.append(journeyCard); scroll(); }
    journeyCard.querySelectorAll("[data-x]").forEach((b) => (b.onclick = () => stepAction(b.dataset.x)));
  }

  async function stepAction(x) {
    if (x === "map") return openMap("overview");
    if (x === "next") { user("Done ✓"); await typing(300); renderStep(state.step + 1); }
    if (x === "ride") { user("Compare rides"); ridePrompt(); }
    if (x === "lost") {
      user("I'm lost");
      await typing();
      bot("No problem. I can't see your exact position indoors, so tell me what's around you.");
      log("tool", "venue.ask_landmark", { reason: "indoor position unknown" });
      chips(D.airportSteps.slice(0, 5).map((s, k) => [s.landmark, async () => {
        log("tool", "venue.match_landmark", { landmark: s.landmark, matched_step: s.id, confidence: "user_confirmed" });
        await typing(); bot(`Got it. You're at <b>${s.title.toLowerCase()}</b>. Picking up from there.`); renderStep(k);
      }]));
    }
    if (x === "needs") {
      user("What do I need?"); await typing();
      bot("Passport, plus any visa or entry permit that applies to you. Requirements depend on your nationality, so check the official entry requirements if unsure. <span class='pill'>Official guidance link</span>");
    }
    if (x === "belt") {
      user("Save my belt number"); await typing();
      const c = card(`<h3>Belt number</h3><div class="sub">Read it from the arrivals screen. I won't guess it.</div>
        <div style="display:flex;gap:8px"><input id="beltIn" placeholder="Number on the screen" class="field" maxlength="6" autocomplete="off">
        <button class="btn small" id="beltSave">Save</button></div><div class="err" id="beltErr"></div>`);
      c.querySelector("#beltSave").onclick = async () => {
        const v = c.querySelector("#beltIn").value.trim();
        if (!v) { c.querySelector("#beltErr").textContent = "Type the belt number you can see on the screen, or leave this for later."; return; }
        remember("Baggage belt", `Belt ${v} · ${D.flight.number}`);
        c.innerHTML = `<h3>Saved: Belt ${esc(v)}</h3><div class="pills">${youPill}</div>`;
        await typing(); bot(`I'll remember belt ${esc(v)}. Ask "which belt?" any time.`);
      };
    }
  }

  // ---------- ride step: time + weekday + terminal ----------
  // Deterministic rule from data.js (rules.metro). Returns { ok, reason }.
  function metroStatus(weekday, min, terminal) {
    const R = D.rules.metro;
    if (R.no_metro_terminals[terminal]) return { ok: false, reason: R.no_metro_terminals[terminal] };
    const lateEnd = R.late_close_min[weekday] || 0;
    const ok = min >= toMin(R.first_train) || min < lateEnd;
    return ok ? { ok: true } : { ok: false, reason: `Metro has stopped for the night (first train ${R.first_train})` };
  }

  function ridePrompt() {
    if (state.dest && state.terminalSet) return rides();
    const c = card(`<h3>Two quick questions</h3><div class="sub">I don't guess these. Tap to confirm.</div>
      <div class="qrow">Which terminal are you in? <span class="pill demo">Preset from the demo flight</span></div>
      <div class="inline-chips" id="qTerm">${Object.keys(D.terminals).map((t) => `<button class="chip ${t === state.terminal ? "on" : ""}" data-t="${t}">${D.terminals[t]}</button>`).join("")}</div>
      <div class="qrow">Where are you staying tonight?</div>
      <div class="inline-chips" id="qArea">${Object.keys(D.destinations).map((d) => `<button class="chip ${d === state.dest ? "on" : ""}" data-d="${esc(d)}">${esc(d)}</button>`).join("")}</div>
      <div class="btn-row"><button class="btn small" id="qGo" ${state.dest ? "" : "disabled"}>Compare rides</button></div>`);
    let term = state.terminal, area = state.dest;
    const mark = (sel, attr, val) => c.querySelectorAll(sel + " .chip").forEach((b) => b.classList.toggle("on", b.dataset[attr] === val));
    c.querySelectorAll("#qTerm .chip").forEach((b) => (b.onclick = () => { term = b.dataset.t; mark("#qTerm", "t", term); }));
    c.querySelectorAll("#qArea .chip").forEach((b) => (b.onclick = () => { area = b.dataset.d; mark("#qArea", "d", area); c.querySelector("#qGo").disabled = false; }));
    c.querySelector("#qGo").onclick = () => {
      if (!area) return;
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      state.terminal = term; state.dest = area; state.terminalSet = true;
      user(`${D.terminals[term]}, ${area}`);
      remember("Staying in", area);
      remember("Terminal", D.terminals[term]);
      rides();
    };
  }

  async function rides() {
    await typing();
    const d = D.destinations[state.dest];
    const ms = metroStatus(state.weekday, state.clock, state.terminal);
    log("tool", "transport.compare", {
      from: `DXB ${state.terminal}`, to: state.dest, local_time: now(), weekday: state.weekday,
      metro: ms, rule_provenance: D.rules.provenance, rule_as_of: D.rules.as_of, estimates: "estimate", live: false
    });
    const c = card(`
      <div class="card-head"><div><h3>To ${esc(state.dest)}</h3><div class="sub">From DXB ${esc(state.terminal)} · ${esc(state.weekday)} ${now()} · with luggage</div></div>
      <div class="pills"><span class="pill est">Estimate</span>${demoPill}</div></div>
      ${ms.ok ? "" : `<div class="banner"><b>Taxi recommended.</b> ${esc(ms.reason)}.</div>`}
      <div class="opt"><div class="ico">🚕</div><div><b>Taxi${ms.ok ? "" : `<span class="pill user rec">Recommended</span>`}</b><div class="line">${d.taxi.time} · ${d.taxi.price} (estimate) · door to door, easy with bags</div></div><button class="btn small" data-r="taxi">Choose</button></div>
      <div class="opt ${ms.ok ? "" : "off"}"><div class="ico">🚇</div><div><b>Metro, Red Line</b><div class="line">${ms.ok ? `${d.metro.time} · ${d.metro.price} (estimate) · luggage size rules apply` : `<span class="why">Not available: ${esc(ms.reason)}</span>`}</div></div><button class="btn small" data-r="metro" ${ms.ok ? "" : "disabled"}>${ms.ok ? "Choose" : "Unavailable"}</button></div>
      <div class="opt"><div class="ico">📱</div><div><b>Ride-hailing app</b><div class="line">Alternative · opens your app. Dubai-io doesn't book it</div></div><button class="btn small ghost" data-r="app">Open</button></div>
      <div class="foot"><span>Fares and times are estimates (demo data). Timetable rule: demo fixture, as of ${D.rules.as_of}. Verify with official RTA info</span></div>`);
    c.querySelectorAll("[data-r]").forEach((b) => (b.onclick = () => {
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      ({ taxi: taxiFlow, metro: metroFlow, app: appFlow })[b.dataset.r]();
    }));
  }

  // ---------- taxi memory: nothing is invented ----------
  async function taxiFlow() {
    user("Taxi"); await typing();
    bot("Follow the <b>Taxi</b> signs to the official rank outside arrivals. Use only the official airport taxis.");
    await typing(600);
    tripForm();
  }

  function tripForm() {
    const route = `DXB ${state.terminal} → ${state.dest}`;
    const c = card(`<h3>Save your taxi details?</h3><div class="sub">Only what you type. If you leave something in the car, I'll already have it.</div>
      <div class="form">
        <label>Plate or taxi number<input class="field" id="tPlate" placeholder="From the taxi door or your receipt" autocomplete="off"></label>
        <div class="btn-row" style="margin:0"><button class="btn small ghost" id="tReceipt" type="button">Attach receipt photo (simulated)</button><span class="pill est" id="tReceiptPill" hidden>Receipt photo attached (simulated)</span></div>
        <label>Roof colour<input class="field" id="tRoof" placeholder="e.g. red" autocomplete="off"></label>
        <label>Route<div class="ro">${esc(route)}</div></label>
        <label>Start time<input class="field" id="tStart" type="time"></label>
        <div class="err" id="tErr"></div>
        <div class="btn-row"><button class="btn small" id="tSave" type="button">Save</button><button class="btn small ghost" id="tEx" type="button">Use example values</button><button class="btn small ghost" id="tSkip" type="button">Skip</button></div>
      </div>
      <div class="foot"><span>Example values are saved as Demo example, never as You told me.</span></div>`);
    const f = { plate: c.querySelector("#tPlate"), roof: c.querySelector("#tRoof"), start: c.querySelector("#tStart") };
    const ex = { plate: false, roof: false, start: false };
    let receipt = false;
    Object.keys(f).forEach((k) => f[k].addEventListener("input", () => { ex[k] = false; }));
    c.querySelector("#tReceipt").onclick = () => { receipt = true; c.querySelector("#tReceiptPill").hidden = false; log("memory", "receipt photo attached (simulated)", { stored: "filename only", ocr: false }); };
    c.querySelector("#tEx").onclick = () => {
      f.plate.value = "12345 (example)"; f.roof.value = "red (example)"; f.start.value = "00:55";
      ex.plate = ex.roof = ex.start = true;
    };
    c.querySelector("#tSkip").onclick = async () => {
      c.innerHTML = `<h3>Not saved</h3><div class="sub">Without taxi details, a lost-item report would need you to find them first.</div>`;
      await typing(); arrived();
    };
    c.querySelector("#tSave").onclick = async () => {
      const plate = f.plate.value.trim(), roof = f.roof.value.trim(), start = f.start.value;
      const err = c.querySelector("#tErr");
      if (!plate && !receipt) { err.textContent = "Add the plate or taxi number, or attach the receipt photo. I won't guess it."; return; }
      if (!roof) { err.textContent = "Add the roof colour of the taxi."; return; }
      if (!start) { err.textContent = "Add the time the ride started."; return; }
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      const prov = (k) => (ex[k] ? "demo_fixture" : "user_supplied");
      state.trip = {
        plate, receipt, roof, start, route, terminal: state.terminal, dest: state.dest, saved_at: now(),
        prov: { plate: prov("plate"), roof: prov("roof"), start: prov("start") }
      };
      const anyExample = Object.values(state.trip.prov).includes("demo_fixture");
      remember("Taxi trip", `${plate ? "Plate " + plate : "Receipt photo (simulated)"} · roof ${roof} · ${route} · started ${start}`, anyExample ? "demo_fixture" : "user_supplied");
      c.className = "card"; c.innerHTML = tripCardHTML(state.trip);
      state.tripEl = c;
      big("Trip details saved", { memory_saved: true, provenance: anyExample ? "includes demo_fixture" : "user_supplied", fields: ["plate_or_receipt", "roof_colour", "route", "start_time"] });
      await typing(); arrived();
    };
  }

  // memory_saved card. Each value shows its own provenance label.
  function tripCardHTML(t, title) {
    const p = (k) => (t.prov[k] === "user_supplied" ? youPill : examplePill);
    const anyExample = Object.values(t.prov).includes("demo_fixture");
    return `<div class="card-head"><div><h3>${title || "Taxi details saved"}</h3><div class="sub">Saved ${esc(t.saved_at)} · stays on this phone, shared with no one</div></div>
      <div class="pills">${anyExample ? examplePill : youPill}</div></div>
      <div class="mem-row"><span class="k">Plate / taxi number</span><span class="v">${t.plate ? esc(t.plate) + " " + p("plate") : `Receipt photo <span class="pill est">simulated</span>`}</span></div>
      ${t.plate && t.receipt ? `<div class="mem-row"><span class="k">Receipt photo</span><span class="v"><span class="pill est">simulated</span></span></div>` : ""}
      <div class="mem-row"><span class="k">Roof colour</span><span class="v">${esc(t.roof)} ${p("roof")}</span></div>
      <div class="mem-row"><span class="k">Route</span><span class="v">${esc(t.route)} ${youPill}</span></div>
      <div class="mem-row"><span class="k">Start time</span><span class="v">${esc(t.start)} ${p("start")}</span></div>
      <div class="foot"><span>Visible in Me › What I remember</span></div>`;
  }

  async function metroFlow() {
    user("Metro"); await typing();
    const d = D.destinations[state.dest];
    const steps = [
      "Follow the <b>Metro</b> signs from arrivals to the terminal's Metro station.",
      "Get a <b>Nol card</b> at the ticket office or machine. You need it to tap in.",
      "Take the <b>Red Line</b> toward the city. Check the direction on the platform map.",
      `Get off at <b>${d.metro.station}</b>.`,
      "Last stretch: walk or take a short taxi to your hotel."
    ];
    let k = 0;
    const c = card("");
    const draw = () => {
      c.innerHTML = `<div class="card-head"><div><h3>Metro to ${esc(state.dest)}</h3><div class="sub">Step ${k + 1} of ${steps.length}</div></div><span class="pill est">Check on RTA</span></div>
        <div class="step-body" style="font-size:14px">${steps[k]}</div>
        <div class="btn-row"><button class="btn small" id="mNext">${k < steps.length - 1 ? "Done, next ✓" : "I've arrived ✓"}</button></div>`;
      c.querySelector("#mNext").onclick = () => { log("agent", "metro step confirmed", { step: k + 1 }); if (k < steps.length - 1) { k++; draw(); } else { c.querySelectorAll("button").forEach((x) => (x.disabled = true)); arrived(); } };
    };
    draw();
  }

  async function appFlow() {
    user("Ride-hailing app"); await typing();
    log("action", "handoff.external_app", { status: "HANDOFF", note: "not a booking" });
    card(`<h3>Opening your ride app</h3><div class="sub">This is a handoff. I won't show it as booked, because I can't see it.</div><span class="pill">Status: handed off</span>`);
    arrived();
  }

  async function arrived() {
    await sleep(800);
    bot(`Enjoy the ride. Tell me when you've reached your hotel in ${esc(state.dest)}.`);
    chips([["I've reached my hotel", () => hotelReached()]]);
  }

  async function hotelReached() {
    await typing();
    if (!state.dest) {
      bot("Which area is your hotel in? I don't guess it.");
      return chips(Object.keys(D.destinations).map((d) => [d, () => { state.dest = d; remember("Staying in", d); hotelReached(); }]));
    }
    setClock(toMin(D.scenario.hotelClock));
    log("trigger", "trip.arrived_hotel_area", { source: "user_confirmed", dedupe_key: "arrive:" + state.dest });
    bot(`Welcome to ${esc(state.dest)}. I've kept your hotel area (you told me), so I can use it when you ask for something nearby.`);
    chips([["I need a shirt pressed by 9 tomorrow", () => laundryIntent("I need a shirt pressed by 9 tomorrow")]]);
  }

  // ---------- deadline (user_supplied) ----------
  // Reads "by 9 tomorrow", "before 9:30pm", "by 09:00". No am/pm and 5 to 11 is read as morning; the reply says so.
  function parseDeadline(t) {
    const m = /\b(?:by|before)\s+(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)?/i.exec(t);
    if (!m) return null;
    let h = Number(m[1]); const mi = m[2] ? Number(m[2]) : 0; const ap = m[3] ? m[3][0].toLowerCase() : "";
    if (mi > 59 || h > 24) return null;
    let assumed = false;
    if (ap) { if (h < 1 || h > 12) return null; h = (h % 12) + (ap === "p" ? 12 : 0); }
    else if (h >= 13 || m[1].length === 2 && m[1][0] === "0") { /* 24-hour time */ }
    else if (h >= 5 && h <= 11) { assumed = true; }
    else return { ambiguous: true, hint: m[1] };
    const day = /\btoday\b|\btonight\b/i.test(t) ? "today" : "tomorrow";
    const dayAssumed = !/\btomorrow\b|\btoday\b|\btonight\b/i.test(t);
    return { ok: true, min: h * 60 + mi, day, assumed, dayAssumed };
  }

  function setDeadline(p) {
    state.deadline = { label: `${fmt(p.min)} ${p.day}`, min: p.min, day: p.day, provenance: "user_supplied" };
    remember("Laundry deadline", state.deadline.label);
    log("memory", "deadline stored", { ...state.deadline, as_of: now() });
    card(`<div class="card-head"><div><h3>Deadline saved</h3><div class="sub">Saved ${now()} · I'll check every ready-time against it</div></div><div class="pills">${youPill}</div></div>
      <div class="mem-row"><span class="k">Deadline</span><span class="v">${esc(state.deadline.label)} ${youPill}</span></div>
      ${state.dest ? `<div class="mem-row"><span class="k">Hotel area</span><span class="v">${esc(state.dest)} ${youPill}</span></div>` : ""}
      ${p.assumed || p.dayAssumed ? `<div class="foot"><span>I read your time as ${esc(state.deadline.label)}. Tell me if you meant something else.</span></div>` : ""}`);
    big("Deadline saved", { deadline: state.deadline.label, provenance: "user_supplied" });
  }

  async function laundryIntent(text) {
    const p = parseDeadline(text);
    if (p && p.ambiguous) { state.awaitDeadline = true; return bot(`Do you mean ${esc(p.hint)} in the morning or the evening? Say it like "by ${esc(p.hint)}am tomorrow".`); }
    if (p && p.ok) setDeadline(p);
    if (!state.deadline) { state.awaitDeadline = true; return bot('By what time do you need it back? For example: "by 9 tomorrow".'); }
    state.awaitDeadline = false;
    if (!state.dest) {
      bot("Which area are you staying in? I don't guess it.");
      return chips(Object.keys(D.destinations).map((d) => [d, () => { state.dest = d; remember("Staying in", d); laundryResults(); }]));
    }
    await typing(300);
    laundryResults();
  }

  // ---------- Talabat-normal list: closest first, then rating ----------
  const priceFrom = (m) => Math.min(...m.price_list.items.map((i) => i.price));
  const sortShops = (list) => list.slice().sort((a, b) => a.distance_km - b.distance_km || (b.rating || 0) - (a.rating || 0));

  function shopRow(m) {
    const rating = m.rating == null ? `<span class="new">No ratings yet</span>` : `★ ${m.rating.toFixed(1)} (${m.rating_count})`;
    return `<div class="shop"><div class="logo" style="background:${esc(m.color)}">${esc(m.logo)}</div>
      <div><b>${esc(m.name)}</b>
        <div class="meta2">from AED ${priceFrom(m)} (fixed) · ${m.distance_km.toFixed(1)} km · ${rating}</div>
        <div class="meta3">${esc(m.turnaround)} · ${m.open_now ? `<span class="open">Open now</span>` : `<span class="closed">Closed</span>`} · ${esc(m.hours_note)}${m.orderable === false ? ` · <span class="pill">Browse only</span>` : ""}</div></div>
      <button class="btn small" data-m="${esc(m.id)}">Open</button></div>`;
  }

  async function laundryResults(updated) {
    const list = sortShops(D.merchants.filter((m) => m.category === "Laundry"));
    log("tool", "registry.search", { category: "Laundry", area: state.dest, deadline: state.deadline && state.deadline.label, results: list.map((m) => m.id), sort: "distance_km asc, rating desc" });
    state.laundryShown = true;
    const c = card(`<div class="card-head"><div><h3>${updated ? "Updated results · " : ""}Laundries near ${esc(state.dest || "you")}</h3><div class="sub">Closest first, then rating · each opens its own mini-app</div></div>
      <div class="pills">${demoPill}</div></div>${list.map(shopRow).join("")}
      <div class="foot"><span>Prices are the shops' fixed published prices. Distance, ratings and hours: demo fixture, as of ${D.merchants[0].as_of}</span></div>`);
    c.querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  // ---------- Services tab (browse) ----------
  let svcCat = "Laundry";
  function renderServices() {
    $("#cats").innerHTML = D.categories.map((c) => `<button class="cat ${c === svcCat ? "active" : ""}" data-c="${c}">${c}</button>`).join("");
    $("#cats").querySelectorAll("[data-c]").forEach((b) => (b.onclick = () => { svcCat = b.dataset.c; renderServices(); }));
    const list = sortShops(D.merchants.filter((m) => m.category === svcCat));
    $("#merchantList").innerHTML = list.length
      ? `<div class="card">${demoPill}${list.map(shopRow).join("")}</div>`
      : `<p class="empty">No ${esc(svcCat.toLowerCase())} merchants onboarded yet. A shop can join by uploading a photo of its price list.</p>`;
    $("#merchantList").querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  // ---------- mini-app host + bridge ----------
  // The sandboxed frame has no allow-same-origin, so its origin is opaque ("null"). That is why:
  //  - widget -> host: the widget targets the host origin it was given (?host=...) and the host checks e.source and e.origin
  //  - host -> widget: there is NO message channel. Display data travels in the URL when the host sets the frame src.
  const frame = $("#miniFrame");
  let current = null, miniOpen = false, miniReady = false, previewMode = false, loadTimer = null, closeTimer = null;

  function miniSrc(m) {
    const q = new URLSearchParams({ host: location.origin });
    if (m.manifest.generated) q.set("cfg", JSON.stringify({ name: m.name, line: m.line, color: m.color, logo: m.logo, items: m.price_list.items }));
    return m.manifest.entry + "?" + q.toString();
  }

  function openMini(id, opts = {}) {
    const m = opts.merchant || D.merchants.find((x) => x.id === id);
    if (!m) return;
    clearTimeout(closeTimer); clearTimeout(loadTimer);
    current = m; previewMode = !!opts.preview; miniOpen = true; miniReady = false;
    $("#sheetTitle").innerHTML = `${esc(m.name)}<small>${previewMode ? "Preview for review · " : ""}Merchant mini-app · their own HTML</small>`;
    $("#sheetManifest").textContent = `manifest v${m.manifest.version} · scopes: ${m.manifest.bridge_scopes.join(", ")}`;
    const unusable = $("#slowMini").checked || (m.manifest.approved === false && !previewMode) || location.origin === "null";
    frame.src = unusable ? "about:blank" : miniSrc(m);
    $("#sheet").classList.add("open"); $("#sheetBackdrop").classList.add("open");
    log("ui", `mount mini-app ${m.id}`, { entry: m.manifest.entry, sandbox: "allow-scripts", scopes: m.manifest.bridge_scopes, target_origin: location.origin, loading: !unusable });
    loadTimer = setTimeout(() => { if (miniOpen && !miniReady) loadFailed(m); }, 3000);
  }

  function closeMini() {
    miniOpen = false; clearTimeout(loadTimer);
    $("#sheet").classList.remove("open"); $("#sheetBackdrop").classList.remove("open");
    closeTimer = setTimeout(() => (frame.src = "about:blank"), 300);
  }

  // mini-app did not report ready within 3 s -> plain host-rendered fallback card
  function loadFailed(m) {
    log("security", `mini-app ${m.id} did not load within 3 s → fallback_card`, { fallback: m.manifest.fallback_card });
    closeMini(); showTab("companion");
    const c = card(`<div class="card-head"><div><h3>${esc(m.name)}</h3><div class="sub">The mini-app didn't load in time. Here is the plain version.</div></div><div class="pills"><span class="pill sec">Fallback</span>${demoPill}</div></div>
      <div class="lines">${m.price_list.items.map((i) => `<div class="ln"><span>${esc(i.name)}</span><span>AED ${i.price}</span></div>`).join("")}</div>
      <div class="note-line">${m.distance_km.toFixed(1)} km · ${esc(m.turnaround)} · ${m.open_now ? "Open now" : "Closed"} · fixed prices</div>
      <div class="btn-row"><button class="btn small" data-a="retry">Try the mini-app again</button></div>`);
    c.querySelector('[data-a="retry"]').onclick = () => { c.querySelectorAll("button").forEach((x) => (x.disabled = true)); openMini(m.id, { merchant: m, preview: false }); };
  }

  window.addEventListener("message", (e) => {
    if (!miniOpen || !current || e.source !== frame.contentWindow) return;     // only the mounted mini-app
    if (e.origin !== "null") { log("security", "bridge message dropped: unexpected origin", { origin: e.origin }); return; }   // sandboxed frame = opaque origin
    const m = e.data;
    if (!m || typeof m !== "object" || m.v !== 1 || typeof m.kind !== "string") { log("security", "malformed bridge message dropped", m); return; }
    if (m.kind === "app.ready") { miniReady = true; clearTimeout(loadTimer); log("bridge", `${current.id} ready`, { manifest: current.manifest.version }); return; }
    if (!current.manifest.bridge_scopes.includes(m.kind)) {
      log("security", `BLOCKED "${m.kind}": not in manifest scopes`, { merchant: current.id, allowed: current.manifest.bridge_scopes });
      return;
    }
    log("bridge", `${current.id} → ${m.kind}`, m.payload);
    const merchant = current;
    if (previewMode) { log("ui", "preview mode: order.request ignored", { merchant: merchant.id }); return; }
    const built = buildOrder(merchant, m.payload);
    if (built.error) { log("security", "order.request rejected by host", { reason: built.error, merchant: merchant.id }); return; }
    closeMini(); showTab("companion");
    if (merchant.orderable === false) {
      bot(`${esc(merchant.name)} is browse-only in this demo. The ordering path here is the laundry request.`);
      return;
    }
    approvalCard(merchant, built);
  });

  // The host builds the order from typed item ids + qty and the approved price list. Widget numbers and strings are ignored.
  function buildOrder(m, payload) {
    if (!payload || typeof payload !== "object" || !Array.isArray(payload.items)) return { error: "items missing" };
    const extra = Object.keys(payload).filter((k) => k !== "items");
    if (extra.length) log("security", "extra fields in order.request dropped", { fields: extra });
    const qtyById = new Map();
    for (const it of payload.items) {
      if (!it || typeof it !== "object" || typeof it.id !== "string") return { error: "bad item" };
      if (!Number.isInteger(it.qty) || it.qty < 1 || it.qty > 20) return { error: "bad quantity" };
      if (!m.price_list.items.some((x) => x.id === it.id)) return { error: "unknown item id" };
      qtyById.set(it.id, (qtyById.get(it.id) || 0) + it.qty);
    }
    if (!qtyById.size) return { error: "empty order" };
    const lines = [...qtyById].map(([id, qty]) => {
      const def = m.price_list.items.find((x) => x.id === id);
      const unit = Math.round(def.price * 100);
      return { id, name: def.name, qty, unit_cents: unit, line_cents: unit * qty };
    });
    return { lines, total_cents: lines.reduce((s, l) => s + l.line_cents, 0), price_list_version: m.price_list.version };
  }

  // ---------- airport map viewer ----------
  let zoom = 1;
  function openMap(id) {
    const m = D.maps.find((x) => x.id === id);
    zoom = id === "overview" ? 1.8 : 1.4;
    $("#mapTitle").innerHTML = `${m.title}<small>${m.note}</small>`;
    $("#mapSeg").innerHTML = D.maps.map((x) => `<button class="${x.id === id ? "on" : ""}" data-map="${x.id}">${x.label}</button>`).join("");
    $("#mapSeg").querySelectorAll("[data-map]").forEach((b) => (b.onclick = () => openMap(b.dataset.map)));
    $("#mapCanvas").innerHTML = `<img src="${m.src}" alt="${m.title}">` +
      (m.pin ? `<span class="pin" style="left:${m.pin[0]}%;top:${m.pin[1]}%"></span><span class="map-tag" style="left:${m.pin[0]}%;top:${m.pin[1]}%">${m.pinLabel}</span>` : "");
    $("#mapPill").textContent = m.pin ? "Terminal from your flight (demo)" : "Position unknown here";
    $("#mapNote").textContent = m.pin ? "Pin = the terminal on your scripted flight, not GPS and not your position inside it." : "I don't know where you are on this map. Tell me a shop or gate you can see.";
    applyZoom(m);
    $("#mapSheet").classList.add("open"); $("#sheetBackdrop").classList.add("open");
    log("ui", `open map ${id}`, { pin: m.pin ? "terminal_from_flight_fixture" : null });
  }
  function applyZoom(m) {
    $("#mapCanvas").style.width = zoom * 100 + "%";
    const v = $("#mapView");
    requestAnimationFrame(() => {
      if (m && m.pin) { v.scrollLeft = v.scrollWidth * m.pin[0] / 100 - v.clientWidth / 2; v.scrollTop = v.scrollHeight * m.pin[1] / 100 - v.clientHeight / 2; }
    });
  }
  $("#zoomIn").onclick = () => { zoom = Math.min(4, zoom + 0.4); applyZoom(); };
  $("#zoomOut").onclick = () => { zoom = Math.max(1, zoom - 0.4); applyZoom(); };
  $("#mapClose").onclick = () => { $("#mapSheet").classList.remove("open"); $("#sheetBackdrop").classList.remove("open"); };
  $("#sheetClose").onclick = closeMini;
  $("#sheetBackdrop").onclick = () => { closeMini(); $("#mapSheet").classList.remove("open"); };

  // ---------- host approval card (single approval) ----------
  function approvalCard(m, built) {
    const ap = { key: "idem-" + ++idemSeq, done: false, area: state.dest, deadline: state.deadline };
    const shared = ["Items and quantities"];
    if (ap.area) shared.push(`Hotel area: ${esc(ap.area)}`);
    if (ap.deadline) shared.push(`Deadline: ${esc(ap.deadline.label)}`);
    const c = card(`<div class="host-tag">Dubai-io approval · shown by the app, not by the shop</div>
      <div class="card-head"><div><h3>Send this order to ${esc(m.name)}?</h3><div class="sub">Fixed prices from the shop's price list v${esc(built.price_list_version)}</div></div><div class="pills">${demoPill}</div></div>
      <div class="lines">${built.lines.map((l) => `<div class="ln"><span>${l.qty} × ${esc(l.name)}</span><span>${aed(l.line_cents)}</span></div>`).join("")}
        <div class="ln tot"><span>Fixed total</span><span>${aed(built.total_cents)}</span></div></div>
      <div class="note-line">Total rebuilt by Dubai-io from the price list. The shop's app cannot change it.</div>
      <div class="shares"><b>Will be shared with ${esc(m.name)}</b>${shared.join(" · ")}</div>
      <div class="shares"><b>Never shared</b>Your name · phone number · passport · live location · taxi and trip details</div>
      <div class="wait">Waiting for you. Nothing is sent until you tap Approve.</div>
      <div class="btn-row"><button class="btn small" data-a="ok">Approve and send</button><button class="btn small ghost" data-a="no">Cancel</button></div>`, "host");
    log("action", "request DRAFT → AWAITING_APPROVAL", { merchant: m.id, total: aed(built.total_cents), shares: ["items", ap.area ? "hotel_area" : null, ap.deadline ? "deadline" : null].filter(Boolean), idempotency_key: ap.key });
    c.querySelector('[data-a="ok"]').onclick = () => {
      if (ap.done) { log("security", "duplicate approve ignored (idempotent replay returns the original request)", { idempotency_key: ap.key }); return; }
      ap.done = true;
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      c.querySelector(".wait").remove();
      big("Sharing approved", { to: m.name, shared: shared.map((s) => s.split(":")[0]), never_shared: ["name", "phone", "passport", "live location", "taxi and trip details"], user_tap: true });
      createRequest(m, built, ap);
    };
    c.querySelector('[data-a="no"]').onclick = () => {
      if (ap.done) return; ap.done = true;
      c.innerHTML = `<h3>Cancelled</h3><div class="sub">Nothing was sent.</div>`; c.classList.remove("host");
      log("action", "request cancelled by user before send");
    };
  }

  // ---------- request state machine (ARCHITECTURE §4) ----------
  // EXPIRED, UNKNOWN_STATUS and FAILED exist in the table but this demo has no control that triggers them.
  const ALLOWED = {
    DRAFT: ["AWAITING_APPROVAL"],
    AWAITING_APPROVAL: ["SUBMITTED", "CANCELLED", "EXPIRED"],
    SUBMITTED: ["ACCEPTED", "DECLINED", "CANCELLED", "EXPIRED", "UNKNOWN_STATUS"],
    ACCEPTED: ["READY", "DECLINED", "CANCELLED", "EXPIRED", "UNKNOWN_STATUS"],
    READY: ["COMPLETED", "DECLINED", "CANCELLED", "EXPIRED", "UNKNOWN_STATUS"],
    UNKNOWN_STATUS: ["ACCEPTED", "READY", "COMPLETED", "DECLINED", "CANCELLED", "EXPIRED", "FAILED"],
    COMPLETED: [], DECLINED: [], CANCELLED: [], EXPIRED: [], FAILED: []
  };
  const TERMINAL = ["COMPLETED", "DECLINED", "CANCELLED", "EXPIRED", "FAILED"];
  const FLOW = ["SUBMITTED", "ACCEPTED", "READY", "COMPLETED"];
  const LABEL = { SUBMITTED: "Sent to shop", ACCEPTED: "Accepted at fixed price", READY: "Ready", COMPLETED: "Completed" };
  const EVENT = { SUBMITTED: "You approved the request", ACCEPTED: "Merchant accepted", READY: "Merchant marked ready", COMPLETED: "Merchant marked done", DECLINED: "Merchant declined", CANCELLED: "You cancelled" };
  const isTerminal = (r) => TERMINAL.includes(r.status);
  const canGo = (r, to) => (ALLOWED[r.status] || []).includes(to);

  function createRequest(m, built, ap) {
    const r = {
      id: "REQ-" + ++reqSeq, m, lines: built.lines, total: built.total_cents, area: ap.area, deadline: ap.deadline,
      status: "AWAITING_APPROVAL", prev: null, readyBy: null, ref: null, conflict: false, earlierAsked: false,
      lastEvent: null, el: null, conflictEl: null, autoSeq: 0, draftReadyBy: m.sim.first_ready_by, idem: ap.key
    };
    state.requests.push(r);
    r.el = card("");
    transition(r, "SUBMITTED", "user");
    autoTick(r);
  }

  function transition(r, to, actor) {
    if (!canGo(r, to)) { log("security", `illegal transition ${r.status} → ${to} rejected`, { id: r.id, actor }); return false; }
    log("action", `${r.id} ${r.status} → ${to}`, { actor, source: actor === "merchant" ? "merchant_inbox" : "user_tap" });
    r.prev = r.status; r.status = to;
    if (actor !== "user" || to !== "SUBMITTED") advance(2);
    r.lastEvent = { label: EVENT[to] || to, actor, at: now() };
    drawStatus(r); drawInbox();
    return true;
  }

  const summaryOf = (r) => r.lines.map((l) => `${l.qty}× ${l.name}`).join(", ");
  const readyLabel = (r) => `${r.readyBy} ${r.deadline ? r.deadline.day : "tomorrow"}`;

  function drawStatus(r) {
    const idx = FLOW.indexOf(r.status);
    let track;
    if (r.status === "DECLINED") track = `<div class="st bad"><i></i>Declined by the shop</div>`;
    else if (r.status === "CANCELLED") track = `<div class="st bad"><i></i>${["ACCEPTED", "READY"].includes(r.prev) ? "Cancel requested. The shop has been notified; I can't confirm any work stopped" : "Cancelled before the shop accepted"}</div>`;
    else track = FLOW.map((s, k) => `<div class="st ${k < idx ? "done" : k === idx ? "now" : ""}"><i></i>${LABEL[s]}${s === "ACCEPTED" && r.ref && idx >= 1 ? ` · shop ref ${esc(r.ref)}` : ""}</div>`).join("");
    const deadlineLine = r.readyBy
      ? `<div class="note-line">Ready by <b>${esc(readyLabel(r))}</b> ${merchantPill} <span class="pill">merchant_submitted</span></div>` +
        (r.deadline ? (r.conflict ? `<div class="note-line bad">Misses your ${esc(r.deadline.label)} deadline</div>` : `<div class="note-line">Meets your ${esc(r.deadline.label)} deadline</div>`) : "")
      : "";
    r.el.className = "card";
    r.el.innerHTML = `<div class="card-head"><div><h3>${esc(r.m.name)}</h3><div class="sub">${esc(summaryOf(r))} · ${aed(r.total)} fixed</div></div><div class="pills">${demoPill}<span class="pill">${r.id}</span></div></div>
      <div class="status-track">${track}</div>
      ${r.status === "SUBMITTED" ? `<div class="note-line">Waiting for the shop to answer.</div>` : ""}
      ${deadlineLine}
      ${r.lastEvent ? `<div class="note-line">Last event: ${esc(r.lastEvent.label)} · ${esc(r.lastEvent.at)}</div>` : ""}
      ${isTerminal(r) ? "" : `<div class="btn-row"><button class="btn small ghost" data-a="cancel">Cancel request</button></div>`}
      <div class="foot"><span>Status changes only when the shop or you act</span></div>`;
    const cb = r.el.querySelector('[data-a="cancel"]');
    if (cb) cb.onclick = () => userCancel(r);
    scroll();
  }

  // ----- merchant commands (backstage inbox, simulated merchant role) -----
  function mAccept(r, t) {
    if (!canGo(r, "ACCEPTED") || r.status !== "SUBMITTED") return log("security", "accept rejected", { id: r.id, status: r.status });
    if (!/^\d{2}:\d{2}$/.test(t || "")) return log("security", "accept rejected: ready_by missing", { id: r.id });
    r.readyBy = t;
    r.ref = r.m.logo.replace(/\W/g, "") + "-" + r.id.slice(4);
    if (!transition(r, "ACCEPTED", "merchant")) return;
    log("action", `${r.id} ready_by set by merchant`, { ready_by: t, provenance: "merchant_submitted" });
    big("Merchant accepted", { shop: r.m.name, price: aed(r.total) + " fixed", ready_by: t, provenance: "merchant_submitted" });
    r.conflict = deadlineConflict(r);
    bot(`${merchantPill}<br>${esc(r.m.name)} accepted your order at the fixed price ${aed(r.total)}. Ready by ${esc(readyLabel(r))}.` +
      (r.deadline && !r.conflict ? ` That meets your ${esc(r.deadline.label)} deadline.` : ""));
    if (r.conflict) showConflict(r);
    drawStatus(r); drawInbox();
    autoTick(r);
  }

  // Deterministic check in code, never by the LLM. Ready-by and deadline are compared as clock times on the same day.
  function deadlineConflict(r) { return !!(r.deadline && toMin(r.readyBy) > r.deadline.min); }

  function showConflict(r) {
    const diff = toMin(r.readyBy) - r.deadline.min;
    const gap = diff >= 60 ? `${Math.floor(diff / 60)} h${diff % 60 ? " " + (diff % 60) + " min" : ""}` : `${diff} min`;
    r.earlierAsked = false;
    if (r.conflictEl) r.conflictEl.querySelectorAll("button").forEach((x) => (x.disabled = true));
    r.conflictEl = card(`<h3>Misses your ${esc(r.deadline.label)} deadline</h3>
      <div class="sub">${esc(r.m.name)} says ready by ${esc(readyLabel(r))}, ${gap} after your deadline. Price unchanged: ${aed(r.total)} (fixed).</div>
      <div class="btn-row"><button class="btn small" data-a="earlier">Ask for earlier</button></div>
      <div class="foot"><span>Computed in code: ready-by ${esc(r.readyBy)} is after deadline ${fmt(r.deadline.min)}</span></div>`, "warn");
    log("agent", "deadline_conflict computed", { id: r.id, ready_by: r.readyBy, deadline: fmt(r.deadline.min), deadline_conflict: true });
    big("Conflict flagged", `Ready-by ${r.readyBy} > deadline ${fmt(r.deadline.min)}`);
    r.conflictEl.querySelector('[data-a="earlier"]').onclick = () => askEarlier(r);
  }

  function askEarlier(r) {
    if (r.status !== "ACCEPTED" || !r.conflict || r.earlierAsked) { log("security", "ask-earlier ignored (idempotent)", { id: r.id }); return; }
    r.earlierAsked = true;
    user("Ask for earlier");
    r.conflictEl.querySelectorAll("button").forEach((x) => (x.disabled = true));
    r.conflictEl.querySelector(".btn-row").insertAdjacentHTML("afterend", `<div class="note-line">Asked ${esc(r.m.name)} for an earlier ready-time. Waiting for their answer.</div>`);
    log("action", `${r.id} earlier-slot request → merchant inbox`, { structured: true, before: fmt(r.deadline.min), price_change: "none" });
    big("Earlier ready-time requested", `Sent to ${r.m.name}'s inbox · before ${fmt(r.deadline.min)} · price unchanged`);
    drawInbox();
    autoTick(r);
  }

  function mSetReadyBy(r, t) {
    if (r.status !== "ACCEPTED") return log("security", "set_ready_by rejected", { id: r.id, status: r.status });
    if (!/^\d{2}:\d{2}$/.test(t || "")) return log("security", "set_ready_by rejected: bad time", { id: r.id });
    r.readyBy = t; advance(2);
    r.lastEvent = { label: "Merchant set ready-by " + t, actor: "merchant", at: now() };
    log("action", `${r.id} ready_by set by merchant`, { ready_by: t, provenance: "merchant_submitted" });
    r.conflict = deadlineConflict(r);
    if (r.conflict) {
      big("Merchant set ready-by " + t, "Still after the deadline");
      bot(`${merchantPill}<br>${esc(r.m.name)} says ready by ${esc(readyLabel(r))}. That is still after your ${esc(r.deadline.label)} deadline.`);
      showConflict(r);
    } else {
      big("Ready confirmed", { shop: r.m.name, ready_by: t, price: aed(r.total) + " unchanged", provenance: "merchant_submitted" });
      bot(`${merchantPill}<br>${esc(r.m.name)} confirmed ready by ${esc(readyLabel(r))}.` +
        (r.deadline ? ` That meets your ${esc(r.deadline.label)} deadline.` : "") + ` Price unchanged: ${aed(r.total)} (fixed).`);
      if (r.conflictEl) {
        r.conflictEl.className = "card";
        r.conflictEl.innerHTML = `<h3>Resolved</h3><div class="sub">${esc(r.m.name)} moved ready-by to ${esc(readyLabel(r))}. Your ${esc(r.deadline.label)} deadline is met. Price unchanged: ${aed(r.total)}.</div>`;
      }
    }
    drawStatus(r); drawInbox();
    autoTick(r);
  }

  function mReady(r) {
    if (!transition(r, "READY", "merchant")) return;
    big("Order ready", { shop: r.m.name, source: "merchant_inbox" });
    bot(`${merchantPill}<br>${esc(r.m.name)} marked your order ready.`);
    autoTick(r);
  }
  function mComplete(r) {
    if (!transition(r, "COMPLETED", "merchant")) return;
    big("Order completed", { shop: r.m.name, source: "merchant_inbox" });
    bot(`${merchantPill}<br>${esc(r.m.name)} marked the order completed.`);
    chips([["Show the laundries again", () => laundryResults()]]);
  }
  function mDecline(r) {
    const was = r.status;
    if (!transition(r, "DECLINED", "merchant")) return;
    big("Merchant declined", { shop: r.m.name, from: was });
    bot(`${merchantPill}<br>${esc(r.m.name)} declined this order. Nothing more will happen on it. Want to try another laundry?`);
    chips([["Show other laundries", () => laundryResults()]]);
  }
  function userCancel(r) {
    const was = r.status;
    if (!transition(r, "CANCELLED", "user")) return;
    big("Request cancelled", { by: "user", from: was });
    bot(["ACCEPTED", "READY"].includes(was)
      ? `Cancel requested. I've told ${esc(r.m.name)}, but I can't confirm any work stopped until they say so.`
      : `Cancelled. ${esc(r.m.name)} hadn't accepted yet.`);
  }

  // Simulated merchant when "auto-respond" is on. Re-checks everything after each wait; a newer tick cancels older ones.
  async function autoTick(r) {
    const seq = ++r.autoSeq;
    if (!$("#autoMerchant").checked) return;
    await sleep(1500);
    if (seq !== r.autoSeq || !$("#autoMerchant").checked || isTerminal(r)) return;
    if (r.status === "SUBMITTED") return mAccept(r, r.m.sim.first_ready_by);
    if (r.status === "ACCEPTED") {
      if (r.conflict) { if (r.earlierAsked && r.m.sim.earlier_ready_by) return mSetReadyBy(r, r.m.sim.earlier_ready_by); return; }
      return mReady(r);
    }
    if (r.status === "READY") return mComplete(r);
  }

  function drawInbox() {
    const open = state.requests.filter((r) => r.status !== "AWAITING_APPROVAL");
    if (!open.length) return;
    $("#inbox").innerHTML = open.slice().reverse().map((r) => {
      const btn = (act, label) => `<button class="btn small ghost" data-id="${r.id}" data-act="${act}">${label}</button>`;
      const timeIn = `<input type="time" data-id="${r.id}" data-time value="${esc(r.draftReadyBy)}">`;
      const controls = r.status === "SUBMITTED" ? timeIn + btn("accept", "Accept at fixed price") + btn("decline", "Decline")
        : r.status === "ACCEPTED" ? timeIn + btn("setready", "Set ready-by") + btn("ready", "Mark ready") + btn("decline", "Decline")
        : r.status === "READY" ? btn("complete", "Mark done") + btn("decline", "Decline") : "";
      const cancelNote = r.status === "CANCELLED" ? (["ACCEPTED", "READY"].includes(r.prev) ? "Customer asked to cancel after acceptance (shop notified)" : "Customer cancelled before acceptance") : "";
      return `<div class="inbox-item"><div class="who">${esc(r.m.name)} <span class="when">${r.id}</span></div>
        <div>${esc(summaryOf(r))} · ${aed(r.total)} fixed</div>
        <div class="when">Shared with you: ${r.area ? "hotel area " + esc(r.area) : "no area"} · ${r.deadline ? "deadline " + esc(r.deadline.label) : "no deadline"}</div>
        <div class="st-tag">${r.status}${r.readyBy ? " · ready_by " + esc(r.readyBy) : ""}</div>
        ${r.earlierAsked && r.conflict ? `<div class="flag">Customer asks for an earlier ready-time (before ${fmt(r.deadline.min)}). Price unchanged.</div>` : ""}
        ${cancelNote ? `<div class="flag">${cancelNote}</div>` : ""}
        <div class="btn-row">${controls}${isTerminal(r) ? "" : btn("cancel", "Simulate: customer cancels")}</div></div>`;
    }).join("");
    $("#inbox").querySelectorAll("[data-time]").forEach((i) => (i.oninput = () => { state.requests.find((x) => x.id === i.dataset.id).draftReadyBy = i.value; }));
    $("#inbox").querySelectorAll("[data-act]").forEach((b) => (b.onclick = () => {
      const r = state.requests.find((x) => x.id === b.dataset.id);
      ({ accept: () => mAccept(r, r.draftReadyBy), setready: () => mSetReadyBy(r, r.draftReadyBy), ready: () => mReady(r), complete: () => mComplete(r), decline: () => mDecline(r), cancel: () => userCancel(r) })[b.dataset.act]();
    }));
  }

  // ---------- onboarding: price-list photo → generated mini-app → operator approval ----------
  function photoSVG() {
    const lines = D.onboarding.photo_lines.map((t, i) => `<text x="14" y="${30 + i * 22}" font-family="Georgia,serif" font-size="${i === 0 ? 15 : 12.5}" fill="#3a3322" ${i === 0 ? 'font-weight="700"' : ""}>${esc(t)}</text>`).join("");
    return `<svg class="photo" viewBox="0 0 220 150" role="img" aria-label="Simulated photo of a handwritten price list"><rect width="220" height="150" fill="#FFFDF5"/><rect x="4" y="4" width="212" height="142" fill="none" stroke="#D9CFB0" stroke-dasharray="3 3"/>${lines}</svg>`;
  }

  async function startOnboarding() {
    if (state.draft || state.joined) { bot("A shop has already joined in this run. Restart the demo to see it again."); return; }
    showTab("companion");
    const draft = JSON.parse(JSON.stringify(D.onboarding.shop));
    state.draft = draft;
    log("trigger", "merchant.price_list_photo_uploaded", { shop: draft.name, simulated: true });
    const c = card(`<div class="card-head"><div><h3>${esc(draft.name)} wants to join</h3><div class="sub">The owner uploaded a photo of the price list</div></div><div class="pills"><span class="pill est">Simulated photo</span></div></div>${photoSVG()}
      <div class="note-line">Reading the photo…</div>`);
    await sleep(1400);
    c.innerHTML = `<div class="card-head"><div><h3>${esc(draft.name)}: draft</h3><div class="sub">Extracted from the photo · simulated, no OCR runs in this demo</div></div><div class="pills"><span class="pill">Draft · not live</span></div></div>
      ${photoSVG()}
      <div class="lines">${draft.price_list.items.map((i) => `<div class="prov-row"><span>${esc(i.name)} · AED ${i.price}</span><span class="pill">merchant_submitted</span></div>`).join("")}</div>
      <div class="note-line">The same mini-app template is filled from this catalog. Nothing is published until the operator approves it.</div>
      <div class="foot"><span>See Under the hood › Ops review</span></div>`;
    big("Draft mini-app generated", { shop: draft.name, items: draft.price_list.items.length, template: "miniapps/template.html", status: "draft" });
    drawOps();
  }

  function drawOps() {
    const d = state.draft;
    if (!d) { $("#ops").innerHTML = `<div class="inbox-empty">No shop waiting for review.</div>`; return; }
    $("#ops").innerHTML = `<div class="inbox-item"><div class="who">${esc(d.name)} <span class="when">draft · not live</span></div>
      <div>${d.price_list.items.map((i) => esc(i.name) + " AED " + i.price).join(" · ")}</div>
      <div class="when">Generated from the template + extracted catalog · prices: merchant_submitted</div>
      <div class="btn-row"><button class="btn small ghost" data-o="preview">Preview mini-app</button><button class="btn small" data-o="approve">Approve and publish</button><button class="btn small ghost" data-o="reject">Reject</button></div></div>`;
    $("#ops").querySelector('[data-o="preview"]').onclick = () => openMini(null, { merchant: d, preview: true });
    $("#ops").querySelector('[data-o="approve"]').onclick = () => approveDraft();
    $("#ops").querySelector('[data-o="reject"]').onclick = () => { log("action", "operator rejected draft", { shop: d.name }); big("Draft rejected", d.name); state.draft = null; drawOps(); };
  }

  async function approveDraft() {
    const d = state.draft; if (!d) return;
    d.manifest.approved = true; d.manifest.version = "1.0.0"; d.price_list.version = D.merchants[0].as_of;
    D.merchants.push(d);
    state.draft = null; state.joined = true;
    log("action", "operator approved provider draft → approved", { shop: d.name });
    big("Shop approved by operator", { shop: d.name, live: true });
    drawOps(); renderServices();
    bot(`${esc(d.name)} just joined Dubai-io (reviewed by the operator). It now appears in the laundry results.`);
    if (state.laundryShown && state.dest) { await typing(400); laundryResults(true); }
  }

  // ---------- memory payoff: lost item in taxi ----------
  async function recovery() {
    log("agent", "intent: lost_item_in_taxi", { uses_memory: !!state.trip });
    if (!state.trip) return bot("I'm sorry. I don't have taxi details saved, and I won't guess them. If you have the receipt or the plate, tell me and I'll help you prepare the report. The official channels can also help.");
    const t = state.trip;
    log("memory", "recall taxi trip", { ...t, retrieval: "memory.get(trip)" });
    bot("Don't worry. I have the trip details you gave me, so you won't need to remember them.");
    await typing(500);
    card(tripCardHTML(t, "Saved earlier: your taxi details"));
    const pl = document.createElement("div"); pl.className = "pairlabel"; pl.textContent = "↓ pre-filled into this report"; chat.append(pl);
    const c = card(`<div class="card-head"><div><h3>Lost item report</h3><div class="sub">Pre-filled with the fields RTA asks for · nothing submitted</div></div><div class="pills"><span class="pill">Not recovered</span></div></div>
      ${reportFields(t)}
      <div class="shares"><b>Missing: describe the bag</b><input class="field" id="bagIn" placeholder="Colour, type, what's inside" style="width:100%;margin-top:4px" autocomplete="off"><div class="err" id="bagErr"></div></div>
      <div class="btn-row"><button class="btn small" id="bagGo">Prepare report</button></div>`);
    c.querySelector("#bagGo").onclick = async () => {
      const bag = c.querySelector("#bagIn").value.trim();
      if (!bag) { c.querySelector("#bagErr").textContent = "Describe the bag so the report is complete. I won't guess."; return; }
      const text = reportText(t, bag);
      log("action", "recovery.report_prepared", { plate: t.plate || null, receipt: t.receipt, item: bag, status: "PREPARED_NOT_SUBMITTED" });
      big("Lost-item report prepared", { status: "Not recovered", submitted: false, source: "saved trip details + bag description" });
      c.innerHTML = `<div class="card-head"><div><h3>Report ready to send</h3><div class="sub">You send it through the official channel. I haven't sent anything.</div></div><div class="pills"><span class="pill">Not recovered</span></div></div>
        <div class="shares"><b>Item</b>${esc(bag)}</div>${reportFields(t)}
        <div class="btn-row"><button class="btn small" id="rtaGo">Contact official</button><button class="btn small ghost" id="rtaCopy">Copy report</button></div>
        <div class="note-line" id="rtaNote">Official channels per RTA: call centre (800 9090), chat agent or the RTA app. Check rta.ae for the current options.</div>
        <div class="foot"><span>Handoff only. I won't mark anything recovered until you tell me</span></div>`;
      c.querySelector("#rtaGo").onclick = () => { window.open("https://www.rta.ae/", "_blank", "noopener"); log("action", "handoff.official_channel", { url: "https://www.rta.ae/", status: "HANDOFF" }); };
      c.querySelector("#rtaCopy").onclick = () => copyReport(text, c);
      await typing(); bot("I won't mark the bag as recovered until you tell me it's found.");
    };
  }

  function reportFields(t) {
    return `<div class="mem-row"><span class="k">Ride started</span><span class="v">${esc(t.start)}</span></div>
      <div class="mem-row"><span class="k">Pickup</span><span class="v">DXB ${esc(D.terminals[t.terminal])}</span></div>
      <div class="mem-row"><span class="k">Drop-off area</span><span class="v">${esc(t.dest)}</span></div>
      <div class="mem-row"><span class="k">Roof colour</span><span class="v">${esc(t.roof)}</span></div>
      <div class="mem-row"><span class="k">Plate / receipt</span><span class="v">${t.plate ? esc(t.plate) : ""}${t.plate && t.receipt ? " · " : ""}${t.receipt ? "receipt photo (simulated)" : ""}</span></div>`;
  }
  function reportText(t, bag) {
    return ["Lost item report (prepared by Dubai-io, not submitted)",
      `Item: ${bag}`, `Ride started: ${t.start}`, `Pickup: DXB ${D.terminals[t.terminal]}`, `Drop-off area: ${t.dest}`, `Roof colour: ${t.roof}`,
      `Plate / taxi number: ${t.plate || "not given"}`, `Receipt photo: ${t.receipt ? "attached (simulated)" : "none"}`, "Status: Not recovered"].join("\n");
  }
  async function copyReport(text, c) {
    const btn = c.querySelector("#rtaCopy");
    try {
      await navigator.clipboard.writeText(text);
      btn.textContent = "Copied ✓"; setTimeout(() => (btn.textContent = "Copy report"), 2000);
      log("action", "report copied to clipboard", { chars: text.length });
    } catch (e) {
      log("security", "clipboard unavailable, showing text to copy by hand", { error: String(e && e.name) });
      if (!c.querySelector("#rtaText")) c.querySelector("#rtaNote").insertAdjacentHTML("beforebegin", `<textarea id="rtaText" class="field" rows="7" readonly style="width:100%;margin-top:8px"></textarea>`);
      const ta = c.querySelector("#rtaText"); ta.value = text; ta.focus(); ta.select();
    }
  }

  // ---------- free text ----------
  async function handleText(t) {
    log("agent", "intent classify", { text: t });
    await typing();
    const q = t.toLowerCase();
    if (/(left|lost|forgot).*(bag|taxi|cab)|(taxi|cab).*(left|lost|forgot)/.test(q)) return recovery();
    if (state.awaitDeadline && /\b(by|before)\b/.test(q)) return laundryIntent(t);
    if (/reached.*hotel|arrived.*hotel|at (my|the) hotel/.test(q)) return hotelReached();
    if (/laundry|iron|press|shirt/.test(q)) return laundryIntent(t);
    if (/pharm|medic|panadol|headache|sick/.test(q)) return bot("Pharmacies are browse-only in this demo. You can look at them in the Services tab.");
    if (/deadline/.test(q)) return bot(state.deadline ? `You told me: <b>${esc(state.deadline.label)}</b>. ${youPill}` : "You haven't told me a deadline yet.");
    if (/belt/.test(q)) return bot(state.memory["Baggage belt"] ? `You told me: <b>${esc(state.memory["Baggage belt"].value)}</b>. ${youPill}` : "You haven't told me a belt number yet. Check the arrivals screens.");
    if (/taxi number|which taxi|plate/.test(q)) return bot(state.trip ? `Your taxi: <b>${state.trip.plate ? esc(state.trip.plate) : "receipt photo (simulated)"}</b>, roof ${esc(state.trip.roof)}, ${esc(state.trip.route)}, started ${esc(state.trip.start)}.` : "I don't have a taxi saved.");
    if (/taxi|metro|hotel|ride/.test(q)) return ridePrompt();
    if (/lost|where am i/.test(q)) return stepAction("lost");
    bot("This demo is scripted. Try: <i>I've reached my hotel</i>, <i>I need a shirt pressed by 9 tomorrow</i>, <i>I left my bag in the taxi!</i>");
  }
  $("#composer").onsubmit = (e) => {
    e.preventDefault();
    const t = $("#input").value.trim(); if (!t) return;
    $("#input").value = ""; user(t);
    handleText(t);
  };

  // ---------- start ----------
  function resetState() {
    const weekday = state.weekday || D.scenario.weekday;
    Object.keys(state).forEach((k) => delete state[k]);
    Object.assign(state, {
      memory: {}, requests: [], dest: null, terminal: D.flight.terminalId, terminalSet: false, step: 0, trip: null, tripEl: null,
      deadline: null, awaitDeadline: false, laundryShown: false, draft: null, joined: false, weekday, clock: toMin(D.scenario.clock)
    });
  }

  async function start() {
    epoch++;
    clearTimeout(loadTimer); closeMini();
    chat.innerHTML = ""; journeyCard = null; resetState();
    D.merchants.length = BASE_MERCHANTS;
    $("#log").innerHTML = ""; $("#keylog").innerHTML = "";
    $("#inbox").innerHTML = `<div class="inbox-empty">No requests yet. Open a laundry mini-app and send an order request.</div>`;
    paintClock(); renderMemory(); renderServices(); drawOps(); showTab("companion");
    log("trigger", "flight.landed", { source: "demo_trigger", flight: D.flight.number, airport: "DXB", terminal: D.flight.terminalId, dedupe_key: "EK002:landed", scripted_clock: `${state.weekday} ${now()}` });
    await sleep(300);
    const hero = card(`<div class="hero-hello">
      <div class="eyebrow">Dubai-io · Proactive <span class="pill trig">Demo trigger</span> <span class="pill demo">Scripted demo</span></div>
      <h1>Hello, visitor.</h1>
      <p>Welcome to Dubai. Your flight ${esc(D.flight.number)} has landed at DXB. I'll walk you from the gate to your ride, one step at a time. Everything here is scripted and uses demo data.</p>
      <div class="btn-row"><button class="btn" id="goGuide">Guide me to arrivals</button></div></div>`);
    hero.querySelector("#goGuide").onclick = async () => {
      hero.querySelector("#goGuide").disabled = true;
      user("Guide me to arrivals"); await typing();
      bot("Let's go. Tap <b>Done</b> after each step, or <b>I'm lost</b> any time. I only know where you are from what you tell me.");
      renderStep(0);
    };
  }

  // ---------- backstage wiring ----------
  $("#restartBtn").onclick = start;
  $("#mobileLogBtn").onclick = () => { $("#backstage").classList.add("open"); $("#closeBackstage").style.display = "inline-block"; };
  $("#closeBackstage").onclick = () => $("#backstage").classList.remove("open");
  $("#joinBtn").onclick = startOnboarding;
  $("#autoMerchant").onchange = () => state.requests.forEach((r) => { if (!isTerminal(r) && r.status !== "AWAITING_APPROVAL") autoTick(r); });
  $("#weekdaySel").onchange = (e) => { state.weekday = e.target.value; start(); };
  document.querySelectorAll("[data-say]").forEach((b) => (b.onclick = () => {
    showTab("companion");
    $("#input").value = b.dataset.say;
    $("#composer").dispatchEvent(new Event("submit", { cancelable: true }));
  }));
  document.querySelectorAll("#logSeg button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll("#logSeg button").forEach((x) => x.classList.toggle("on", x === b));
    $("#keylog").hidden = b.dataset.view !== "key"; $("#log").hidden = b.dataset.view !== "raw";
  }));
  $("#weekdaySel").value = D.scenario.weekday;
  state.weekday = D.scenario.weekday;
  start();
})();
