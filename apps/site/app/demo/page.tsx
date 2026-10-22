import Link from "next/link";
import { DemoPill, ImageBand, SiteFooter, SiteHeader } from "@/components/chrome";
import { IMAGES } from "@/lib/images";
import styles from "./page.module.css";

const steps = [
  {
    title: "1 · Morning brief",
    body: "Open /app and read Today: what needs you, what's running, what's on your list. One deterministic brief line — never model chatter.",
    href: "/app",
  },
  {
    title: "2 · Decide, don't guess",
    body: "A decision card shows the context, the amount, what gets shared and what never does. Approve sends exactly that revision; 409 means reload.",
    href: "/app",
  },
  {
    title: "3 · Talk it through",
    body: "Ask answers with the same rules as everywhere else: provenance on every number, Demo labels on fixtures, no status without evidence.",
    href: "/app/ask",
  },
  {
    title: "4 · Meet the neighbours",
    body: "Feed mixes community posts with headlines. Seeded content is labelled; join a community and it carries through to Chat › Communities.",
    href: "/app/feed",
  },
  {
    title: "5 · Get things done",
    body: "Services list fixed published prices — no bidding, no quotes. Orders and receipts state plainly that no payment was taken.",
    href: "/app/services",
  },
];

export default function Demo() {
  return (
    <>
      <SiteHeader />
      <div className={styles.page}>
        <main>
          <p className={styles.eyebrow}>Create AI Agents Championship · entry demo</p>
          <h1>The five-minute Dubai-io tour.</h1>
          <p className={styles.lede}>
            <DemoPill /> Everything on this page is demo content running
            against the same FastAPI backend as the prototype — the same
            approval, provenance and status rules apply.
          </p>
          <ImageBand image={IMAGES.burj} ratio="21 / 9" eager />
          <ol className={styles.steps}>
            {steps.map((step) => (
              <li key={step.title}>
                <h2>{step.title}</h2>
                <p>{step.body}</p>
                <Link href={step.href}>Open it →</Link>
              </li>
            ))}
          </ol>
          <section id="credits" aria-labelledby="credits-title">
            <h2 id="credits-title">Image credits</h2>
            <p>
              All photographs on this site are openly licensed and hosted
              locally. Fictional demo identities never imply the pictured
              person authored posts or endorses the app.
            </p>
            <ul className={styles.credits}>
              {Object.values(IMAGES).map((image) => (
                <li key={image.src}>
                  {image.caption} — {image.credit},{" "}
                  <a href={image.sourceUrl} rel="noreferrer">
                    source
                  </a>
                  , {image.license}
                </li>
              ))}
            </ul>
          </section>
        </main>
      </div>
      <SiteFooter />
    </>
  );
}
