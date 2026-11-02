"use client";
import { useEffect, useState } from "react";
import { apiGet } from "../data/api";
import { detectUserLocation, placePhotoUrl, type UserLocation } from "../data/location";
import { searchPlaces, type Place } from "../data/places";
import { LiveMap } from "../maps/LiveMap";
import { useThreads } from "../data/threads";
import { useApp } from "../state";
import { Button, DemoPill } from "../ui";
import s from "./dashboard.module.css";

interface PrayerOk {
  status: "ok";
  city: string;
  date: string;
  timings: Record<string, string>;
  source: string;
  provenance?: string;
}
interface PrayerBad { status: "unavailable"; reason?: string }

interface Weather {
  temp: number;
  weathercode: number;
  wind: number;
  as_of: string;
}

interface Article {
  id?: string;
  title?: string;
  url?: string;
  source?: string;
  snippet?: string;
}

interface Reading {
  articles?: Article[];
  status?: string;
  attribution?: string;
  checked_at?: string;
}

interface Told { key?: string; value?: string }

function weatherLabel(code: number): string {
  if (code === 0) return "Clear";
  if (code <= 3) return "Partly cloudy";
  if (code <= 48) return "Fog";
  if (code <= 67) return "Rain";
  if (code <= 77) return "Snow / ice";
  if (code <= 82) return "Showers";
  return "Stormy";
}

async function fetchWeather(lat: number, lng: number): Promise<Weather> {
  const url =
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lng}&current=temperature_2m,weather_code,wind_speed_10m&timezone=Asia%2FDubai`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("weather");
  const data = await res.json();
  const cur = data.current;
  return {
    temp: cur.temperature_2m,
    weathercode: cur.weather_code,
    wind: cur.wind_speed_10m,
    as_of: cur.time,
  };
}

export function DashboardView() {
  const { setScreen, openThread } = useApp();
  const { threads } = useThreads();
  const [prayer, setPrayer] = useState<PrayerOk | PrayerBad | null>(null);
  const [weather, setWeather] = useState<Weather | null>(null);
  const [weatherErr, setWeatherErr] = useState<string | null>(null);
  const [news, setNews] = useState<Reading | null>(null);
  const [told, setTold] = useState<Told[]>([]);
  const [loc, setLoc] = useState<UserLocation | null>(null);
  const [nearby, setNearby] = useState<Place[]>([]);
  const [picked, setPicked] = useState<Place | null>(null);

  useEffect(() => {
    let alive = true;
    apiGet<PrayerOk | PrayerBad>("/api/prayer-times")
      .then((d) => { if (alive) setPrayer(d); })
      .catch(() => { if (alive) setPrayer({ status: "unavailable", reason: "Prayer times unavailable." }); });
    apiGet<Reading>("/api/reading?topic=for_you")
      .then((d) => { if (alive) setNews(d); })
      .catch(() => { if (alive) setNews({ status: "unavailable", articles: [] }); });
    apiGet<{ told?: Told[] }>("/api/session/memory")
      .then((d) => { if (alive) setTold(d.told ?? []); })
      .catch(() => { if (alive) setTold([]); });
    detectUserLocation().then(async (here) => {
      if (!alive) return;
      setLoc(here);
      fetchWeather(here.lat, here.lng)
        .then((w) => { if (alive) setWeather(w); })
        .catch(() => { if (alive) setWeatherErr("Weather unavailable."); });
      try {
        const res = await searchPlaces("coffee shops", here);
        if (!alive) return;
        setNearby(res.places.slice(0, 5));
        setPicked(res.places[0] ?? null);
      } catch { /* map strip optional */ }
    });
    return () => { alive = false; };
  }, []);

  const needs = threads.filter((t) => t.lane === "needs_you").slice(0, 5);
  const open = threads.slice(0, 8);

  return (
    <div className={s.page} data-testid="dashboard-view">
      <div className={s.inner}>
        <header className={s.head}>
          <h1>Dashboard</h1>
          <p className={s.lede}>
            Live weather, prayer times, your threads, and headlines — measured providers only. Connectors (mail/calendar) stay later.
          </p>
        </header>

        <div className={s.grid}>
          <section className={`${s.card} ${s.wide}`} aria-labelledby="near-title" data-testid="dashboard-map">
            <h2 id="near-title">Near you</h2>
            <p>{loc ? loc.label : "Detecting location…"} · coffee nearby (live Places)</p>
            {loc && (
              <LiveMap
                center={loc}
                places={nearby}
                selected={picked}
                onSelect={setPicked}
                compact
              />
            )}
            <ul className={s.list}>
              {nearby.map((p) => {
                const photo = placePhotoUrl(p.photo, 160);
                return (
                  <li key={p.id || p.name} className={s.row}>
                    <button type="button" onClick={() => setPicked(p)} style={{ all: "unset", cursor: "pointer", display: "flex", gap: 10, flex: 1, alignItems: "center" }}>
                      {photo ? <img src={photo} alt="" width={40} height={40} style={{ borderRadius: 8, objectFit: "cover" }} /> : null}
                      <div>
                        <b>{p.name}</b>
                        <small>{p.rating != null ? `★ ${Number(p.rating).toFixed(1)}` : "No rating"} · provider_confirmed</small>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
            <div className={s.actions}>
              <Button variant="primary" onClick={() => setScreen("maps")}>Open interactive Maps</Button>
            </div>
          </section>

          <section className={s.card} aria-labelledby="weather-title">
            <h2 id="weather-title">Weather · near you</h2>
            {weatherErr && <p className={s.err}>{weatherErr}</p>}
            {weather && (
              <>
                <div className={s.weather}>
                  <strong>{Math.round(weather.temp)}°</strong>
                  <div>
                    <p>{weatherLabel(weather.weathercode)}</p>
                    <p>Wind {Math.round(weather.wind)} km/h</p>
                  </div>
                </div>
                <p className={s.foot}>Open-Meteo · provider_confirmed · {weather.as_of}</p>
              </>
            )}
            {!weather && !weatherErr && <p>Loading…</p>}
          </section>

          <section className={s.card} aria-labelledby="prayer-title">
            <h2 id="prayer-title">Prayer times</h2>
            {!prayer && <p>Loading…</p>}
            {prayer?.status === "unavailable" && <p className={s.err}>{prayer.reason || "Unavailable"}</p>}
            {prayer?.status === "ok" && (
              <>
                <p>{prayer.city} · {prayer.date}</p>
                <div className={s.timings}>
                  {Object.entries(prayer.timings).map(([name, time]) => (
                    <div key={name} className={s.timing}>
                      <span>{name}</span>
                      <b>{time}</b>
                    </div>
                  ))}
                </div>
                <p className={s.foot}>{prayer.source} · {prayer.provenance || "provider_confirmed"}</p>
              </>
            )}
          </section>

          <section className={s.card} aria-labelledby="tasks-title">
            <h2 id="tasks-title">Needs you</h2>
            {needs.length === 0 ? <p>Nothing waiting on you right now.</p> : (
              <ul className={s.list}>
                {needs.map((t) => (
                  <li key={t.id} className={s.row}>
                    <button type="button" onClick={() => openThread(t.id)} style={{ all: "unset", cursor: "pointer" }}>
                      <b>{t.title}</b>
                      <small>{t.preview}</small>
                    </button>
                    {t.demo && <DemoPill />}
                  </li>
                ))}
              </ul>
            )}
            <div className={s.actions}>
              <Button variant="secondary" onClick={() => setScreen("assistant")}>Open Assistant</Button>
            </div>
          </section>

          <section className={s.card} aria-labelledby="memory-title">
            <h2 id="memory-title">You told me</h2>
            {told.length === 0 ? <p>Nothing saved yet — tell me your area or size in chat.</p> : (
              <ul className={s.list}>
                {told.map((f) => (
                  <li key={f.key} className={s.row}>
                    <div>
                      <b>{f.key}</b>
                      <small>{f.value}</small>
                    </div>
                    <span className={s.pill}>You told me</span>
                  </li>
                ))}
              </ul>
            )}
            <div className={s.actions}>
              <Button variant="secondary" onClick={() => setScreen("me")}>Open Me</Button>
            </div>
          </section>

          <section className={`${s.card} ${s.wide}`} aria-labelledby="threads-title">
            <h2 id="threads-title">Open threads</h2>
            <ul className={s.list}>
              {open.map((t) => (
                <li key={t.id} className={s.row}>
                  <button type="button" onClick={() => openThread(t.id)} style={{ all: "unset", cursor: "pointer", flex: 1 }}>
                    <b>{t.title}</b>
                    <small>{t.preview}</small>
                  </button>
                  {t.demo ? <DemoPill /> : <span className={s.pill}>{t.lane}</span>}
                </li>
              ))}
            </ul>
          </section>

          <section className={`${s.card} ${s.wide}`} aria-labelledby="news-title">
            <h2 id="news-title">Headlines</h2>
            {news?.status === "unavailable" && <p className={s.err}>News feed unavailable right now.</p>}
            {(news?.articles?.length ?? 0) === 0 && news?.status !== "unavailable" && <p>No headlines yet.</p>}
            <ul className={s.list}>
              {(news?.articles ?? []).slice(0, 6).map((a, i) => (
                <li key={a.id || i} className={s.row}>
                  <div>
                    {a.url?.startsWith("https://") ? (
                      <a href={a.url} target="_blank" rel="noopener noreferrer">{a.title || "Article"}</a>
                    ) : (
                      <b>{a.title || "Article"}</b>
                    )}
                    <small>{[a.source, a.snippet].filter(Boolean).join(" · ")}</small>
                  </div>
                </li>
              ))}
            </ul>
            {news?.attribution && <p className={s.foot}>{news.attribution}{news.checked_at ? ` · ${news.checked_at}` : ""}</p>}
            <div className={s.actions}>
              <Button variant="secondary" onClick={() => setScreen("maps")}>Open Maps</Button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
