"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import RealPostCard from "@/components/RealPostCard";
import * as api from "@/lib/api";
import type { FeedSort } from "@/lib/feed";
import { followedHandlesFrom, groupNameMap } from "@/lib/feed";
import { isSignedIn } from "@/lib/session";
import type { Post } from "@/lib/types";

const SORTS: { id: FeedSort; label: string }[] = [
  { id: "hot", label: "Hot" },
  { id: "top", label: "Top" },
  { id: "new", label: "New" },
  { id: "rising", label: "Rising" },
  { id: "controversial", label: "Controversial" },
];

export default function TagFeedPage() {
  const params = useParams<{ tag: string }>();
  const rawTag = decodeURIComponent(String(params?.tag ?? ""));
  const tag = rawTag.trim().replace(/^#+/, "").toLowerCase();

  const [sort, setSort] = useState<FeedSort>("new");
  const [posts, setPosts] = useState<Post[]>([]);
  const [followed, setFollowed] = useState<string[]>([]);
  const [groupNames, setGroupNames] = useState<Record<string, string>>({});
  const [state, setState] = useState<"loading" | "live" | "error" | "signedout">("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn()) {
      setState("signedout");
      return;
    }
    setState("loading");
    setError(null);
    try {
      const [p, f, g] = await Promise.all([
        api.getFeed(50, sort, tag),
        api.getFollows().catch(() => []),
        api.getGroups().catch(() => []),
      ]);
      setPosts(p);
      setFollowed(followedHandlesFrom(f));
      setGroupNames(groupNameMap(g));
      setState("live");
    } catch (e) {
      setError((e as Error).message || "Could not load tag feed");
      setState("error");
    }
  }, [sort, tag]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <section>
      <p>
        <Link href="/">← Feed</Link>
      </p>
      <h1>#{tag}</h1>
      <p className="sub">Posts tagged #{tag}</p>

      <div className="feed-v2">
        <div className="v2-pills" role="tablist" aria-label="Sort">
          {SORTS.map((s) => (
            <button
              key={s.id}
              type="button"
              className="v2-pill"
              role="tab"
              aria-selected={sort === s.id}
              onClick={() => setSort(s.id)}
            >
              {s.label}
            </button>
          ))}
        </div>

        {state === "signedout" && (
          <div className="notice" role="status">
            Sign in to browse #{tag}. <Link href="/signin">Sign in</Link>
          </div>
        )}
        {state === "loading" && <p className="v2-empty">Loading…</p>}
        {state === "error" && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {state === "live" && posts.length === 0 && (
          <p className="v2-empty" data-testid="tag-empty">
            No posts tagged #{tag} yet.
          </p>
        )}
        {state === "live" &&
          posts.map((p) => (
            <RealPostCard
              key={p.id}
              post={p}
              groupName={p.group_id ? groupNames[p.group_id] : undefined}
              following={followed.some(
                (h) => h.toLowerCase() === p.author.handle.toLowerCase(),
              )}
              onChanged={() => void load()}
            />
          ))}
      </div>
    </section>
  );
}
