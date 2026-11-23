// Live stock quotes (Finnhub on the server; [] when not configured).
import { json } from "./http";

export interface Quote { ticker: string; price: number; change: number; changePct: number }
export async function getQuotes(symbols: string[]): Promise<Quote[]> {
  return json<Quote[]>(await fetch(`/api/stocks?symbols=${encodeURIComponent(symbols.join(","))}`));
}
