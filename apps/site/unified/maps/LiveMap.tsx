"use client";
import { useEffect, useRef, useState } from "react";
import { apiGet } from "../data/api";
import type { Place } from "../data/places";
import s from "./maps.module.css";

type MapsConfig = { key: string; source?: string };

type GoogleMap = {
  setCenter: (c: { lat: number; lng: number }) => void;
  setZoom: (z: number) => void;
  fitBounds: (b: unknown, padding?: number) => void;
  panTo: (c: { lat: number; lng: number }) => void;
};
type GoogleMarker = { setMap: (m: GoogleMap | null) => void; addListener: (e: string, fn: () => void) => void };
type GoogleMapsApi = {
  Map: new (el: HTMLElement, opts: Record<string, unknown>) => GoogleMap;
  Marker: new (opts: Record<string, unknown>) => GoogleMarker;
  LatLngBounds: new () => { extend: (p: { lat: number; lng: number }) => void };
};

type MapsWindow = Window & {
  google?: { maps?: GoogleMapsApi };
  __dubaiioMapsPromise?: Promise<void>;
};

function mapsWin(): MapsWindow {
  return window as MapsWindow;
}

function loadMapsScript(key: string): Promise<void> {
  const w = mapsWin();
  if (w.google?.maps?.Map) return Promise.resolve();
  if (w.__dubaiioMapsPromise) return w.__dubaiioMapsPromise;
  w.__dubaiioMapsPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-dubaiio-maps]");
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("maps script")));
      return;
    }
    const script = document.createElement("script");
    script.dataset.dubaiioMaps = "1";
    script.async = true;
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(key)}`;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("maps script"));
    document.head.appendChild(script);
  });
  return w.__dubaiioMapsPromise;
}

function staticSrc(center: { lat: number; lng: number }, places: Place[]): string {
  const pins = places.filter((p) => p.lat != null && p.lng != null).slice(0, 9);
  const m = pins.map((p) => `${p.lat},${p.lng}`).join("|");
  const q = new URLSearchParams({
    c: `${center.lat},${center.lng}`,
    z: "14",
    s: "wide",
  });
  if (m) q.set("m", m);
  return `/api/staticmap?${q.toString()}`;
}

export function LiveMap({
  center,
  places,
  selected,
  onSelect,
  compact = false,
}: {
  center: { lat: number; lng: number };
  places: Place[];
  selected?: Place | null;
  onSelect?: (p: Place) => void;
  compact?: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const mapRef = useRef<GoogleMap | null>(null);
  const markersRef = useRef<GoogleMarker[]>([]);
  const [mode, setMode] = useState<"loading" | "live" | "static">("loading");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const cfg = await apiGet<MapsConfig>("/api/maps/config");
        if (!cfg.key) throw new Error("no key");
        await loadMapsScript(cfg.key);
        const api = mapsWin().google?.maps;
        if (cancelled || !host.current || !api?.Map) throw new Error("no maps");
        const MapCtor = api.Map;
        const map = new MapCtor(host.current, {
          center,
          zoom: 14,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: !compact,
          clickableIcons: false,
        });
        mapRef.current = map;
        if (!cancelled) setMode("live");
      } catch {
        if (!cancelled) setMode("static");
      }
    })();
    return () => {
      cancelled = true;
      markersRef.current.forEach((m) => m.setMap(null));
      markersRef.current = [];
      mapRef.current = null;
    };
  }, [compact, center.lat, center.lng]);

  useEffect(() => {
    const map = mapRef.current;
    const g = mapsWin().google?.maps;
    if (!map || !g || mode !== "live") return;
    markersRef.current.forEach((m) => m.setMap(null));
    markersRef.current = [];
    const bounds = new g.LatLngBounds();
    bounds.extend(center);
    const you = new g.Marker({
      map,
      position: center,
      title: "You are here",
    });
    markersRef.current.push(you);

    places.forEach((p, i) => {
      if (p.lat == null || p.lng == null) return;
      const pos = { lat: p.lat, lng: p.lng };
      bounds.extend(pos);
      const marker = new g.Marker({
        map,
        position: pos,
        title: p.name,
        label: `${i + 1}`,
      });
      marker.addListener("click", () => onSelect?.(p));
      markersRef.current.push(marker);
    });

    const selectedPin = selected && selected.lat != null && selected.lng != null ? selected : null;
    if (selectedPin) {
      map.panTo({ lat: selectedPin.lat!, lng: selectedPin.lng! });
      map.setZoom(15);
    } else if (places.some((p) => p.lat != null)) {
      map.fitBounds(bounds, compact ? 24 : 48);
    } else {
      map.setCenter(center);
      map.setZoom(14);
    }
  }, [center, places, selected, onSelect, mode, compact]);

  return (
    <div className={`${s.mapFrame} ${compact ? s.mapCompact : ""}`} data-testid="maps-interactive" data-mode={mode}>
      <div ref={host} className={s.mapHost} role="application" aria-label="Interactive map" />
      {mode !== "live" && (
        <img
          className={s.mapFallback}
          src={staticSrc(center, places)}
          alt="Map of search results"
          data-testid="maps-static"
        />
      )}
      {mode === "loading" && <p className={s.mapLoading}>Loading map…</p>}
    </div>
  );
}
