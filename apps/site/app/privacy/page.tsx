import Link from "next/link";
import { ImageBand, SiteFooter, SiteHeader } from "@/components/chrome";
import { IMAGES } from "@/lib/images";
import styles from "./page.module.css";

const neverItems = [
  {
    title: "No invented status",
    body: "Dubai-io never shows Confirmed, Booked, Paid, Filed or Delivered without an authoritative event — a merchant action or a verified adapter response. Anything else stays visibly unknown.",
  },
  {
    title: "No numbers without provenance",
    body: "Every price, balance, rating, date and count carries where it came from: official, provider-confirmed, merchant-submitted, user-supplied, inferred, estimated or demo fixture — plus when it was true.",
  },
  {
    title: "No bidding, quotes or negotiation",
    body: "Services show fixed, published prices only. Bidding and negotiation in any form are forbidden, and sharing data or placing an order always needs your explicit tap on an approval card first.",
  },
  {
    title: "No government execution",
    body: "Salik, DEWA, RTA, Tasjeel and fines are display-only or open-official-portal links. No top-ups, no bookings, no wait times.",
  },
  {
    title: "No fake positions or facts",
    body: "The app never invents an indoor position, a belt or gate number, or a queue time you didn't confirm. Map pins mark only places you confirmed.",
  },
  {
    title: "No hidden memory",
    body: "Things you state are shown as “You told me”. Things the app notices are hypotheses you can confirm, edit or delete — an unconfirmed guess never pre-fills a form, triggers a message or sets a status. Nothing about you is stored where you can't see it.",
  },
  {
    title: "No background tracking",
    body: "Reminders come from a scheduler you consented to, with quiet hours and dedupe. The web app does no background geofencing.",
  },
];

export default function Privacy() {
  return (
    <>
      <SiteHeader />
      <div className={styles.page}>
        <main>
          <p className={styles.eyebrow}>Privacy</p>
          <h1>What Dubai-io will never do.</h1>
          <p className={styles.lede}>
            Seven hard rules, enforced in the product — not just promised on
            this page.
          </p>
          <ImageBand image={IMAGES.marina} ratio="21 / 9" />
          <ol className={styles.neverList}>
            {neverItems.map((item) => (
              <li key={item.title}>
                <h2>{item.title}</h2>
                <p>{item.body}</p>
              </li>
            ))}
          </ol>
          <p className={styles.closing}>
            Questions? The signed-in app shows the same rules in action —{" "}
            <Link href="/app">open /app</Link> — or walk the{" "}
            <Link href="/demo">contest demo</Link>.
          </p>
        </main>
      </div>
      <SiteFooter />
    </>
  );
}
