"use client";
import { useState } from "react";
import { mapsHref, type Place } from "../data/places";
import { placePhotoUrl } from "../data/location";
import type { ChatBecause, ChatProduct } from "../state";
import { ResultSection, type ResultItem } from "./ResultTemplate";
import { TryOnSheet } from "./TryOnSheet";
import s from "./assistant.module.css";

function formatAsOf(iso: string | undefined): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleString("en-GB", {
      timeZone: "Asia/Dubai",
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export function BecauseChips({ because }: { because?: ChatBecause[] }) {
  if (!because?.length) return null;
  return (
    <div className={s.becauseRow} data-testid="because-chips">
      {because.map((b) => (
        <span key={`${b.key}-${b.value}`} className={s.becauseChip}>
          Because {b.label || b.value}
        </span>
      ))}
    </div>
  );
}

export function PlaceCards({
  places,
  asOf,
  attribution,
}: {
  places: Place[];
  asOf?: string;
  attribution?: string;
}) {
  if (!places.length) return null;
  const items: ResultItem[] = places.map((p, i) => {
    const href = mapsHref(p.maps_url);
    const photo = placePhotoUrl(p.photo, 320);
    const bits = [
      p.rating != null ? `★ ${Number(p.rating).toFixed(1)}${p.ratings != null ? ` (${p.ratings})` : ""}` : "No rating yet",
      p.open_now != null ? (p.open_now ? "Open now" : "Closed") : null,
      (p.short_address || p.address || "").split(" - ").slice(0, 2).join(", ") || null,
    ].filter(Boolean);
    return {
      id: p.id || `${p.name}-${i}`,
      title: p.name,
      body: bits.join(" · "),
      provider: "place" as const,
      media: photo,
      provenance: "Google · provider_confirmed",
      testId: "live-place",
      actions: href ? (
        <a className={s.placeMaps} href={href} target="_blank" rel="noopener noreferrer">
          Maps
        </a>
      ) : null,
    };
  });
  return (
    <div data-testid="live-places">
      <ResultSection
        heading="Near you"
        items={items}
        testId="live-places-section"
        foot={`Live from ${attribution || "Google"}${asOf ? ` · ${formatAsOf(asOf)} Dubai time` : ""}. Discovery only — nothing ordered or booked.`}
      />
    </div>
  );
}

export function SourceList({ sources }: { sources: { title?: string; url?: string; snippet?: string }[] }) {
  if (!sources.length) return null;
  const items: ResultItem[] = sources.slice(0, 4).map((src, i) => ({
    id: src.url || `src-${i}`,
    title: src.title || src.url || "Source",
    body: src.snippet || "Open the source for details.",
    provider: "web" as const,
    actions: src.url?.startsWith("https://") ? (
      <a className={s.placeMaps} href={src.url} target="_blank" rel="noopener noreferrer">
        Open
      </a>
    ) : null,
  }));
  return <ResultSection heading="Sources" items={items} testId="live-sources" />;
}

export function ProductList({ products, because }: { products: ChatProduct[]; because?: ChatBecause[] }) {
  const [tryOn, setTryOn] = useState<ChatProduct | null>(null);
  if (!products.length) return null;
  const asOf = products.find((p) => p.as_of)?.as_of;
  const items: ResultItem[] = products.slice(0, 5).map((p, i) => ({
    id: p.link || `${p.title}-${i}`,
    title: p.title || "Product",
    body: `${p.price || "Price unknown"}${p.source ? ` at ${p.source}` : ""}. Live listing — nothing is purchased in Dubai-io.`,
    provider: "shopping" as const,
    media: p.thumbnail?.startsWith("https://") ? p.thumbnail : null,
    provenance: `${p.provenance || "provider_confirmed"} · live listing`,
    testId: "live-product",
    actions: (
      <>
        <button type="button" className={s.placeMaps} data-testid="tryon-open" onClick={() => setTryOn(p)}>
          Try it on
        </button>
        {p.link?.startsWith("https://") ? (
          <a className={s.placeMaps} href={p.link} target="_blank" rel="noopener noreferrer">
            Open store
          </a>
        ) : null}
      </>
    ),
  }));
  return (
    <div className={s.liveBlock} data-testid="live-products" aria-label="Live shopping results">
      <BecauseChips because={because} />
      <ResultSection
        heading="Worth a look"
        items={items}
        foot={`Live shopping · UAE${asOf ? ` · ${formatAsOf(asOf)} Dubai time` : ""}. Prices change; nothing is purchased in Dubai-io.`}
      />
      {tryOn && <TryOnSheet product={tryOn} onClose={() => setTryOn(null)} />}
    </div>
  );
}

/** Mail / career profiler cards — same Grok grammar as shopping & places. */
export function MailResultList({
  heading,
  items,
}: {
  heading: string;
  items: {
    id: string;
    title: string;
    body: string;
    provenance?: string;
    demo?: boolean;
  }[];
}) {
  if (!items.length) return null;
  const mapped: ResultItem[] = items.map((m) => ({
    id: m.id,
    title: m.title,
    body: m.body,
    provider: m.demo ? "demo" : "mail",
    provenance: m.provenance || (m.demo ? "demo_fixture" : "provider_confirmed"),
  }));
  return <ResultSection heading={heading} items={mapped} testId="live-mail" />;
}
