"use client";

import { useEffect, useRef, useState } from "react";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingState,
  SectionCard,
} from "@/components/chrome";
import { MAPS_KEY } from "@/lib/api";

declare global {
  interface Window {
    google?: {
      maps?: {
        Map?: new (el: HTMLElement, opts: Record<string, unknown>) => unknown;
      };
    };
  }
}

type MapState = "idle" | "no-key" | "loading" | "ready" | "failed";

export default function MapPage() {
  const [state, setState] = useState<MapState>("idle");
  const [detail, setDetail] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!MAPS_KEY) {
      setState("no-key");
      return;
    }
    if (window.google?.maps?.Map) {
      setState("ready");
      return;
    }
    setState("loading");
    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(MAPS_KEY)}&libraries=places`;
    script.async = true;
    script.onload = () => {
      if (!ref.current || !window.google?.maps?.Map) {
        setState("failed");
        setDetail("The Maps library loaded but did not initialise.");
        return;
      }
      new window.google.maps.Map(ref.current, {
        center: { lat: 25.2048, lng: 55.2708 },
        zoom: 12,
      });
      setState("ready");
    };
    script.onerror = () => {
      setState("failed");
      setDetail("The Google Maps script could not be loaded.");
    };
    document.head.appendChild(script);
    return () => {
      document.head.removeChild(script);
    };
  }, []);

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Maps</h1>
        <p>
          Places open on demand — in-app and in-chat. Pins mark only places
          you confirmed; Google content sits on a Google map with its
          attribution.
        </p>
      </div>
      <SectionCard title="Explore near you">
        {state === "no-key" ? (
          <EmptyState
            title="Map key not configured"
            body="Set NEXT_PUBLIC_MAPS_KEY (a referrer-restricted browser key) to enable the live map. Until then, places search in Ask still works through the backend."
          />
        ) : null}
        {state === "loading" || state === "idle" ? (
          <LoadingState label="Loading the map…" />
        ) : null}
        {state === "failed" ? (
          <ErrorState
            message={detail ?? "The map failed to load."}
            onRetry={() => window.location.reload()}
          />
        ) : null}
        {state !== "no-key" ? (
          <div
            ref={ref}
            role="application"
            aria-label="Map of Dubai"
            style={{
              minHeight: 420,
              borderRadius: "var(--radius)",
              background: "var(--band)",
              display: state === "ready" ? "block" : "none",
            }}
          />
        ) : null}
      </SectionCard>
    </>
  );
}
