import Link from "next/link";
import { DemoPill, ImageBand, SiteFooter, SiteHeader } from "@/components/chrome";
import { IMAGES } from "@/lib/images";
import styles from "./page.module.css";

const bands = [
  {
    id: "tasks",
    title: "Tasks",
    body: "A calm list of what matters today, with due dates and gentle follow-through. Source-backed work stays inspectable; nothing approves or dispatches itself.",
    image: IMAGES.morning,
  },
  {
    id: "decisions",
    title: "Decisions",
    body: "Real choices stay inspectable: what was decided, what it was based on, and what happens next. Approval always comes before anything is sent, shared, or paid.",
    image: IMAGES.marina,
  },
  {
    id: "communities",
    title: "Communities",
    body: "Neighbourhood groups, shared interests and local know-how. Seeded posts are clearly labelled demo content, and community posts are untrusted until confirmed.",
    image: IMAGES.souk,
  },
  {
    id: "services",
    title: "Services",
    body: "Everyday services with fixed, published prices. No bidding, no quotes, no surprises — you approve exactly what you see, and status only ever comes from real evidence.",
    image: IMAGES.mezze,
  },
  {
    id: "maps",
    title: "Maps",
    body: "Places open on demand, in-app and in-chat. Pins mark only places you confirmed; every number carries its provenance.",
    image: IMAGES.metro,
  },
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <div className={styles.page}>
        <main>
          <section className={styles.hero} aria-labelledby="hero-title">
            <p className={styles.eyebrow}>
              Everyday life in Dubai, handled calmly
            </p>
            <h1 id="hero-title">
              Your personal assistant for
              <br />
              life and work in Dubai.
            </h1>
            <p className={styles.lede}>
              Tasks, decisions, communities, services and maps — one quiet app
              that shows its work and asks before it acts.
            </p>
            <div className={styles.ctas}>
              <Link className={styles.primary} href="/app">
                Open the signed-in app
              </Link>
              <Link className={styles.secondary} href="/demo">
                See the contest demo
              </Link>
            </div>
          </section>

          <ImageBand image={IMAGES.skyline} ratio="21 / 9" eager />
          <p className={styles.demoNote}>
            <DemoPill /> Marketing preview — the signed-in app below runs
            against the same FastAPI backend as the prototype.
          </p>

          <div id="features" className={styles.bandGrid}>
            {bands.map((band) => (
              <section
                key={band.id}
                id={band.id}
                className={styles.band}
                aria-labelledby={`${band.id}-title`}
              >
                <ImageBand image={band.image} ratio="16 / 9" />
                <h2 id={`${band.id}-title`}>{band.title}</h2>
                <p>{band.body}</p>
              </section>
            ))}
          </div>

          <section className={styles.wideBand} aria-labelledby="weekend-title">
            <div>
              <h2 id="weekend-title">Made for weekends, not just weekdays.</h2>
              <p>
                Food, souks, desert air, late marina nights — Dubai-io keeps the
                plan, the people and the places in one place.{" "}
                <Link href="/privacy">Read what it will never do.</Link>
              </p>
            </div>
            <ImageBand image={IMAGES.desert} ratio="4 / 3" />
          </section>

          <section className={styles.ctaBand} aria-labelledby="cta-title">
            <h2 id="cta-title">Try the signed-in app.</h2>
            <p>
              Home, Chat, Services, Feed and Ask — running on the same backend,
              with the same rules: approval before send or share, status only
              from authoritative events, provenance on every number.
            </p>
            <div className={styles.ctas}>
              <Link className={styles.primary} href="/app">
                Open /app
              </Link>
              <Link className={styles.secondary} href="/privacy">
                Privacy first
              </Link>
            </div>
          </section>
        </main>
      </div>
      <SiteFooter />
    </>
  );
}
