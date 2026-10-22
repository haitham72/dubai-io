import { API_BASE } from "@/lib/api";
import styles from "./page.module.css";

const bands = [
  {
    id: "tasks",
    title: "Tasks",
    body: "A calm list of what matters today, with due dates and gentle follow-through. Nothing shouty, nothing lost.",
  },
  {
    id: "decisions",
    title: "Decisions",
    body: "Real choices stay inspectable: what was decided, what it was based on, and what happens next.",
  },
  {
    id: "communities",
    title: "Communities",
    body: "Neighbourhood groups, shared interests and local know-how — clearly labelled demo content where it is demo.",
  },
  {
    id: "services",
    title: "Services",
    body: "Everyday services with fixed, published prices. No bidding, no quotes, no surprises — approve exactly what you see.",
  },
  {
    id: "maps",
    title: "Maps",
    body: "Places open on demand, in-app and in-chat. Pins mark only places you confirmed.",
  },
];

export default function Home() {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.wordmark}>Dubai-io</span>
        <nav aria-label="Features" className={styles.nav}>
          {bands.map((band) => (
            <a key={band.id} href={`#${band.id}`}>
              {band.title}
            </a>
          ))}
        </nav>
      </header>

      <main>
        <section className={styles.hero} aria-labelledby="hero-title">
          <p className={styles.eyebrow}>Everyday life in Dubai, handled calmly</p>
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
            <a className={styles.primary} href="#tasks">
              Explore features
            </a>
            <a className={styles.secondary} href="#services">
              See how services work
            </a>
          </div>
        </section>

        {bands.map((band) => (
          <section
            key={band.id}
            id={band.id}
            className={styles.band}
            aria-labelledby={`${band.id}-title`}
          >
            <h2 id={`${band.id}-title`}>{band.title}</h2>
            <p>{band.body}</p>
          </section>
        ))}
      </main>

      <footer className={styles.footer}>
        <p>
          Dubai-io marketing preview. Local API default: {API_BASE}.
        </p>
      </footer>
    </div>
  );
}
