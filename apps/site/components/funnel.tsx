import Link from "next/link";
import type { ReactNode } from "react";
import { Wordmark } from "./chrome";
import styles from "./funnel.module.css";

export const FUNNEL = ["Start", "Set up", "First task", "Done"] as const;

export function FunnelShell({
  step,
  skipHref,
  skipLabel,
  children,
}: {
  /** 0-based index into FUNNEL. */
  step: number;
  skipHref: string;
  skipLabel: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.shell}>
      <header className={styles.top}>
        <Wordmark />
        <Link href={skipHref} className={styles.skip}>
          {skipLabel}
        </Link>
      </header>
      <nav aria-label="Progress" className={styles.progress}>
        <ol>
          {FUNNEL.map((label, i) => (
            <li
              key={label}
              data-state={i < step ? "done" : i === step ? "current" : "todo"}
              aria-current={i === step ? "step" : undefined}
            >
              <span className={styles.bar} />
              <span className={styles.label}>
                {label}
                <span className="sr-only">
                  {i < step ? " (done)" : i === step ? " (current)" : ""}
                </span>
              </span>
            </li>
          ))}
        </ol>
      </nav>
      <main className={styles.main}>{children}</main>
    </div>
  );
}

export function FunnelError({
  message,
  onRetry,
  busy,
}: {
  message: string;
  onRetry: () => void;
  busy?: boolean;
}) {
  return (
    <div className={styles.error} role="alert">
      <p>
        <strong>That did not go through.</strong> {message}
      </p>
      <p>Nothing was lost. You can try again, or skip this step.</p>
      <button
        type="button"
        className={styles.btnSecondary}
        onClick={onRetry}
        disabled={busy}
      >
        Try again
      </button>
    </div>
  );
}

export { styles as funnelStyles };
