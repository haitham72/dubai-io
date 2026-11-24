// GET /api/flights?from&to&depart&return?&passengers&cabin → Flight[]. SerpAPI when SERPAPI_KEY is set, else seeded mock.
import { env, fail, json, route } from "../lib/http.js";

const AIRLINES: [string, string][] = [
  ["Emirates", "EK"], ["flydubai", "FZ"], ["Etihad", "EY"], ["Qatar Airways", "QR"], ["Saudia", "SV"], ["Turkish", "TK"], ["British Airways", "BA"],
];

function displayDate(depart: string) {
  const d = /^\d{4}-\d{2}-\d{2}$/.test(depart) ? new Date(`${depart}T12:00:00Z`) : new Date();
  return d.toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", timeZone: "UTC" }).replace(",", ",");
}

/** Deterministic RNG per route/date so the same search shows the same flights. */
function rng(seed: string) {
  let h = 2166136261;
  for (const c of seed) h = Math.imul(h ^ c.charCodeAt(0), 16777619);
  return () => { h += 0x6d2b79f5; let t = h; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

function mock(from: string, to: string, depart: string, cabin: string) {
  const r = rng(`${from}|${to}|${depart}|${cabin}`);
  const int = (a: number, b: number) => a + Math.floor(r() * (b - a + 1));
  const n = 5 + int(0, 3);
  const pool = [...AIRLINES].sort(() => r() - 0.5);
  const mult = ({ economy: 1, business: 2.2, first: 3.5 } as Record<string, number>)[cabin] ?? 1;
  const pad = (x: number) => String(x).padStart(2, "0");
  const flights = Array.from({ length: n }, (_, i) => {
    const [airline, prefix] = pool[i % pool.length];
    const depH = int(0, 23), depM = int(0, 11) * 5, dur = int(180, 540);
    const arr = depH * 60 + depM + dur;
    return {
      id: `${from}-${to}-${depart}-${i}`, airline, flightNo: `${prefix} ${int(11, 989)}`, date: displayDate(depart),
      fromCode: from, fromTime: `${pad(depH)}:${pad(depM)}`, toCode: to, toTime: `${pad(Math.floor(arr / 60) % 24)}:${pad(arr % 60)}`,
      duration: `${Math.floor(dur / 60)}h ${pad(dur % 60)}m`, stops: r() < 0.45 ? 0 : 1,
      price: Math.round((int(800, 3200) * mult) / 10) * 10, currency: "AED", cabin: cabin[0].toUpperCase() + cabin.slice(1),
    };
  });
  flights.sort((a, b) => a.price - b.price);
  return flights.map((f, i) => (i === 0 ? { ...f, bestPrice: true } : f));
}

interface SerpLeg { flight_number?: string; departure_airport?: { time?: string }; arrival_airport?: { time?: string }; airline?: string; duration?: number }
interface SerpItem { flights?: SerpLeg[]; price?: number; total_duration?: number; airline?: string }

export const GET = route(async (req) => {
  const q = new URL(req.url).searchParams;
  const from = (q.get("from") ?? "").trim().toUpperCase(), to = (q.get("to") ?? "").trim().toUpperCase(), depart = q.get("depart") ?? "";
  const cabin = q.get("cabin") ?? "economy";
  // Strict mode (the trip-planning flow) never substitutes mock fares: an unavailable live search fails so the
  // card says so, and an empty live result stays empty ("no flights") instead of invented prices.
  const strict = q.get("strict") === "1";
  if (!from || !to || !depart) return fail(400, "from, to and depart are required");
  if (!["economy", "business", "first"].includes(cabin)) return fail(400, "cabin must be economy, business or first");

  const key = env("SERPAPI_KEY");
  if (!key) {
    if (strict) return fail(503, "flight search unavailable (no live provider)");
    return json(mock(from, to, depart, cabin));
  }

  const params = new URLSearchParams({ engine: "google_flights", departure_id: from, arrival_id: to, outbound_date: depart, currency: "AED", api_key: key, hl: "en" });
  const ret = q.get("return");
  params.set("type", ret ? "1" : "2");
  if (ret) params.set("return_date", ret);
  if (cabin !== "economy") params.set("travel_class", cabin === "business" ? "3" : "4");
  const res = await fetch(`https://serpapi.com/search.json?${params}`);
  if (!res.ok) {
    if (strict) return fail(502, "flight search failed");
    return json(mock(from, to, depart, cabin)); // keep the demo alive
  }
  const data = (await res.json()) as { best_flights?: SerpItem[]; other_flights?: SerpItem[] };
  const time = (t?: string) => (t ?? "").split(" ").pop() || "??:??";
  const out = [...(data.best_flights ?? []), ...(data.other_flights ?? [])].flatMap((it, i) => {
    const legs = it.flights ?? [];
    if (!legs.length || !it.price) return [];
    const mins = it.total_duration ?? 0;
    return [{
      id: `${from}-${to}-${depart}-${i}`, airline: it.airline ?? legs[0].airline ?? "Airline", flightNo: legs[0].flight_number ?? `${i + 100}`,
      date: displayDate(depart), fromCode: from, fromTime: time(legs[0].departure_airport?.time), toCode: to, toTime: time(legs[legs.length - 1].arrival_airport?.time),
      duration: mins ? `${Math.floor(mins / 60)}h ${String(mins % 60).padStart(2, "0")}m` : "—", stops: legs.length - 1,
      price: it.price, currency: "AED", cabin: cabin[0].toUpperCase() + cabin.slice(1),
    }];
  });
  if (!out.length && !strict) return json(mock(from, to, depart, cabin));
  out.sort((a, b) => a.price - b.price);
  return json(out.map((f, i) => (i === 0 ? { ...f, bestPrice: true } : f)));
});
