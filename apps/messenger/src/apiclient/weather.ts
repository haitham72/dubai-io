// Weather (Open-Meteo, called from the browser; no key).
import type { WeatherReport } from "../types";
import { json } from "./http";

const WMO: Record<number, string> = {
  0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Fog",
  51: "Drizzle", 53: "Drizzle", 55: "Drizzle", 61: "Light rain", 63: "Rain", 65: "Heavy rain",
  71: "Light snow", 73: "Snow", 75: "Heavy snow", 80: "Showers", 81: "Showers", 82: "Heavy showers",
  95: "Thunderstorm", 96: "Thunderstorm", 99: "Thunderstorm",
};
export const weatherLabel = (code: number) => WMO[code] ?? "—";

/* Cache: one fetch per city per hour, kept in localStorage so reloads and screen switches reuse it.
   If a refresh fails, the last saved report is used instead (however old). */
const WEATHER_TTL_MS = 60 * 60 * 1000;
const WEATHER_KEY = "mirsal.weather";
type WeatherCache = Record<string, { at: number; report: WeatherReport }>;
const cacheKey = (city: string) => city.trim().toLowerCase();
function readWeatherCache(): WeatherCache {
  try { return JSON.parse(localStorage.getItem(WEATHER_KEY) ?? "{}") as WeatherCache; } catch { return {}; }
}
function writeWeatherCache(city: string, report: WeatherReport) {
  const cache = readWeatherCache();
  cache[cacheKey(city)] = { at: Date.now(), report };
  try { localStorage.setItem(WEATHER_KEY, JSON.stringify(cache)); } catch { /* storage unavailable */ }
}
const inFlight = new Map<string, Promise<WeatherReport>>();

/** The saved report for a city if it is less than an hour old (for showing it instantly). */
export function peekWeather(city: string): WeatherReport | null {
  const hit = readWeatherCache()[cacheKey(city)];
  return hit && Date.now() - hit.at < WEATHER_TTL_MS ? hit.report : null;
}

export async function getWeather(city: string): Promise<WeatherReport> {
  const fresh = peekWeather(city);
  if (fresh) return fresh;
  const key = cacheKey(city);
  const pending = inFlight.get(key);
  if (pending) return pending;
  const run = fetchWeather(city)
    .then((report) => { writeWeatherCache(city, report); return report; })
    .catch((err) => {
      const stale = readWeatherCache()[key];
      if (stale) return stale.report;
      throw err;
    })
    .finally(() => inFlight.delete(key));
  inFlight.set(key, run);
  return run;
}

async function fetchWeather(city: string): Promise<WeatherReport> {
  const geo = await json<{ results?: { name: string; country: string; latitude: number; longitude: number }[] }>(
    await fetch(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1`),
  );
  const place = geo.results?.[0];
  if (!place) throw new Error(`No location found for "${city}"`);

  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${place.latitude}&longitude=${place.longitude}` +
    `&current=temperature_2m,apparent_temperature,relative_humidity_2m,wind_speed_10m,weather_code,uv_index` +
    `&hourly=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min,weather_code` +
    `&forecast_days=7&timezone=auto`;
  const d = await json<any>(await fetch(url));

  const nowIdx = Math.max(0, d.hourly.time.findIndex((t: string) => t >= d.current.time.slice(0, 13)));
  return {
    location: place.name,
    country: place.country,
    tempC: Math.round(d.current.temperature_2m),
    feelsLikeC: Math.round(d.current.apparent_temperature),
    condition: weatherLabel(d.current.weather_code),
    humidity: d.current.relative_humidity_2m,
    windKmh: Math.round(d.current.wind_speed_10m),
    uv: Math.round(d.current.uv_index ?? 0),
    hourly: d.hourly.time.slice(nowIdx, nowIdx + 12).map((t: string, i: number) => ({
      time: t.slice(11, 16),
      tempC: Math.round(d.hourly.temperature_2m[nowIdx + i]),
      code: d.hourly.weather_code[nowIdx + i],
      condition: weatherLabel(d.hourly.weather_code[nowIdx + i]),
    })),
    daily: d.daily.time.map((t: string, i: number) => ({
      day: new Date(t).toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" }),
      minC: Math.round(d.daily.temperature_2m_min[i]),
      maxC: Math.round(d.daily.temperature_2m_max[i]),
      code: d.daily.weather_code[i],
      condition: weatherLabel(d.daily.weather_code[i]),
    })),
  };
}
