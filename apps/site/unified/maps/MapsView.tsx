"use client";
import { useCallback, useEffect, useState } from "react";
import { LocateFixed, Search } from "lucide-react";
import { businessHref, openBusinessSite } from "../data/open-business";
import { detectUserLocation, placePhotoUrl, type UserLocation } from "../data/location";
import { searchPlaces, type Place } from "../data/places";
import { Button } from "../ui";
import { LiveMap } from "./LiveMap";
import s from "./maps.module.css";

const QUICK = [
  { label: "Coffee", query: "coffee shops" },
  { label: "Gyms", query: "gym" },
  { label: "British schools", query: "British curriculum school" },
  { label: "Pharmacies", query: "pharmacy" },
];

export function MapsView() {
  const [loc, setLoc] = useState<UserLocation | null>(null);
  const [draft, setDraft] = useState("coffee shops");
  const [query, setQuery] = useState("");
  const [places, setPlaces] = useState<Place[]>([]);
  const [selected, setSelected] = useState<Place | null>(null);
  const [asOf, setAsOf] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshLocation = useCallback(async () => {
    const next = await detectUserLocation();
    setLoc(next);
    return next;
  }, []);

  useEffect(() => {
    void (async () => {
      const next = await refreshLocation();
      // First paint search near the user (or Marina fallback).
      setBusy(true);
      try {
        const res = await searchPlaces("coffee shops", next);
        setPlaces(res.places);
        setSelected(res.places[0] ?? null);
        setAsOf(res.as_of);
        setQuery("coffee shops");
      } catch {
        setError("Live Google Places unavailable right now.");
      } finally {
        setBusy(false);
      }
    })();
  }, [refreshLocation]);

  const run = async (q: string, at?: UserLocation) => {
    const text = q.trim();
    const center = at ?? loc;
    if (!text || !center) return;
    setBusy(true);
    setError(null);
    setQuery(text);
    setDraft(text);
    try {
      const res = await searchPlaces(text, center);
      setPlaces(res.places);
      setSelected(res.places[0] ?? null);
      setAsOf(res.as_of);
      if (!res.places.length) setError("No places matched near you. Try another search.");
    } catch {
      setPlaces([]);
      setSelected(null);
      setError("Live Google Places unavailable right now.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={s.page} data-testid="maps-view">
      <header className={s.head}>
        <h1>Maps</h1>
        <p className={s.lede}>
          Interactive Google Map inside Dubai-io — results near <strong>{loc?.label ?? "…"}</strong>
          {loc?.source === "fallback" ? " (allow location for your pin)" : ""}. Photos and ratings are live Places data.
        </p>
        <div className={s.locRow}>
          <span className={s.locChip} data-testid="maps-location" data-source={loc?.source ?? "pending"}>
            {loc ? loc.label : "Detecting location…"}
          </span>
          <Button variant="secondary" icon={LocateFixed} onClick={() => void refreshLocation().then((n) => run(draft || "coffee shops", n))}>
            Use my location
          </Button>
        </div>
        <div className={s.searchRow}>
          <input
            data-testid="maps-search"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void run(draft); }}
            placeholder="Search near you…"
            aria-label="Search places near you"
          />
          <Button variant="primary" icon={Search} onClick={() => void run(draft)} disabled={busy || !loc}>
            Search
          </Button>
        </div>
        <div className={s.chipRow} aria-label="Quick searches">
          {QUICK.map((q) => (
            <button
              key={q.label}
              type="button"
              className={`${s.chip} ${query === q.query ? s.chipActive : ""}`}
              onClick={() => void run(q.query)}
            >
              {q.label}
            </button>
          ))}
        </div>
      </header>

      <div className={s.body}>
        <section className={s.mapPane} aria-label="Map">
          {loc && (
            <LiveMap
              center={loc}
              places={places}
              selected={selected}
              onSelect={setSelected}
            />
          )}
          {asOf && <p className={s.foot}>Live from Google · {asOf} · map + photos stay in-app</p>}
        </section>

        <section className={s.listPane} aria-label="Results">
          {busy && <p className={s.status} role="status">Searching near you…</p>}
          {error && <p className={s.err} role="alert">{error}</p>}
          {!busy && places.map((p) => {
            const site = businessHref(p.website);
            const photo = placePhotoUrl(p.photo, 360);
            const active = (selected?.id || selected?.name) === (p.id || p.name);
            return (
              <article
                key={p.id || p.name}
                className={`${s.card} ${active ? s.cardSelected : ""}`}
                data-testid="maps-place"
              >
                <button type="button" className={s.cardHit} onClick={() => setSelected(p)}>
                  {photo ? (
                    <img className={s.thumb} src={photo} alt="" data-testid="maps-place-photo" />
                  ) : (
                    <div className={s.thumbEmpty} aria-hidden />
                  )}
                  <div className={s.cardText}>
                    <strong>{p.name}</strong>
                    <p className={s.meta}>
                      {p.rating != null ? `★ ${Number(p.rating).toFixed(1)}` : "No rating"}
                      {p.short_address || p.address ? ` · ${(p.short_address || p.address || "").split(" - ").slice(0, 2).join(", ")}` : ""}
                      {p.open_now != null ? ` · ${p.open_now ? "Open now" : "Closed"}` : ""}
                    </p>
                    {p.photo_by?.[0] && <p className={s.foot}>Photo: {p.photo_by[0]}</p>}
                    <p className={s.foot}>provider_confirmed</p>
                  </div>
                </button>
                <div className={s.actions}>
                  <Button variant="primary" onClick={() => setSelected(p)}>
                    Show on map
                  </Button>
                  {site && (
                    <Button variant="secondary" onClick={() => openBusinessSite(site)}>
                      Open website
                    </Button>
                  )}
                </div>
              </article>
            );
          })}
          {!busy && !places.length && !error && (
            <p className={s.status}>Allow location, then search for places near you.</p>
          )}
        </section>
      </div>
    </div>
  );
}
