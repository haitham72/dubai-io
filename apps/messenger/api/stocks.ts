// GET /api/stocks?symbols=AAPL,TSLA → [{ticker, price, change, changePct}] from Finnhub (empty list without a key).
import { env, json, route } from "../lib/http.js";

export const GET = route(async (req) => {
  const key = env("FINNHUB_API_KEY");
  const symbols = (new URL(req.url).searchParams.get("symbols") ?? "").split(",").map((s) => s.trim().toUpperCase()).filter(Boolean).slice(0, 12);
  if (!key || !symbols.length) return json([]);
  const quotes = await Promise.all(symbols.map(async (ticker) => {
    const res = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(ticker)}&token=${key}`);
    if (!res.ok) return null;
    const q = (await res.json()) as { c?: number; d?: number; dp?: number };
    return q.c ? { ticker, price: q.c, change: q.d ?? 0, changePct: q.dp ?? 0 } : null;
  }));
  return json(quotes.filter(Boolean));
});
