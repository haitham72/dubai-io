"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bell, ChevronLeft, Home, PenLine, Search, UserRound, Users,
} from "lucide-react";
import PostCard from "@/components/PostCard";
import RealPostCard from "@/components/RealPostCard";
import DemoPill from "@/components/DemoPill";
import * as api from "@/lib/api";
import type { DiscoveryItem, DiscoveryResult } from "@/lib/api";
import type { Group, Post } from "@/lib/types";
import { desktopPosts, jlt, phonePosts, suggested } from "@/lib/feedFixture";
import {
  feedState, filterPostsByLane, followedHandlesFrom, groupNameMap, joinedGroupIdsFrom,
  sortPosts, splitDiscovery,
} from "@/lib/feed";
import type { FeedSort } from "@/lib/feed";
import { isSignedIn } from "@/lib/session";

type Sort = FeedSort;
type Lane = "foryou" | "following" | "communities";

const tabs = [
  { href: "/", label: "Home", icon: Home },
  { href: "/communities", label: "Communities", icon: Users },
  { href: "/create", label: "Create", icon: PenLine },
  { href: "/inbox", label: "Inbox", icon: Bell },
  { href: "/profile", label: "Me", icon: UserRound },
];

function sortFixture(posts: typeof phonePosts, sort: Sort) {
  const copy = [...posts];
  if (sort === "top") copy.sort((a, b) => b.votes - a.votes);
  if (sort === "hot") copy.sort((a, b) => b.comments - a.comments);
  return copy;
}

export default function FeedScreen() {
  const router = useRouter();
  const [sort, setSort] = useState<Sort>("new");
  const [lane, setLane] = useState<Lane>("foryou");
  const [query, setQuery] = useState("");

  const [signedIn, setSignedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [apiFailed, setApiFailed] = useState(false);
  const [posts, setPosts] = useState<Post[]>([]);
  const [followed, setFollowed] = useState<string[]>([]);
  const [groups, setGroups] = useState<Group[]>([]);
  const [discovery, setDiscovery] = useState<DiscoveryResult | null>(null);
  const [foryouPosts, setForyouPosts] = useState<Post[]>([]);
  const [foryouWhy, setForyouWhy] = useState<Record<string, string>>({});
  const [unread, setUnread] = useState(0);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isSignedIn()) { setSignedIn(false); setLoading(false); return; }
    setSignedIn(true);
    setLoading(true); setApiFailed(false); setNotice(null);
    const results = await Promise.allSettled([
      api.getFeed(), api.getFollows(), api.getGroups(), api.getDiscovery(20), api.getNotifications(),
    ]);
    const [feedR, followsR, groupsR, discR, notifR] = results;
    if (feedR.status === "rejected") {
      const status = (feedR.reason as { status?: number })?.status ?? 0;
      if (status === 401) { setSignedIn(false); setLoading(false); return; }
      setApiFailed(true); setLoading(false);
      setNotice("Community service unavailable — showing the demo preview feed below.");
      return;
    }
    setPosts(feedR.value);
    if (followsR.status === "fulfilled") setFollowed(followedHandlesFrom(followsR.value));
    if (groupsR.status === "fulfilled") setGroups(groupsR.value);
    if (notifR.status === "fulfilled") setUnread(notifR.value.unread_count);
    if (discR.status === "fulfilled") {
      setDiscovery(discR.value);
      const { postIds } = splitDiscovery(discR.value.items ?? []);
      const why: Record<string, string> = {};
      for (const it of discR.value.items ?? []) {
        const pid = it.post_id ?? (it.kind === "post" ? it.id : undefined);
        if (pid && it.why_this) why[pid] = it.why_this;
      }
      setForyouWhy(why);
      const fetched = await Promise.allSettled(postIds.slice(0, 12).map((id) => api.getPost(id)));
      setForyouPosts(fetched.flatMap((r) => (r.status === "fulfilled" ? [r.value] : [])));
    } else {
      setDiscovery(null); setForyouPosts([]); setForyouWhy({});
    }
    setLoading(false);
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);

  const state = feedState({ loading, signedIn, apiFailed, postCount: posts.length + foryouPosts.length });
  const groupNames = useMemo(() => groupNameMap(groups), [groups]);
  const joinedIds = useMemo(() => joinedGroupIdsFrom(groups), [groups]);
  const followCtx = useMemo(() => ({ followedHandles: followed, joinedGroupIds: joinedIds }), [followed, joinedIds]);

  const lanePosts = useMemo(() => {
    const base = lane === "following"
      ? filterPostsByLane(posts, "following", followCtx)
      : lane === "communities"
        ? filterPostsByLane(posts, "communities", followCtx)
        : posts;
    return sortPosts(base, sort);
  }, [posts, lane, sort, followCtx]);

  const foryouGroups = useMemo(
    () => splitDiscovery(discovery?.items ?? []).groups,
    [discovery],
  );

  // For-you = discovery picks first, then the rest of the real feed (deduped),
  // so a user's own new post always shows at the top of the default lane.
  // Top/Hot re-rank the whole lane by engagement like the other lanes.
  const foryouAll = useMemo(() => {
    const seen = new Set(foryouPosts.map((p) => p.id));
    const merged = [...foryouPosts, ...posts.filter((p) => !seen.has(p.id))];
    return sort === "new" ? merged : sortPosts(merged, sort);
  }, [foryouPosts, posts, sort]);

  const demoPhone = useMemo(() => sortFixture(phonePosts, sort), [sort]);
  const demoDesktop = useMemo(() => {
    const base = lane === "following" ? desktopPosts.filter((p) => p.followed) : desktopPosts;
    return sortFixture(base, sort);
  }, [lane, sort]);

  const goSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
  };

  const onFollowChange = useCallback((handle: string, nowFollowing: boolean) => {
    setFollowed((prev) => {
      const h = handle.toLowerCase();
      const has = prev.some((x) => x.toLowerCase() === h);
      if (nowFollowing && !has) return [...prev, handle];
      if (!nowFollowing && has) return prev.filter((x) => x.toLowerCase() !== h);
      return prev;
    });
  }, []);

  const renderRealPost = (post: Post, why?: string) => (
    <RealPostCard
      key={post.id}
      post={post}
      groupName={post.group_id ? groupNames[post.group_id] : undefined}
      following={followed.some((h) => h.toLowerCase() === post.author.handle.toLowerCase())}
      onFollowChange={onFollowChange}
      onChanged={() => void refresh()}
      why={why}
    />
  );

  const renderDiscoveryGroup = (g: DiscoveryItem) => (
    <DiscoveryGroupCard key={g.group_id ?? g.id} item={g} onChanged={() => void refresh()} />
  );

  const laneTabs: { id: Lane; label: string }[] = [
    { id: "foryou", label: "For you" },
    { id: "following", label: "Following" },
    { id: "communities", label: "Communities" },
  ];

  const feedBody = state === "live" || state === "empty" ? (
    lane === "foryou" ? (
      <>
        {foryouAll.map((p) => renderRealPost(p, foryouWhy[p.id]))}
        {foryouGroups.map(renderDiscoveryGroup)}
        {foryouAll.length === 0 && foryouGroups.length === 0 && (
          <p className="v2-empty" data-testid="feed-empty">Nothing to suggest yet — follow people or join communities to fill this lane.</p>
        )}
        {discovery?.reason && <p className="v2-meta">{discovery.reason}</p>}
      </>
    ) : lanePosts.length === 0 ? (
      <p className="v2-empty" data-testid="feed-empty">
        {lane === "following" ? "No posts from people you follow yet." : "No posts in your communities yet."}
      </p>
    ) : (
      lanePosts.map((p) => renderRealPost(p))
    )
  ) : state === "demo" ? (
    <>
      {notice && <div className="v2-notice" role="status">{notice} <DemoPill /></div>}
      {demoPhone.map((post) => <PostCard key={post.id} post={post} header="person" />)}
    </>
  ) : (
    <p className="v2-empty">Loading…</p>
  );

  return (
    <>
      <div className="v2-phone">
        <header className="v2-topbar">
          <button type="button" className="v2-iconbtn" aria-label="Back"><ChevronLeft size={18} /></button>
          <div className="v2-iconrow">
            <Link href="/search" className="v2-iconbtn" aria-label="Search"><Search size={18} /></Link>
          </div>
        </header>
        {state === "demo" && (
          <section className="v2-community">
            <img src={jlt.image} alt="JLT towers by the water, demo photo" />
            <div>
              <h1>{jlt.name}</h1>
              <p>{jlt.members}</p>
              <p>{jlt.blurb}</p>
            </div>
            <button type="button" className="v2-joined" aria-pressed="true">Joined</button>
          </section>
        )}
        {state !== "demo" && (
          <div className="v2-lanes" role="tablist" aria-label="Feed">
            {laneTabs.map((t) => (
              <button key={t.id} type="button" className="v2-tabtext" role="tab" aria-selected={lane === t.id} onClick={() => setLane(t.id)}>{t.label}</button>
            ))}
          </div>
        )}
        {state !== "demo" && <SortPills sort={sort} onSort={setSort} />}
        {feedBody}
        <nav className="v2-tabbar" aria-label="Primary">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const current = tab.href === "/";
            return (
              <Link key={tab.href} href={tab.href} className="v2-tab" aria-current={current ? "page" : undefined}>
                <span className="v2-tabicon"><Icon size={18} aria-hidden="true" /></span>
                {tab.label}
                {tab.href === "/inbox" && unread > 0 && <span className="v2-badge">{unread}</span>}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="v2-desktop">
        <aside className="v2-nav">
          <Link href="/" className="v2-logo">Dubai-io</Link>
          <Link href="/" className="v2-navlink" aria-current="page"><Home size={18} aria-hidden="true" />Home</Link>
          <Link href="/communities" className="v2-navlink"><Users size={18} aria-hidden="true" />Communities</Link>
          <Link href="/inbox" className="v2-navlink"><Bell size={18} aria-hidden="true" />Inbox{unread > 0 && <span className="v2-badge">{unread}</span>}</Link>
          <Link href="/profile" className="v2-navlink"><UserRound size={18} aria-hidden="true" />Me</Link>
          <Link href="/create" className="v2-postbtn"><PenLine size={18} aria-hidden="true" />Post</Link>
        </aside>
        <main>
          <div className="v2-centerhead">
            {state !== "demo" ? (
              <div className="v2-tabs" role="tablist" aria-label="Feed">
                {laneTabs.map((t) => (
                  <button key={t.id} type="button" className="v2-tabtext" role="tab" aria-selected={lane === t.id} onClick={() => setLane(t.id)}>{t.label}</button>
                ))}
              </div>
            ) : (
              <div className="v2-tabs"><span className="v2-tabtext">For you</span></div>
            )}
            {state !== "demo" && <SortPills sort={sort} onSort={setSort} />}
            <form className="v2-search" onSubmit={goSearch} role="search">
              <Search size={16} aria-hidden="true" />
              <input type="search" placeholder="Search communities, posts or ask anything..." aria-label="Search" value={query} onChange={(e) => setQuery(e.target.value)} />
            </form>
          </div>
          {state === "demo" ? demoDesktop.map((post) => <PostCard key={post.id} post={post} header="community" />) : feedBody}
        </main>
        <aside className="v2-rail">
          {state === "demo" ? (
            <section className="v2-railcard" id="ask">
              <div className="v2-askrow">
                <h2>Ask Dubai-io privately</h2>
                <span className="v2-demo">Demo data</span>
              </div>
              <p className="v2-meta">Get local advice, plan things, check latest info.</p>
              <input className="v2-askbox" placeholder="Ask anything about life in Dubai..." aria-label="Ask Dubai-io privately" />
            </section>
          ) : null}
          <section className="v2-railcard">
            <div className="v2-askrow">
              <h2>Communities for you</h2>
              {state === "demo" && <span className="v2-demo">Demo data</span>}
            </div>
            {state === "demo"
              ? suggested.map((group) => (
                <div className="v2-suggest" key={group.name}>
                  <img src={group.image} alt="" />
                  <div>
                    <strong>{group.name}</strong>
                    <span>{group.members}</span>
                    <span>{group.blurb}</span>
                  </div>
                  <button type="button" className="v2-join">Join</button>
                </div>
              ))
              : foryouGroups.map(renderDiscoveryGroup)}
            {state !== "demo" && foryouGroups.length === 0 && <p className="v2-meta">No suggestions yet.</p>}
            <Link href="/communities" className="v2-more">Discover more communities →</Link>
          </section>
        </aside>
      </div>
    </>
  );
}

function SortPills({ sort, onSort }: { sort: Sort; onSort: (sort: Sort) => void }) {
  const items: { id: Sort; label: string }[] = [
    { id: "new", label: "New" },
    { id: "top", label: "Top" },
    { id: "hot", label: "Hot" },
  ];
  return (
    <div className="v2-pills" role="tablist" aria-label="Sort">
      {items.map((item) => (
        <button key={item.id} type="button" className="v2-pill" role="tab" aria-selected={sort === item.id} onClick={() => onSort(item.id)}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

function DiscoveryGroupCard({ item, onChanged }: { item: DiscoveryItem; onChanged?: () => void }) {
  const [busy, setBusy] = useState(false);
  const [joined, setJoined] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const gid = item.group_id ?? item.id;
  const why = item.why_this ?? item.why_chip;

  async function join() {
    if (busy || joined) return;
    setBusy(true); setError(null);
    try {
      await api.joinGroup(gid);
      setJoined(true);
    } catch (e) {
      setError((e as Error).message || "Could not join");
    } finally { setBusy(false); }
  }

  return (
    <section className="v2-card" data-testid="discovery-group">
      <div className="v2-askrow">
        <h2 className="v2-name">{item.name}</h2>
        {item.demo_data && <DemoPill />}
      </div>
      <p className="v2-body">{item.description}</p>
      <p className="v2-meta">{item.members != null ? `${item.members} members` : ""}{item.origin === "cold_start" ? " · Popular public community" : ""}</p>
      {why && <div className="v2-chips"><span className="v2-why">{why}</span></div>}
      <div className="v2-actions">
        <Link href={`/communities/${encodeURIComponent(gid)}`} className="v2-pill">Open</Link>
        <button type="button" className="v2-join" onClick={join} disabled={busy || joined}>
          {joined ? "Joined" : busy ? "Joining…" : "Join"}
        </button>
      </div>
      {error && <p className="v2-error" role="alert">{error}</p>}
    </section>
  );
}
