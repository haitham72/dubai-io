// Demo fixtures. Every value here is illustrative demo data, not live information.
// Prices and times are labelled "Demo estimate" in the UI. Merchants are fictional.

window.DEMO = {
  flight: { number: "EK 002 (demo)", airport: "DXB", terminal: "Terminal 3" },

  // Indoor airport journey. Generic, signage-based steps. No invented belt numbers,
  // queue times or gate positions. The user confirms each step.
  airportSteps: [
    {
      id: "gate",
      zone: 0,
      title: "Off the plane",
      body: "Follow the <b>Arrivals</b> signs. Depending on your gate, a short airport train may link your concourse to passport control. Just follow the signs and staff.",
      landmark: "Gate numbers, duty-free shops",
      img: "maps/t3-duty-free.jpg",
      imgCaption: "T3 concourse & Dubai Duty Free",
      sideStop: { img: "maps/t3-business-lounge.jpg", title: "Need a break?", note: "Business Class Lounge, if your ticket includes it", imgCaption: "T3 Business Class Lounge" }
    },
    {
      id: "immigration",
      zone: 1,
      title: "Passport control",
      body: "Have your passport and any visa or entry document ready. Smart gates may be available if you're eligible. Otherwise use the counters. I won't guess eligibility; the signs and officers decide.",
      landmark: "Passport counters or smart gates",
      tile: { icon: "🛂", note: "Follow the Passport control signs" },
      extra: "needs"
    },
    {
      id: "baggage",
      zone: 2,
      title: "Baggage reclaim",
      body: "Find your flight on the screens to see your belt number. I don't guess belts. Tell me the number and I'll remember it for you.",
      landmark: "Baggage belts and screens",
      tile: { icon: "🧳", note: "Find your flight on the belt screens" },
      extra: "belt"
    },
    {
      id: "customs",
      zone: 3,
      title: "Customs",
      body: "Nothing to declare? Use the <b>green</b> channel. Carrying items you need to declare? Use the <b>red</b> channel. Official customs guidance has the full list.",
      landmark: "Customs, green/red channel signs",
      tile: { icon: "🛃", note: "Green channel: nothing to declare" }
    },
    {
      id: "arrivals",
      zone: 4,
      title: "Arrivals hall",
      body: "You're landside. There are usually ATMs, telecom counters and meeting points here. Ready for your ride?",
      landmark: "Arrivals hall, people waiting",
      img: "maps/t3-check-in.jpg",
      imgCaption: "T3 landside hall"
    },
    {
      id: "ride",
      zone: 5,
      title: "Choose your ride",
      body: "Compare taxi and Metro to your hotel area.",
      landmark: "Taxi rank or Metro signs",
      img: "maps/dxb-overview.png",
      imgCaption: "Dubai International · Terminal 3",
      pin: [60, 61]            // [x%, y%] of the terminal you told me, not live GPS
    }
  ],

  // Built-in mini-apps (publisher "dubai-io"). Same host, manifest and scoped bridge as the
  // merchants below: anything the user browses opens as a modal HTML mini-app.
  // New surfaces (communities, shopping, taxi desk) are registry entries, not bespoke cards.
  apps: [
    {
      id: "dxbguide", name: "DXB arrival guide", category: "Guide", publisher: "dubai-io", kind: "guide",
      manifest: { version: "1.0.0", entry: "miniapps/dxb-guide.html", bridge_scopes: ["journey.confirm_waypoint", "memory.save", "ride.compare"], fallback_card: "journey_summary" }
    },

    // ---- Community: one request ("find group egyptians about ai engineering") → rows from several
    // apps, built-in first. Each row opens its own mini-app. Groups are synthetic: no real people,
    // approximate areas only, joining needs the group's own accept. tags drive Luna's matching.
    {
      id: "dubaiio-groups", name: "Dubai-io Communities", category: "Community", publisher: "dubai-io", logo: "D", color: "#0A9CC2",
      blurb: "Built-in · opt-in groups around you",
      manifest: { version: "1.0.0", entry: "miniapps/community.html?app=dubaiio-groups", bridge_scopes: ["auth.signin", "community.join_request"], fallback_card: "community_summary" },
      groups: [
        { id: "egtech", name: "EgTech Dubai", line: "Egyptians in tech · AI engineering", kind: "Public group", members: "12 interested", area: "Dubai Marina area", tags: ["egyptian", "ai", "engineering", "tech"] },
        { id: "aibuilders", name: "Dubai AI Builders coffee", line: "Weekly builders' coffee", kind: "Public group", members: "8 interested", area: "Marina / JLT area", tags: ["ai", "engineering", "tech"] },
        { id: "newindubai", name: "New in Dubai: Marina", line: "Casual meetups for newcomers", kind: "Meetup · Saturdays", members: "6 going", area: "Public café, Marina", tags: ["newcomers", "social"] }
      ]
    },
    {
      id: "meetly", name: "Meetly (demo)", category: "Community", publisher: "partner", logo: "M", color: "#6B4EFF",
      blurb: "Partner app · meetups and clubs",
      manifest: { version: "2.3.0", entry: "miniapps/community.html?app=meetly", bridge_scopes: ["auth.signin", "community.join_request"], fallback_card: "community_summary" },
      groups: [
        { id: "mt-aiegy", name: "AI Engineers Dubai · Arabic-speaking", line: "Talks and code nights", kind: "Meetup group", members: "240 members", area: "Business Bay (approximate)", tags: ["ai", "engineering", "egyptian", "arabic", "tech"] },
        { id: "mt-py", name: "Dubai Python Night", line: "Monthly lightning talks", kind: "Meetup group", members: "410 members", area: "Media City (approximate)", tags: ["python", "engineering", "ai", "tech"] },
        { id: "mt-run", name: "Marina Sunrise Runners", line: "5 km, all paces", kind: "Club", members: "95 members", area: "Marina Walk (approximate)", tags: ["running", "fitness", "social"] }
      ]
    },
    {
      id: "circlehub", name: "CircleHub (demo)", category: "Community", publisher: "partner", logo: "C", color: "#E0663A",
      blurb: "Partner app · communities by origin and interest",
      manifest: { version: "0.9.4", entry: "miniapps/community.html?app=circlehub", bridge_scopes: ["auth.signin", "community.join_request"], fallback_card: "community_summary" },
      groups: [
        { id: "ch-eg", name: "Egyptians in the Emirates", line: "Newcomer tips and events", kind: "Community", members: "1.2k members", area: "Dubai-wide", tags: ["egyptian", "arabic", "social", "newcomers"] },
        { id: "ch-ml", name: "ML Study Circle", line: "Reading group, beginner friendly", kind: "Study group", members: "60 members", area: "Dubai Internet City (approximate)", tags: ["ai", "data", "engineering", "tech"] }
      ]
    },

    // ---- Shopping: "buy <item>" → rows sorted by price (list prices, fixed; payment happens on the
    // provider's own site, never through Dubai-io). Prices are computed per item and labelled demo.
    {
      id: "souqexpress", name: "Souq Express (demo)", category: "Shopping", publisher: "partner", logo: "SE", color: "#1F8A5B",
      blurb: "Next-day delivery · free shipping", price: { mult: 1.0, shipping: 0 }, eta: "Tomorrow",
      manifest: { version: "4.1.0", entry: "miniapps/shop.html?app=souqexpress", bridge_scopes: ["auth.signin", "purchase.report"], fallback_card: "shopping_summary" }
    },
    {
      id: "cartnest", name: "CartNest (demo)", category: "Shopping", publisher: "partner", logo: "CN", color: "#C2410C",
      blurb: "Lowest list price · slower delivery", price: { mult: 0.94, shipping: 15 }, eta: "2–3 days",
      manifest: { version: "2.0.2", entry: "miniapps/shop.html?app=cartnest", bridge_scopes: ["auth.signin", "purchase.report"], fallback_card: "shopping_summary" }
    },
    {
      id: "dealdash", name: "DealDash Dubai (demo)", category: "Shopping", publisher: "partner", logo: "DD", color: "#7C3AED",
      blurb: "Same-day in Dubai · pay a little more", price: { mult: 1.08, shipping: 0 }, eta: "Today, 4–8 pm",
      manifest: { version: "1.7.0", entry: "miniapps/shop.html?app=dealdash", bridge_scopes: ["auth.signin", "purchase.report"], fallback_card: "shopping_summary" }
    }
  ],

  zones: ["Gate", "Passport", "Baggage", "Customs", "Arrivals", "Taxi / Metro"],

  destinations: {
    "Business Bay": {
      taxi: { time: "20–30 min", price: "AED 60–90" },
      metro: { time: "35–45 min", price: "AED 6–9 + Nol card", station: "Business Bay station" }
    },
    "Dubai Marina": {
      taxi: { time: "35–45 min", price: "AED 110–150" },
      metro: { time: "55–70 min", price: "AED 7–9 + Nol card", station: "the Red Line station nearest your hotel" }
    }
  },

  categories: ["Pharmacy", "Laundry", "Groceries", "Tailors"],

  // Late-night scenario clock (fictional demo time). Metro hours: Mon–Thu
  // 05:00–00:00, Fri–05:00–01:00. At 00:40 the Metro has stopped → taxi.
  scenarioTime: "00:40",

  // Official handoffs (display only — Dubai-io never executes these).
  official: {
    vatRefund: "https://tax.gov.ae/en/services/tourist.VAT.refunds.aspx",
    flightStatus: "https://dubaiairports.ae/flight-status",
    metro: "https://dubaiairports.ae/transport/metro"
  },

  // ---- Figma-mock fixtures: tickets (graphic), mosques, prayer times ----
  // All demo art. Live seams (ticketing provider, Aladhan) plug in at build.
  events: [
    {
      id: "jazzgardens",
      name: "Jazz Gardens Live",
      venue: "Media City Amphitheatre",
      date: "Fri 24 Oct · 20:00",
      priceFrom: "AED 195",
      hue: ["#3B4F8F", "#0F1626"],
      tiers: [
        { name: "Standard", price: 195 },
        { name: "Premium", price: 295 },
        { name: "VIP front", price: 450 }
      ]
    },
    {
      id: "foodfest",
      name: "Dubai Food Nights",
      venue: "Burj Park",
      date: "Sat 25 Oct · 18:00",
      priceFrom: "AED 75",
      hue: ["#B4587A", "#3A1F2E"],
      tiers: [
        { name: "General", price: 75 },
        { name: "Tasting pass", price: 160 }
      ]
    }
  ],

  mosques: [
    { id: "jumeirah", name: "Jumeirah Grand Mosque", area: "Jumeirah", distance: "3.2 km" },
    { id: "marina", name: "Marina Mosque", area: "Dubai Marina", distance: "0.9 km" },
    { id: "zayed", name: "Sheikh Zayed Grand Mosque", area: "Abu Dhabi (day trip)", distance: "130 km" }
  ],

  // Demo prayer fixtures for Dubai. Build seam: GET
  // https://api.aladhan.com/v1/timingsByCity?city=Dubai&country=UAE&method=16
  // (keyless). Live values render with as_of; any failure → these fixtures.
  prayerFixtures: {
    date: "demo day",
    times: { Fajr: "05:12", Sunrise: "06:34", Dhuhr: "12:05", Asr: "15:28", Maghrib: "17:52", Isha: "19:22" }
  },

  // Operator-fired scenes (backstage Trigger panel). Demo fixtures only.
  triggerFixtures: {
    mosqueDistance: "400 m",         // scripted proximity for geo.mosque_nearby
    eventRef: "TK1247",              // ticket ref for the "tomorrow" reminder (fixture, not a booking)
    flightTime: "12:40",             // departure flight (fixture, not live)
    vatCutoff: "10:30",              // VAT validation before check-in (fixture)
    quietHours: "22:00–07:00"        // proactive messages are held outside this window
  },

  // Lost-item trace fixtures (card + cash paths). Fake media, no external fetches.
  recoveryFixtures: {
    taxi: "DXB-4471",
    driver: "Imran K.",
    cashTeam: "Airport taxi valley team",
    rtaChannel: "RTA lost &amp; found"
  },

  // Seeded demo photo library (stock art). User uploads join this list;
  // keyword search runs over names + labels. Embeddings plug in later.
  seedPhotos: [
    { name: "marina-parking.jpg", label: "parking garage pillar", url: "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=400&q=60&auto=format&fit=crop" },
    { name: "mall-entrance.jpg", label: "mall entrance meeting point", url: "https://images.unsplash.com/photo-1518684079-3c830dcef090?w=400&q=60&auto=format&fit=crop" }
  ],

  // Service registry: each merchant ships its own mini-app HTML with a manifest.
  // Fixed published prices only. The only bridge scope is "order.request".
  merchants: [
    {
      id: "palmleaf",
      name: "Palm Leaf Pharmacy",
      category: "Pharmacy",
      line: "Everyday medicines · delivery",
      distance: "0.8 km",
      distanceKm: 0.8,
      rating: "4.5",
      priceFrom: "AED 9",
      turnaround: "Delivery ~1h",
      color: "#2F7D5B",
      logo: "PL",
      manifest: { version: "1.2.0", entry: "miniapps/palmleaf.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    },
    {
      id: "nightowl",
      name: "Night Owl Pharmacy 24h",
      category: "Pharmacy",
      line: "Open 24h · prescriptions",
      distance: "1.4 km",
      distanceKm: 1.4,
      rating: "4.7",
      priceFrom: "Varies",
      turnaround: "Open 24h",
      color: "#1E2A4A",
      logo: "NO",
      manifest: { version: "2.0.1", entry: "miniapps/nightowl.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    },
    {
      id: "bloom",
      name: "Bloom Care",
      category: "Pharmacy",
      line: "Wellness and travel kits · pickup",
      distance: "2.1 km",
      distanceKm: 2.1,
      rating: "4.4",
      priceFrom: "AED 68",
      turnaround: "Pickup in 30 min",
      color: "#B4587A",
      logo: "BC",
      manifest: { version: "0.9.4", entry: "miniapps/bloom.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    },
    {
      id: "foldpress",
      name: "Fold & Press Laundry",
      category: "Laundry",
      line: "Ironing · pickup and drop-off",
      distance: "1.0 km",
      distanceKm: 1.0,
      rating: "4.6",
      priceFrom: "AED 5",
      turnaround: "Express by 08:30",
      color: "#A8843F",
      logo: "FP",
      manifest: { version: "3.0.0", entry: "miniapps/foldpress.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    },
    {
      id: "marinaexpress",
      name: "Marina Express Laundry",
      category: "Laundry",
      line: "Wash and press · same-day",
      distance: "0.6 km",
      distanceKm: 0.6,
      rating: "4.8",
      priceFrom: "AED 6",
      turnaround: "Same-day by 20:00",
      color: "#0A9CC2",
      logo: "ME",
      manifest: { version: "1.0.0", entry: "miniapps/marinaexpress.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    },
    {
      id: "palmquick",
      name: "Palm Quick Press",
      category: "Laundry",
      line: "Budget pressing · next-day",
      distance: "1.8 km",
      distanceKm: 1.8,
      rating: "4.3",
      priceFrom: "AED 4",
      turnaround: "Next-day by 08:00",
      color: "#6B5CA5",
      logo: "PQ",
      manifest: { version: "1.0.0", entry: "miniapps/palmquick.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison" }
    }
  ]
};
