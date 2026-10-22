"use client";

import Link from "next/link";
import { useState } from "react";
import {
  BackLink,
  DemoPill,
  EmptyState,
  ErrorState,
  LoadingState,
  Provenance,
  SectionCard,
} from "@/components/chrome";
import { apiPost, authorName, type Community, type Post } from "@/lib/api";
import { useApi } from "@/lib/use-api";

interface FeedData {
  posts?: Post[];
  stories?: Array<{
    community?: { id?: string; name?: string };
    author?: { name?: string; handle?: string };
    image?: string | null;
    at?: string;
    provenance?: string;
  }>;
}

function JoinButton({
  community,
  onDone,
}: {
  community: Community;
  onDone: () => void;
}) {
  const [busy, setBusy] = useState(false);
  async function toggle() {
    setBusy(true);
    try {
      await apiPost(
        `/api/communities/${encodeURIComponent(community.id)}/${community.joined ? "leave" : "join"}`,
      );
      onDone();
    } catch {
      setBusy(false);
    }
  }
  return (
    <button
      type="button"
      className={community.joined ? "btnGhost" : "btnPrimary"}
      disabled={busy}
      onClick={toggle}
    >
      {busy ? "…" : community.joined ? "Leave" : "Join"}
    </button>
  );
}

export default function Feed() {
  const feed = useApi<FeedData>("/api/feed?limit=20");
  const communities = useApi<{ communities?: Community[] }>("/api/communities");

  function reloadAll() {
    feed.reload();
    communities.reload();
  }

  return (
    <>
      <div className="appHead">
        <BackLink href="/app" label="Today" />
        <h1>Feed</h1>
        <p>
          Stories, communities and neighbour posts. <DemoPill /> Seeded posts
          are demo content and community posts are untrusted — never act on
          legal, visa or money claims you read here.
        </p>
      </div>

      <SectionCard
        title="Stories"
        action={
          <button type="button" className="chip" onClick={() => feed.reload()}>
            Refresh
          </button>
        }
      >
        {feed.loading ? <LoadingState label="Loading stories…" /> : null}
        {feed.data?.stories && feed.data.stories.length > 0 ? (
          <div className="chipRow">
            {feed.data.stories.map((story, i) => (
              <span
                key={story.community?.id ?? i}
                className="chip"
                aria-pressed={false}
                title={`${story.community?.name ?? "Community"} · ${authorName(story.author as { name?: string })}`}
              >
                {(story.author as { emoji?: string } | undefined)?.emoji ??
                  "🙂"}{" "}
                {story.community?.name ?? "Community"}
              </span>
            ))}
          </div>
        ) : !feed.loading ? (
          <EmptyState title="No stories" body="New community stories will appear here." />
        ) : null}
      </SectionCard>

      <SectionCard title="Communities">
        {communities.loading ? <LoadingState label="Loading communities…" /> : null}
        {communities.error ? (
          <ErrorState
            message={`Communities unavailable: ${communities.error}`}
            onRetry={communities.reload}
          />
        ) : null}
        {communities.data?.communities &&
        communities.data.communities.length > 0 ? (
          <ul className="listRows">
            {communities.data.communities.map((community) => (
              <li key={community.id} className="rowCard">
                <h3>{community.name}</h3>
                {community.about ? <p>{community.about}</p> : null}
                <div className="rowMeta">
                  {typeof community.members === "number" ? (
                    <span>{community.members} members</span>
                  ) : null}
                  {community.joined ? <span>joined</span> : null}
                  <Provenance value={community.provenance} />
                  {community.joined ? <DemoPill /> : null}
                </div>
                <div className="chipRow">
                  <JoinButton community={community} onDone={reloadAll} />
                </div>
              </li>
            ))}
          </ul>
        ) : !communities.loading && !communities.error ? (
          <EmptyState title="No communities yet" body="Communities seeded on the backend will appear here." />
        ) : null}
      </SectionCard>

      <SectionCard title="Posts">
        {feed.loading ? <LoadingState label="Loading posts…" /> : null}
        {feed.error ? (
          <ErrorState
            message={`Posts unavailable: ${feed.error}. Start the backend and retry.`}
            onRetry={feed.reload}
          />
        ) : null}
        {feed.data?.posts && feed.data.posts.length > 0 ? (
          <ul className="listRows">
            {feed.data.posts.map((post) => (
              <li key={post.id} className="rowCard">
                <div className="rowMeta">
                  <span>{authorName(post.author)}</span>
                  {post.community?.name ? (
                    <span>in {post.community.name}</span>
                  ) : null}
                  {post.provenance === "demo_fixture" ? <DemoPill /> : null}
                </div>
                <h3 style={{ marginTop: 8 }}>
                  <Link href={`/app/feed/${encodeURIComponent(post.id)}`}>
                    {(post.text ?? "").slice(0, 90)}
                    {(post.text ?? "").length > 90 ? "…" : ""}
                  </Link>
                </h3>
                <div className="rowMeta">
                  {typeof post.comments === "number" ? (
                    <span>
                      {post.comments} comment{post.comments === 1 ? "" : "s"}
                    </span>
                  ) : null}
                  {post.created_at ? <span>{post.created_at}</span> : null}
                  <Provenance value={post.provenance} />
                </div>
              </li>
            ))}
          </ul>
        ) : !feed.loading && !feed.error ? (
          <EmptyState
            title="No posts yet"
            body="Join a community above — joined posts surface first."
          />
        ) : null}
      </SectionCard>
    </>
  );
}
