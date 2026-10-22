"use client";

import Link from "next/link";
import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import {
  apiUrl,
  type NewsArticle,
  type TaskItem,
  type TodayData,
} from "@/lib/api";
import { useApi } from "@/lib/use-api";

function TaskRow({ task }: { task: TaskItem }) {
  const decision = task.decision;
  return (
    <li className="rowCard">
      <h3>
        {task.id ? (
          <Link href={`/app/tasks/${task.id}`}>{task.title ?? task.id}</Link>
        ) : (
          (task.title ?? "Untitled")
        )}
      </h3>
      {task.detail ? <p>{task.detail}</p> : null}
      {decision ? (
        <p>
          <strong>Decision{decision.kind ? ` · ${decision.kind}` : ""}:</strong>{" "}
          {decision.title ?? decision.detail ?? "Review required."}{" "}
          {decision.amount_aed !== undefined ? (
            <span>AED {decision.amount_aed}</span>
          ) : null}
        </p>
      ) : null}
      <div className="rowMeta">
        {task.status ? <span>{task.status}</span> : null}
        {task.due_at ? <span>due {task.due_at}</span> : null}
        {decision?.action_id ? (
          <Link href={`/app/decisions/${decision.action_id}`}>
            Open decision →
          </Link>
        ) : null}
        {task.id ? <Link href={`/app/tasks/${task.id}`}>Details →</Link> : null}
      </div>
    </li>
  );
}

function Lane({
  title,
  tasks,
  empty,
}: {
  title: string;
  tasks: TaskItem[];
  empty: string;
}) {
  return (
    <SectionCard title={title}>
      {tasks.length === 0 ? (
        <EmptyState title="Nothing here" body={empty} />
      ) : (
        <ul className="listRows">
          {tasks.map((task, i) => (
            <TaskRow key={task.id ?? `${title}-${i}`} task={task} />
          ))}
        </ul>
      )}
    </SectionCard>
  );
}

function News() {
  const { data, error, loading, reload } = useApi<{ articles?: NewsArticle[] }>(
    "/api/reading?limit=6",
  );
  if (loading) return <LoadingState label="Loading headlines…" />;
  if (error)
    return (
      <ErrorState
        message={`Headlines unavailable: ${error}. The backend may be offline.`}
        onRetry={reload}
      />
    );
  const articles = data?.articles ?? [];
  if (articles.length === 0)
    return (
      <EmptyState
        title="No headlines right now"
        body="Real headline retrieval lives in the prototype; when the news provider is unreachable there is nothing to show — and nothing is invented."
      />
    );
  return (
    <ul className="listRows">
      {articles.map((a, i) => (
        <li key={a.id ?? i} className="rowCard">
          {a.thumbnail?.url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={apiUrl(a.thumbnail.url)}
              alt=""
              className="appImg"
              loading="lazy"
              style={{ aspectRatio: "16 / 9", marginBottom: 12 }}
            />
          ) : null}
          <h3>
            {a.url ? (
              <a href={a.url} rel="noreferrer">
                {a.title ?? "Untitled story"}
              </a>
            ) : (
              (a.title ?? "Untitled story")
            )}
          </h3>
          {a.subtitle ? <p>{a.subtitle}</p> : null}
          <div className="rowMeta">
            {a.source ? <span>{a.source}</span> : null}
            {a.published_at ? <span>{a.published_at}</span> : null}
            <Provenance value={a.provenance} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function AppHome() {
  const { data, error, loading, reload } = useApi<TodayData>("/api/today");
  return (
    <>
      <div className="appHead">
        <BackLink href="/" label="Marketing site" />
        <h1>Today</h1>
        <p>
          What needs you, what&apos;s running, what&apos;s on your list — plus
          the latest headlines. <DemoPill /> Seeded content is labelled where
          it appears.
        </p>
      </div>
      {loading ? <LoadingState label="Loading Today…" /> : null}
      {error ? (
        <ErrorState
          message={`Today is unavailable: ${error}. Start the backend (uvicorn app.main:app) and retry.`}
          onRetry={reload}
        />
      ) : null}
      {data ? (
        <>
          <Lane
            title={`Needs you${data.counts?.needs_you ? ` (${data.counts.needs_you})` : ""}`}
            tasks={data.needs_you?.tasks ?? []}
            empty="No decisions waiting. When one arrives it will show its basis and ask for approval first."
          />
          <Lane
            title={`Running${data.counts?.running ? ` (${data.counts.running})` : ""}`}
            tasks={data.running?.tasks ?? []}
            empty="Nothing running right now."
          />
          <Lane
            title="On your list"
            tasks={data.on_list?.tasks ?? []}
            empty="Your list is clear."
          />
        </>
      ) : null}
      <SectionCard
        title="News"
        action={<Link href="/app/feed">Community feed →</Link>}
      >
        <News />
      </SectionCard>
    </>
  );
}
