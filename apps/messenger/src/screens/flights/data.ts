// Flights fake data + city map. Photos verified: curl → 200 and viewed 2026-10-04.
import { img } from "../../ui";

export interface City {
  name: string;
  code: string;
}

export const CITIES: City[] = [
  { name: "Dubai", code: "DXB" },
  { name: "Abu Dhabi", code: "AUH" },
  { name: "Riyadh", code: "RUH" },
  { name: "Jeddah", code: "JED" },
  { name: "Cairo", code: "CAI" },
  { name: "London", code: "LHR" },
  { name: "Paris", code: "CDG" },
  { name: "Istanbul", code: "IST" },
  { name: "Doha", code: "DOH" },
  { name: "Amman", code: "AMM" },
  { name: "Beirut", code: "BEY" },
  { name: "New York", code: "JFK" },
  { name: "Singapore", code: "SIN" },
  { name: "Bangkok", code: "BKK" },
];

/** "dubai" / "dxb" / "Dubai (DXB)" → "DXB". Falls back to upper-cased input. */
export function resolveCity(raw: string): string {
  const t = raw.trim().toLowerCase();
  const hit = CITIES.find((c) => c.name.toLowerCase() === t || c.code.toLowerCase() === t);
  if (hit) return hit.code;
  const m = t.match(/\(([a-z]{3})\)/);
  if (m) return m[1].toUpperCase();
  return raw.trim().toUpperCase().slice(0, 4) || "DXB";
}

export function cityName(code: string): string {
  return CITIES.find((c) => c.code === code.toUpperCase())?.name ?? code.toUpperCase();
}

export interface Destination {
  code: string;
  name: string;
  price: string;
  photo: string;
}

export const DESTINATIONS: Destination[] = [
  { code: "DXB", name: "Dubai", price: "From AED 320", photo: img("photo-1512453979798-5ea266f8880c", 600) },
  { code: "RUH", name: "Riyadh", price: "From AED 740", photo: img("photo-1586724237569-f3d0c1dee8c6", 600) },
  { code: "CAI", name: "Cairo", price: "From AED 650", photo: img("photo-1503177119275-0aa32b3a9368", 600) },
  { code: "LHR", name: "London", price: "From AED 1,950", photo: img("photo-1513635269975-59663e0ac1ad", 600) },
];

export interface Booking {
  id: string;
  airline: string;
  route: string;
  date: string;
  status: "Confirmed" | "Upcoming";
}

export const SEED_BOOKINGS: Booking[] = [
  { id: "b1", airline: "Saudia", route: "DXB → JED", date: "12 Oct 2026", status: "Confirmed" },
  { id: "b2", airline: "EgyptAir", route: "CAI → DXB", date: "3 Nov 2026", status: "Upcoming" },
  { id: "b3", airline: "Emirates", route: "DXB → LHR", date: "20 Dec 2026", status: "Confirmed" },
];

export interface RecentSearch {
  id: string;
  from: string;
  to: string;
  depart: string; // YYYY-MM-DD
  ret?: string;
  passengers: number;
  cabin: "economy" | "business" | "first";
  label: string;
}

export const RECENT_SEARCHES: RecentSearch[] = [
  { id: "r1", from: "DXB", to: "LHR", depart: "2026-10-12", ret: "2026-10-20", passengers: 1, cabin: "economy", label: "DXB → LHR · 12–20 Oct · 1 pax" },
  { id: "r2", from: "DXB", to: "CAI", depart: "2026-11-05", ret: "2026-11-10", passengers: 2, cabin: "economy", label: "DXB → CAI · 5–10 Nov · 2 pax" },
  { id: "r3", from: "JED", to: "DXB", depart: "2026-09-18", ret: "2026-09-22", passengers: 1, cabin: "business", label: "JED → DXB · 18–22 Sep · 1 pax" },
  { id: "r4", from: "DXB", to: "RUH", depart: "2026-10-01", ret: "2026-10-03", passengers: 1, cabin: "economy", label: "DXB → RUH · 1–3 Oct · 1 pax" },
];

/** "5h 46m" → minutes. */
export function parseDuration(d: string): number {
  const h = d.match(/(\d+)\s*h/);
  const m = d.match(/(\d+)\s*m(?!o)/);
  return (h ? parseInt(h[1], 10) * 60 : 0) + (m ? parseInt(m[1], 10) : 0);
}

/** "2026-10-12" + "14:15" → ISO string (local time). */
export function toISO(date: string, time: string): string {
  const d = new Date(`${date}T${time}:00`);
  return isNaN(d.getTime()) ? new Date().toISOString() : d.toISOString();
}

export function addMinutes(iso: string, mins: number): string {
  return new Date(new Date(iso).getTime() + mins * 60000).toISOString();
}
