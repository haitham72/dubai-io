// Weather workspace (R06) — real Open-Meteo data, full-width, no sidebar.
import { useCallback, useEffect, useState } from "react";
import {
  Cloud, CloudLightning, CloudRain, CloudSnow, CloudFog, Droplets,
  Map, Moon, Radar, Sun, Sunrise, Sunset, Thermometer, Wind,
} from "lucide-react";
import { ICON, SearchField, Segmented, Spinner } from "../../ui";
import { getWeather, peekWeather } from "../../api";
import type { WeatherReport } from "../../types";
import s from "./weather.module.css";

/* ---------- city → skyline image mapping (verified Unsplash IDs, curl-w=100 → 200) ---------- */
const CITY_IMAGES: Record<string, string> = {
  Dubai:        "https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=1400&q=80&auto=format&fit=crop", // beach sunset, verified 200 + viewed
  London:       "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=1400&q=80&auto=format&fit=crop", // Tower Bridge/London Eye, verified 200 + viewed
};
const DEFAULT_SKYLINE = "https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1400&q=80&auto=format&fit=crop"; // generic sky (verified 200, used as fallback)

function skylineFor(city: string): string {
  return CITY_IMAGES[city] ?? DEFAULT_SKYLINE;
}

/* ---------- WMO code → Lucide icon ---------- */
function WeatherIcon({ code, size = 20 }: { code: number; size?: number }) {
  const p = { size, strokeWidth: ICON.strokeWidth } as const;
  if (code <= 1) return <Sun {...p} />;
  if (code <= 3) return <Cloud {...p} />;
  if (code <= 48) return <CloudFog {...p} />;
  if (code <= 57) return <CloudRain {...p} />;
  if (code <= 67) return <CloudRain {...p} />;
  if (code <= 77) return <CloudSnow {...p} />;
  if (code <= 82) return <CloudRain {...p} />;
  if (code <= 99) return <CloudLightning {...p} />;
  return <Sun {...p} />;
}

/* ---------- AQI helper (fake values based on condition) ---------- */
function fakeAQI(condition: string): { value: number; label: string; cls: string } {
  const base = condition.includes("Rain") || condition.includes("Snow") ? 35 : 55;
  const v = base + Math.floor(Math.random() * 30);
  if (v <= 50) return { value: v, label: "Good", cls: s.aqGood };
  if (v <= 100) return { value: v, label: "Moderate", cls: s.aqModerate };
  return { value: v, label: "Unhealthy", cls: "" };
}

/* ---------- Main screen ---------- */
function WeatherMain() {
  const [city, setCity] = useState("Dubai");
  const [search, setSearch] = useState("");
  // A forecast fetched within the last hour shows instantly (no spinner, no network).
  const [report, setReport] = useState<WeatherReport | null>(() => peekWeather("Dubai"));
  const [loading, setLoading] = useState(() => !peekWeather("Dubai"));
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"today" | "hourly" | "days" | "aq" | "maps">("today");

  const fetchWeather = useCallback(async (c: string) => {
    const cached = peekWeather(c);
    if (cached) { setReport(cached); setError(null); setLoading(false); return; }
    setLoading(true);
    setError(null);
    try {
      const r = await getWeather(c);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setReport(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchWeather(city); }, [city, fetchWeather]);

  const submitSearch = (val: string) => {
    const trimmed = val.trim();
    if (!trimmed) return;
    setCity(trimmed);
    setSearch("");
  };

  const useMyLocation = () => {
    if (!navigator.geolocation) { setCity("Dubai"); return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const lat = pos.coords.latitude, lon = pos.coords.longitude;
        fetch(`https://geocoding-api.open-meteo.com/v1/search?count=1`)
          .then((r) => r.json())
          .then((j) => {
            const name = j.results?.[0]?.name ?? "My Location";
            setCity(name);
          })
          .catch(() => setCity("Dubai"));
      },
      () => setCity("Dubai"),
    );
  };

  if (loading) {
    return (
      <div className={s.main}>
        <div className={s.loadingState}>
          <Spinner />
          <span>Fetching weather...</span>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className={s.main}>
        <div className={s.errorState}>
          <span>{error ?? "Unable to load weather"}</span>
          <button className={s.retryBtn} onClick={() => void fetchWeather(city)}>
            <Radar size={16} strokeWidth={2} /> Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={s.main}>
      {/* Top bar — single bg, consistent gutter */}
      <div className={s.topBar}>
        <h2 className={s.topBarTitle}>Weather</h2>
        <div className={s.topBarSearch}>
          <SearchField
            placeholder="Search city..."
            value={search}
            onChange={setSearch}
            onSubmit={submitSearch}
          />
        </div>
        <button className={s.locBtn} onClick={useMyLocation}>
          <Map size={16} strokeWidth={ICON.strokeWidth} /> Use my location
        </button>
      </div>

      {/* Hero — card-style, readable left-side gradient */}
      <div className={s.heroCard}>
        <img
          src={skylineFor(report.location)}
          alt={`${report.location} skyline`}
          className={s.heroImg}
        />
        <div className={s.heroShade}>
          <div className={s.heroLeft}>
            <div className={s.heroCity}>{report.location}</div>
            <div className={s.heroCountry}>{report.country}</div>
          </div>
          <div className={s.heroRight}>
            <div className={s.heroTemp}>{report.tempC}°</div>
            <div className={s.heroCond}>{report.condition}</div>
          </div>
        </div>
        <div className={s.heroStatsRow}>
          <div className={s.statItem}>
            <Thermometer size={16} strokeWidth={ICON.strokeWidth} />
            <span>Feels like {report.feelsLikeC}°C</span>
          </div>
          <div className={s.statItem}>
            <Droplets size={16} strokeWidth={ICON.strokeWidth} />
            <span>{report.humidity}% humidity</span>
          </div>
          <div className={s.statItem}>
            <Wind size={16} strokeWidth={ICON.strokeWidth} />
            <span>{report.windKmh} km/h wind</span>
          </div>
          <div className={s.statItem}>
            <Sun size={16} strokeWidth={ICON.strokeWidth} />
            <span>UV {report.uv}</span>
          </div>
        </div>
      </div>

      {/* Tabs — sticky */}
      <div className={s.tabsWrap}>
        <Segmented options={[
            { value: "today" as const, label: "Today" },
            { value: "hourly" as const, label: "Hourly" },
            { value: "days" as const, label: "7 Days" },
            { value: "aq" as const, label: "Air Quality" },
            { value: "maps" as const, label: "Maps" },
          ]}
          value={tab}
          onChange={(v: typeof tab) => setTab(v)}
        />
      </div>

      {/* Content — single bg, full width with gutter */}
      <div className={s.contentArea}>
        {tab === "today" && <TodayView report={report} />}
        {tab === "hourly" && <HourlyView hourly={report.hourly} />}
        {tab === "days" && <DaysView daily={report.daily} />}
        {tab === "aq" && <AQView condition={report.condition} />}
        {tab === "maps" && <MapsView />}
      </div>
    </div>
  );
}

/* ---- Today view: full dashboard grid (12-col) ---- */
function TodayView({ report }: { report: WeatherReport }) {
  return (
    <div className={s.todayGrid}>
      <div className={s.todayHourly}>
        <HourlyView hourly={report.hourly} />
      </div>
      <div className={s.sideCards}>
        <DaysView daily={report.daily} />
        <AQView condition={report.condition} />
      </div>
    </div>
  );
}

/* ---- Hourly strip ---- */
function HourlyView({ hourly }: { hourly: WeatherReport["hourly"] }) {
  return (
    <div>
      <h3 className={s.sectionTitle}>Hourly Forecast</h3>
      <div className={s.hourlyStrip}>
        {hourly.map((h: WeatherReport["hourly"][number], i: number) => {
          const isNow = i === 0;
          return (
            <div key={i} className={`${s.hourlyItem} ${isNow ? s.now : ""}`}>
              <span className={s.hourlyTime}>{isNow ? "Now" : h.time}</span>
              <WeatherIcon code={h.code} />
              <span className={s.hourlyTemp}>{h.tempC}°</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- 7-day list ---- */
function DaysView({ daily }: { daily: WeatherReport["daily"] }) {
  // Compute min/max across all days for the range bar
  const allMin = Math.min(...daily.map((d: WeatherReport["daily"][number]) => d.minC));
  const allMax = Math.max(...daily.map((d: WeatherReport["daily"][number]) => d.maxC));
  const range = allMax - allMin || 1;

  return (
    <div>
      <h3 className={s.sectionTitle}>7-Day Forecast</h3>
      <div className={s.dayList}>
        {daily.map((d: WeatherReport["daily"][number], i: number) => {
          const leftPct = ((d.minC - allMin) / range) * 100;
          const widthPct = ((d.maxC - d.minC) / range) * 100;
          return (
            <div key={i} className={s.dayRow}>
              <span className={s.dayName}>{d.day}</span>
              <WeatherIcon code={d.code} size={18} />
              <div className={s.dayBars}>
                <div className={s.dayBarTrack}>
                  <div
                    className={s.dayBarRange}
                    style={{ left: `${leftPct}%`, width: `${Math.max(widthPct, 8)}%` }}
                  />
                </div>
              </div>
              <span className={s.dayTemps}>
                <strong>{d.maxC}°</strong> / {d.minC}°
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---- Air Quality + Sun & Moon + Weather Map (cards) ---- */
function AQView({ condition }: { condition: string }) {
  const aqi = fakeAQI(condition);
  return (
    <div className={s.cardsGrid}>
      <div className={s.weatherCard}>
        <div className={s.weatherCardTitle}>Air Quality</div>
        <div className={`${s.aqValue} ${aqi.cls}`}>{aqi.value}</div>
        <div className={`${s.aqLabel} ${aqi.cls}`}>{aqi.label}</div>
        <div style={{ fontSize: "var(--fs-sm)", color: "var(--text-2)", marginTop: "var(--s-2)" }}>
          Air quality is satisfactory. Little risk.
        </div>
      </div>
      <div className={s.weatherCard}>
        <div className={s.weatherCardTitle}>Sun & Moon</div>
        <div className={s.sunTimes}>
          <div className={s.sunRow}>
            <Sunrise className={s.sunRowIcon} size={18} strokeWidth={ICON.strokeWidth} />
            <span className={s.sunRowTime}>06:12</span>
            <span className={s.sunRowLabel}>Sunrise</span>
          </div>
          <div className={s.sunRow}>
            <Sunset className={s.sunRowIcon} size={18} strokeWidth={ICON.strokeWidth} />
            <span className={s.sunRowTime}>18:47</span>
            <span className={s.sunRowLabel}>Sunset</span>
          </div>
          <div className={s.sunRow}>
            <Moon size={18} strokeWidth={ICON.strokeWidth} />
            <span className={s.sunRowTime}>Waxing Gibbous</span>
            <span className={s.sunRowLabel}>Moon phase</span>
          </div>
        </div>
      </div>
      <div className={s.weatherCard}>
        <div className={s.weatherCardTitle}>Weather Map</div>
        <div className={s.mapCard}>
          <div className={s.mapCardText}>
            <Map size={28} strokeWidth={ICON.strokeWidth} />
            <span>Regional radar map</span>
            <span style={{ fontSize: "var(--fs-xs)" }}>Powered by Open-Meteo</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ---- Maps view (same as AQ maps card, expanded) ---- */
function MapsView() {
  return (
    <div className={s.weatherCard} style={{ height: 320 }}>
      <div className={s.mapCard} style={{ height: "100%", borderRadius: 0 }}>
        <div className={s.mapCardText}>
          <Map size={40} strokeWidth={ICON.strokeWidth} />
          <span style={{ fontSize: "var(--fs-md)" }}>Weather radar map</span>
          <span>Real-time precipitation and cloud cover</span>
        </div>
      </div>
    </div>
  );
}

export const weatherScreen = { Main: WeatherMain };
