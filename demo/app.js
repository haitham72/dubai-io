// Dubai-io clickable demo. Scripted, no backend, no LLM.
// The "Under the hood" panel shows what a real build would do at each step.
(() => {
  const D = window.DEMO;
  const $ = (s) => document.querySelector(s);
  const chat = $("#chat");
  const state = { mode: "Visitor", memory: {}, requests: [], dest: null, step: 0, epoch: 0, cashRuns: 0 };
  let reqSeq = 4800;

  // ---------- Luna NLU seam (STUB, not wired) ----------
  // Phase 1 puts the language model behind the API proxy, never in this static page.
  // No keys here, and nothing is fetched. weight 0.0 = the regex router below always wins.
  const UNDERSTORY_URL = window.location.origin.replace("/index.html", "") + "/demo/luna.js";
  const NLU = { url: UNDERSTORY_URL, weight: 0.0 };

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
  // Long timers must not post into a chat the operator has since restarted.
  // Resolves true if the demo is still the same run, false if it was restarted.
  async function waitRun(ms, epoch) { await sleep(ms); return epoch === state.epoch; }

  // Fake media only: inline SVG placeholders, no network, no real photos.
  function fakeMedia(name) {
    const glyph = /receipt/i.test(name) ? "🧾" : /driver|id/i.test(name) ? "🧑‍✈️" : "📸";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="72" viewBox="0 0 96 72"><rect width="96" height="72" rx="10" fill="#F2F2F7"/><rect x=".5" y=".5" width="95" height="71" rx="9.5" fill="none" stroke="#D1D1D6"/><text x="48" y="42" text-anchor="middle" font-size="26">${glyph}</text><text x="48" y="62" text-anchor="middle" font-size="8" fill="#8E8E93" font-family="sans-serif">demo placeholder</text></svg>`;
    return { name, thumb: "data:image/svg+xml;utf8," + encodeURIComponent(svg) };
  }

  // Simulated payment trace. "0000" stands in for "no match"; anything else matches.
  // Never contacts anything; the result is a demo fixture, not a merchant or RTA event.
  function fakeTracePayment(last4) {
    const matched = /^\d{4}$/.test(last4) && last4 !== "0000";
    return { traceId: "TRC-" + (1000 + (parseInt(last4, 10) || 0) % 9000), matched, receiptRef: matched ? "RCPT-" + last4 : null };
  }

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
    log("tool", "transport.compare", { from: "DXB T3", to: state.dest, at: D.scenarioTime, sources: ["demo_fixture"], live: false });
    bot(`It's <b>${D.scenarioTime}</b>, so the Metro has stopped for the night — a taxi is the sensible option. The alternative is below if you want it.`);
    const c = card(`
      <div class="card-head"><div><h3>To ${state.dest}</h3><div class="sub">From DXB ${D.flight.terminal} at ${D.scenarioTime} · with luggage</div></div>
      <div class="pills"><span class="pill est">Demo estimate</span></div></div>
      <div class="opt"><div class="ico">🚕</div><div><b>Taxi — recommended</b><div class="line">${d.taxi.time} · ${d.taxi.price} · door to door, easy with bags. Metro stopped at 00:00, resumes 05:00</div></div><button class="btn small" data-r="taxi">Choose</button></div>
      <div class="opt"><div class="ico">🚇</div><div><b>Metro, Red Line — stopped</b><div class="line">${d.metro.time} · ${d.metro.price} · not running at ${D.scenarioTime}; luggage size rules apply when it runs</div></div><button class="btn small ghost" data-r="metro">Choose</button></div>
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
    bot("Follow the <b>Taxi</b> signs to the official rank outside arrivals. Use only the cream official airport taxis, not anyone offering rides inside.");
    await typing(600);
    const c = card(`<h3>Save your taxi details?</h3><div class="sub">Useful if you leave something in the car — the official report asks for exactly these</div>
      <div style="display:grid;gap:8px">
        <input id="taxiIn" placeholder="Plate number on the taxi" class="field">
        <input id="roofIn" placeholder="Roof colour (e.g. cream)" class="field">
        <label class="sub" style="margin:0">📸 Snap the receipt <input id="rcptIn" type="file" accept="image/*" style="margin-top:4px"></label>
        <button class="btn small" id="taxiSave">Save</button></div>`);
    c.querySelector("#taxiSave").onclick = async () => {
      const v = c.querySelector("#taxiIn").value.trim() || "12345";
      const roof = c.querySelector("#roofIn").value.trim() || "cream";
      const rcpt = (c.querySelector("#rcptIn").files[0] && c.querySelector("#rcptIn").files[0].name) || "receipt photo";
      state.trip = { number: v, roof, receipt: rcpt, route: `DXB T3 → ${state.dest}`, pickup: "DXB Terminal 3 taxi rank", started: D.scenarioTime };
      remember("Taxi trip", `Taxi ${v} · ${roof} roof · ${state.trip.route} · started ${state.trip.started} · ${rcpt} (you confirmed)`);
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
    chips([["Find a pharmacy", () => pharmacies()], ["I need a shirt pressed by 9 tomorrow", () => laundryDeadline()], ["Meet people", () => community()], ["What's on", () => tickets()], ["I'm fine, thanks", () => bot("Enjoy Dubai. I'm here whenever you need me.")]]);
  }

  // ---------- services: laundry with a deadline (fixed order, no quotes) ----------
  async function laundryDeadline() {
    await typing();
    const deadline = "09:00 tomorrow";
    remember("Deadline", `Shirt pressed by ${deadline} (meeting)`);
    remember("Staying in", `${state.dest} — carries into the request`);
    bot(`Got it — a shirt pressed by <b>${deadline}</b> for your meeting. Here are nearby laundries with fixed prices. Each row opens its own mini-app.`);
    await typing(400);
    const list = D.merchants.filter((m) => m.category === "Laundry").slice().sort((a, b) => a.distanceKm - b.distanceKm);
    log("tool", "registry.search", { category: "Laundry", area: state.dest, deadline, results: list.map((m) => m.id) });
    const rows = list.map((m) => `<div class="opt"><div class="ico" style="background:${m.color};color:#fff;font-size:12px;font-weight:700">${m.logo}</div>
      <div><b>${m.name}</b><div class="line">★ ${m.rating} · from ${m.priceFrom} · ${m.turnaround} · ${m.distance}</div></div><button class="btn small" data-m="${m.id}">Open</button></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>Laundries near ${state.dest}</h3><div class="sub">Closest + rating + price-from + turnaround · fixed prices, no bidding</div></div><span class="pill demo">Demo merchants</span></div>${rows}
      <div class="foot"><span>Ratings are merchant-submitted demo data, not verified</span></div>`);
    state.pendingDeadline = deadline;
    c.querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  async function laundryMerchantFlow(r) {
    await sleep(1500); if (r.status !== "SUBMITTED") return;
    r.readyTime = "10:00";
    transition(r, "ACCEPTED", "merchant");
    await typing(400);
    bot(`<span class="pill trig">Merchant update</span><br>${r.m.name} accepted at the fixed price, ready at <b>10:00</b> — but that <b>misses your 09:00 deadline</b>.`);
    chips([["Ask for an earlier slot", async () => {
      await typing();
      log("action", "deadline.conflict_escalation", { id: r.id, readyTime: "10:00", deadline: r.deadline, price_unchanged: true });
      bot(`Asking ${r.m.name} for an earlier slot. Same items, same fixed price — only the time changes.`);
      await sleep(1500);
      r.readyTime = "08:30";
      drawStatus(r); drawInbox();
      log("action", `${r.id} ready-time 10:00 → 08:30`, { actor: "merchant", source: "merchant_inbox" });
      bot(`<span class="pill trig">Merchant update</span><br>${r.m.name} confirmed <b>08:30</b> at the same fixed price. That meets your deadline — confirmed only because the shop confirmed.`);
      await sleep(1500); if (r.status === "ACCEPTED") transition(r, "READY", "merchant");
      await sleep(1500); if (r.status === "READY") transition(r, "COMPLETED", "merchant");
    }]]);
  }

  // ---------- community: opt-in groups, mutual join, demo fixtures ----------
  async function community() {
    await typing();
    remember("Interests", "AI engineering · Egyptian community");
    log("tool", "community.search", { area: state.dest || "Dubai Marina", interests: ["ai_engineering", "egyptian"], results: D.communities.map((g) => g.id) });
    bot("I can show <b>opt-in communities</b> around the Marina. These are <b>demo examples</b> — no real people. Joining always needs both sides to agree, and areas stay approximate.");
    await typing(400);
    const rows = D.communities.map((g, i) => `<div class="opt"><div class="ico">👥</div>
      <div><b>${g.name}</b><div class="line">${g.line || g.kind} · ${g.kind} · ${g.interested}</div><div class="line">${g.area} (approximate)</div>
      <div class="st-tag" id="joinState${i}">REQUESTABLE</div></div><button class="btn small" data-g="${i}" id="joinBtn${i}">Request to join</button></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>People &amp; communities near you</h3><div class="sub">Demo examples · mutual opt-in only</div></div><span class="pill demo">Demo data</span></div>${rows}
      <div class="foot"><span>No precise locations · no contact shared until both sides agree</span></div>`);
    c.querySelectorAll("[data-g]").forEach((b) => (b.onclick = () => requestJoin(+b.dataset.g, c)));
  }

  async function requestJoin(i, c) {
    const g = D.communities[i];
    const btn = c.querySelector(`#joinBtn${i}`); btn.disabled = true;
    c.querySelector(`#joinState${i}`).textContent = "REQUESTED";
    log("action", "community.join_requested", { group: g.id, actor: "user" });
    user(`Request to join ${g.name}`);
    await typing();
    bot(`Request sent to <b>${g.name}</b>. Nothing is shared until a group admin approves.`);
    await sleep(1800);
    c.querySelector(`#joinState${i}`).textContent = "ACCEPTED";
    log("trigger", "community.join_accepted", { group: g.id, actor: "group_admin (demo)", provenance: "demo_fixture" });
    bot(`<span class="pill trig">Community update</span><br><b>${g.name}</b> accepted you ✓. Their next meetup: Saturday, public café in Marina — say the word and I'll add it to your plan.`);
  }

  // ---------- parking memory: photo + user-confirmed spot, recall on demand ----------
  async function parkingFlow(q) {
    if (/where|find|recall|lost|forgot/.test(q) || (!/save|parked|spot|pillar/.test(q) && state.memory["Parking spot"])) {
      log("memory", "recall parking spot", { provenance: "user_supplied" });
      return bot(state.memory["Parking spot"]
        ? `Your car: <b>${state.memory["Parking spot"]}</b>. <span class="pill user">You told me</span>`
        : "I don't have a parking spot saved. Tap <b>Save my parking spot</b> after you park — a photo plus the level and bay you type.");
    }
    await typing();
    bot("Snap the pillar or sign, then type the level and bay. I only save what you confirm — no GPS guessing.");
    const c = card(`<div class="card-head"><div><h3>Save my parking spot</h3><div class="sub">Photo + your words, nothing inferred</div></div><span class="pill demo">Demo</span></div>
      <div style="display:grid;gap:8px">
        <label class="sub" style="margin:0">📸 Pillar photo <input id="parkPhoto" type="file" accept="image/*" style="margin-top:4px"></label>
        <input id="parkLevel" placeholder="Level (e.g. P2 Green)" class="field">
        <input id="parkBay" placeholder="Bay / pillar (e.g. 14)" class="field">
        <button class="btn small" id="parkSave">Save spot</button></div>`);
    c.querySelector("#parkSave").onclick = async () => {
      const file = c.querySelector("#parkPhoto").files[0];
      const photo = (file && file.name) || "pillar photo";
      const lvl = c.querySelector("#parkLevel").value.trim() || "P2 Green";
      const bay = c.querySelector("#parkBay").value.trim() || "14";
      remember("Parking spot", `${lvl} · bay ${bay} · ${photo} (you confirmed)`);
      state.photos.push({ name: photo, label: `parking ${lvl} bay ${bay}`, url: file ? URL.createObjectURL(file) : null, mine: true });
      log("action", "evidence.photo_saved", { name: photo, kind: "parking" });
      c.innerHTML = `<h3>Saved: ${esc(lvl)} · ${esc(bay)}</h3><div class="pills"><span class="pill user">You told me</span></div>`;
      await typing(); bot(`Saved. Ask "where is my car?" any time and I'll read it back.`);
    };
  }

  // ---------- departure: checklist + VAT official handoff, nothing filed ----------
  async function departure() {
    await typing();
    log("trigger", "trip.departure_prep", { source: "user_confirmed" });
    bot(`<span class="pill trig">Proactive</span><br>Flying home tomorrow? Here's your checkout and airport plan. Anything tax-free in your bags — say <b>tax refund</b> before you check in.`);
    departureCard();
  }

  function departureCard() {
    const dc = card(`<div class="card-head"><div><h3>Going home · DXB</h3><div class="sub">Draft checklist, not booked</div></div><span class="pill demo">Demo data</span></div>
      <div class="shares"><b>Before checkout</b>Confirm hotel checkout time · pack documents</div>
      <div class="shares"><b>Flight</b>Check flight + terminal with the airline — I can't track live flights</div>
      <div class="shares"><b>Transport</b>Compare taxi / Metro for your departure time</div>
      <div class="shares"><b>VAT refund</b>Planet validation <b>before</b> checking in bags that need inspection</div>
      <div class="btn-row"><button class="btn small" id="depVat">Tax refund guide</button><button class="btn small ghost" id="depRide">Get me to DXB</button></div>`);
    dc.querySelector("#depVat").onclick = () => vatGuide();
    dc.querySelector("#depRide").onclick = () => { state.dest = state.dest || "Business Bay"; rides(); };
  }

  async function vatGuide() {
    user("Tax refund guide"); await typing();
    log("tool", "official.handoff", { topic: "tourist_vat_refund", url: D.official.vatRefund });
    card(`<div class="card-head"><div><h3>Tourist VAT refund</h3><div class="sub">Official process, not filed by me</div></div><span class="pill">Official guidance link</span></div>
      <div class="shares"><b>Eligibility</b>Minimum AED 250 per purchase · validated within 90 days · you get 85% of VAT minus AED 4.80 per tag</div>
      <div class="shares"><b>At the airport</b>Original passport + eligible goods + departure evidence · validate at Planet <b>before</b> check-in</div>
      <div class="btn-row"><a class="btn small" href="${D.official.vatRefund}" target="_blank" rel="noopener">Open Federal Tax Authority guide</a></div>
      <div class="foot"><span>I explain the official steps. Validation happens at the Planet counter, not here.</span></div>`);
  }

  // ---------- day plan: editable draft, selective change, suggested ≠ booked ----------
  const PLAN_FIXTURES = {
    morning: "Old Dubai photo walk (Al Fahidi + creek)",
    lunch: "Café near the morning stop",
    evening: "Modern skyline viewpoint"
  };
  async function dayplan(swapEvening) {
    await typing();
    if (swapEvening) {
      log("agent", "itinerary.edit", { scope: "evening_only", preserved: ["morning", "lunch"] });
      PLAN_FIXTURES.evening = "Quiet marina walk + early night";
      bot(`Updated — morning and lunch untouched, evening swapped for something quieter.`);
    } else {
      log("tool", "itinerary.draft", { area: state.dest || "Dubai", sources: ["demo_fixture"] });
      bot(`Here's a draft for tomorrow — <b>suggested, not booked</b>. Nothing reserves anything.`);
    }
    card(`<div class="card-head"><div><h3>Today's plan</h3><div class="sub">Draft, not booked</div></div><span class="pill demo">Demo data</span></div>
      <div class="shares"><b>Morning</b>${PLAN_FIXTURES.morning}</div>
      <div class="shares"><b>Lunch</b>${PLAN_FIXTURES.lunch}</div>
      <div class="shares"><b>Evening</b>${PLAN_FIXTURES.evening}</div>
      <div class="btn-row"><button class="btn small ghost" id="planSwap">Swap the evening</button></div>
      <div class="foot"><span>One change never wipes the rest of the plan</span></div>`)
      .querySelector("#planSwap").onclick = () => dayplan(true);
  }

  // ---------- tickets (graphic mock): discover → seat art → approval → graphic ticket ----------
  // Payment + booking happen on the provider site. CONFIRMED only on provider event.
  function eventArt(e, seed) {
    const [a, b] = e.hue;
    return `<svg viewBox="0 0 320 120" style="width:100%;border-radius:12px;display:block" role="img" aria-label="${esc(e.name)} art (demo)">
      <defs><linearGradient id="tg${e.id}${seed}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>
      <rect width="320" height="120" fill="url(#tg${e.id}${seed})"/>
      <circle cx="260" cy="30" r="40" fill="#ffffff" opacity="0.12"/><circle cx="40" cy="100" r="55" fill="#ffffff" opacity="0.08"/>
      <text x="16" y="58" font-size="20" font-weight="700" fill="#fff" font-family="-apple-system,Segoe UI,sans-serif">${esc(e.name)}</text>
      <text x="16" y="80" font-size="12" fill="#ffffff" opacity="0.85" font-family="-apple-system,Segoe UI,sans-serif">${esc(e.venue)} · ${esc(e.date)}</text>
      <text x="16" y="100" font-size="11" fill="#ffffff" opacity="0.7" font-family="-apple-system,Segoe UI,sans-serif">Demo art · from ${esc(e.priceFrom)}</text></svg>`;
  }

  async function tickets() {
    await typing();
    log("tool", "events.search", { area: state.dest || "Dubai", results: D.events.map((e) => e.id) });
    bot(`Two demo events near you. Pick one to see the graphic ticket flow — booking and payment stay on the provider's site.`);
    const rows = D.events.map((e) => `<div class="opt" style="display:block"><div style="margin-bottom:8px">${eventArt(e, "list")}</div>
      <div style="display:flex;justify-content:space-between;align-items:center"><div><b>${e.name}</b><div class="line">${e.venue} · ${e.date} · from ${e.priceFrom}</div></div>
      <button class="btn small" data-e="${e.id}">Open</button></div></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>Events near you</h3><div class="sub">Suggested, not booked</div></div><span class="pill demo">Demo data</span></div>${rows}`);
    c.querySelectorAll("[data-e]").forEach((b) => (b.onclick = () => ticketSeats(b.dataset.e)));
  }

  async function ticketSeats(id) {
    const e = D.events.find((x) => x.id === id);
    user(e.name); await typing();
    const seats = e.tiers.map((t, i) => {
      const x = 40 + i * 90;
      return `<g data-tier="${i}" style="cursor:pointer"><rect x="${x}" y="18" width="76" height="52" rx="10" fill="${i === 0 ? "#0A9CC2" : "#F2F2F7"}" stroke="#0A9CC2"/>
        <text x="${x + 38}" y="40" text-anchor="middle" font-size="11" font-weight="600" fill="${i === 0 ? "#fff" : "#0A9CC2"}" font-family="-apple-system,Segoe UI,sans-serif">${esc(t.name)}</text>
        <text x="${x + 38}" y="58" text-anchor="middle" font-size="11" fill="${i === 0 ? "#fff" : "#3C3C43"}" font-family="-apple-system,Segoe UI,sans-serif">AED ${t.price}</text></g>`;
    }).join("");
    const c = card(`<div class="card-head"><div><h3>${e.name}</h3><div class="sub">${e.venue} · ${e.date} · pick a tier</div></div><span class="pill demo">Demo art</span></div>
      <div style="margin-bottom:6px">${eventArt(e, "seat")}</div>
      <svg id="seatmap" viewBox="0 0 320 88" style="width:100%">${seats}<text x="160" y="84" text-anchor="middle" font-size="10" fill="#8E8E93" font-family="-apple-system,Segoe UI,sans-serif">STAGE ↑ · graphic seat map, not to scale</text></svg>
      <div class="btn-row"><button class="btn small" id="tierGo">Continue</button></div>`);
    let pick = 0;
    const paint = () => {
      c.querySelectorAll("[data-tier]").forEach((g, k) => {
        const on = k === pick;
        g.querySelector("rect").setAttribute("fill", on ? "#0A9CC2" : "#F2F2F7");
        const [name, price] = g.querySelectorAll("text");
        name.setAttribute("fill", on ? "#fff" : "#0A9CC2");
        price.setAttribute("fill", on ? "#fff" : "#3C3C43");
      });
    };
    c.querySelectorAll("[data-tier]").forEach((g) => (g.onclick = () => { pick = +g.dataset.tier; paint(); log("ui", "ticket tier selected", { tier: e.tiers[pick].name }); }));
    c.querySelector("#tierGo").onclick = () => ticketApproval(e, e.tiers[pick]);
  }

  function ticketApproval(e, tier) {
    const c = card(`<div class="card-head"><div><h3>Request ${tier.name} · AED ${tier.price}?</h3><div class="sub">${e.name} · ${e.date}</div></div><span class="pill demo">Demo provider</span></div>
      <div class="shares"><b>Will be shared</b>Your first name · contact via in-app chat · tier ${esc(tier.name)}</div>
      <div class="shares"><b>Payment</b>Happens on the provider's site — Dubai-io never charges</div>
      <div class="foot"><span>Confirmed only when the provider confirms. No fake tickets.</span></div>
      <div class="btn-row"><button class="btn small" data-a="ok">Approve and send</button><button class="btn small ghost" data-a="no">Cancel</button></div>`);
    log("action", "ticket DRAFT → AWAITING_APPROVAL", { event: e.id, tier: tier.name, price: tier.price });
    c.querySelector('[data-a="ok"]').onclick = async () => {
      c.querySelectorAll("button").forEach((x) => (x.disabled = true));
      const ref = "TKT-" + Math.floor(1000 + Math.random() * 9000);
      log("action", `ticket SUBMITTED`, { event: e.id, tier: tier.name });
      c.innerHTML = `<h3>Sent to provider…</h3><div class="sub">Waiting for their confirmation — nothing is booked yet.</div><span class="pill">Status: sent</span>`;
      await sleep(1800);
      log("trigger", "ticket ACCEPTED", { ref, actor: "provider (demo)", provenance: "demo_fixture" });
      c.innerHTML = `<div style="border:2px dashed #0A9CC2;border-radius:14px;padding:4px">${eventArt(e, "tix")}</div>
        <div class="card-head" style="margin-top:8px"><div><h3>${tier.name} · AED ${tier.price}</h3><div class="sub">${e.venue} · ${e.date} · ref ${ref}</div></div><span class="pill trig">ACCEPTED</span></div>
        <div class="foot"><span>Confirmed because the provider confirmed · pay on their site</span></div>
        <div class="btn-row"><button class="btn small ghost" id="tixRem">Remind me day before</button></div>`;
      c.querySelector("#tixRem").onclick = async () => {
        log("action", "scheduler.propose_reminder", { what: e.name, when: "day before", status: "SET" });
        bot(`Reminder set: I'll nudge you the day before <b>${e.name}</b>.`);
      };
      await typing(); bot(`<span class="pill trig">Provider update</span><br>Your <b>${tier.name}</b> ticket is confirmed (ref ${ref}). See you there.`);
    };
    c.querySelector('[data-a="no"]').onclick = () => { c.innerHTML = `<h3>Cancelled</h3><div class="sub">Nothing was sent.</div>`; };
  }

  // ---------- prayer times (mock): live Aladhan seam, fixture fallback ----------
  async function prayer() {
    await typing();
    let times = D.prayerFixtures.times, live = false, asOf = "demo fixtures";
    try {
      const ctl = new AbortController();
      const to = setTimeout(() => ctl.abort(), 3500);
      const r = await fetch("https://api.aladhan.com/v1/timingsByCity?city=Dubai&country=UAE&method=16", { signal: ctl.signal });
      clearTimeout(to);
      const j = await r.json();
      if (j && j.data && j.data.timings) {
        times = { Fajr: j.data.timings.Fajr.slice(0, 5), Sunrise: j.data.timings.Sunrise.slice(0, 5), Dhuhr: j.data.timings.Dhuhr.slice(0, 5), Asr: j.data.timings.Asr.slice(0, 5), Maghrib: j.data.timings.Maghrib.slice(0, 5), Isha: j.data.timings.Isha.slice(0, 5) };
        live = true; asOf = "Aladhan, just now";
      }
    } catch { /* offline or blocked → fixtures (the designed fallback) */ }
    log("tool", live ? "prayer.live" : "prayer.fixture_fallback", { as_of: asOf });
    const order = ["Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha"];
    const nowHM = now();
    const next = order.find((p) => times[p] > nowHM) || "Fajr";
    if (!live) bot(`Prayer times for Dubai <b>(demo fixtures</b> — live lookup plugs in at build). Third-party calculation, not official UAE time.`);
    else bot(`Prayer times for Dubai — live lookup, <b>${asOf}</b>. Third-party calculation, not official UAE time.`);
    const rows = order.map((p) => `<div class="opt"><div class="ico">${p === next ? "🕌" : "·"}</div>
      <div><b>${p}${p === next ? " — next" : ""}</b><div class="line">${times[p]}</div></div>
      ${p === next ? `<button class="btn small" id="prayRem">Remind me</button>` : ""}</div>`).join("");
    const c = card(`<div class="card-head"><div><h3>Prayer times · Dubai</h3><div class="sub">${live ? "Live · " + asOf : "Demo fixtures"}</div></div><span class="pill ${live ? "" : "demo"}">${live ? "Third-party calc" : "Demo data"}</span></div>${rows}
      <div class="btn-row"><button class="btn small ghost" id="prayQibla">Qibla direction</button><button class="btn small ghost" id="prayNear">Simulate: near a mosque</button></div>`);
    const rb = c.querySelector("#prayRem");
    if (rb) rb.onclick = () => { log("action", "scheduler.propose_reminder", { what: next + " prayer", status: "SET" }); bot(`Reminder set for <b>${next}</b> (${times[next]}). Respects quiet hours — tell me to mute nights and I will.`); };
    c.querySelector("#prayQibla").onclick = () => qibla();
    c.querySelector("#prayNear").onclick = () => nearMosque();
  }

  // ---------- qibla compass (mock): math bearing, optional live heading ----------
  function qiblaBearing(lat1, lng1) {
    const lat2 = 21.4225, lng2 = 39.8262, rad = Math.PI / 180;
    const dLng = (lng2 - lng1) * rad;
    const y = Math.sin(dLng);
    const x = Math.cos(lat1 * rad) * Math.tan(lat2 * rad) - Math.sin(lat1 * rad) * Math.cos(dLng);
    return ((Math.atan2(y, x) / rad) + 360) % 360;
  }

  // opts.trigger: fired from the operator panel → no echoed user bubble, one trigger-labelled message + the widget.
  async function qibla(opts = {}) {
    if (!opts.trigger) { user("Qibla direction"); await typing(); }
    const bearing = Math.round(qiblaBearing(25.2048, 55.2708));
    log("tool", "qibla.bearing", { from: "Dubai Marina (demo)", bearing, provenance: "estimate" });
    if (opts.trigger) bot(`<span class="pill trig">Demo trigger</span><br>Qibla bearing <b>${bearing}° WSW</b> — an estimate. Tap <b>Enable live compass</b> below for a live needle.`);
    else bot(`From the Marina the qibla is about <b>${bearing}°</b> (WSW) — an estimate, not a fatwa. Hold the phone flat and enable the compass for a live needle.`);
    const c = card(`<div class="card-head"><div><h3>Qibla compass</h3><div class="sub">~${bearing}° from Marina · estimate</div></div><span class="pill demo">Demo widget</span></div>
      <svg id="qdial" viewBox="0 0 200 200" style="width:70%;margin:0 auto;display:block">
        <circle cx="100" cy="100" r="90" fill="#F2F2F7"/><circle cx="100" cy="100" r="90" fill="none" stroke="#E5E5EA"/>
        <text x="100" y="24" text-anchor="middle" font-size="14" font-weight="700" font-family="-apple-system,Segoe UI,sans-serif">N</text>
        <g id="qneedle" transform="rotate(${bearing} 100 100)"><polygon points="100,30 110,110 100,100 90,110" fill="#0A9CC2"/>
        <text x="100" y="52" text-anchor="middle" font-size="11" font-weight="700" fill="#fff" font-family="-apple-system,Segoe UI,sans-serif">🕋</text></g>
        <circle cx="100" cy="100" r="8" fill="#0A9CC2"/></svg>
      <div class="btn-row"><button class="btn small ghost" id="qLive">Enable live compass</button></div>
      <div class="foot"><span>Needs motion permission · foreground only · manual bearing always shown</span></div>`);
    c.querySelector("#qLive").onclick = async () => {
      try {
        if (typeof DeviceOrientationEvent !== "undefined" && DeviceOrientationEvent.requestPermission) {
          const res = await DeviceOrientationEvent.requestPermission();
          if (res !== "granted") throw new Error("denied");
        }
        const needle = c.querySelector("#qneedle");
        const handler = (ev) => {
          const h = ev.webkitCompassHeading != null ? ev.webkitCompassHeading : (ev.alpha != null ? 360 - ev.alpha : null);
          if (h == null) return;
          needle.setAttribute("transform", `rotate(${bearing - h} 100 100)`);
        };
        window.addEventListener("deviceorientation", handler, { once: false });
        log("tool", "qibla.live_heading", { source: "device_sensor (foreground)" });
        bot(`Live needle on — rotate and the dial follows your heading.`);
      } catch {
        log("tool", "qibla.compass_denied", { fallback: "manual_bearing" });
        bot(`Compass unavailable — the manual bearing (~${bearing}° WSW) above still works.`);
      }
    };
  }

  // ---------- mosque proximity (mock): simulated trigger, never claimed GPS ----------
  async function nearMosque() {
    user("Simulate: near a mosque"); await typing();
    log("trigger", "geo.mosque_nearby", { source: "demo_trigger", mosque: "marina", dedupe_key: "geo:marina-mosque" });
    bot(`<span class="pill trig">Demo trigger</span><br>This is a <b>simulated</b> proximity ping — the demo can't detect where you are.`);
    const rows = D.mosques.map((m) => `<div class="opt"><div class="ico">🕌</div>
      <div><b>${m.name}</b><div class="line">${m.area} · ${m.distance} (demo estimate)</div></div></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>Mosques near you</h3><div class="sub">Demo fixtures · you tell me where you are</div></div><span class="pill demo">Demo data</span></div>${rows}
      <div class="btn-row"><button class="btn small ghost" id="gmPrayer">Prayer times</button><button class="btn small ghost" id="gmQibla">Qibla</button></div>`);
    c.querySelector("#gmPrayer").onclick = () => prayer();
    c.querySelector("#gmQibla").onclick = () => qibla();
  }

  // ---------- operator trigger panel: deterministic scenes, deduplicated ----------
  // The backstage chips post {kind:"app.trigger"} to THIS window. Only same-window messages
  // are honoured (a mini-app frame has a different source and is blocked by the bridge scopes).
  // No LLM and no background geofencing: an operator tap stands in for the scheduler/outbox.
  const TRIGGER_DEDUPE_MS = 2500;
  const TRIGGERS = {
    "geo.mosque_nearby": { dedupe_key: "geo:marina-mosque", run: () => sceneMosque() },
    "trip.event_tomorrow": { dedupe_key: "trip:event-tomorrow", run: () => sceneEventTomorrow() },
    "trip.departure_am": { dedupe_key: "trip:departure-am", run: () => sceneDepartureAm() },
    "qibla.now": { dedupe_key: "qibla:now", run: () => qibla({ trigger: true }) }
  };

  function installTriggers() {
    const wrap = $("#trigChips"); wrap.innerHTML = "";
    Object.keys(TRIGGERS).forEach((kind) => {
      const b = document.createElement("button");
      b.className = "chip"; b.textContent = kind;
      b.onclick = () => window.postMessage({ v: 1, kind: "app.trigger", payload: { kind, dedupe_key: TRIGGERS[kind].dedupe_key } }, "*");
      wrap.append(b);
    });
  }

  window.addEventListener("message", (e) => {
    if (e.source !== window) return;
    const m = e.data;
    if (!m || m.v !== 1 || m.kind !== "app.trigger" || !m.payload) return;
    fireTrigger(m.payload.kind, m.payload.dedupe_key);
  });

  function fireTrigger(kind, dedupeKey) {
    const t = TRIGGERS[kind];
    if (!t || dedupeKey !== t.dedupe_key) { log("security", "unknown trigger dropped", { kind, dedupe_key: dedupeKey || null }); return; }
    const at = Date.now();
    if (state.fired[dedupeKey] && at - state.fired[dedupeKey] < TRIGGER_DEDUPE_MS) {
      log("security", "duplicate trigger dropped", { kind, dedupe_key: dedupeKey, window_ms: TRIGGER_DEDUPE_MS });
      return;
    }
    state.fired[dedupeKey] = at;
    log("trigger", kind, { dedupe_key: dedupeKey, source: "demo_trigger", quiet_hours: D.triggerFixtures.quietHours + " respected" });
    showTab("companion");
    t.run();
  }

  async function sceneMosque() {
    const m = D.mosques.find((x) => x.id === "marina");
    const times = D.prayerFixtures.times, order = ["Fajr", "Dhuhr", "Asr", "Maghrib", "Isha"];
    const next = order.find((p) => times[p] > now()) || "Fajr";
    await typing(300);
    bot(`<span class="pill trig">Demo trigger</span><br><b>${m.name}</b> is about ${m.distance} away (demo estimate). Bring wudu? Next prayer: <b>${next} ${times[next]}</b> (demo fixture).`);
    const c = card(`<div class="card-head"><div><h3>Mosque near you</h3><div class="sub">${m.name} · ${m.area} · ${m.distance} (demo estimate)</div></div><span class="pill demo">Demo data</span></div>
      <div class="shares"><b>Wudu reminder</b><span id="wuduState">pending · tap to set it</span></div>
      <div class="btn-row"><button class="btn small" id="wuduSet">Set wudu reminder</button><button class="btn small ghost" id="trigQibla">Qibla</button></div>
      <div class="foot"><span>Simulated proximity ping. The demo can't detect where you are.</span></div>`);
    c.querySelector("#wuduSet").onclick = (ev) => {
      ev.target.disabled = true;
      log("action", "scheduler.propose_reminder", { what: "wudu before " + next, status: "SET", dedupe_key: "wudu:" + next });
      c.querySelector("#wuduState").textContent = `set · before ${next} ${times[next]}`;
    };
    c.querySelector("#trigQibla").onclick = () => qibla();
  }

  async function sceneEventTomorrow() {
    const e = D.events[0], ref = D.triggerFixtures.eventRef;
    await typing(300);
    bot(`<span class="pill trig">Demo trigger</span><br>Reminder: <b>${e.name}</b> tickets tomorrow. Bring your ticket ref + photo ID.`);
    const c = card(`<div class="card-head"><div><h3>${e.name}</h3><div class="sub">${e.venue} · ${e.date} · ticket ref ${ref}</div></div><span class="pill demo">Demo data</span></div>
      <div class="shares"><b>Bring</b>Ticket ref ${ref} (demo fixture) · photo ID</div>
      <div class="btn-row"><button class="btn small" id="trigRide">Get me there</button></div>`);
    c.querySelector("#trigRide").onclick = () => { state.dest = state.dest || "Business Bay"; user("Get me there"); rides(); };
  }

  async function sceneDepartureAm() {
    const f = D.triggerFixtures;
    await typing(300);
    bot(`<span class="pill trig">Demo trigger</span><br>Good morning. Your flight departs <b>${f.flightTime}</b> (demo fixture, I can't track live flights). VAT: validate before your <b>${f.vatCutoff}</b> check-in.<br>
      <span class="pill est">Quiet hours ${f.quietHours} respected: queued for 07:00</span>`);
    departureCard();
  }

  // ---------- photo search (mock): keyword over your evidence list, embeddings later ----------
  function photoSearch(q) {
    const stop = /search|find|show|me|my|photos?|images?|pictures?|the|a|please/g;
    const keys = q.toLowerCase().replace(stop, "").split(/[^a-z0-9]+/).filter((w) => w.length > 1);
    log("tool", "evidence.search", { keys, mode: "keyword (embedding stub)", count: state.photos.length });
    const hits = !keys.length ? state.photos : state.photos.filter((p) => keys.some((k) => (p.name + " " + p.label).toLowerCase().includes(k)));
    if (!hits.length) return bot(`No photos match "<b>${esc(keys.join(" "))}</b>" in your ${state.photos.length} saved photos. Try "parking" or "all photos".`);
    bot(`Found <b>${hits.length}</b> photo${hits.length > 1 ? "s" : ""} by keyword — embedding search plugs in later.`);
    const grid = hits.map((p) => `<div style="flex:1 1 40%;background:#F2F2F7;border-radius:12px;overflow:hidden">
      ${p.url ? `<img src="${p.url}" alt="${esc(p.label)}" style="width:100%;height:90px;object-fit:cover;display:block" onerror="this.style.display='none'">` : `<div style="height:90px;display:flex;align-items:center;justify-content:center;font-size:28px">📸</div>`}
      <div style="padding:6px 8px;font-size:11px"><b>${esc(p.name)}</b><br><span style="color:#8E8E93">${esc(p.label)}</span>
      <span class="pill ${p.mine ? "user" : "demo"}" style="margin-left:4px">${p.mine ? "You added" : "Demo stock"}</span></div></div>`).join("");
    card(`<div class="card-head"><div><h3>Photo results</h3><div class="sub">Keyword match · "${esc(keys.join(" ") || "all")}"</div></div><span class="pill demo">Mock search</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">${grid}</div>`);
  }

  // ---------- services: aggregator → per-merchant mini-apps ----------
  async function pharmacies(cat = "Pharmacy") {
    await typing();
    const list = D.merchants.filter((m) => m.category === cat).slice().sort((a, b) => (a.distanceKm || 9) - (b.distanceKm || 9));
    log("tool", "registry.search", { category: cat, area: state.dest || "Business Bay", results: list.map((m) => m.id) });
    if (!list.length) return emptyCategory(cat);
    const rows = list.map((m) => `<div class="opt"><div class="ico" style="background:${m.color};color:#fff;font-size:12px;font-weight:700">${m.logo}</div>
      <div><b>${m.name}</b><div class="line">${m.rating ? `★ ${m.rating} · ` : ""}${m.priceFrom ? `from ${m.priceFrom} · ` : ""}${m.turnaround ? `${m.turnaround} · ` : ""}${m.distance}</div><div class="line">${m.line}</div></div><button class="btn small" data-m="${m.id}">Open</button></div>`).join("");
    const c = card(`<div class="card-head"><div><h3>${cat} near ${state.dest || "you"}</h3><div class="sub">Each one opens its own mini-app · fixed prices</div></div><span class="pill demo">Demo merchants</span></div>${rows}
      <div class="foot"><span>Ratings and prices are merchant-submitted demo data, not verified</span></div>`);
    c.querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
  }

  // ---------- platform: a shop joins from a price-list photo ----------
  function emptyCategory(cat) {
    const c = card(`<div class="card-head"><div><h3>No ${cat.toLowerCase()} merchants yet</h3><div class="sub">New shops join from a photo of their price list</div></div><span class="pill demo">Demo</span></div>
      <div class="btn-row"><button class="btn small" id="onbGo">Simulate: add a shop from a price-list photo</button></div>`);
    c.querySelector("#onbGo").onclick = () => onboardingSim(cat, c);
  }

  async function onboardingSim(cat, c) {
    user("Add a shop from a price-list photo");
    await typing();
    log("action", "onboarding.photo_received", { category: cat, source: "demo_fixture" });
    c.innerHTML = `<h3>Reading price list…</h3><div class="sub">Extracting items and fixed prices (demo)</div>`;
    await sleep(1200);
    const draft = { name: cat === "Laundry" ? "Deira Star Laundry" : `New ${cat} Shop`, items: cat === "Laundry" ? "Shirt press AED 6 · Suit AED 25 · Same-day" : "Fixed price list (demo)" };
    log("action", "onboarding.draft_ready", draft);
    c.innerHTML = `<div class="card-head"><div><h3>${draft.name}</h3><div class="sub">${draft.items}</div></div><span class="pill">Operator review</span></div>
      <div class="sub">AI-generated mini-app preview is ready. Nothing goes live without operator approval.</div>
      <div class="btn-row"><button class="btn small" id="onbApprove">Operator: approve and publish</button></div>`;
    c.querySelector("#onbApprove").onclick = async () => {
      log("action", "onboarding.approved", { shop: draft.name, actor: "operator" });
      D.merchants.push({ id: "deirastar", name: draft.name, category: cat, line: draft.items, distance: "0.4 km", distanceKm: 0.4, rating: "New", priceFrom: "AED 6", turnaround: "Same-day", color: "#3E6B48", logo: "DS", manifest: { version: "1.0.0", entry: "miniapps/marinaexpress.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" } });
      c.innerHTML = `<h3>${draft.name} is live ✓</h3><div class="sub">Approved by the operator. It now appears in ${cat.toLowerCase()} results.</div>`;
      renderServices(cat);
      await typing(); bot(`A new shop just joined from a photo and passed operator review. It's now in your ${cat.toLowerCase()} results — same conversation, same approval rules.`);
    };
  }

  function renderServices(cat = "Pharmacy") {
    $("#cats").innerHTML = D.categories.map((c) => `<button class="cat ${c === cat ? "active" : ""}" data-c="${c}">${c}</button>`).join("");
    $("#cats").querySelectorAll("[data-c]").forEach((b) => (b.onclick = () => renderServices(b.dataset.c)));
    const list = D.merchants.filter((m) => m.category === cat).slice().sort((a, b) => (a.distanceKm || 9) - (b.distanceKm || 9));
    $("#merchantList").innerHTML = list.length ? list.map((m) => `<div class="merchant"><div class="logo" style="background:${m.color}">${m.logo}</div>
      <div><b>${m.name}</b><div class="line">${m.rating ? `★ ${m.rating} · ` : ""}${m.priceFrom ? `from ${m.priceFrom} · ` : ""}${m.distance}</div><div class="line">${m.line}</div><span class="pill demo">Demo merchant</span></div>
      <button class="btn small" data-m="${m.id}">Open</button></div>`).join("")
      : `<p class="empty">No ${cat.toLowerCase()} merchants onboarded yet.</p><button class="btn small" id="svcOnb">Add a shop from a price-list photo (demo)</button>`;
    $("#merchantList").querySelectorAll("[data-m]").forEach((b) => (b.onclick = () => openMini(b.dataset.m)));
    const ob = $("#svcOnb"); if (ob) ob.onclick = () => { showTab("companion"); onboardingSim(cat, card("")); };
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
  const FLOW = ["SUBMITTED", "ACCEPTED", "READY", "COMPLETED"];
  const ALLOWED = {
    AWAITING_APPROVAL: ["SUBMITTED", "CANCELLED"],
    SUBMITTED: ["ACCEPTED", "DECLINED", "CANCELLED"],
    ACCEPTED: ["READY", "DECLINED", "CANCELLED"],
    READY: ["COMPLETED", "CANCELLED"],
    COMPLETED: []
  };
  const LABEL = { SUBMITTED: "Sent to merchant", ACCEPTED: "Merchant accepted", READY: "Ready for pickup", COMPLETED: "Completed" };

  function approval(m, kind, p) {
    const deadline = state.pendingDeadline; state.pendingDeadline = null;
    const shares = [`Item list`, `${m.category === "Laundry" ? "Pickup" : "Delivery"} area: ${state.dest || "Business Bay"}`, "Contact: in-app chat (phone hidden)"];
    const items = (p.items || []).map((i) => `${i.qty}× ${esc(i.name)}`).join(", ") || esc(p.summary || "");
    const c = card(`<div class="card-head"><div><h3>Send to ${m.name}?</h3><div class="sub">${items}</div></div><span class="pill demo">Demo merchant</span></div>
      <div class="shares"><b>Will be shared</b>${shares.join(" · ")}</div>
      ${p.estimate ? `<div class="shares"><b>Fixed total</b>AED ${p.estimate.toFixed(2)} · price unchanged by the merchant</div>` : ""}
      ${deadline ? `<div class="shares"><b>Deadline</b>Ready by ${deadline}</div>` : ""}
      <div class="foot"><span>The mini-app can only ask. This card waits for your tap.</span></div>
      <div class="btn-row"><button class="btn small" data-a="ok">Approve and send</button><button class="btn small ghost" data-a="no">Cancel</button></div>`);
    log("action", "request DRAFT → AWAITING_APPROVAL", { merchant: m.id, kind, deadline: deadline || null });
    c.querySelector('[data-a="ok"]').onclick = () => { c.querySelectorAll("button").forEach((x) => (x.disabled = true)); createRequest(m, kind, p, items, deadline); };
    c.querySelector('[data-a="no"]').onclick = () => { c.innerHTML = `<h3>Cancelled</h3><div class="sub">Nothing was sent.</div>`; log("action", "request cancelled by user before send"); };
  }

  function createRequest(m, kind, p, summary, deadline) {
    const r = { id: "REQ-" + ++reqSeq, m, kind, p, summary, deadline: deadline || null, readyTime: null, status: "AWAITING_APPROVAL", ref: null, el: null };
    state.requests.push(r);
    r.el = card(""); transition(r, "SUBMITTED", "user");
    if (m.category === "Laundry" && deadline) laundryMerchantFlow(r);
    else if ($("#autoMerchant").checked) autoMerchant(r);
  }

  function transition(r, to, actor) {
    if (!(ALLOWED[r.status] || []).includes(to)) { log("security", `illegal transition ${r.status} → ${to} rejected`, { id: r.id, actor }); return; }
    log("action", `${r.id} ${r.status} → ${to}`, { actor, source: actor === "merchant" ? "merchant_inbox" : "user_tap" });
    r.status = to;
    if (to === "COMPLETED") r.ref = r.m.logo + "-" + Math.floor(1000 + Math.random() * 9000);
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
      : FLOW.map((s, k) => `<div class="st ${k < idx ? "done" : k === idx ? "now" : ""}"><i></i>${LABEL[s]}${s === "COMPLETED" && r.ref ? ` · ref ${r.ref}` : ""}</div>`).join("");
    r.el.innerHTML = `<div class="card-head"><div><h3>${r.m.name}</h3><div class="sub">${r.summary}</div></div><span class="pill">${r.id}</span></div>
      ${r.deadline ? `<div class="shares"><b>Deadline</b>Ready by ${r.deadline}</div>` : ""}
      ${r.readyTime ? `<div class="shares"><b>Merchant-confirmed ready time</b>${r.readyTime} · fixed price unchanged</div>` : ""}
      <div class="status-track">${track}</div>
      <div class="foot"><span>Status changes only when the merchant or you act</span></div>`;
    scroll();
  }

  async function autoMerchant(r) {
    await sleep(1500); if (r.status === "SUBMITTED") transition(r, "ACCEPTED", "merchant");
    await sleep(2000); if (r.status === "ACCEPTED") transition(r, "READY", "merchant");
    await sleep(1500); if (r.status === "READY") transition(r, "COMPLETED", "merchant");
  }

  function drawInbox() {
    const open = state.requests.filter((r) => r.status !== "AWAITING_APPROVAL");
    if (!open.length) return;
    $("#inbox").innerHTML = open.slice().reverse().map((r) => {
      const b = (to, label) => (ALLOWED[r.status] || []).includes(to) && to !== "CANCELLED"
        ? `<button class="btn small ghost" data-id="${r.id}" data-to="${to}">${label}</button>` : "";
      return `<div class="inbox-item"><div class="who">${r.m.name}</div><div>${r.id} · ${r.summary}</div>
        <div class="st-tag">${r.status}</div>
        <div class="btn-row">${b("ACCEPTED", "Accept")}${b("READY", "Mark ready")}${b("COMPLETED", "Complete")}${b("DECLINED", "Decline")}</div></div>`;
    }).join("");
    $("#inbox").querySelectorAll("[data-to]").forEach((btn) => (btn.onclick = () => {
      const r = state.requests.find((x) => x.id === btn.dataset.id); transition(r, btn.dataset.to, "merchant");
    }));
  }

  // ---------- memory payoff: lost item in taxi ----------
  // Warm start (taxi saved) → prepared report from memory. Cold start → "How did you pay?"
  // → card trace (last 4 + receipt → driver confirm) or cash (valley team, pending → result).
  // Every simulated step carries SIM_PILL; nothing here is a real payment, driver or RTA event.
  const F = D.recoveryFixtures;
  const SIM_PILL = `<span class="pill trig">Demo trigger · Simulated trace</span>`;
  const statusTag = (s) => `<div class="st-tag" style="font-family:var(--mono);font-size:11px;color:var(--tint);margin-top:4px">${s}</div>`;

  async function recovery(opts = {}) {
    log("agent", "intent: lost_item_in_taxi", { uses_memory: !!state.trip, path: opts.trace ? "trace" : opts.hint || "report" });
    if (!state.trip) return recoveryPayChoice(opts.hint);
    log("memory", "recall taxi trip", { ...state.trip, provenance: "user_supplied" });
    if (opts.hint === "cash") {
      bot(`Using the taxi you saved (plate <b>${esc(state.trip.number)}</b>). I'll ask the <b>${F.cashTeam}</b> to check the rank records. ${SIM_PILL}`);
      return traceByCash(state.epoch);
    }
    if (opts.trace) {
      bot(`I'll reuse the taxi you saved (plate <b>${esc(state.trip.number)}</b>) so you don't have to retype it. <span class="pill user">You told me</span>`);
      await typing(500);
      return driverConfirm(state.trip.number, { traceId: "TRC-" + state.trip.number, matched: true, receiptRef: state.trip.receipt }, state.epoch);
    }
    bot("Don't worry. I have the trip details you gave me, so you won't need to remember them.");
    await typing(500);
    rtaReport({ sim: false });
  }

  async function recoveryPayChoice(hint) {
    const ep = state.epoch;
    await typing(300);
    bot(hint === "cash"
      ? `The <b>${F.cashTeam}</b> handles trips paid in cash at the DXB ranks. I don't have a taxi saved yet, so first: how did you pay?`
      : "I'm sorry. I don't have your taxi details saved. How did you pay? That decides how we trace the driver.");
    card(`<div class="card-head"><div><h3>How did you pay?</h3><div class="sub">No taxi saved yet · pick one</div></div>${SIM_PILL}</div>`);
    chips([["Paid by card", () => traceByCard(ep)], ["Paid cash", () => traceByCash(ep)]]);
  }

  async function traceByCard(ep) {
    await typing();
    bot("Last 4 digits of the card you used, plus the receipt photo?");
    const c = card(`<div class="card-head"><div><h3>Trace by card</h3><div class="sub">Last 4 digits + receipt photo · simulated, nothing is sent</div></div>${SIM_PILL}</div>
      <div style="display:grid;gap:8px">
        <input id="last4In" class="field" inputmode="numeric" maxlength="4" placeholder="Last 4 digits (e.g. 4242)">
        <label class="sub" style="margin:0">📸 Receipt photo <input id="trcRcpt" type="file" accept="image/*" style="margin-top:4px"></label>
        <button class="btn small" id="trcGo">Trace my taxi</button></div>
      <div class="foot"><span>Demo: any 4 digits match, "0000" simulates no match. No payment network is contacted.</span></div>`);
    c.querySelector("#trcGo").onclick = async () => {
      const last4 = c.querySelector("#last4In").value.trim() || "4242";
      if (!/^\d{4}$/.test(last4)) { c.querySelector(".foot span").textContent = "Enter exactly 4 digits."; return; }
      const file = c.querySelector("#trcRcpt").files[0];
      const rcpt = fakeMedia((file && file.name) || "receipt.jpg");
      c.querySelectorAll("button,input").forEach((x) => (x.disabled = true));
      user(`Card ending ${last4} + receipt photo`);
      const tr = fakeTracePayment(last4);
      log("action", "recovery.trace_requested", { path: "card", card: "•••• " + last4, receipt: rcpt.name, trace_id: tr.traceId, source: "demo_trigger", simulated: true });
      bot(`Tracing… ${SIM_PILL}`);
      if (!(await waitRun(1500, ep))) return;
      if (!tr.matched) {
        log("action", "recovery.trace_no_match", { trace_id: tr.traceId, status: "UNKNOWN_STATUS" });
        bot(`No trip matches those details (${SIM_PILL}). I won't guess. I'll prepare the RTA report instead.`);
        return rtaReport({ sim: true });
      }
      driverConfirm(F.taxi, tr, ep, rcpt);
    };
  }

  function driverConfirm(taxiNo, tr, ep, rcpt) {
    const drv = fakeMedia("driver-id.jpg");
    const thumbs = [drv, rcpt].filter(Boolean).map((m) => `<img src="${m.thumb}" alt="${esc(m.name)}" style="width:96px;height:72px;border-radius:10px">`).join("");
    log("tool", "recovery.driver_candidate", { taxi: taxiNo, trace_id: tr.traceId, receipt_ref: tr.receiptRef, provenance: "demo_fixture" });
    card(`<div class="card-head"><div><h3>Taxi #${esc(taxiNo)} · driver ${esc(F.driver)}</h3><div class="sub">Trace ${esc(tr.traceId)} · ${esc(tr.receiptRef || "receipt")} · is this your trip?</div></div>${SIM_PILL}</div>
      <div style="display:flex;gap:8px">${thumbs}</div>${statusTag("pending")}
      <div class="foot"><span>Demo fixture driver and photos. Not a real person or ID.</span></div>`);
    chips([
      ["Yes, correct", async () => {
        log("action", "recovery.driver_confirmed", { taxi: taxiNo, actor: "user" });
        await typing();
        bot(`Thanks. Driver ${esc(F.driver)} (taxi #${esc(taxiNo)}) is on the way back to the Terminal 3 rank. ${SIM_PILL}`);
        const st = card(`<div class="card-head"><div><h3>Driver update</h3><div class="sub">Taxi #${esc(taxiNo)} · ${esc(F.driver)}</div></div>${SIM_PILL}</div>${statusTag("driver en route")}
          <div class="foot"><span>Simulated status. A real build changes this only on the driver's or RTA's own update.</span></div>`);
        if (!(await waitRun(5000, ep))) return;
        bot(`Still tracing. The driver hasn't confirmed the bag yet. ${SIM_PILL}`);
        if (!(await waitRun(3000, ep))) return;
        log("trigger", "recovery.bag_located", { taxi: taxiNo, trace_id: tr.traceId, actor: "driver (demo)", provenance: "demo_fixture", status: "READY" });
        st.innerHTML = `<div class="card-head"><div><h3>Bag located</h3><div class="sub">Taxi #${esc(taxiNo)} · ${esc(F.driver)} has it · pickup at the Terminal 3 taxi rank</div></div>${SIM_PILL}</div>${statusTag("READY")}
          <div class="btn-row"><button class="btn small ghost" id="rtaAnyway">Prepare RTA report anyway</button></div>
          <div class="foot"><span>Simulated result. I'll only call it handed over when you tell me it is.</span></div>`;
        st.querySelector("#rtaAnyway").onclick = () => rtaReport({ sim: true });
        bot(`Good news (simulated): ${esc(F.driver)} has your bag and will hold it at the rank. ${SIM_PILL}`);
      }],
      ["No", async () => {
        log("action", "recovery.driver_rejected", { taxi: taxiNo, actor: "user" });
        await typing();
        bot("Then that isn't your trip, and I won't pretend it is. I'll prepare the RTA report with what you have.");
        rtaReport({ sim: true });
      }]
    ]);
  }

  async function traceByCash(ep) {
    await typing();
    bot(`Contacting the <b>${F.cashTeam}</b>… Cash trips can't be traced by payment, so they check the rank records for your pickup. ${SIM_PILL}`);
    log("action", "recovery.cash_trace_requested", { path: "cash", team: F.cashTeam, status: "UNKNOWN_STATUS", simulated: true });
    const c = card(`<div class="card-head"><div><h3>${esc(F.cashTeam)}</h3><div class="sub">Request sent (simulated) · waiting for their reply</div></div>${SIM_PILL}</div>${statusTag("UNKNOWN_STATUS")}
      <div class="foot"><span>Unknown until they reply. I won't invent a result.</span></div>`);
    if (!(await waitRun(6000, ep))) return;
    const found = state.cashRuns++ % 2 === 0;   // alternates so both branches are demoable
    log("trigger", found ? "recovery.cash_match" : "recovery.cash_no_match", { actor: "valley_team (demo)", simulated_outcome: found ? "match" : "no_match", provenance: "demo_fixture", status: found ? "READY" : "UNKNOWN_STATUS" });
    if (found) {
      c.innerHTML = `<div class="card-head"><div><h3>Driver identified</h3><div class="sub">${esc(F.driver)} · taxi #${esc(F.taxi)} · bag secured · ETA 12 min to the Terminal 3 rank</div></div>${SIM_PILL}</div>${statusTag("READY")}
        <div class="foot"><span>Simulated reply from the valley team (demo fixture).</span></div>`;
      bot(`Driver identified, bag secured, ETA 12 min (simulated reply). ${SIM_PILL}`);
    } else {
      c.innerHTML = `<div class="card-head"><div><h3>No match</h3><div class="sub">The valley team found no trip for your pickup</div></div>${SIM_PILL}</div>${statusTag("UNKNOWN_STATUS")}`;
      bot(`No match from the valley team, so I'm preparing the RTA report. ${SIM_PILL}`);
      rtaReport({ sim: true });
    }
  }

  // RTA lost-item report: prefilled from saved taxi fields when present, blank form otherwise.
  // Never filed from here: the card ends at PREPARED_NOT_FILED and hands off to the official channel.
  function rtaReport({ sim }) {
    const t = state.trip, simPill = sim ? " " + SIM_PILL : "";
    log("tool", "recovery.rta_report_form", { prefilled: !!t });
    const tripBlock = t
      ? `<div class="shares"><b>Trip <span class="pill user" style="margin-left:4px">You told me</span></b>
          Time <b>${esc(t.started)}</b> · Pickup <b>${esc(t.pickup)}</b> · Drop-off <b>${esc(t.route.split("→")[1] || state.dest || "")}</b> · Plate <b>${esc(t.number)}</b> · Roof <b>${esc(t.roof)}</b> · Receipt <b>${esc(t.receipt)}</b></div>`
      : `<div class="shares"><b>Trip details (blank, nothing saved)</b>
          <div style="display:grid;gap:6px;margin-top:4px">
            <input class="field" id="rtaPlate" placeholder="Taxi plate number, if you have it">
            <input class="field" id="rtaTime" placeholder="Pickup time (e.g. 00:40)">
            <input class="field" id="rtaRoute" placeholder="From → to (e.g. DXB T3 → Marina)"></div></div>`;
    const c = card(`<div class="card-head"><div><h3>Lost item report</h3><div class="sub">${t ? "Prepared from what you told me" : "Blank form, fill what you know"} · official fields</div></div><span class="pill">Not filed yet</span>${simPill}</div>
      ${tripBlock}
      <div class="shares"><b>Missing: describe the bag</b><input class="field" id="bagIn" placeholder="e.g. black backpack, laptop inside" style="width:100%;margin-top:4px"></div>
      <div class="btn-row"><button class="btn small" id="bagGo">Prepare report</button></div>`);
    c.querySelector("#bagGo").onclick = async () => {
      const val = (id) => { const el = c.querySelector(id); return el ? el.value.trim() : ""; };
      const bag = val("#bagIn") || "black backpack, laptop inside";
      const detail = t
        ? `taxi ${esc(t.number)} (${esc(t.roof)} roof) · ${esc(t.route)} · ${esc(t.started)} · ${esc(t.receipt)}`
        : `taxi ${esc(val("#rtaPlate") || "plate not provided")} · ${esc(val("#rtaRoute") || "route not provided")} · ${esc(val("#rtaTime") || "time not provided")}`;
      log("action", "recovery.report_prepared", { taxi: t ? t.number : val("#rtaPlate") || null, item: bag, prefilled: !!t, status: "PREPARED_NOT_FILED" });
      c.innerHTML = `<div class="card-head"><div><h3>Report ready</h3><div class="sub">${esc(bag)} · ${detail}</div></div><span class="pill">Bag not recovered yet</span>${simPill}</div>${statusTag("PREPARED_NOT_FILED")}
        <div class="btn-row"><button class="btn small">Contact official lost &amp; found</button><button class="btn small ghost">Copy report</button></div>
        <div class="foot"><span>Handoff to the official channel (${F.rtaChannel}). I won't mark anything recovered until you tell me</span></div>`;
      await typing(); bot("I'll check in with you tomorrow morning about the bag, unless you tell me it's found.");
    };
  }

  // ---------- honest fallback: every other S/T/X case gets a truthful answer ----------
  // Nothing invented, nothing executed. Official handoff or "not in this demo".
  const FALLBACKS = [
    // Entries with `go` dispatch to a flow instead of showing a card (kept first so they win).
    { re: /airport taxi|taxi valley|valley team/, s: "recovery/cash", go: () => recovery({ hint: "cash" }) },
    { re: /\btrace\b|\bdriver\b|(find|recover|get back).*\bbag\b|\bbag\b.*(missing|gone)/, s: "recovery/trace", go: () => recovery({ trace: true }) },
    { re: /salik|dewa|fine|toll|top ?up|\bpay\b|parking fine/, s: "S08",
      t: "Fines and balances are display-only",
      b: "I never pay fines, top up Salik/DEWA, or book government services. I can show official amounts and hand you to the official portal." },
    { re: /visa|residency|emirates id|work permit/, s: "S10",
      t: "Visa and residency: official channel only",
      b: "I give general guidance with official links. Status checks and applications happen on the official portal, never here." },
    { re: /ticket|concert|attraction|book a|reservation|reserve/, s: "S23/S09",
      t: "I can't book or reserve anything",
      b: "No tickets, tables, or slots from me — a booking needs the provider's own confirmation. I can list demo options and remind you before the time." },
    { re: /package|parcel|\bdelivery\b|order status|snorkel|countdown/, s: "S21",
      t: "Deliveries linked to your trip",
      b: "I can't see live courier tracking. Give me the ETA and the trip it matters for (e.g. snorkeling tomorrow) and I'll remind you — and offer to replan if it runs late." },
    { re: /geofenc|\btrack\b|background|follow me|nearby automatically/, s: "S22",
      t: "No background tracking in this app",
      b: "This demo has no geofencing or motion detection. Reminders come from times you confirm and merchant updates — tell me a time and I'll remind you." },
    { re: /video|recording|clip|moment/, s: "S18",
      t: "Video memory isn't in this demo",
      b: "I can't search inside videos yet. I keep what you type, confirm, or attach as photos and receipts." },
    { re: /deposit|scam|cheat|complain|refund|dispute|rental car|rent a car/, s: "S19/S10",
      t: "Disputes: evidence first, official channel second",
      b: "Keep the contract, photos, and receipts with dates — that's what decides deposit cases. I'll organize them into a timeline and hand you to the official consumer-rights channel. I can't file for you." },
    { re: /clinic|doctor|hospital|insurance|emergency|ambulance|sick|fever/, s: "S07",
      t: "Health: urgent cases call 997 / 998",
      b: "For anything urgent, call emergency services first. Otherwise I can find a nearby pharmacy (demo list) or hand you to clinic/insurance contacts — I never diagnose." },
    { re: /safari|desert/, s: "S15",
      t: "Safari operators: compare, then verify",
      b: "I can compare demo operators by price and pickup — but verify the operator's licence and what's included before paying anyone. I don't take bookings." },
    { re: /mosque|abu dhabi|day trip|cultural/, s: "S14/T08",
      t: "Day-trip prep, not a booking",
      b: "I can prep the checklist — dress code, prayer-time closures, official hours, transport comparison. Entry and tours are booked on the official site." },
    { re: /dinner|restaurant|\beat\b|\bfood\b|cuisine|\bdiet\w*|breakfast|\blunch\b|\bmeal\w*|halal|vegan|vegetarian/, s: "S05/S09",
      t: "Food discovery (demo list)",
      b: "I can list demo places near you with cuisines and dietary notes. Ordering or reserving happens in the restaurant's own app — tell me dietary needs and I'll filter." },
    { re: /\bwalk\b|weather|\bhot\b|heat|humid|sun\b|evening walk/, s: "S04",
      t: "Heat is a real constraint",
      b: "Summer midday hits 35–45°C — I plan outdoor things for morning or evening with water and shade stops. I don't invent live weather; check a weather source for today." },
    { re: /skydiv|beach|snorkel|diving|pool|waterpark/, s: "S02",
      t: "Activities via the operator",
      b: "I can shortlist demo operators — but skydives, beach clubs, and trips are booked on the operator's site. Tell me the date and I'll link reminders to it." },
    { re: /repair|broken| cracked|screen|print|notary|documents/, s: "X01",
      t: "Repairs and errands: discovery first",
      b: "I can find demo repair shops and errand services near you with fixed prices. Back up the phone before any repair — and get the turnaround promise in writing." },
    { re: /flight.*(delay|cancel|status|late)|missed|connection|rebook/, s: "X07/Journey D",
      t: "I can't see live flight status",
      b: "Check the airline or the DXB status board for the real picture. Tell me the new arrival time and I'll replan the hotel night and transport — confirmed plans stay untouched." },
    { re: /budget|cheap|save|expensive|cost/, s: "S20",
      t: "Budget-aware by default",
      b: "Every list I show is sorted closest, with price-from and turnaround up front, so the cheap option is visible. Tell me a nightly cap and I'll filter to it." },
    { re: /family|kids|children|baby|stroller/, s: "X09",
      t: "Family trips need shade and pace",
      b: "I plan shorter outdoor stretches, indoor midday breaks, and stroller-friendly routes. Tell me ages and I'll adjust the draft." },
    { re: /arabic|language|speak|translate/, s: "i18n",
      t: "I answer in your language",
      b: "Ask me in Arabic or English and I'll reply the same way. A full Arabic interface is later — the words work now." },
    { re: /cleaning|apartment|move|utilities/, s: "X02/X12",
      t: "Home services: same fixed-order pattern",
      b: "Cleaning and home services would work like laundry — fixed price list, approval, merchant confirmation. No demo merchant in this category yet; a shop can join from a price-list photo." },
    { re: /charging|ev |tesla|sim|esim|wifi|cash|atm|plug|roam/, s: "arrival essentials",
      t: "Arrival essentials",
      b: "Tourist SIMs are sold at all DXB terminals; UAE isn't covered by EU roaming. ATMs sit landside in arrivals. Ask and I'll point you to the official counter or page." }
  ];

  function honestFallback(q) {
    const hit = FALLBACKS.find((f) => f.re.test(q));
    if (hit && hit.go) { log("agent", "fallback → flow", { scenario: hit.s }); return hit.go(); }
    log("agent", "honest fallback", { scenario: hit ? hit.s : "none" });
    if (!hit) return bot("This demo is scripted. Try: <i>pharmacy</i>, <i>shirt pressed by 9 tomorrow</i>, <i>what's on</i>, <i>prayer times</i>, <i>qibla</i>, <i>near a mosque</i>, <i>search my photos</i>, <i>I left my bag in the taxi</i>.");
    card(`<div class="card-head"><div><h3>${hit.t}</h3><div class="sub">Case ${hit.s} · honest answer, nothing executed</div></div><span class="pill demo">Demo data</span></div>
      <div class="step-body" style="font-size:14px">${hit.b}</div>
      <div class="foot"><span>Guidance + official handoff. I won't show it as booked, filed, or paid.</span></div>`);
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
    if (/tailor/.test(q)) return pharmacies("Tailors");
    if (/grocer/.test(q)) return pharmacies("Groceries");
    if (/laundry|iron|shirt|press|deadline|by 9|by nine/.test(q)) return laundryDeadline();
    if (/communit|egyptian|egypt|meet ?up|meet people|friends|ai engineer|social|people/.test(q)) return community();
    if (/ticket|event|concert|jazz|show.*on|what.*on\b/.test(q)) return tickets();
    if (/prayer|pray|fajr|maghrib|isha|dhuhr|asr|fasting|ramadan/.test(q)) return prayer();
    if (/qibla|compass|direction.*(pray|mecca|kaaba)|mecca|kaaba/.test(q)) return qibla();
    if (/mosque|near.*(mosque|masjid)|geofenc|jummah|friday prayer/.test(q)) return nearMosque();
    if (/search.*photo|find.*photo|my photos|car photo|parking photo|all photos|photo search/.test(q)) return photoSearch(q);
    if (/parking|my car|where.*car|pillar|parked|parking spot/.test(q)) return parkingFlow(q);
    if (/flying home|going home|departure|check.?out|tax refund|\bvat\b|leaving dubai/.test(q)) return departure();
    if (/plan my|itinerary|swap.*evening|what.*(do|see)|my day|\btomorrow\b/.test(q)) return dayplan(false);
    if (/(left|lost|forgot).*(taxi|cab|car|bag)|(taxi|cab).*(left|lost|forgot)|left my bag/.test(q)) return recovery();
    if (FALLBACKS.some((f) => f.go && f.re.test(q))) return honestFallback(q);   // trace / driver / valley team
    if (/belt|bag/.test(q)) return bot(state.memory["Baggage belt"] ? `You told me: <b>${state.memory["Baggage belt"]}</b>.` : "You haven't told me a belt number yet. Check the arrivals screens.");
    if (/taxi number|which taxi|receipt|roof/.test(q)) return bot(state.trip ? `Your taxi: plate <b>${state.trip.number}</b>, ${state.trip.roof} roof, ${state.trip.route}, started ${state.trip.started}, ${state.trip.receipt}. <span class="pill user">You told me</span>` : "I don't have a taxi saved.");
    if (/taxi|metro|hotel|ride/.test(q)) { state.dest = state.dest || "Business Bay"; return rides(); }
    if (/lost|where am i/.test(q)) return stepAction("lost");
    if (NLU.weight > 0) log("agent", "nlu seam enabled but not wired in the static demo", { url: NLU.url, weight: NLU.weight });
    return honestFallback(q);
  };

  // ---------- start ----------
  async function start() {
    chat.innerHTML = ""; journeyCard = null; state.requests = []; state.memory = {}; state.dest = null; state.trip = null;
    state.epoch++; state.cashRuns = 0; state.fired = {};   // restart: stale timers stop, sims and dedupe reset
    state.photos = D.seedPhotos.map((p) => ({ ...p, mine: false }));
    $("#log").innerHTML = ""; $("#inbox").innerHTML = `<div class="inbox-empty">No requests yet. Order something from a merchant mini-app.</div>`;
    renderMemory(); renderServices(); showTab("companion");
    $("#modePill").textContent = state.mode;
    if (state.mode === "Resident") {
      log("ui", "resident mode: no arrival flow");
      bot("Good afternoon. Nothing urgent today. Need anything nearby?");
      chips([["Find a pharmacy", () => { state.dest = "Business Bay"; pharmacies(); }], ["I need a shirt pressed by 9 tomorrow", () => { state.dest = "Business Bay"; laundryDeadline(); }]]);
      return;
    }
    log("trigger", "flight.landed", { source: "demo_trigger", flight: D.flight.number, airport: "DXB T3", dedupe_key: "EK002:landed" });
    await sleep(300);
    card(`<div class="hero-hello">
      <div class="eyebrow">Dubai-io · Proactive <span class="pill trig">Demo trigger</span> <span class="pill demo">Scripted demo</span></div>
      <h1>Hello, visitor.</h1>
      <p>Welcome to Dubai. Your flight ${D.flight.number} has landed at DXB ${D.flight.terminal} at ${D.scenarioTime}. I'll walk you from the gate to your taxi or Metro, one step at a time.</p></div>`);
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
  installTriggers();
  start();
})();
