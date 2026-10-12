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
      landmark: "Gate numbers, duty-free shops"
    },
    {
      id: "immigration",
      zone: 1,
      title: "Passport control",
      body: "Have your passport and any visa or entry document ready. Smart gates may be available if you're eligible. Otherwise use the counters. I won't guess eligibility; the signs and officers decide.",
      landmark: "Passport counters or smart gates",
      extra: "needs"
    },
    {
      id: "baggage",
      zone: 2,
      title: "Baggage reclaim",
      body: "Find your flight on the screens to see your belt number. I don't guess belts. Tell me the number and I'll remember it for you.",
      landmark: "Baggage belts and screens",
      extra: "belt"
    },
    {
      id: "customs",
      zone: 3,
      title: "Customs",
      body: "Nothing to declare? Use the <b>green</b> channel. Carrying items you need to declare? Use the <b>red</b> channel. Official customs guidance has the full list.",
      landmark: "Customs, green/red channel signs"
    },
    {
      id: "arrivals",
      zone: 4,
      title: "Arrivals hall",
      body: "You're landside. There are usually ATMs, telecom counters and meeting points here. Ready for your ride?",
      landmark: "Arrivals hall, people waiting"
    },
    {
      id: "ride",
      zone: 5,
      title: "Choose your ride",
      body: "Compare taxi and Metro to your hotel area.",
      landmark: "Taxi rank or Metro signs"
    }
  ],

  // Placeholder maps (to be replaced). pin = [x%, y%] of "you are here" on that image.
  maps: [
    { id: "overview", label: "DXB", src: "maps/dxb-overview.png", title: "Dubai International (DXB)", pin: [60, 61], pinLabel: "Terminal 3 · you", note: "Overview of all terminals and concourses." },
    { id: "checkin", label: "Check-in", src: "maps/t3-check-in.jpg", title: "T3 · Check-in", note: "Check-in hall layout." },
    { id: "dutyfree", label: "Duty Free", src: "maps/t3-duty-free.jpg", title: "T3 · Duty Free", note: "Shops, food and transfer routes." },
    { id: "lounge", label: "Lounge", src: "maps/t3-business-lounge.jpg", title: "T3 · Business Class Lounge", note: "Lounge services and gates." }
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

  // Community fixtures: consenting synthetic groups only. No real people,
  // no precise locations — approximate area, mutual opt-in, demo labels.
  communities: [
    {
      id: "egtech",
      name: "EgTech Dubai",
      line: "Egyptians in tech · AI engineering",
      kind: "Public group",
      interested: "12 interested",
      area: "Dubai Marina area"
    },
    {
      id: "aibuilders",
      name: "Dubai AI Builders coffee",
      kind: "Public group",
      interested: "8 interested",
      area: "Marina / JLT area"
    },
    {
      id: "newindubai",
      name: "New in Dubai: Marina",
      line: "Casual meetups for newcomers",
      kind: "Meetup · Saturdays",
      interested: "6 going",
      area: "Public café, Marina"
    }
  ],

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
