// Tiny sidebar↔main bridge for the Flights screen (shell renders them as siblings).
// Sidebar writes intents; Main subscribes and applies them. All inside src/screens/flights/**.
import { createStore } from "../../storeFactory";
import { SEED_BOOKINGS, type Booking } from "./data";

export type Trip = "return" | "oneway";

interface Prefill {
  to?: string;
  from?: string;
  trip?: Trip;
  search?: boolean;
  run: number; // bump to trigger Main
}

interface UiState {
  trip: Trip;
  bookings: Booking[];
  prefill: Prefill;
}

const flightStore = createStore<UiState>({ trip: "return", bookings: SEED_BOOKINGS, prefill: { run: 0 } });





export function useFlightsUi<T>(select: (s: UiState) => T): T {
  return flightStore.use(select);
}

const uid = () => Math.random().toString(36).slice(2, 10);

export const flightUi = {
  setTrip(trip: Trip) {
    flightStore.set({ trip });
  },
  /** Prefill the search form (and optionally run the search). One-shot: replaces the previous intent. */
  request(p: { to?: string; from?: string; trip?: Trip; search?: boolean }) {
    flightStore.update((s) => ({
      ...s,
      ...(p.trip ? { trip: p.trip } : {}),
      prefill: { to: p.to, from: p.from, trip: p.trip, search: p.search, run: s.prefill.run + 1 },
    }));
  },
  addBooking(b: Omit<Booking, "id">) {
    flightStore.update((s) => ({ ...s, bookings: [{ ...b, id: uid() }, ...s.bookings] }));
  },
  /** Reset to a fresh search (clears results, scrolls to the form). */
  newSearch() {
    flightStore.update((s) => ({ ...s, prefill: { run: s.prefill.run + 1 } }));
  },
};
