import Link from "next/link";
import type { ReactNode } from "react";
import type { SiteImage } from "@/lib/images";
import styles from "./chrome.module.css";

/* ---------- Marketing chrome ---------- */

export function SiteHeader() {
  return (
    <header className={styles.siteHeader}>
      <div className={styles.siteHeaderInner}>
        <Link href="/" className={styles.wordmark}>
          Dubai-io
        </Link>
        <nav aria-label="Site" className={styles.siteNav}>
          <Link href="/#features">Features</Link>
          <Link href="/privacy">Privacy</Link>
          <Link href="/demo">Contest demo</Link>
          <Link href="/app" className={styles.navCta}>
            Open the app
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className={styles.siteFooter}>
      <p>
        Dubai-io is a contest demo. Photos are openly licensed; full credits in{" "}
        <Link href="/demo#credits">image credits</Link>. Pictured people are not
        affiliated with Dubai-io and do not endorse it.
      </p>
      <nav aria-label="Footer" className={styles.siteNav}>
        <Link href="/privacy">Privacy</Link>
        <Link href="/demo">Contest demo</Link>
        <Link href="/app">Open the app</Link>
      </nav>
    </footer>
  );
}

/* ---------- Trust labels ---------- */

export function DemoPill({ label = "Demo data" }: { label?: string }) {
  return <span className={styles.demoPill}>{label}</span>;
}

export function Provenance({ value }: { value?: string | null }) {
  if (!value) return null;
  return <span className={styles.provenance}>provenance: {value}</span>;
}

/* ---------- Photography ---------- */

export function ImageBand({
  image,
  ratio = "21 / 9",
  eager = false,
}: {
  image: SiteImage;
  ratio?: string;
  eager?: boolean;
}) {
  return (
    <figure className={styles.imageBand}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.src}
        alt={image.alt}
        loading={eager ? "eager" : "lazy"}
        style={{ aspectRatio: ratio }}
      />
      <figcaption>
        {image.caption} · Photo: {image.credit} (
        <a href={image.sourceUrl} rel="noreferrer">
          source
        </a>
        , {image.license})
      </figcaption>
    </figure>
  );
}

/* ---------- Data states ---------- */

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <p className={styles.stateNote} role="status">
      {label}
    </p>
  );
}

export function EmptyState({
  title,
  body,
}: {
  title: string;
  body?: string;
}) {
  return (
    <div className={styles.stateCard}>
      <h3>{title}</h3>
      {body ? <p>{body}</p> : null}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className={styles.stateCard} role="alert">
      <h3>Something didn&apos;t load</h3>
      <p>{message}</p>
      {onRetry ? (
        <button type="button" className={styles.retry} onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

/* ---------- Signed-in app chrome ---------- */

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className={styles.backLink}>
      ← {label}
    </Link>
  );
}

export function SectionCard({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className={styles.sectionCard} aria-label={title}>
      <div className={styles.sectionHead}>
        <h2>{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
