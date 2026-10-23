import Link from "next/link";
import { SiteFooter, SiteHeader } from "@/components/chrome";
import { Drift, Reveal, Story, type StoryStep } from "@/components/motion";
import { Phone } from "@/components/phone";
import { IMAGES } from "@/lib/images";
import styles from "./page.module.css";

const steps: StoryStep[] = [
  {
    id: "tell",
    title: "Tell it once.",
    body: "Say where you live, who is in your household, what you pay for. Dubai-io lists every fact under You told me, where you can edit it or make it forget.",
  },
  {
    id: "prepare",
    title: "It prepares the task.",
    body: "Ask for something ordinary, like pressed shirts tonight. It fills in the order from what you told it and a published price. Nothing leaves yet.",
  },
  {
    id: "approve",
    title: "You approve the exact details.",
    body: "The approval card lists every field that will be shared, and what will not be. One tap from you sends it. No tap, no send.",
  },
  {
    id: "status",
    title: "Status comes from the provider.",
    body: "It says Sent when you sent it. It says Confirmed only when the shop does. Until then you see Waiting, or Unknown. Never a guess.",
  },
];

const tiles = [
  {
    name: "Laundry and pressing",
    note: "Fixed prices per item",
    src: "/images/media/laundry.jpg",
    alt: "Stacks of folded shirts",
  },
  {
    name: "AC repair",
    note: "Checks and deep cleans",
    src: "/images/media/ac.jpg",
    alt: "A wall-mounted air conditioner",
  },
  {
    name: "Pet grooming",
    note: "Mobile and in-shop",
    src: "/images/media/pets.jpg",
    alt: "A small white dog being groomed",
  },
  {
    name: "Home help",
    note: "Cleaning by the hour",
    src: "/images/media/home.jpg",
    alt: "A bright living room",
  },
];

const rules = [
  {
    title: "Status comes from evidence.",
    body: "Booked, Paid and Confirmed show only after the provider or merchant reports it. Without that, you see Unknown.",
  },
  {
    title: "You approve what is shared.",
    body: "Approval cards list exactly which fields go to a merchant. Nothing is sent before your tap.",
  },
  {
    title: "Numbers show their source.",
    body: "Prices, dates and counts say where they came from and when. Demo data wears a Demo data label.",
  },
  {
    title: "Memory you can see.",
    body: "Everything it knows about you is listed, editable and forgettable. A guess never fills in a form for you.",
  },
  {
    title: "No pretend integrations.",
    body: "Government and utility actions run only through a real, registered adapter. Where none exists, it shows the blocker and keeps your draft.",
  },
];

const plans = [
  {
    name: "Preview",
    price: "No payment taken",
    state: "Available now",
    points: [
      "Chat with the assistant",
      "Services directory with demo providers",
      "Community feed and calls hub",
      "Memory you can edit and forget",
    ],
    cta: true,
  },
  {
    name: "Personal",
    price: "Price to be announced",
    state: "Not available yet",
    points: ["Scope not decided yet", "Details to follow"],
  },
  {
    name: "Business",
    price: "Price to be announced",
    state: "Not available yet",
    points: ["Scope not decided yet", "Details to follow"],
  },
];

const faqs = [
  {
    q: "Is this a visitor guide?",
    a: "No. Dubai-io is for people who live and work in Dubai: errands, household services, bills, neighbours. It does not plan holidays.",
  },
  {
    q: "Does starting create an account?",
    a: "No. Starting opens an anonymous session in this browser. Real sign-in is not built yet, so clearing your browser data starts you fresh.",
  },
  {
    q: "Will it book real providers?",
    a: "Not today. The providers and prices in the directory are demo data and are labelled that way. Sending an order always needs your approval first.",
  },
  {
    q: "Can it pay my Salik, DEWA or fines?",
    a: "Not yet. Government and utility actions will run only through a real registered adapter, with your approval each time. Until one exists, Dubai-io shows what is blocking and keeps your draft.",
  },
  {
    q: "What does it remember?",
    a: "Only what you tell it, listed under You told me. You can edit or forget any item. Anything it works out for itself is shown as a guess you can confirm or delete.",
  },
  {
    q: "Is it connected to the government?",
    a: "No. Dubai-io is independent. It uses no government branding and does not speak for any authority.",
  },
];

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main>
        <section className={styles.hero} aria-labelledby="hero-title">
          <div className={styles.heroText}>
            <h1 id="hero-title">An assistant that asks before it acts.</h1>
            <p className={styles.lede}>
              Dubai-io is a personal assistant for everyday life and work in
              Dubai. It remembers what you tell it, prepares the task, and
              shows exactly what gets shared. You decide.
            </p>
            <div className={styles.ctas}>
              <Link className={styles.primary} href="/signup">
                Start setup
              </Link>
              <Link className={styles.secondary} href="/demo">
                Try the demo
              </Link>
            </div>
            <p className={styles.fineprint}>
              Starts an anonymous session. No account, no card.
            </p>
          </div>
          <div className={styles.stage}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={IMAGES.morning.src}
              alt={IMAGES.morning.alt}
              className={styles.stageImg}
              fetchPriority="high"
            />
            <Drift className={styles.stagePhone} amount={70}>
              <Phone screen="approve" />
            </Drift>
            <p className={styles.stageCredit}>
              Photo: {IMAGES.morning.credit}, {IMAGES.morning.license}. Phone:
              illustration with demo data.
            </p>
          </div>
        </section>

        <section id="how" className={styles.how} aria-labelledby="how-title">
          <Reveal className={styles.sectionHead}>
            <h2 id="how-title">Four steps. You hold the last one.</h2>
            <p>
              Most assistants act first and explain later. This one prepares,
              shows its work, and waits.
            </p>
          </Reveal>
          <Story steps={steps} />
        </section>

        <section className={styles.statement} aria-labelledby="statement-title">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={IMAGES.marina.src}
            alt={IMAGES.marina.alt}
            className={styles.statementImg}
            loading="lazy"
          />
          <div className={styles.statementVeil} />
          <Reveal className={styles.statementText}>
            <h2 id="statement-title">
              The daily admin of living and working here, in one calm place.
            </h2>
            <p>
              Laundry on Tuesday, the AC before summer, a neighbour&apos;s
              recommendation, a call you need to make. Dubai-io keeps the
              thread.
            </p>
          </Reveal>
          <p className={styles.statementCredit}>
            Photo: {IMAGES.marina.credit}, {IMAGES.marina.license}
          </p>
        </section>

        <section
          id="services"
          className={styles.services}
          aria-labelledby="services-title"
        >
          <Reveal className={styles.sectionHead}>
            <h2 id="services-title">Everyday services, priced up front.</h2>
            <p>
              Laundry, cleaning, AC repair, pets and more, each with a fixed
              published price.{" "}
              <span className={styles.pill}>Demo providers today</span>
            </p>
          </Reveal>
          <ul className={styles.tiles}>
            {tiles.map((tile, i) => (
              <li key={tile.name}>
                <Reveal delay={i * 90}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={tile.src}
                    alt={tile.alt}
                    loading="lazy"
                    className={styles.tileImg}
                  />
                  <h3>{tile.name}</h3>
                  <p>{tile.note}</p>
                </Reveal>
              </li>
            ))}
          </ul>
          <p className={styles.credit}>
            Stock photographs, illustrative only. Sources on the{" "}
            <Link href="/demo#credits">credits list</Link>.
          </p>
        </section>

        <section className={styles.features} aria-label="More of the app">
          <Reveal className={styles.feature}>
            <div className={styles.featureCopy}>
              <h2>It remembers only what you tell it.</h2>
              <p>
                Your area, your household, the bills you pay. Each fact is
                listed in plain view, and any item can be edited or forgotten
                in a tap.
              </p>
            </div>
            <div className={styles.memory} role="img" aria-label="Illustration of the You told me list, with demo values">
              <p className={styles.memoryTitle}>
                You told me <span className={styles.pill}>Illustration</span>
              </p>
              <dl>
                <div>
                  <dt>Area</dt>
                  <dd>Dubai Marina</dd>
                  <span>Edit</span>
                  <span>Forget</span>
                </div>
                <div>
                  <dt>Household</dt>
                  <dd>2 adults, 1 dog</dd>
                  <span>Edit</span>
                  <span>Forget</span>
                </div>
                <div>
                  <dt>Services</dt>
                  <dd>DEWA, Salik, du</dd>
                  <span>Edit</span>
                  <span>Forget</span>
                </div>
              </dl>
            </div>
          </Reveal>

          <Reveal className={`${styles.feature} ${styles.featureFlip}`}>
            <div className={styles.featureImage}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/images/media/cafe-counter.jpg"
                alt="A bright coffee shop with a curved wooden counter"
                loading="lazy"
              />
            </div>
            <div className={styles.featureCopy}>
              <h2>Your neighbourhood, and the people you call.</h2>
              <p>
                A community feed for local know-how, and one place for the
                calls and contacts you keep needing. Feed posts today are demo
                content and are labelled.
              </p>
              <Link href="/demo" className={styles.textLink}>
                Browse the demo
              </Link>
            </div>
          </Reveal>
        </section>

        <section
          id="trust"
          className={styles.trust}
          aria-labelledby="trust-title"
        >
          <div className={styles.trustInner}>
            <Reveal className={styles.trustHead}>
              <h2 id="trust-title">Rules it cannot break.</h2>
              <p>
                No customer quotes here, because there are no customers to
                quote yet. This is an early-access build, made in Dubai. What
                we can show you is how it behaves.
              </p>
              <Link href="/privacy" className={styles.trustLink}>
                Read the full list
              </Link>
            </Reveal>
            <ul className={styles.rules}>
              {rules.map((rule, i) => (
                <li key={rule.title}>
                  <Reveal delay={i * 60}>
                    <h3>{rule.title}</h3>
                    <p>{rule.body}</p>
                  </Reveal>
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section
          id="pricing"
          className={styles.pricing}
          aria-labelledby="pricing-title"
        >
          <Reveal className={styles.sectionHead}>
            <h2 id="pricing-title">Pricing, when it is ready.</h2>
            <p>
              No price is set, and nothing on this site takes payment. This is
              the shape of what is planned.
            </p>
          </Reveal>
          <ul className={styles.plans}>
            {plans.map((plan) => (
              <li
                key={plan.name}
                className={styles.plan}
                data-live={plan.cta ? "true" : "false"}
              >
                <h3>{plan.name}</h3>
                <p className={styles.planPrice}>{plan.price}</p>
                <p className={styles.planState}>{plan.state}</p>
                <ul>
                  {plan.points.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
                {plan.cta ? (
                  <Link className={styles.primary} href="/signup">
                    Start setup
                  </Link>
                ) : (
                  <span className={styles.planOff}>Not available</span>
                )}
              </li>
            ))}
          </ul>
        </section>

        <section id="faq" className={styles.faq} aria-labelledby="faq-title">
          <Reveal className={styles.sectionHead}>
            <h2 id="faq-title">Questions, answered plainly.</h2>
          </Reveal>
          <div className={styles.faqList}>
            {faqs.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className={styles.close} aria-labelledby="close-title">
          <Reveal>
            <h2 id="close-title">Start with one task.</h2>
            <p>
              Three short questions, then your first task. Skip any step.
            </p>
            <div className={styles.ctasCenter}>
              <Link className={styles.primary} href="/signup">
                Start setup
              </Link>
              <Link className={styles.secondary} href="/demo">
                Try the demo first
              </Link>
            </div>
          </Reveal>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
