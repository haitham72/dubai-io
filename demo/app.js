// Dubai-io clickable demo. Scripted, no backend, no LLM.
// The "Under the hood" panel shows what a real build would do at each step.
(() => {
  const D = window.DEMO;
  const $ = (s) => document.querySelector(s);
  const chat = $("#chat");
  const state = { mode: "Visitor", memory: {}, requests: [], dest: null, step: 0 };
  let reqSeq = 4800;

  // ---------- helpers ----------
  const now = () => new Date().toTimeString().slice(0, 5);
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

  function log(kind, text, obj) {
    const el = document.createElement("div");
    el.className = "entry";
    el.innerHTML = `<span class="ts">${new Date().toTimeString().slice(0, 8)}</span> <span class="kind k-${kind}">${kind}</span> ${esc(text)}` +
      (obj ? `<div class="detail">${esc(JSON.stringify(obj))}</div>` : "");
    $("#log").prepend(el);
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
  function card(html) {
    const el = document.createElement("div");
    el.className = "card"; el.innerHTML = html;
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
  async function typing(ms = 500) { await sleep(ms); }

  function remember(key, value) {
    state.memory[key] = value;
    log("memory", `saved "${key}"`, { value, provenance: "user_supplied" });
    renderMemory();
  }
  function renderMemory() {
    const keys = Object.keys(state.memory);
    $("#memoryList").innerHTML = keys.length
      ? keys.map((k) => `<div class="row"><div>${esc(k)}<div class="k">${esc(state.memory[k])}</div></div><span class="pill user">You told me</span></div>`).join("")
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
      <div class="card-head"><div><h3>DXB arrival guide</h3><div class="sub">${D.flight.terminal} · step ${i + 1} of ${D.airportSteps.length}</div></div>
      <div class="pills"><span class="pill demo">Demo data</span></div></div>
      <div class="journey">${schematic(s.zone)}
        <div><div class="step-title">${s.title}</div><div class="step-body">${s.body}</div>
        <div class="btn-row">${i < D.airportSteps.length - 1 ? `<button class="btn small" data-x="next">Done, next ✓</button>` : `<button class="btn small" data-x="ride">Compare rides</button>`}
        <button class="btn small ghost" data-x="lost">I'm lost</button>${extras}</div></div></div>
      ${i === 0 ? `<button class="map-thumb" data-x="map" aria-label="Open airport map"><span class="pin"></span><span class="cap">You're at Terminal 3 · tap for map</span></button>` : ""}
      <div class="progress">${prog}</div>
      <div class="foot"><span>Steps confirmed by you, no indoor GPS</span><button class="btn small ghost" data-x="map" style="padding:4px 10px;font-size:12px">Airport maps</button></div>`;
    if (!journeyCard) journeyCard = card(html); else { journeyCard.innerHTML = html; chat.append(journeyCard); scroll(); }
    journeyCard.querySelectorAll("[data-x]").forEach((b) => (b.onclick = () => stepAction(b.dataset.x)));
  }

  async function stepAction(x) {
    if (x === "map") return openMap("overview");
    if (x === "next") { user("Done ✓"); await typing(300); renderStep(state.step + 1); }
    if (x === "ride") { user("Compare rides"); rides(); }
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
      const c = card(`<h3>Belt number</h3><div class="sub">Read it from the arrivals screen</div>
        <div style="display:flex;gap:8px"><input id="beltIn" placeholder="e.g. 7" class="field">
        <button class="btn small" id="beltSave">Save</button></div>`);
      c.querySelector("#beltSave").onclick = async () => {
        const v = c.querySelector("#beltIn").value.trim() || "7";
        remember("Baggage belt", `Belt ${v} · ${D.flight.number}`);
        c.innerHTML = `<h3>Saved: Belt ${esc(v)}</h3><div class="pills"><span class="pill user">You told me</span></div>`;
        await typing(); bot(`I'll remember belt ${esc(v)}. Ask "which belt?" any time.`);
      };
    }
  }

  async function rides() {
    await typing();
    const d = D.destinations[state.dest];
    log("tool", "transport.compare", { from: "DXB T3", to: state.dest, sources: ["demo_fixture"], live: false });
    const c = card(`
      <div class="card-head"><div><h3>To ${state.dest}</h3><div class="sub">From DXB ${D.flight.terminal} · with luggage</div></div>
      <div class="pills"><span class="pill est">Demo estimate</span></div></div>
      <div class="opt"><div class="ico">🚕</div><div><b>Taxi</b><div class="line">${d.taxi.time} · ${d.taxi.price} · door to door, easy with bags</div></div><button class="btn small" data-r="taxi">Choose</button></div>
      <div class="opt"><div class="ico">🚇</div><div><b>Metro, Red Line</b><div class="line">${d.metro.time} · ${d.metro.price} · luggage size rules apply</div></div><button class="btn small" data-r="metro">Choose</button></div>
      <div class="opt"><div class="ico">📱</div><div><b>Ride-hailing app</b><div class="line">Opens your app. Dubai-io doesn't book it</div></div><button class="btn small ghost" data-r="app">Open</button></div>
      <div class="foot"><span>Fares and times are examples. Verify with official RTA info</span></div>`);
    c.querySelectorAll("[data-r]").forEach((b) => (b.onclick = () => {
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      ({ taxi: taxiFlow, metro: metroFlow, app: appFlow })[b.dataset.r]();
    }));
  }

  async function taxiFlow() {
    user("Taxi"); await typing();
    renderStep(5);
    bot("Follow the <b>Taxi</b> signs to the official rank outside arrivals. Use only the official airport taxis.");
    await typing(600);
    const c = card(`<h3>Save your taxi number?</h3><div class="sub">Useful if you leave something in the car</div>
      <div style="display:flex;gap:8px"><input id="taxiIn" placeholder="Number on the taxi" class="field">
      <button class="btn small" id="taxiSave">Save</button></div>`);
    c.querySelector("#taxiSave").onclick = async () => {
      const v = c.querySelector("#taxiIn").value.trim() || "12345";
      state.trip = { number: v, route: `DXB T3 → ${state.dest}`, started: now() };
      remember("Taxi trip", `Taxi ${v} · ${state.trip.route} · started ${state.trip.started} (you confirmed)`);
      c.innerHTML = `<h3>Taxi ${esc(v)} saved</h3><div class="pills"><span class="pill user">You told me</span></div>`;
      await typing();
      const a = card(`<h3>Share your trip with family?</h3>
        <div class="shares"><b>Will be shared</b>Taxi number · destination area (${state.dest}) · rough arrival time</div>
        <div class="shares"><b>Never shared</b>Live location · passport · phone number</div>
        <div class="btn-row"><button class="btn small" id="shareYes">Approve and share</button><button class="btn small ghost" id="shareNo">Not now</button></div>`);
      a.querySelector("#shareYes").onclick = () => { log("action", "trip.share approved", { shares: ["taxi_number", "destination_area", "eta"], approval: "user_tap" }); a.innerHTML = `<h3>Shared with family ✓</h3><div class="sub">Only what you approved</div>`; arrived(); };
      a.querySelector("#shareNo").onclick = () => { a.innerHTML = `<h3>Not shared</h3>`; arrived(); };
    };
  }

  async function metroFlow() {
    user("Metro"); await typing();
    renderStep(5);
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
      c.innerHTML = `<div class="card-head"><div><h3>Metro to ${state.dest}</h3><div class="sub">Step ${k + 1} of ${steps.length}</div></div><span class="pill est">Verify on RTA</span></div>
        <div class="step-body" style="font-size:14px">${steps[k]}</div>
        <div class="btn-row"><button class="btn small" id="mNext">${k < steps.length - 1 ? "Done, next ✓" : "I've arrived ✓"}</button></div>`;
      c.querySelector("#mNext").onclick = () => { log("agent", "metro step confirmed", { step: k + 1 }); if (k < steps.length - 1) { k++; draw(); } else { c.querySelectorAll("button").forEach((x) => (x.disabled = true)); arrived(); } };
    };
    draw();
  }

  async function appFlow() {
    user("Ride-hailing app"); await typing();
    log("action", "handoff.external_app", { status: "HANDOFF", note: "not a confirmed booking" });
    card(`<h3>Opening your ride app</h3><div class="sub">This is a handoff. I won't show it as booked, because I can't confirm it.</div><span class="pill">Status: handed off</span>`);
    arrived();
  }

  async function arrived() {
    await sleep(800);
    bot(`Enjoy the ride. Tell me when you've reached your hotel in ${state.dest}.`);
    chips([["I've reached my hotel", () => hotelReached()]]);
  }

  async function hotelReached() {
    await typing();
    log("trigger", "trip.arrived_hotel_area", { source: "user_confirmed", dedupe_key: "arrive:" + state.dest });
    bot(`<span class="pill trig">Proactive</span><br>Welcome to ${state.dest}. After a long flight, people often need a pharmacy, a SIM or laundry. Want me to find something nearby?`);
    chips([["Find a pharmacy", () => pharmacies()], ["Laundry for tomorrow", () => pharmacies("Laundry")], ["I'm fine, thanks", () => bot("Enjoy Dubai. I'm here whenever you need me.")]]);
  }

  // ---------- services: aggregator → per-merchant mini-apps ----------
  async function pharmacies(cat = "Pharmacy") {
    await typing();
    const list = D.merchants.filter((m) => m.category === cat);
    log("tool", "registry.search", { category: cat, area: state.dest || "Business Bay", results: list.map((m) => m.id) });
    const rows = list.map((m) => `<div class="opt"><div class="ico" style="background:${m.color};color:#fff;font-size:12px;font-weight:700">${m.logo}</div>
      <div><b>${m.name}</b><div class="line">${m.line} · ${m.distance}</div></div><button class="btn small" data-m="${m.id}">Open</button></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>${cat} near ${state.dest || "you"}</h3><div class="sub">Each one opens its own mini-app</div></div><span class="pill demo">Demo merchants</span></div>${rows}
      <div class="foot"><span>No ratings shown. None are verified yet</span></div>`);
    c.querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  function renderServices(cat = "Pharmacy") {
    $("#cats").innerHTML = D.categories.map((c) => `<button class="cat ${c === cat ? "active" : ""}" data-c="${c}">${c}</button>`).join("");
    $("#cats").querySelectorAll("[data-c]").forEach((b) => (b.onclick = () => renderServices(b.dataset.c)));
    const list = D.merchants.filter((m) => m.category === cat);
    $("#merchantList").innerHTML = list.length ? list.map((m) => `<div class="merchant"><div class="logo" style="background:${m.color}">${m.logo}</div>
      <div><b>${m.name}</b><div class="line">${m.line} · ${m.distance}</div><span class="pill demo">Demo merchant</span></div>
      <button class="btn small" data-m="${m.id}">Open</button></div>`).join("")
      : `<p class="empty">No ${cat.toLowerCase()} merchants onboarded yet. A shop can join by uploading a photo of its menu or price list.</p>`;
    $("#merchantList").querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  // ---------- mini-app host + bridge ----------
  const frame = $("#miniFrame");
  let current = null;
  function openMini(id) {
    current = D.merchants.find((m) => m.id === id);
    $("#sheetTitle").innerHTML = `${current.name}<small>Merchant mini-app · their own HTML</small>`;
    $("#sheetManifest").textContent = `manifest v${current.manifest.version} · scopes: ${current.manifest.bridge_scopes.join(", ")}`;
    frame.src = current.manifest.entry;
    $("#sheet").classList.add("open"); $("#sheetBackdrop").classList.add("open");
    log("ui", `mount mini-app ${id}`, { entry: current.manifest.entry, sandbox: "allow-scripts", scopes: current.manifest.bridge_scopes });
  }
  function closeMini() {
    $("#sheet").classList.remove("open"); $("#sheetBackdrop").classList.remove("open");
    setTimeout(() => (frame.src = "about:blank"), 300);
  }
  $("#sheetClose").onclick = closeMini; $("#sheetBackdrop").onclick = () => { closeMini(); $("#mapSheet").classList.remove("open"); };

  window.addEventListener("message", (e) => {
    if (e.source !== frame.contentWindow) return;           // only the mounted mini-app
    const m = e.data;
    if (!m || m.v !== 1 || typeof m.kind !== "string") { log("security", "malformed bridge message dropped", m); return; }
    if (m.kind === "app.ready") {
      const ctx = { area: state.dest || "Business Bay", lang: "en" };
      log("bridge", `${current.id} ready → host shares minimal context`, ctx);
      frame.contentWindow.postMessage({ v: 1, kind: "host.context", payload: ctx }, "*");
      return;
    }
    if (m.kind === "diag.report") { log("security", `${current.id} sandbox self-test`, m.payload); return; }
    if (!current.manifest.bridge_scopes.includes(m.kind)) {
      log("security", `BLOCKED "${m.kind}": not in manifest scopes`, { merchant: current.id, allowed: current.manifest.bridge_scopes });
      frame.contentWindow.postMessage({ v: 1, kind: "host.error", payload: { reason: "scope_denied", kind: m.kind } }, "*");
      return;
    }
    log("bridge", `${current.id} → ${m.kind}`, m.payload);
    const merchant = current;
    closeMini(); showTab("companion");
    approval(merchant, m.kind, m.payload);
  });

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
    $("#mapPill").textContent = m.pin ? "You are here: confirmed by you" : "Position unknown here";
    $("#mapNote").textContent = m.pin ? "Pin = the terminal you told me, not GPS." : "I don't know where you are on this map. Tell me a shop or gate you can see.";
    applyZoom(m);
    $("#mapSheet").classList.add("open"); $("#sheetBackdrop").classList.add("open");
    log("ui", `open map ${id}`, { pin: m.pin ? "user_confirmed_terminal" : null });
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

  // ---------- approval + request state machine ----------
  const FLOW = ["SUBMITTED", "PROVIDER_ACKNOWLEDGED", "QUOTED", "QUOTE_ACCEPTED", "CONFIRMED"];
  const ALLOWED = {
    AWAITING_APPROVAL: ["SUBMITTED", "CANCELLED"],
    SUBMITTED: ["PROVIDER_ACKNOWLEDGED", "DECLINED", "CANCELLED"],
    PROVIDER_ACKNOWLEDGED: ["QUOTED", "DECLINED", "CANCELLED"],
    QUOTED: ["QUOTE_ACCEPTED", "CANCELLED"],
    QUOTE_ACCEPTED: ["CONFIRMED", "CANCELLED"],
    CONFIRMED: ["COMPLETED"]
  };
  const LABEL = { SUBMITTED: "Sent to merchant", PROVIDER_ACKNOWLEDGED: "Merchant acknowledged", QUOTED: "Merchant quoted", QUOTE_ACCEPTED: "You accepted the quote", CONFIRMED: "Merchant confirmed" };

  function approval(m, kind, p) {
    const shares = {
      "cart.request": ["Item list", `Delivery area: ${state.dest || "Business Bay"}`, "Contact: in-app chat (phone hidden)"],
      "rx.request": ["Prescription photo", `Delivery area: ${state.dest || "Business Bay"}`, "Contact: in-app chat (phone hidden)"],
      "pickup.request": ["Item list", "Your first name for pickup"],
      "quote.request": ["Item count and pickup slot", `Pickup area: ${state.dest || "Business Bay"}`]
    }[kind];
    const items = (p.items || []).map((i) => `${i.qty}× ${esc(i.name)}`).join(", ") || esc(p.summary || "");
    const c = card(`<div class="card-head"><div><h3>Send to ${m.name}?</h3><div class="sub">${items}</div></div><span class="pill demo">Demo merchant</span></div>
      <div class="shares"><b>Will be shared</b>${shares.join(" · ")}</div>
      ${p.estimate ? `<div class="shares"><b>Estimate</b>AED ${p.estimate.toFixed(2)}. The merchant confirms the final price</div>` : ""}
      <div class="btn-row"><button class="btn small" data-a="ok">Approve and send</button><button class="btn small ghost" data-a="no">Cancel</button></div>`);
    log("action", "request DRAFT → AWAITING_APPROVAL", { merchant: m.id, kind });
    c.querySelector('[data-a="ok"]').onclick = () => { c.querySelectorAll("button").forEach((x) => (x.disabled = true)); createRequest(m, kind, p, items); };
    c.querySelector('[data-a="no"]').onclick = () => { c.innerHTML = `<h3>Cancelled</h3><div class="sub">Nothing was sent.</div>`; log("action", "request cancelled by user before send"); };
  }

  function createRequest(m, kind, p, summary) {
    const r = { id: "REQ-" + ++reqSeq, m, kind, p, summary, status: "AWAITING_APPROVAL", quote: null, ref: null, el: null };
    state.requests.push(r);
    r.el = card(""); transition(r, "SUBMITTED", "user");
    if ($("#autoMerchant").checked) autoMerchant(r);
  }

  function transition(r, to, actor) {
    if (!(ALLOWED[r.status] || []).includes(to)) { log("security", `illegal transition ${r.status} → ${to} rejected`, { id: r.id, actor }); return; }
    log("action", `${r.id} ${r.status} → ${to}`, { actor, source: actor === "merchant" ? "merchant_inbox" : "user_tap" });
    r.status = to;
    if (to === "QUOTED") r.quote = { total: +((r.p.estimate || 30) + 7).toFixed(2), eta: "35–45 min" };
    if (to === "CONFIRMED") r.ref = r.m.logo + "-" + Math.floor(1000 + Math.random() * 9000);
    drawStatus(r); drawInbox();
  }

  function merchantUpdate(r) {
    if (r.ofd) { log("security", "duplicate merchant update dropped", { dedupe_key: r.id + ":ofd" }); return; }
    r.ofd = true;
    log("trigger", "provider.update out_for_delivery", { id: r.id, actor: "merchant", provenance: "merchant_reported", dedupe_key: r.id + ":ofd" });
    bot(`<span class="pill trig">Merchant update</span><br>${r.m.name} says your order is on its way.`);
    drawInbox();
  }

  function drawStatus(r) {
    const idx = FLOW.indexOf(r.status);
    const track = r.status === "DECLINED" || r.status === "CANCELLED"
      ? `<div class="st bad"><i></i>${r.status === "DECLINED" ? "Merchant declined. Want me to try another pharmacy?" : "Cancelled"}</div>`
      : FLOW.map((s, k) => `<div class="st ${k < idx ? "done" : k === idx ? "now" : ""}"><i></i>${LABEL[s]}${s === "QUOTED" && r.quote ? `: <b>AED ${r.quote.total.toFixed(2)}</b>, ${r.quote.eta}` : ""}${s === "CONFIRMED" && r.ref ? ` · ref ${r.ref}` : ""}</div>`).join("");
    r.el.innerHTML = `<div class="card-head"><div><h3>${r.m.name}</h3><div class="sub">${r.summary}</div></div><span class="pill">${r.id}</span></div>
      <div class="status-track">${track}</div>
      ${r.status === "QUOTED" ? `<div class="btn-row"><button class="btn small" data-q="ok">Accept AED ${r.quote.total.toFixed(2)}</button><button class="btn small ghost" data-q="no">Decline</button></div>` : ""}
      <div class="foot"><span>Status changes only when the merchant or you act</span></div>`;
    const ok = r.el.querySelector('[data-q="ok"]');
    if (ok) {
      ok.onclick = () => { transition(r, "QUOTE_ACCEPTED", "user"); if ($("#autoMerchant").checked) setTimeout(() => transition(r, "CONFIRMED", "merchant"), 1500); };
      r.el.querySelector('[data-q="no"]').onclick = () => transition(r, "CANCELLED", "user");
    }
    scroll();
  }

  async function autoMerchant(r) {
    await sleep(1500); if (r.status === "SUBMITTED") transition(r, "PROVIDER_ACKNOWLEDGED", "merchant");
    await sleep(2000); if (r.status === "PROVIDER_ACKNOWLEDGED") transition(r, "QUOTED", "merchant");
  }

  function drawInbox() {
    const open = state.requests.filter((r) => r.status !== "AWAITING_APPROVAL");
    if (!open.length) return;
    $("#inbox").innerHTML = open.slice().reverse().map((r) => {
      const b = (to, label) => (ALLOWED[r.status] || []).includes(to) && to !== "QUOTE_ACCEPTED" && to !== "CANCELLED"
        ? `<button class="btn small ghost" data-id="${r.id}" data-to="${to}">${label}</button>` : "";
      return `<div class="inbox-item"><div class="who">${r.m.name}</div><div>${r.id} · ${r.summary}</div>
        <div class="st-tag">${r.status}</div>
        <div class="btn-row">${b("PROVIDER_ACKNOWLEDGED", "Acknowledge")}${b("QUOTED", "Send quote")}${b("CONFIRMED", "Confirm")}${b("DECLINED", "Decline")}${r.status === "CONFIRMED" && !r.ofd ? `<button class="btn small ghost" data-ofd="${r.id}">Send "on the way"</button>` : ""}</div></div>`;
    }).join("");
    $("#inbox").querySelectorAll("[data-to]").forEach((btn) => (btn.onclick = () => {
      const r = state.requests.find((x) => x.id === btn.dataset.id); transition(r, btn.dataset.to, "merchant");
    }));
    $("#inbox").querySelectorAll("[data-ofd]").forEach((btn) => (btn.onclick = () => merchantUpdate(state.requests.find((x) => x.id === btn.dataset.ofd))));
  }

  // ---------- memory payoff: lost item in taxi ----------
  async function recovery() {
    log("agent", "intent: lost_item_in_taxi", { uses_memory: !!state.trip });
    if (!state.trip) return bot("I'm sorry. I don't have your taxi details saved. Do you have a receipt or the taxi number? I'll help you prepare the report.");
    log("memory", "recall taxi trip", { ...state.trip, provenance: "user_supplied" });
    bot("Don't worry. I have the trip details you gave me, so you won't need to remember them.");
    await typing(500);
    const c = card(`<div class="card-head"><div><h3>Lost item report</h3><div class="sub">Prepared from what you told me</div></div><span class="pill">Not filed yet</span></div>
      <div class="shares"><b>From your trip <span class="pill user" style="margin-left:4px">You told me</span></b>Taxi <b>${esc(state.trip.number)}</b> · ${esc(state.trip.route)} · started ${state.trip.started}</div>
      <div class="shares"><b>Missing: describe the bag</b><input class="field" id="bagIn" placeholder="e.g. black backpack, laptop inside" style="width:100%;margin-top:4px"></div>
      <div class="btn-row"><button class="btn small" id="bagGo">Prepare report</button></div>`);
    c.querySelector("#bagGo").onclick = async () => {
      const bag = c.querySelector("#bagIn").value.trim() || "black backpack, laptop inside";
      log("action", "recovery.report_prepared", { taxi: state.trip.number, item: bag, status: "PREPARED_NOT_FILED" });
      c.innerHTML = `<div class="card-head"><div><h3>Report ready</h3><div class="sub">${esc(bag)} · taxi ${esc(state.trip.number)} · ${esc(state.trip.route)} · ${state.trip.started}</div></div><span class="pill">Bag not recovered yet</span></div>
        <div class="btn-row"><button class="btn small">Contact official lost &amp; found</button><button class="btn small ghost">Copy report</button></div>
        <div class="foot"><span>Handoff to the official channel. I won't mark anything recovered until you tell me</span></div>`;
      await typing(); bot("I'll check in with you tomorrow morning about the bag, unless you tell me it's found.");
    };
  }

  // ---------- free text ----------
  $("#composer").onsubmit = async (e) => {
    e.preventDefault();
    const t = $("#input").value.trim(); if (!t) return;
    $("#input").value = ""; user(t);
    log("agent", "intent classify", { text: t });
    await typing();
    const q = t.toLowerCase();
    if (/pharm|medic|panadol|headache|sick/.test(q)) return pharmacies();
    if (/laundry|iron|shirt/.test(q)) return pharmacies("Laundry");
    if (/(left|lost|forgot).*(taxi|cab|car)|(taxi|cab).*(left|lost|forgot)/.test(q)) return recovery();
    if (/belt|bag/.test(q)) return bot(state.memory["Baggage belt"] ? `You told me: <b>${state.memory["Baggage belt"]}</b>.` : "You haven't told me a belt number yet. Check the arrivals screens.");
    if (/taxi number|which taxi/.test(q)) return bot(state.trip ? `Your taxi: <b>${state.trip.number}</b>, ${state.trip.route}, started ${state.trip.started}. <span class="pill user">You told me</span>` : "I don't have a taxi saved.");
    if (/taxi|metro|hotel|ride/.test(q)) { state.dest = state.dest || "Business Bay"; return rides(); }
    if (/lost|where am i/.test(q)) return stepAction("lost");
    bot("This demo is scripted. Try: <i>pharmacy</i>, <i>laundry</i>, <i>which belt?</i>, <i>taxi or metro</i>.");
  };

  // ---------- start ----------
  async function start() {
    chat.innerHTML = ""; journeyCard = null; state.requests = []; state.memory = {}; state.dest = null; state.trip = null;
    $("#log").innerHTML = ""; $("#inbox").innerHTML = `<div class="inbox-empty">No requests yet. Order something from a pharmacy mini-app.</div>`;
    renderMemory(); renderServices(); showTab("companion");
    $("#modePill").textContent = state.mode;
    if (state.mode === "Resident") {
      log("ui", "resident mode: no arrival flow");
      bot("Good afternoon. Nothing urgent today. Need anything nearby?");
      chips([["Find a pharmacy", () => { state.dest = "Business Bay"; pharmacies(); }], ["Laundry for tomorrow", () => { state.dest = "Business Bay"; pharmacies("Laundry"); }]]);
      return;
    }
    log("trigger", "flight.landed", { source: "demo_trigger", flight: D.flight.number, airport: "DXB T3", dedupe_key: "EK002:landed" });
    await sleep(300);
    card(`<div class="hero-hello">
      <div class="eyebrow">Dubai-io · Proactive <span class="pill trig">Demo trigger</span></div>
      <h1>Hello, visitor.</h1>
      <p>Welcome to Dubai. Your flight ${D.flight.number} has landed at DXB ${D.flight.terminal}. I'll walk you from the gate to your taxi or Metro, one step at a time.</p></div>`);
    await typing(700);
    bot("Where are you staying tonight?");
    chips(Object.keys(D.destinations).map((d) => [d, async () => {
      state.dest = d; remember("Staying in", d); await typing(); bot("Perfect. Let's go. Tap <b>Done</b> after each step, or <b>I'm lost</b> any time."); renderStep(0);
    }]));
  }

  document.querySelectorAll("#modeSeg button").forEach((b) => (b.onclick = () => {
    document.querySelectorAll("#modeSeg button").forEach((x) => x.classList.toggle("on", x === b));
    state.mode = b.dataset.mode; log("memory", "mode set by user", { mode: state.mode }); start();
  }));
  $("#restartBtn").onclick = start;
  $("#mobileLogBtn").onclick = () => { $("#backstage").classList.add("open"); $("#closeBackstage").style.display = "inline-block"; };
  $("#closeBackstage").onclick = () => $("#backstage").classList.remove("open");
  setInterval(() => ($("#clock").textContent = now()), 10000); $("#clock").textContent = now();
  start();
})();
