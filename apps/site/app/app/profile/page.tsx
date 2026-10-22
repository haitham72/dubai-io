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

interface ProfileFact {
  key?: string;
  value?: string;
  facet?: string;
}

interface ProfileDoc {
  core?: { display_name?: string; home_area?: string; language?: string };
  facts?: ProfileFact[];
}

interface ProfileEpisodes {
  episodes?: Array<{ at?: string; kind?: string; text?: string; source?: string }>;
  overrides?: Record<string, string>;
}

export default function Profile() {
  const doc = useApi<ProfileDoc>("/api/profile/me");
  const seen = useApi<ProfileEpisodes>("/api/profile");
  const error = doc.error ?? seen.error;
  const loading = doc.loading || seen.loading;
  const reload = () => {
    doc.reload();
    seen.reload();
  };

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
      {!loading && !error ? (
        <>
          <SectionCard title="You told me">
            {(!doc.data?.facts || doc.data.facts.length === 0) &&
            !doc.data?.core?.display_name &&
            !doc.data?.core?.home_area ? (
              <EmptyState
                title="Nothing stored yet"
                body="Facts you state in Ask appear here with user_supplied provenance. Confirming a hypothesis also records it here."
              />
            ) : (
              <ul className="listRows">
                {doc.data?.core?.display_name || doc.data?.core?.home_area ? (
                  <li className="rowCard">
                    <h3>
                      {doc.data.core.display_name ?? "You"}
                      {doc.data.core.home_area
                        ? ` · ${doc.data.core.home_area}`
                        : ""}
                    </h3>
                    <div className="rowMeta">
                      <Provenance value="user_supplied" />
                    </div>
                  </li>
                ) : null}
                {(doc.data?.facts ?? []).map((fact, i) => (
                  <li key={fact.key ?? i} className="rowCard">
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
          <SectionCard title="I noticed (observed moments)">
            {(!seen.data?.episodes || seen.data.episodes.length === 0) ? (
              <EmptyState
                title="No hypotheses"
                body="Unconfirmed guesses only ever re-rank options with a visible “Because…” chip — never pre-fill, trigger or set status."
              />
            ) : (
              <ul className="listRows">
                {seen.data.episodes.map((episode, i) => (
                  <li key={i} className="rowCard">
                    <h3>{episode.kind ?? "Moment"}</h3>
                    <p>{episode.text ?? "—"}</p>
                    <div className="rowMeta">
                      <Provenance value="inferred" />
                      {episode.at ? <span>{episode.at}</span> : null}
                      {episode.source ? <span>{episode.source}</span> : null}
                    </div>
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
