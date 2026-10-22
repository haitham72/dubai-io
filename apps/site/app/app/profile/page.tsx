"use client";

import Link from "next/link";
import {
  BackLink,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import { useApi } from "@/lib/use-api";

interface ProfileData {
  told?: Array<{ key?: string; value?: string }>;
  hypotheses?: Array<{
    key?: string;
    value?: string;
    confidence?: number;
    evidence?: string;
  }>;
  me?: Record<string, string>;
}

export default function Profile() {
  const { data, error, loading, reload } = useApi<ProfileData>("/api/profile");

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Me</h1>
        <p>
          Everything the app remembers about you, where you can see it.
          Inferences are hypotheses until you confirm them.
        </p>
      </div>
      {loading ? <LoadingState label="Loading profile…" /> : null}
      {error ? (
        <ErrorState message={`Profile unavailable: ${error}`} onRetry={reload} />
      ) : null}
      {data ? (
        <>
          <SectionCard title="You told me">
            {!data.told || data.told.length === 0 ? (
              <EmptyState
                title="Nothing stored yet"
                body="Facts you state in Ask will appear here with provenance."
              />
            ) : (
              <ul className="listRows">
                {data.told.map((fact, i) => (
                  <li key={i} className="rowCard">
                    <h3>{fact.key ?? "Fact"}</h3>
                    <p>{fact.value ?? "—"}</p>
                    <div className="rowMeta">
                      <Provenance value="user_supplied" />
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
          <SectionCard title="I noticed (hypotheses)">
            {!data.hypotheses || data.hypotheses.length === 0 ? (
              <EmptyState
                title="No hypotheses"
                body="Unconfirmed guesses only ever re-rank options with a visible “Because…” chip — never pre-fill, trigger or set status."
              />
            ) : (
              <ul className="listRows">
                {data.hypotheses.map((h, i) => (
                  <li key={i} className="rowCard">
                    <h3>{h.key ?? "Hypothesis"}</h3>
                    <p>{h.value ?? "—"}</p>
                    <div className="rowMeta">
                      <Provenance value="inferred" />
                      {typeof h.confidence === "number" ? (
                        <span>confidence {h.confidence}</span>
                      ) : null}
                    </div>
                    {h.evidence ? <p>{h.evidence}</p> : null}
                  </li>
                ))}
              </ul>
            )}
          </SectionCard>
        </>
      ) : null}
      <p style={{ color: "var(--muted)" }}>
        <Link href="/">Marketing site</Link> ·{" "}
        <Link href="/privacy">Privacy rules</Link>
      </p>
    </>
  );
}
