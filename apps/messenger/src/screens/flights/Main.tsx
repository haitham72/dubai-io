// Flights main workspace: prompt bar, destinations, search card, recents, results.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeftRight, Car, Hotel, Minus, Plane, Plus, RotateCcw, Search, Sparkles,
} from "lucide-react";
import { ICON, ImageCard, SectionTitle, Segmented, Spinner } from "../../ui";
import { searchFlights } from "../../api";
import type { Flight } from "../../types";
import { CITIES, DESTINATIONS, RECENT_SEARCHES, cityName, resolveCity } from "./data";
import { flightUi, useFlightsUi, type Trip } from "./ui";
import { cabinLabel, flightDates, passengerLabel } from "./format";
import { FlightRow } from "./FlightRow";
import s from "./flights.module.css";

type Cabin = "economy" | "business" | "first";
type Status = "idle" | "loading" | "done" | "error";

const iso = (d: Date) => d.toISOString().slice(0, 10);
const plusDays = (n: number) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };

function parsePrompt(text: string): { from?: string; to?: string } {
  const t = text.trim().toLowerCase();
  if (!t) return {};
  const m = t.match(/(.+?)\s+to\s+(.+)/);
  if (m) {
    const out: { from?: string; to?: string } = {};
    const a = resolveCity(m[1]);
    const b = resolveCity(m[2]);
    if (m[1].trim()) out.from = a;
    if (m[2].trim()) out.to = b;
    return out;
  }
  const toM = t.match(/^to\s+(.+)/);
  if (toM) return { to: resolveCity(toM[1]) };
  for (const c of CITIES) {
    if (t.includes(c.name.toLowerCase()) || t.split(/\s+/).includes(c.code.toLowerCase())) {
      return { to: c.code };
    }
  }
  return {};
}

export function FlightsMain() {
  const storeTrip = useFlightsUi((u) => u.trip);
  const prefill = useFlightsUi((u) => u.prefill);

  const [trip, setTrip] = useState<Trip>("return");
  const [from, setFrom] = useState("DXB");
  const [to, setTo] = useState("LHR");
  const [depart, setDepart] = useState(() => plusDays(7));
  const [ret, setRet] = useState(() => plusDays(14));
  const [pax, setPax] = useState(1);
  const [cabin, setCabin] = useState<Cabin>("economy");
  const [tab, setTab] = useState<"flights" | "hotels" | "cars">("flights");
  const [prompt, setPrompt] = useState("");
  const [promptHint, setPromptHint] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [results, setResults] = useState<Flight[]>([]);
  const [summary, setSummary] = useState("");
  const formRef = useRef<HTMLDivElement>(null);

  // Sidebar intents (quick search, popular, new booking).
  const lastRun = useRef(0);
  useEffect(() => {
    if (prefill.run === lastRun.current) return;
    lastRun.current = prefill.run;
    if (prefill.trip) setTrip(prefill.trip);
    if (prefill.from) setFrom(prefill.from);
    if (prefill.to) setTo(prefill.to);
    if (prefill.search && prefill.to) {
      const effFrom = prefill.from ?? from;
      runSearch({ from: effFrom, to: prefill.to, depart, ret: (prefill.trip ?? trip) === "return" ? ret : undefined, passengers: pax, cabin });
    }
    if (!prefill.to && !prefill.from && !prefill.trip) {
      setStatus("idle"); // New Booking → back to browse
      formRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill.run]);

  useEffect(() => { setTrip(storeTrip); }, [storeTrip]);

  const runSearch = useCallback(async (q: {
    from: string; to: string; depart: string; ret?: string; passengers: number; cabin: Cabin;
  }) => {
    setStatus("loading");
    setSummary(`${q.from} → ${q.to} · ${flightDates(q.depart, q.ret)} · ${passengerLabel(q.passengers)} · ${cabinLabel(q.cabin)}`);
    try {
      const flights = await searchFlights({
        from: q.from, to: q.to, depart: q.depart,
        ...(q.ret ? { return: q.ret } : {}),
        passengers: q.passengers, cabin: q.cabin,
      });
      setResults(flights);
      setStatus("done");
    } catch {
      setResults([]);
      setStatus("error");
    }
  }, []);

  const submit = () => {
    const q = {
      from: resolveCity(from), to: resolveCity(to), depart,
      ret: trip === "return" ? ret : undefined, passengers: pax, cabin,
    };
    setFrom(q.from); setTo(q.to);
    runSearch(q);
  };

  const submitPrompt = (v: string) => {
    const p = parsePrompt(v);
    if (!p.from && !p.to) {
      setPromptHint("Try “Dubai to London”.");
      return;
    }
    setPromptHint("");
    const q = {
      from: p.from ?? resolveCity(from), to: p.to ?? resolveCity(to),
      depart, ret: trip === "return" ? ret : undefined, passengers: pax, cabin,
    };
    setFrom(q.from); setTo(q.to);
    runSearch(q);
  };

  const swap = () => { setFrom(to); setTo(from); };

  return (
    <div className={s.main}>
      <div className={s.promptBar}>
        <Sparkles size={16} strokeWidth={2} />
        <input
          placeholder="Where would you like to fly?"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submitPrompt((e.target as HTMLInputElement).value)}
          aria-label="Where would you like to fly?"
        />
        <button className={s.promptGo} onClick={() => submitPrompt(prompt)} aria-label="Ask">
          <Search size={16} strokeWidth={2} />
        </button>
      </div>
      {promptHint && <div className={s.hint}>{promptHint}</div>}

      <div className={s.destGrid}>
        {DESTINATIONS.map((d) => (
          <ImageCard
            key={d.code}
            src={d.photo}
            title={d.name}
            subtitle={d.price}
            ratio={4 / 3}
            onClick={() => { setTo(d.code); runSearch({ from: resolveCity(from), to: d.code, depart, ret: trip === "return" ? ret : undefined, passengers: pax, cabin }); }}
          />
        ))}
      </div>

      <div className={s.searchCard} ref={formRef}>
        <div className={s.tabs} role="tablist">
          {(["flights", "hotels", "cars"] as const).map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={tab === t}
              className={tab === t ? s.tabActive : s.tab}
              onClick={() => setTab(t)}
            >
              {t === "flights" ? <Plane size={16} strokeWidth={2} /> : t === "hotels" ? <Hotel size={16} strokeWidth={2} /> : <Car size={16} strokeWidth={2} />}
              {t[0].toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>

        {tab !== "flights" ? (
          <div className={s.muted}>{tab === "hotels" ? "Hotels" : "Cars"} are coming soon in this demo — flight search works today.</div>
        ) : (
          <>
            <div className={s.tripRow}>
              <Segmented<Trip>
                options={[{ value: "return", label: "Return" }, { value: "oneway", label: "One way" }]}
                value={trip}
                onChange={(v) => { setTrip(v); flightUi.setTrip(v); }}
              />
            </div>
            <div className={s.formGrid}>
              <label className={s.field}>
                <span>From</span>
                <input list="flight-cities" value={from} onChange={(e) => setFrom(e.target.value)} placeholder="DXB" />
              </label>
              <button className={s.swap} onClick={swap} aria-label="Swap origin and destination">
                <ArrowLeftRight {...ICON} />
              </button>
              <label className={s.field}>
                <span>To</span>
                <input list="flight-cities" value={to} onChange={(e) => setTo(e.target.value)} placeholder="LHR" />
              </label>
              <datalist id="flight-cities">
                {CITIES.map((c) => <option key={c.code} value={c.code}>{`${c.name} (${c.code})`}</option>)}
              </datalist>
              <label className={s.field}>
                <span>Departure</span>
                <input type="date" value={depart} min={iso(new Date())} onChange={(e) => setDepart(e.target.value)} />
              </label>
              <label className={s.field}>
                <span>Return</span>
                <input type="date" value={ret} min={depart} disabled={trip === "oneway"} onChange={(e) => setRet(e.target.value)} />
              </label>
              <div className={s.field}>
                <span>Passengers</span>
                <div className={s.stepper}>
                  <button onClick={() => setPax((p) => Math.max(1, p - 1))} aria-label="Fewer passengers"><Minus size={16} strokeWidth={2} /></button>
                  <strong>{pax}</strong>
                  <button onClick={() => setPax((p) => Math.min(9, p + 1))} aria-label="More passengers"><Plus size={16} strokeWidth={2} /></button>
                </div>
              </div>
              <label className={s.field}>
                <span>Class</span>
                <select value={cabin} onChange={(e) => setCabin(e.target.value as Cabin)}>
                  <option value="economy">Economy</option>
                  <option value="business">Business</option>
                  <option value="first">First</option>
                </select>
              </label>
            </div>
            <button className={s.searchBtn} onClick={submit}>
              <Search size={16} strokeWidth={2} /> Search Flights
            </button>
          </>
        )}
      </div>

      <SectionTitle action="See all" onAction={() => runSearch({ from: resolveCity(from), to: resolveCity(to), depart, ret: trip === "return" ? ret : undefined, passengers: pax, cabin })}>
        Recent Searches
      </SectionTitle>
      <div className={s.recentGrid}>
        {RECENT_SEARCHES.map((r) => (
          <button
            key={r.id}
            className={s.recent}
            title={`${r.from} → ${r.to} · ${flightDates(r.depart, r.ret)} · ${passengerLabel(r.passengers)} · ${cabinLabel(r.cabin)}`}
            onClick={() => {
              setFrom(r.from); setTo(r.to); setDepart(r.depart);
              if (r.ret) setRet(r.ret);
              setPax(r.passengers); setCabin(r.cabin);
              runSearch({ from: r.from, to: r.to, depart: r.depart, ret: r.ret, passengers: r.passengers, cabin: r.cabin });
            }}
          >
            <Plane size={16} strokeWidth={ICON.strokeWidth} />
            <span><strong>{r.from} → {r.to}</strong><small>{flightDates(r.depart, r.ret)}</small><small>{passengerLabel(r.passengers)} · {cabinLabel(r.cabin)} · {cityName(r.to)}</small></span>
          </button>
        ))}
      </div>

      {status !== "idle" && (
        <div className={s.results}>
          <SectionTitle>{summary || "Results"}</SectionTitle>
          {status === "loading" && <div className={s.stateRow}><Spinner /> Searching flights…</div>}
          {status === "error" && (
            <div className={s.stateRow}>
              <span>Flight search unavailable · <button className={s.retry} onClick={submit}><RotateCcw size={16} strokeWidth={2} /> Retry</button></span>
            </div>
          )}
          {status === "done" && results.length === 0 && <div className={s.muted}>No flights found for this search.</div>}
          {status === "done" && results.map((f) => <FlightRow key={f.id} f={f} query={{ depart }} />)}
        </div>
      )}

    </div>
  );
}
