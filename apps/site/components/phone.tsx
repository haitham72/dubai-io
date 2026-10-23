import styles from "./phone.module.css";

/**
 * A phone frame holding an HTML/CSS rendering of the app's chat. It follows
 * the app's conventions (plain assistant text, tinted user box, white
 * rounded action boxes). Every screen is an illustration built with demo
 * data and says so.
 */

export type ScreenId = "tell" | "prepare" | "approve" | "status";

function Bar() {
  return (
    <div className={styles.bar}>
      <span className={styles.barTitle}>Dubai-io</span>
      <span className={styles.demo}>Demo data</span>
    </div>
  );
}

function You({ children }: { children: React.ReactNode }) {
  return <p className={styles.you}>{children}</p>;
}

function Bot({ children }: { children: React.ReactNode }) {
  return <p className={styles.bot}>{children}</p>;
}

function TellScreen() {
  return (
    <>
      <Bar />
      <div className={styles.thread}>
        <You>I live in Dubai Marina with my partner and our dog.</You>
        <Bot>Got it. Here is what I saved, so you can check it.</Bot>
        <div className={styles.card}>
          <p className={styles.cardTitle}>You told me</p>
          <dl className={styles.facts}>
            <div>
              <dt>Area</dt>
              <dd>Dubai Marina</dd>
            </div>
            <div>
              <dt>Household</dt>
              <dd>2 adults, 1 dog</dd>
            </div>
          </dl>
          <div className={styles.row}>
            <span className={styles.ghost}>Edit</span>
            <span className={styles.ghost}>Forget</span>
          </div>
        </div>
      </div>
    </>
  );
}

function PrepareScreen() {
  return (
    <>
      <Bar />
      <div className={styles.thread}>
        <You>Get my shirts pressed tonight.</You>
        <Bot>
          I prepared an order from the demo directory. Nothing is sent yet.
        </Bot>
        <div className={styles.card}>
          <p className={styles.cardTitle}>Palm Quick Press</p>
          <dl className={styles.facts}>
            <div>
              <dt>Service</dt>
              <dd>Shirt pressing</dd>
            </div>
            <div>
              <dt>Price</dt>
              <dd>AED 4 per shirt</dd>
            </div>
            <div>
              <dt>Pickup</dt>
              <dd>Today 18:00</dd>
            </div>
          </dl>
          <p className={styles.fine}>Published price, demo fixture.</p>
          <span className={styles.primary}>Review what is shared</span>
        </div>
      </div>
    </>
  );
}

function ApproveScreen() {
  return (
    <>
      <Bar />
      <div className={styles.thread}>
        <Bot>Check this before it goes anywhere.</Bot>
        <div className={styles.card}>
          <p className={styles.cardTitle}>Approve and send</p>
          <p className={styles.label}>Shared with Palm Quick Press</p>
          <ul className={styles.list}>
            <li>Pickup area: Dubai Marina</li>
            <li>Item: shirt pressing</li>
            <li>Slot: Today 18:00</li>
          </ul>
          <p className={styles.label}>Not shared</p>
          <ul className={styles.list}>
            <li>Phone number</li>
            <li>Payment details</li>
          </ul>
          <div className={styles.row}>
            <span className={styles.primary}>Approve and send</span>
            <span className={styles.ghost}>Not now</span>
          </div>
        </div>
      </div>
    </>
  );
}

function StatusScreen() {
  return (
    <>
      <Bar />
      <div className={styles.thread}>
        <Bot>Sent. I will only say more when the shop does.</Bot>
        <div className={styles.card}>
          <p className={styles.cardTitle}>Shirt pressing order</p>
          <ol className={styles.steps}>
            <li data-state="done">
              <span>Sent after your approval</span>
              <em>You approved</em>
            </li>
            <li data-state="wait">
              <span>Shop confirmation</span>
              <em>Waiting for the shop</em>
            </li>
            <li data-state="none">
              <span>Ready for pickup</span>
              <em>Unknown until reported</em>
            </li>
          </ol>
          <p className={styles.fine}>
            Confirmed appears only after the shop confirms.
          </p>
        </div>
      </div>
    </>
  );
}

const SCREENS: Record<ScreenId, () => React.ReactElement> = {
  tell: TellScreen,
  prepare: PrepareScreen,
  approve: ApproveScreen,
  status: StatusScreen,
};

export function Phone({
  screen,
  layers = false,
  className = "",
}: {
  screen: ScreenId;
  /** Render all four screens stacked and crossfade by `screen`. */
  layers?: boolean;
  className?: string;
}) {
  const ids = Object.keys(SCREENS) as ScreenId[];
  return (
    <div
      className={`${styles.phone} ${className}`}
      role="img"
      aria-label="Illustration of the Dubai-io chat, built with demo data"
    >
      <div className={styles.island} aria-hidden="true" />
      <div className={styles.screen} aria-hidden="true">
        <div className={styles.composer}>Ask Dubai-io</div>
        {(layers ? ids : [screen]).map((id) => {
          const S = SCREENS[id];
          return (
            <div
              key={id}
              className={styles.layer}
              data-active={id === screen ? "true" : "false"}
            >
              <S />
            </div>
          );
        })}
      </div>
    </div>
  );
}
