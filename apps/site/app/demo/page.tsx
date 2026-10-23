import type { Metadata } from "next";
import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { IMAGES } from "@/lib/images";
import { MEDIA } from "@/lib/media";
import Browser from "./browser";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Demo, no signup",
  description:
    "Browse the Dubai-io services directory and community feed, read-only, straight from the real API.",
};

export default function Demo() {
  return (
    <>
      <SiteHeader />
      <main className={styles.page}>
        <header className={styles.head}>
          <h1>Try it before you sign up.</h1>
          <p>
            This is live data from the Dubai-io API. It is read-only: nothing
            here can be sent, booked or paid. Everything is demo content and
            says so.
          </p>
        </header>

        <Browser />

        <aside className={styles.next}>
          <div>
            <h2>Like what you see?</h2>
            <p>Set up takes three short questions. Skip any of them.</p>
          </div>
          <Link href="/signup" className={styles.cta}>
            Start setup
          </Link>
        </aside>

        <section id="credits" aria-labelledby="credits-title" className={styles.credits}>
          <h2 id="credits-title">Image credits</h2>
          <p>
            Photographs are openly licensed or stock images, hosted locally.
            They are illustrative: none shows a specific provider, and pictured
            people are not affiliated with Dubai-io.
          </p>
          <ul>
            {Object.values(IMAGES).map((image) => (
              <li key={image.src}>
                {image.caption}: {image.credit} (
                <a href={image.sourceUrl} rel="noreferrer">
                  source
                </a>
                , {image.license})
              </li>
            ))}
            {Object.entries(MEDIA).map(([name, m]) => (
              <li key={name}>
                {m.subject}: Unsplash stock (
                <a href={m.sourceUrl} rel="noreferrer">
                  source
                </a>
                , Unsplash License)
              </li>
            ))}
          </ul>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
