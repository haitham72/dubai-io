"use client";

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

export default function ServiceDetail({ serviceId }: { serviceId: string }) {
  const { data, error, loading, reload } = useApi<{
    providers?: CatalogProvider[];
    provenance?: string;
  }>("/api/catalog");
  const provider = (data?.providers ?? []).find((p) => p.id === serviceId);

  return (
    <>
      <div className="appHead">
        <BackLink href="/app/services" label="Services" />
        <h1>{provider?.name ?? "Service"}</h1>
        <p>
          {provider?.service ?? ""} <DemoPill />
        </p>
      </div>
      {loading ? <LoadingState label="Loading service…" /> : null}
      {error ? (
        <ErrorState message={`Service unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {!loading && !error && !provider ? (
        <EmptyState
          title="Service not found"
          body="It may have left the published catalog."
        />
      ) : null}
      {provider ? (
        <>
          <SectionCard
            title="Fixed price list"
            action={<Provenance value={data?.provenance} />}
          >
            {!provider.items || provider.items.length === 0 ? (
              <EmptyState
                title="No priced items"
                body="This provider has nothing orderable right now."
              />
            ) : (
              <ul className="listRows">
                {provider.items.map((item) => {
                  const price = priceAed(item.price_aed);
                  return (
                    <li key={item.id} className="rowCard">
                      <h3>{item.name}</h3>
                      <div className="rowMeta">
                        {price !== null ? (
                          <span>AED {price.toFixed(2)} · fixed</span>
                        ) : (
                          <span>Price on request from the merchant</span>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
            {provider.slots && provider.slots.length > 0 ? (
              <div className="chipRow" aria-label="Available slots">
                {provider.slots.map((slot) => (
                  <span key={slot} className="chip">
                    {slot}
                  </span>
                ))}
              </div>
            ) : null}
          </SectionCard>
          <SectionCard title="Before you order">
            <p style={{ color: "var(--muted)", lineHeight: 1.65, margin: 0 }}>
              Ordering opens an approval card naming exactly which fields are
              shared with {provider.name} and the exact amount. Approve sends
              that revision; anything else — a 409, a changed price, a missing
              receipt — means reload and review. No payment is taken in this
              demo; receipts say so plainly.
            </p>
          </SectionCard>
        </>
      ) : null}
    </>
  );
}
