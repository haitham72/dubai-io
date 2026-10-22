"use client";

import Link from "next/link";
import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import { priceAed, type CatalogProvider } from "@/lib/api";
import { useApi } from "@/lib/use-api";

export default function Services() {
  const { data, error, loading, reload } = useApi<{
    providers?: CatalogProvider[];
    provenance?: string;
    as_of?: string;
  }>("/api/catalog");

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Services</h1>
        <p>
          Fixed published prices — no bidding, no quotes, no surprises.{" "}
          <DemoPill /> Orders state plainly that no payment was taken.
        </p>
      </div>
      {loading ? <LoadingState label="Loading services…" /> : null}
      {error ? (
        <ErrorState
          message={`Services unavailable: ${error}. Start the backend and retry.`}
          onRetry={reload}
        />
      ) : null}
      {data?.providers && data.providers.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
            gap: 12,
          }}
        >
          {data.providers.map((provider) => (
            <div key={provider.id} className="rowCard">
              <h3>
                <Link href={`/app/services/${encodeURIComponent(provider.id)}`}>
                  {provider.name}
                </Link>
              </h3>
              <p>{provider.service}</p>
              <div className="rowMeta">
                {provider.items && provider.items.length > 0 ? (
                  <span>
                    from AED{" "}
                    {Math.min(
                      ...provider.items.map(
                        (i) => priceAed(i.price_aed) ?? Infinity,
                      ),
                    )}
                  </span>
                ) : null}
                <Provenance value={data.provenance} />
              </div>
            </div>
          ))}
        </div>
      ) : !loading && !error ? (
        <EmptyState
          title="No services listed"
          body="The published catalog lives on the backend; when it is reachable it appears here."
        />
      ) : null}
      <SectionCard title="How ordering works">
        <p style={{ color: "var(--muted)", lineHeight: 1.65, margin: 0 }}>
          Every order shows an approval card first: exactly what is shared,
          with whom, and for how much. Nothing is sent, shared or paid until
          you tap approve — and status only ever comes from the merchant&apos;s
          own evidence, never from a chat reply.
        </p>
      </SectionCard>
    </>
  );
}
