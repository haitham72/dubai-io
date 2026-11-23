// Flights: server returns mock flights, or SerpAPI results when SERPAPI_KEY is set.
import type { Flight, FlightQuery } from "../types";
import { json } from "./http";

/* `strict` (the trip-planning flow) never substitutes mock fares: without a live provider the search fails
 * so the card can say it is unavailable instead of showing made-up prices. */
export async function searchFlights(q: FlightQuery, opts?: { strict?: boolean }): Promise<Flight[]> {
  const params = new URLSearchParams({
    from: q.from, to: q.to, depart: q.depart, passengers: String(q.passengers), cabin: q.cabin,
    ...(q.return ? { return: q.return } : {}),
    ...(opts?.strict ? { strict: "1" } : {}),
  });
  return json<Flight[]>(await fetch(`/api/flights?${params}`));
}
