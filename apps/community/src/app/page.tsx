"use client";
import { useEffect, useMemo, useState } from "react";
import PostCard from "@/components/PostCard";
import { getFeed } from "@/lib/api";
import { filterPostsByLane } from "@/lib/feed";
import { followedHandles, joinedGroupIds, seedPosts } from "@/lib/seed";
import type { Lane, Post } from "@/lib/types";

const LANES: { id: Lane; label: string }[] = [
  { id: "following", label: "Following" },
  { id: "communities", label: "Communities" },
  { id: "discover", label: "Discover" },
];

export default function FeedPage() {
  const [lane, setLane] = useState<Lane>("following");
  const [posts, setPosts] = useState<Post[]>(seedPosts);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getFeed()
      .then((p) => { if (live && p.length) setPosts(p); })
      .catch(() => { if (live) setNotice("Community service unavailable — showing the demo preview feed below."); });
    return () => { live = false; };
  }, []);

  const visible = useMemo(
    () => filterPostsByLane(posts, lane, { followedHandles, joinedGroupIds }),
    [posts, lane],
  );

  return (
    <section>
      <h1>Feed</h1>
      <p className="sub">People and communities you follow.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      <div className="lanes" role="tablist" aria-label="Feed lanes">
        {LANES.map((l) => (
          <button key={l.id} role="tab" aria-selected={lane === l.id} className={lane === l.id ? "lane-btn active" : "lane-btn"} onClick={() => setLane(l.id)}>
            {l.label}
          </button>
        ))}
      </div>
      {visible.length === 0
        ? <p className="empty">Nothing here yet. Try another lane.</p>
        : visible.map((p) => <PostCard key={p.id} post={p} />)}
    </section>
  );
}
