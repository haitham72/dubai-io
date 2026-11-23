// GET /api/health → which live services are configured (booleans only, never values).
import { env, higgsAuth, json, route } from "../lib/http.js";

export const GET = route(async () => json({
  ok: true,
  openai: !!env("OPENAI_API_KEY"), flights: !!env("SERPAPI_KEY"), stocks: !!env("FINNHUB_API_KEY"),
  research: !!(env("TVLY_API_KEY") || env("TAVILY_API_KEY")),
  images: !!higgsAuth() && !!env("HIGGS_IMAGE_ENDPOINT") && env("MIRSAL_FAKE_IMAGES") !== "1",
  videos: !!higgsAuth() && env("MIRSAL_FAKE_VIDEOS", "1") !== "1",
}));
