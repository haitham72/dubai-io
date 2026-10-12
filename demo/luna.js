// Mock Luna: scripted understanding for the Figma-style demo. No model, no network, no keys.
//
// Contract (a real Luna service returns the same shape behind the API proxy; swap understand()):
//   understand(text) → Promise<{ intent, category, interests[], origin, item, trace, confidence, via, matched[] }>
//
// app.js dispatches on `intent` when confidence >= minConfidence. Anything Luna does not understand
// returns intent "none" and the regex router answers, so existing routes keep working.
(() => {
  const lev = (a, b) => {
    const m = a.length, n = b.length;
    let prev = Array.from({ length: n + 1 }, (_, j) => j);
    for (let i = 1; i <= m; i++) {
      const cur = [i];
      for (let j = 1; j <= n; j++) cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
      prev = cur;
    }
    return prev[n];
  };
  // Typo tolerant: short words must match exactly, longer ones allow 1 (or 2 when long) edits.
  const near = (t, v) => t === v || (v.length >= 5 && t.length >= 4 && lev(t, v) <= (v.length >= 8 ? 2 : 1));
  const hit = (tokens, vocab) => tokens.find((t) => vocab.some((v) => near(t, v)));

  const norm = (s) => String(s).toLowerCase()
    .replace(/[ً-ٟ]/g, "").replace(/[أإآ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي")
    .replace(/[^a-z0-9؀-ۿ\s]/g, " ");
  const tokenize = (s) => norm(s).split(/\s+/).filter(Boolean).map((t) => t.replace(/^ال(?=.{3,})/, ""));

  const COMM = ["community", "communities", "group", "groups", "meetup", "meetups", "club", "clubs", "circle", "circles",
    "network", "people", "friends", "buddy", "buddies", "crowd", "مجتمع", "مجموعه", "مجموعات", "جروب", "جماعه", "تجمع", "اصدقاء"];
  const ORIGINS = {
    egyptian: ["egyptian", "egyptians", "egypt", "masri", "masry", "cairo", "alexandria", "مصري", "مصريين", "مصر", "مصريه"],
    indian: ["indian", "indians", "india", "mumbai", "delhi"],
    filipino: ["filipino", "filipinos", "filipina", "philippines", "pinoy", "manila"],
    pakistani: ["pakistani", "pakistanis", "pakistan", "karachi", "lahore"],
    british: ["british", "brit", "brits", "uk"],
    lebanese: ["lebanese", "lebanon", "beirut"]
  };
  const INTERESTS = {
    ai: ["ai", "ml", "llm", "llms", "genai", "artificial", "intelligence", "ذكاء"],
    engineering: ["engineering", "engineer", "engineers", "developer", "developers", "devs", "software", "coding", "programmer", "programmers", "مهندسين", "مهندس", "برمجه"],
    python: ["python"],
    data: ["data", "analytics"],
    startup: ["startup", "startups", "founder", "founders"],
    tech: ["tech", "technology"],
    football: ["football", "soccer"],
    running: ["running", "runners", "runner", "jogging"],
    fitness: ["gym", "fitness", "crossfit", "workout"],
    photography: ["photography", "photographer", "photographers"],
    hiking: ["hiking", "hike", "hikers"]
  };
  const BUY = ["buy", "purchase", "shopping", "cheapest", "price", "prices", "deals", "اشتري", "اشتر", "شراء", "ارخص", "سعر"];
  const LOST = ["left", "lost", "forgot", "forgotten", "missing", "dropped", "misplaced", "نسيت", "ضاعت", "ضاع", "فقدت"];
  const TAXI = ["taxi", "taxis", "taksi", "teksi", "cab", "driver", "تاكسي"];
  const TRACE = ["trace", "track", "find"];
  const STOP = new Set(["a", "an", "the", "me", "for", "some", "my", "i", "want", "to", "need", "please", "best", "price", "prices",
    "of", "on", "from", "find", "cheapest", "buy", "purchase", "where", "can", "how", "much", "is", "are", "online", "in", "dubai",
    "uae", "shopping", "deals", "looking", "get", "we", "us", "there", "any", "good", "new"]);

  function understand(text) {
    const tokens = tokenize(text), joined = norm(text);
    const none = { intent: "none", category: null, interests: [], origin: null, item: null, trace: false, confidence: 0, via: "mock-luna", matched: [] };
    if (!tokens.length) return none;

    // lost item in a taxi (typos like "taksi" resolve through near())
    const lost = hit(tokens, LOST), taxi = hit(tokens, TAXI), trace = hit(tokens, ["trace", "track"]);
    if ((lost && taxi) || (trace && taxi)) {
      return { ...none, intent: "lost_item.taxi", category: "Recovery", trace: !!trace && !lost, confidence: lost ? 0.9 : 0.8, matched: [lost || trace, taxi] };
    }

    // shopping: "buy airpods", "cheapest running shoes"
    const buy = hit(tokens, BUY);
    if (buy) {
      const item = tokens.filter((t) => !STOP.has(t) && !BUY.includes(t)).slice(0, 4).join(" ").trim() || null;
      if (item && /ticket|concert|event|show\b/.test(item)) return none;   // events keep their own route
      return { ...none, intent: "shopping.buy", category: "Shopping", item, confidence: item ? 0.85 : 0.6, matched: [buy] };
    }

    // community: "find group egyptians about ai engineering"
    const interests = Object.keys(INTERESTS).filter((k) => hit(tokens, INTERESTS[k]));
    if (/machine\s+learning/.test(joined) && !interests.includes("ai")) interests.push("ai");
    const origin = Object.keys(ORIGINS).find((k) => hit(tokens, ORIGINS[k])) || null;
    const comm = hit(tokens, COMM);
    if (comm || (origin && interests.length)) {
      let c = 0.55;
      if (origin) c += 0.15;
      if (interests.length) c += 0.15;
      if (comm && COMM.includes(comm)) c += 0.1;   // exact (not typo) community word
      return { ...none, intent: "community.find", category: "Community", interests, origin, confidence: Math.min(c, 0.95), matched: [comm, origin, ...interests].filter(Boolean) };
    }
    return none;
  }

  window.LUNA = { name: "Luna (mock)", minConfidence: 0.6, understand: (text) => Promise.resolve(understand(text)) };
})();
