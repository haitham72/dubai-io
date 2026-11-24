// GET /api/health → which live services are configured (booleans only, never values).
import { env, json, route } from "../lib/http.js";

export const GET = route(async () => json({
  ok: true,
  openai: !!env("OPENAI_API_KEY"), flights: !!env("SERPAPI_KEY"), stocks: !!env("FINNHUB_API_KEY"),
  research: !!(env("TVLY_API_KEY") || env("TAVILY_API_KEY")),
  images: false,
  videos: false,
}));
