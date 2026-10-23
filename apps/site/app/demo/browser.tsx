"use client";

import { useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/chrome";
import { type CatalogProvider, type Post, authorName, priceAed } from "@/lib/api";
import { mediaSrc } from "@/lib/media";
import { useApi } from "@/lib/use-api";
import styles from "./page.module.css";

interface Catalog {
  provenance?: string;
  as_of?: string;
  providers: CatalogProvider[];
}

const SERVICE_IMAGE: Record<string, string> = {
  laundry: "media/laundry.jpg",
  ac: "media/ac.jpg",
  grooming: "media/pets.jpg",
  cleaning: "media/home.jpg",
  maid: "media/home-green.jpg",
};

const SERVICE_NAME: Record<string, string> = {
  laundry: "Laundry",
  ac: "AC repair",
  grooming: "Pet grooming",
  cleaning: "Cleaning",
  maid: "Home help",
  carwash: "Car wash",
  pharmacy: "Pharmacy",
};

function Provenance({ value, asOf }: { value?: string; asOf?: string }) {
  return (
    <span className={styles.meta}>
      <span className={styles.pill}>Demo data</span>
      {value ? <span>provenance: {value}</span> : null}
      {asOf ? <span>as of {asOf.slice(0, 10)}</span> : null}
    </span>
  );
}

function Services() {
  // The catalog is public, so no session is needed.
  const { data, error, loading, reload } = useApi<Catalog>("/api/catalog");
  if (loading) return <LoadingState label="Loading demo providers" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const providers = data?.providers ?? [];
  if (providers.length === 0) {
    return (
      <EmptyState
        title="No providers yet"
        body="The directory is empty right now. Check back soon."
      />
    );
  }
  return (
    <>
      <p className={styles.note}>
        Fixed, published prices from demo providers.{" "}
        <Provenance value={data?.provenance} asOf={data?.as_of} />
      </p>
      <ul className={styles.cards}>
        {providers.map((p, i) => {
          // Show each service photo once; repeating it per provider reads as filler.
          const first = providers.findIndex((q) => q.service === p.service) === i;
          const img = first ? mediaSrc(SERVICE_IMAGE[p.service]) : null;
          return (
            <li key={p.id} className={styles.card}>
              {img ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={img} alt="" loading="lazy" className={styles.cardImg} />
              ) : null}
              <div className={styles.cardBody}>
                <p className={styles.kind}>{SERVICE_NAME[p.service] ?? p.service}</p>
                <h3>{p.name}</h3>
                <ul className={styles.prices}>
                  {(p.items ?? []).map((item) => (
                    <li key={item.id}>
                      <span>{item.name}</span>
                      <strong>
                        {priceAed(item.price_aed) !== null
                          ? `AED ${priceAed(item.price_aed)}`
                          : "Price not listed"}
                      </strong>
                    </li>
                  ))}
                </ul>
                {p.slots?.length ? (
                  <p className={styles.slots}>Next slots: {p.slots.join(", ")}</p>
                ) : null}
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}

function Feed() {
  const { data, error, loading, reload } = useApi<{ posts: Post[] }>("/api/feed");
  if (loading) return <LoadingState label="Loading demo posts" />;
  if (error) return <ErrorState message={error} onRetry={reload} />;
  const posts = data?.posts ?? [];
  if (posts.length === 0) {
    return (
      <EmptyState
        title="The feed is quiet"
        body="No posts yet. Communities you join will show up here."
      />
    );
  }
  return (
    <>
      <p className={styles.note}>
        Seeded posts from demo communities. Counts are demo values, not real
        activity.
      </p>
      <ul className={styles.cards}>
        {posts.slice(0, 8).map((post) => {
          const img = mediaSrc(post.image);
          return (
            <li key={post.id} className={styles.card}>
              {img ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={img} alt="" loading="lazy" className={styles.cardImg} />
              ) : null}
              <div className={styles.cardBody}>
                <p className={styles.kind}>{post.community?.name ?? "Community"}</p>
                <p className={styles.post}>{post.text}</p>
                <p className={styles.slots}>
                  {authorName(post.author)} (fictional demo author) · {post.likes ?? 0}{" "}
                  likes · {post.comments ?? 0} comments
                </p>
                <Provenance value={post.provenance} />
              </div>
            </li>
          );
        })}
      </ul>
    </>
  );
}

export default function Browser() {
  const [tab, setTab] = useState<"services" | "feed">("services");
  return (
    <section aria-label="Demo browser">
      <div className={styles.tabs} role="tablist" aria-label="Demo sections">
        {(
          [
            ["services", "Services"],
            ["feed", "Community feed"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={tab === id}
            aria-controls={`panel-${id}`}
            onClick={() => setTab(id)}
          >
            {label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "services" ? <Services /> : <Feed />}
      </div>
    </section>
  );
}
