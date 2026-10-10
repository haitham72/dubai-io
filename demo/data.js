// Demo fixtures. Every value here is illustrative demo data (provenance: demo_fixture), not live information.
// Prices, distances, ratings and times render with a "Demo data" or "Estimate" pill. Merchants are fictional.

window.DEMO = {
  // Scripted scenario: 00:40 on a weekday (not Friday night). The clock never reads the machine time.
  scenario: { clock: "00:40", hotelClock: "01:25", weekday: "Wed", provenance: "demo_fixture" },

  flight: { number: "EK 002 (demo)", airport: "DXB", terminalId: "T3", terminal: "Terminal 3" },
  terminals: { T1: "Terminal 1", T2: "Terminal 2", T3: "Terminal 3" },

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
      body: "Find your flight on the screens to see your belt number. I don't guess belts. If you want, tell me the number and I'll remember it.",
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

  // Placeholder maps (to be replaced). pin = [x%, y%] of the terminal on that image.
  maps: [
    { id: "overview", label: "DXB", src: "maps/dxb-overview.png", title: "Dubai International (DXB)", pin: [60, 61], pinLabel: "Terminal 3 (your flight)", note: "Overview of all terminals and concourses." },
    { id: "checkin", label: "Check-in", src: "maps/t3-check-in.jpg", title: "T3 · Check-in", note: "Check-in hall layout." },
    { id: "dutyfree", label: "Duty Free", src: "maps/t3-duty-free.jpg", title: "T3 · Duty Free", note: "Shops, food and transfer routes." },
    { id: "lounge", label: "Lounge", src: "maps/t3-business-lounge.jpg", title: "T3 · Business Class Lounge", note: "Lounge services and gates." }
  ],

  zones: ["Gate", "Passport", "Baggage", "Customs", "Arrivals", "Taxi / Metro"],

  // Ride estimates (provenance: estimate, shown with Estimate + Demo data pills).
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
  estimate_as_of: "2026-10-10",

  // Ride rule table. Inputs: weekday + local time + terminal. Deterministic, no LLM.
  // Simplified demo timetable (provenance: demo_fixture). Verify the real timetable on RTA.
  //   first_train          : first Metro service of the day
  //   late_close_min[day]  : minutes AFTER midnight (on that calendar weekday) until which trains still run.
  //                          0 = service ends at midnight. Friday runs later.
  //   no_metro_terminals   : terminals with no Metro station -> reason shown
  rules: {
    provenance: "demo_fixture",
    as_of: "2026-10-10",
    metro: {
      first_train: "05:00",
      late_close_min: { Mon: 0, Tue: 0, Wed: 0, Thu: 0, Fri: 60, Sat: 0, Sun: 0 },
      no_metro_terminals: { T2: "Terminal 2 has no Metro station" }
    }
  },

  categories: ["Laundry", "Pharmacy"],

  // Service registry: each merchant ships its own mini-app with a manifest and a published fixed price list.
  // The HOST rebuilds every total from price_list + typed item ids. Widget-side numbers are never trusted.
  // sim = what the simulated merchant does in the backstage inbox (first_ready_by on accept, earlier_ready_by when asked).
  merchants: [
    {
      id: "suds",
      name: "Suds & Co. Express",
      category: "Laundry",
      line: "Wash and press · express",
      color: "#0E7FA8",
      logo: "S&C",
      distance_km: 0.4,
      rating: 4.3,
      rating_count: 88,
      turnaround: "~90 min",
      open_now: true,
      hours_note: "Open 24h",
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "1.4.0", entry: "miniapps/suds.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "shirt_press", name: "Shirt, pressed", price: 6 },
          { id: "shirt_wash_press", name: "Shirt, washed and pressed", price: 10 },
          { id: "trouser_press", name: "Trousers, pressed", price: 8 }
        ]
      },
      sim: { first_ready_by: "08:00", earlier_ready_by: "07:30" }
    },
    {
      id: "crispcollar",
      name: "Crisp Collar Cleaners",
      category: "Laundry",
      line: "Premium pressing · hand finish",
      color: "#1B1F2E",
      logo: "CC",
      distance_km: 0.8,
      rating: 4.8,
      rating_count: 301,
      turnaround: "Same day",
      open_now: false,
      hours_note: "Opens 07:00",
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "2.1.0", entry: "miniapps/crispcollar.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "shirt_press", name: "Shirt, hand pressed", price: 8 },
          { id: "trouser_press", name: "Trousers, hand pressed", price: 9 },
          { id: "thobe_press", name: "Thobe, pressed", price: 14 }
        ]
      },
      sim: { first_ready_by: "09:30", earlier_ready_by: "08:45" }
    },
    {
      id: "foldpress",
      name: "Fold & Press Laundry",
      category: "Laundry",
      line: "Ironing · pickup and drop-off",
      color: "#A8843F",
      logo: "FP",
      distance_km: 0.8,
      rating: 4.6,
      rating_count: 212,
      turnaround: "~2 h",
      open_now: true,
      hours_note: "Open until 02:00",
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "3.1.0", entry: "miniapps/foldpress.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "shirt_press", name: "Shirt, pressed", price: 5 },
          { id: "trouser_press", name: "Trousers, pressed", price: 7 },
          { id: "suit_jacket", name: "Suit jacket, pressed", price: 15 }
        ]
      },
      sim: { first_ready_by: "10:00", earlier_ready_by: "08:30" }
    },

    // Browse-only in the Services tab. Off the main path: the host will not start an order for these (orderable: false).
    {
      id: "palmleaf",
      name: "Palm Leaf Pharmacy",
      category: "Pharmacy",
      line: "Everyday medicines · delivery",
      color: "#2F7D5B",
      logo: "PL",
      distance_km: 0.8,
      rating: 4.4,
      rating_count: 57,
      turnaround: "~45 min",
      open_now: true,
      hours_note: "Open until 23:00",
      orderable: false,
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "1.3.0", entry: "miniapps/palmleaf.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "paracetamol", name: "Paracetamol 500mg x24", price: 9 },
          { id: "ors", name: "Oral rehydration salts x10", price: 18 },
          { id: "sunscreen", name: "Sunscreen SPF 50", price: 59 },
          { id: "nasal_spray", name: "Saline nasal spray", price: 22 },
          { id: "plasters", name: "Blister plasters", price: 16 },
          { id: "lip_balm", name: "Lip balm", price: 12 }
        ]
      },
      sim: { first_ready_by: "10:00", earlier_ready_by: "09:00" }
    },
    {
      id: "nightowl",
      name: "Night Owl Pharmacy 24h",
      category: "Pharmacy",
      line: "Open 24h · over-the-counter",
      color: "#1E2A4A",
      logo: "NO",
      distance_km: 1.4,
      rating: 4.5,
      rating_count: 133,
      turnaround: "~30 min",
      open_now: true,
      hours_note: "Open 24h",
      orderable: false,
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "2.1.0", entry: "miniapps/nightowl.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "paracetamol", name: "Paracetamol 500mg x24", price: 10 },
          { id: "throat_lozenges", name: "Throat lozenges x16", price: 14 },
          { id: "antacid", name: "Antacid tablets x20", price: 17 }
        ]
      },
      sim: { first_ready_by: "10:00", earlier_ready_by: "09:00" }
    },
    {
      id: "bloom",
      name: "Bloom Care",
      category: "Pharmacy",
      line: "Wellness and travel kits",
      color: "#B4587A",
      logo: "BC",
      distance_km: 2.1,
      rating: 4.7,
      rating_count: 41,
      turnaround: "~30 min",
      open_now: true,
      hours_note: "Open until 22:00",
      orderable: false,
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "1.0.0", entry: "miniapps/bloom.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: true },
      price_list: {
        version: "2026-10-10", provenance: "merchant_submitted",
        items: [
          { id: "jetlag_kit", name: "Jet-lag kit", price: 79 },
          { id: "sun_kit", name: "Sun care kit", price: 95 },
          { id: "baby_kit", name: "Baby travel kit", price: 68 }
        ]
      },
      sim: { first_ready_by: "10:00", earlier_ready_by: "09:00" }
    }
  ],

  // Onboarding beat: a price-list photo (simulated) -> extracted catalog -> the SAME mini-app template filled from it.
  // No OCR runs in this demo. The "extracted" lines are a fixture, and the photo is a drawing.
  onboarding: {
    photo_lines: ["CLEAN SLATE", "Shirt press ...... 4", "Trousers ......... 6", "Dress press ..... 12", "Open 7 days"],
    shop: {
      id: "cleanslate",
      name: "Clean Slate Laundry",
      category: "Laundry",
      line: "Pressing · new on Dubai-io",
      color: "#6B4FBB",
      logo: "CS",
      distance_km: 0.6,
      rating: null,
      rating_count: null,
      turnaround: "~2 h",
      open_now: true,
      hours_note: "Open 7 days",
      provenance: "demo_fixture",
      as_of: "2026-10-10",
      manifest: { version: "0.1.0", entry: "miniapps/template.html", bridge_scopes: ["order.request"], fallback_card: "service_comparison", approved: false, generated: true },
      price_list: {
        version: "draft-1", provenance: "merchant_submitted",
        items: [
          { id: "shirt_press", name: "Shirt press", price: 4 },
          { id: "trouser_press", name: "Trousers press", price: 6 },
          { id: "dress_press", name: "Dress press", price: 12 }
        ]
      },
      sim: { first_ready_by: "08:15", earlier_ready_by: "08:00" }
    }
  }
};
