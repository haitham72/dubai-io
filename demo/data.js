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

  // Service registry: each merchant ships its own mini-app HTML with a manifest.
  merchants: [
    {
      id: "palmleaf",
      name: "Palm Leaf Pharmacy",
      category: "Pharmacy",
      line: "Everyday medicines · delivery",
      distance: "0.8 km",
      color: "#2F7D5B",
      logo: "PL",
      manifest: { version: "1.2.0", entry: "miniapps/palmleaf.html", bridge_scopes: ["cart.request"], fallback_card: "service_comparison" }
    },
    {
      id: "nightowl",
      name: "Night Owl Pharmacy 24h",
      category: "Pharmacy",
      line: "Open 24h · prescriptions",
      distance: "1.4 km",
      color: "#1E2A4A",
      logo: "NO",
      manifest: { version: "2.0.1", entry: "miniapps/nightowl.html", bridge_scopes: ["rx.request", "cart.request"], fallback_card: "service_comparison" }
    },
    {
      id: "bloom",
      name: "Bloom Care",
      category: "Pharmacy",
      line: "Wellness and travel kits · pickup",
      distance: "2.1 km",
      color: "#B4587A",
      logo: "BC",
      manifest: { version: "0.9.4", entry: "miniapps/bloom.html", bridge_scopes: ["pickup.request"], fallback_card: "service_comparison" }
    },
    {
      id: "foldpress",
      name: "Fold & Press Laundry",
      category: "Laundry",
      line: "Ironing · pickup and drop-off",
      distance: "1.0 km",
      color: "#A8843F",
      logo: "FP",
      manifest: { version: "3.0.0", entry: "miniapps/foldpress.html", bridge_scopes: ["quote.request"], fallback_card: "service_comparison" }
    }
  ]
};
