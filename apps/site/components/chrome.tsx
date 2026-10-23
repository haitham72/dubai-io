import Link from "next/link";
import type { ReactNode } from "react";
import type { SiteImage } from "@/lib/images";
import styles from "./chrome.module.css";

/* ---------- Marketing chrome ---------- */

export function Wordmark() {
  return (
    <Link href="/" className={styles.wordmark} aria-label="Dubai-io home">
      <span className={styles.mark} aria-hidden="true" />
      Dubai-io
    </Link>
  );
}

export function SiteHeader() {
  return (
    <header className={styles.siteHeader}>
      <div className={styles.siteHeaderInner}>
        <Wordmark />
        <nav aria-label="Site" className={styles.siteNav}>
          <span className={styles.navLinks}>
            <Link href="/#how">How it works</Link>
            <Link href="/#services">Services</Link>
            <Link href="/#trust">Trust</Link>
            <Link href="/#pricing">Pricing</Link>
            <Link href="/demo">Demo</Link>
          </span>
          <Link href="/signup" className={styles.navCta}>
            Get started
          </Link>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className={styles.siteFooter}>
      <div className={styles.footInner}>
        <div>
          <Wordmark />
          <p>
            A personal assistant for everyday life and work in Dubai. Early
            access, built in Dubai.
          </p>
        </div>
        <div>
          <h2>Product</h2>
          <ul>
            <li>
              <Link href="/#how">How it works</Link>
            </li>
            <li>
              <Link href="/#services">Services</Link>
            </li>
            <li>
              <Link href="/#pricing">Pricing</Link>
            </li>
            <li>
              <Link href="/#faq">FAQ</Link>
            </li>
          </ul>
        </div>
        <div>
          <h2>Try it</h2>
          <ul>
            <li>
              <Link href="/demo">Demo, no signup</Link>
            </li>
            <li>
              <Link href="/signup">Start setup</Link>
            </li>
            <li>
              <Link href="/app">In-app preview</Link>
            </li>
          </ul>
        </div>
        <div>
          <h2>Trust</h2>
          <ul>
            <li>
              <Link href="/privacy">What it never does</Link>
            </li>
            <li>
              <Link href="/demo#credits">Image credits</Link>
            </li>
          </ul>
        </div>
      </div>
      <div className={styles.footNote}>
        <p>
          Dubai-io is independent and not affiliated with any government body.
          Services and prices shown today are demo data. Photographs are
          openly licensed and illustrative; pictured people and places are not
          affiliated with Dubai-io.
        </p>
      </div>
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
