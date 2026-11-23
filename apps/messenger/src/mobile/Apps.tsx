// Mobile Apps tab: live widgets on top, then every workspace as an App Store-style row (icon · name · subtitle · OPEN).
import { useEffect, useState } from "react";
import type { ComponentType } from "react";
import type { LucideProps } from "lucide-react";
import { ChartSpline, Clock3, CloudSun, Folder, Mail, Navigation, Plane, Telescope, TrendingUp } from "lucide-react";
import { actions, useStore } from "../store";
import { getWeather, peekWeather } from "../api";
import type { ScreenId, WeatherReport } from "../types";
import { watchlist } from "../screens/stocks/data";
import { useLiveQuotes } from "../screens/stocks/live";
import { emails } from "../screens/mail/data";
import { seedEvents } from "../screens/calendar/data";
import { LargeTitle } from "./parts";
import s from "./mobile.module.css";

/** icon null = drawn by hand (the Calendar tile shows today's weekday + date, like iOS). */
type App = { id: ScreenId; label: string; sub: string; icon: ComponentType<LucideProps> | null; tile: string };
export const APPS: App[] = [
  { id: "files", label: "Files", sub: "Photos, documents & AI creations", icon: Folder, tile: s.tileFiles },
  { id: "flights", label: "Flights", sub: "Search fares and track trips", icon: Plane, tile: s.tileFlights },
  { id: "weather", label: "Weather", sub: "Live forecasts for your cities", icon: CloudSun, tile: s.tileWeather },
  { id: "calendar", label: "Calendar", sub: "Your schedule, shared with Messenger", icon: null, tile: s.tileCalendar },
  { id: "stocks", label: "Stocks", sub: "Live watchlist and markets", icon: ChartSpline, tile: s.tileStocks },
  { id: "mail", label: "Mail", sub: "Inbox with Messenger drafts", icon: Mail, tile: s.tileMail },
  { id: "research", label: "Research", sub: "Deep web research briefs", icon: Telescope, tile: s.tileResearch },
  { id: "history", label: "History", sub: "Everything Messenger did for you", icon: Clock3, tile: s.tileHistory },
];

/** iOS-style app icon: squircle tile, top-lit gradient, white glyph (Files and Calendar use a white tile). */
export function AppIcon({ app, size = 60 }: { app: App; size?: number }) {
  const I = app.icon;
  const today = new Date();
  return (
    <span className={`${s.appIcon} ${app.tile}`} style={{ "--icon": `${size}px` } as React.CSSProperties} aria-hidden>
      {I ? <I size={Math.round(size * 0.5)} strokeWidth={2} fill={app.id === "files" ? "currentColor" : "none"} /> : (
        <span className={s.calIcon}>
          <b>{today.toLocaleDateString("en", { weekday: "short" })}</b>
          <span>{today.getDate()}</span>
        </span>
      )}
    </span>
  );
}

function WeatherWidget() {
  const [w, setW] = useState<WeatherReport | null>(() => peekWeather("Dubai"));
  useEffect(() => { getWeather("Dubai").then(setW).catch(() => {}); }, []);
  return (
    <button className={`${s.widget} ${s.widgetSky}`} onClick={() => actions.navigate("weather")}>
      <span className={s.wLabel}>{w?.location ?? "Dubai"} <Navigation size={12} strokeWidth={2} /></span>
      <span className={s.wBig}>{w ? `${w.tempC}°` : "—"}</span>
      <span className={s.wSmall}><b>{w?.condition ?? "Loading…"}</b>{w && `H:${w.daily[0]?.maxC}° L:${w.daily[0]?.minC}°`}</span>
    </button>
  );
}

function CalendarWidget() {
  const stored = useStore((st) => st.events);
  const today = new Date();
  const events = (stored.length ? stored : seedEvents(today))
    .filter((e) => new Date(e.end) >= today)
    .sort((a, b) => a.start.localeCompare(b.start))
    .slice(0, 2);
  const time = (iso: string) => new Date(iso).toLocaleString([], { weekday: "short", hour: "numeric", minute: "2-digit" });
  return (
    <button className={s.widget} onClick={() => actions.navigate("calendar")}>
      <span className={s.calDay}>{today.toLocaleDateString([], { weekday: "long" }).toUpperCase()}</span>
      <span className={s.calNum}>{today.getDate()}</span>
      {events.map((e, i) => (
        <span key={e.title + i} className={`${s.ev} ${i ? s.evAlt : ""}`}><b>{e.title}</b><span>{time(e.start)}</span></span>
      ))}
      {!events.length && <span className={s.ev}><b>No upcoming events</b></span>}
    </button>
  );
}

function Spark({ data, up }: { data: number[]; up: boolean }) {
  const min = Math.min(...data), max = Math.max(...data);
  const pts = data.map((v, i) => `${(i / (data.length - 1)) * 100},${24 - ((v - min) / (max - min || 1)) * 22}`).join(" ");
  return <svg className={s.spark} viewBox="0 0 100 26" preserveAspectRatio="none"><polyline points={pts} fill="none" strokeWidth="1.75" className={up ? s.upLine : s.downLine} /></svg>;
}

function StocksWidget() {
  useLiveQuotes();
  return (
    <button className={`${s.widget} ${s.widgetWide}`} onClick={() => actions.navigate("stocks")}>
      <span className={s.wLabelMuted}><TrendingUp size={14} strokeWidth={2} />Watchlist</span>
      {watchlist.slice(0, 3).map((st) => (
        <span key={st.ticker} className={s.tick}>
          <b>{st.ticker}</b>
          <Spark data={st.sparkline} up={st.changePct >= 0} />
          <span className={s.px}>{st.price.toFixed(2)}</span>
          <span className={`${s.chg} ${st.changePct >= 0 ? s.chgUp : s.chgDown}`}>{st.changePct >= 0 ? "+" : "−"}{Math.abs(st.changePct).toFixed(2)}%</span>
        </span>
      ))}
    </button>
  );
}

export function AppsHome() {
  const unreadMail = emails.filter((e) => (e as { unread?: boolean }).unread).length;
  return (
    <div className={s.scroll}>
      <LargeTitle title="Apps" />
      <div className={s.widgets}>
        <WeatherWidget />
        <CalendarWidget />
        <StocksWidget />
      </div>
      <h2 className={s.sectionTitle}>All apps</h2>
      <div className={s.appList}>
        {APPS.map((app) => (
          <button key={app.id} className={s.appRow} onClick={() => actions.navigate(app.id)}>
            <AppIcon app={app} />
            <span className={s.appText}>
              <b>{app.label}</b>
              <small>{app.id === "mail" && unreadMail > 0 ? `${unreadMail} unread · ${app.sub}` : app.sub}</small>
            </span>
            <span className={s.openPill}>OPEN</span>
          </button>
        ))}
      </div>
    </div>
  );
}
