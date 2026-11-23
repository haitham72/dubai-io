// Live prices for the watchlist (Finnhub via /api/stocks), refreshed every minute.
// Updates the watchlist entries in place so every view of them (sidebar, detail, Apps widget) shows live numbers;
// charts/sparklines stay the demo shapes. Without a key the API returns [] and the demo prices remain.
import { useEffect, useReducer } from "react";
import { getQuotes } from "../../api";
import { watchlist } from "./data";

const REFRESH_MS = 60_000;
const subscribers = new Set<() => void>();
let started = false;

async function refresh() {
  try {
    for (const q of await getQuotes(watchlist.map((s) => s.ticker))) {
      const stock = watchlist.find((s) => s.ticker === q.ticker);
      if (stock) Object.assign(stock, { price: q.price, change: q.change, changePct: q.changePct });
    }
    subscribers.forEach((render) => render());
  } catch { /* keep the last prices */ }
}

/** Re-render this component when live prices arrive. */
export function useLiveQuotes() {
  const [, render] = useReducer((n: number) => n + 1, 0);
  useEffect(() => {
    subscribers.add(render);
    if (!started) { started = true; void refresh(); window.setInterval(refresh, REFRESH_MS); }
    return () => { subscribers.delete(render); };
  }, []);
}
