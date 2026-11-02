"use client";

import { useMemo, useState } from "react";
import { ArrowBigUp, Car, Lock, MessageCircle, X } from "lucide-react";
import { apiPost } from "../data/api";
import {
  authorEmoji,
  authorName,
  formatWhen,
  isDemoProvenance,
  mediaSrc,
  type Community,
  type FeedComment,
  type Post,
} from "../data/social";
import { useApi } from "../data/use-api";
import { useApp } from "../state";
import { Avatar, Button, DemoPill, SearchField } from "../ui";
import s from "./community.module.css";

type FeedTab = "foryou" | "following";
type Sort = "new" | "top" | "hot";

function StateBox({ title, body, onRetry }: { title: string; body: string; onRetry?: () => void }) {
  return (
    <div className={s.state} role="status">
      <strong>{title}</strong>
      <p>{body}</p>
      {onRetry ? (
        <button type="button" className={s.retry} onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

function looksLikeTransportAsk(text: string): boolean {
  return /\b(taxi|dxb|airport|uber|careem|marina|ride|transfer|terminal)\b/i.test(text);
}

/** Higgsfield l09 — public thread stays public; private prep never posts. */
function PrivateHandoff({ postText, onOpenAssistant }: { postText: string; onOpenAssistant: () => void }) {
  const title = looksLikeTransportAsk(postText)
    ? "Taxi DXB T1 to Dubai Marina, 01:00"
    : "Prepare this privately";
  const detail = looksLikeTransportAsk(postText)
    ? "Pickup from Dubai International Airport Terminal 1 at 01:00 (example). Estimates only until you approve a registered action."
    : "I can help plan this in a private task. Nothing from private chat is posted to the community.";

  return (
    <aside className={s.privatePanel} aria-label="Private with Dubai-io" data-testid="private-handoff">
      <div className={s.privateHead}>
        <Lock size={16} strokeWidth={2} aria-hidden />
        <div>
          <strong>Private with Dubai-io</strong>
          <p>Nothing from private chats is posted publicly.</p>
        </div>
      </div>
      <div className={s.prepared}>
        <span className={s.preparedIcon}><Car size={18} strokeWidth={2} aria-hidden /></span>
        <div>
          <strong>Prepared for you</strong>
          <p className={s.preparedTitle}>{title}</p>
          <p>{detail}</p>
          <p className={s.estimate}>Estimate · RTA taxi fares, as of Oct 2026 <DemoPill /></p>
        </div>
      </div>
      <Button variant="primary" onClick={onOpenAssistant}>Open private chat</Button>
      <ul className={s.privateList}>
        <li>Plan, refine and get options privately</li>
        <li>Your privacy, always — never posted to the community</li>
        <li>I do not book from public threads</li>
      </ul>
    </aside>
  );
}

function PostDetail({ postId, onClose }: { postId: string; onClose: () => void }) {
  const { setMode, setScreen, setDraft, openThread } = useApp();
  const post = useApi<{ post?: Post }>(`/api/posts/${encodeURIComponent(postId)}`);
  const comments = useApi<{ comments?: FeedComment[] }>(
    `/api/posts/${encodeURIComponent(postId)}/comments?sort=new`,
  );

  const p = post.data?.post;
  const text = p?.text ?? "";

  const continuePrivately = () => {
    const ask = looksLikeTransportAsk(text)
      ? "Prepare a private taxi estimate from DXB Terminal 1 to Dubai Marina around 1am — do not book yet"
      : `Help me privately with this community question: ${(text.split("\n")[0] || text).slice(0, 160)}`;
    setDraft(ask);
    setScreen("assistant");
    setMode("assistant");
    openThread(null);
    onClose();
  };

  return (
    <div className={s.detailOverlay} role="dialog" aria-modal="true" aria-label="Post detail" onClick={onClose}>
      <div className={s.detailShell} onClick={(e) => e.stopPropagation()}>
        <div className={s.detail}>
          <div className={s.detailHead}>
            <div>
              {post.loading ? <p className={s.postBody}>Loading…</p> : null}
              {post.error ? (
                <StateBox title="Post unavailable" body={post.error} onRetry={post.reload} />
              ) : p ? (
                <>
                  <div className={s.postMeta}>
                    <Avatar label={authorEmoji(p.author)} size={32} />
                    <span>{authorName(p.author)}</span>
                    {p.community?.name ? <span>· {p.community.name}</span> : null}
                    {isDemoProvenance(p.provenance) ? <DemoPill /> : null}
                    {p.created_at ? <span>· {formatWhen(p.created_at)}</span> : null}
                  </div>
                  <h2>{(p.text ?? "").split("\n")[0]}</h2>
                  <p className={s.postBody}>{p.text}</p>
                  {mediaSrc(p.image) ? (
                    <img className={s.postImg} src={mediaSrc(p.image)!} alt="" />
                  ) : null}
                </>
              ) : null}
            </div>
            <button type="button" className={s.close} onClick={onClose}>
              <X size={18} strokeWidth={2} aria-hidden />
              Close
            </button>
          </div>

          <div className={s.ioReply}>
            <strong>Dubai-io</strong>
            <p>I do not book from public threads. I can prepare it privately for you.</p>
            <Button variant="primary" onClick={continuePrivately}>Continue privately</Button>
          </div>

          <h3 style={{ fontSize: "var(--fs-md)", margin: "0 0 var(--s-2)" }}>Comments</h3>
          {comments.loading ? <p className={s.postBody}>Loading comments…</p> : null}
          {comments.error ? (
            <StateBox title="Comments unavailable" body={comments.error} onRetry={comments.reload} />
          ) : null}
          {(comments.data?.comments ?? []).length === 0 && !comments.loading && !comments.error ? (
            <p className={s.postBody}>No comments yet.</p>
          ) : null}
          {(comments.data?.comments ?? []).map((c) => (
            <div key={c.id} className={s.comment}>
              <div className={s.commentMeta}>
                <span>{authorName(c.author)}</span>
                {c.created_at ? <span>{formatWhen(c.created_at)}</span> : null}
                {isDemoProvenance(c.provenance) ? <DemoPill /> : null}
                {c.mine ? <span>You</span> : null}
              </div>
              <p className={s.commentText}>{c.text}</p>
            </div>
          ))}
        </div>
        <PrivateHandoff postText={text} onOpenAssistant={continuePrivately} />
      </div>
    </div>
  );
}

function CommunityJoin({ community, onDone }: { community: Community; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  async function toggle() {
    setBusy(true);
    try {
      await apiPost(`/api/communities/${encodeURIComponent(community.id)}/${community.joined ? "leave" : "join"}`, {});
      onDone();
    } catch {
      /* keep UI honest — user can retry */
    } finally {
      setBusy(false);
    }
  }
  return (
    <button
      type="button"
      className={`${s.joinBtn} ${community.joined ? s.joined : ""}`}
      disabled={busy}
      onClick={() => void toggle()}
    >
      {busy ? "…" : community.joined ? "Joined" : "Join"}
    </button>
  );
}

export function CommunityView() {
  const { setMode } = useApp();
  const [tab, setTab] = useState<FeedTab>("foryou");
  const [sort, setSort] = useState<Sort>("new");
  const [selected, setSelected] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const feedPath = `/api/feed?limit=30&sort=${sort}`;
  const feed = useApi<{ posts?: Post[] }>(feedPath);
  const communities = useApi<{ communities?: Community[] }>("/api/communities");

  const posts = useMemo(() => {
    let items = feed.data?.posts ?? [];
    if (tab === "following") items = items.filter((p) => p.community?.joined);
    const q = search.trim().toLowerCase();
    if (q) {
      items = items.filter(
        (p) =>
          (p.text ?? "").toLowerCase().includes(q) ||
          (p.community?.name ?? "").toLowerCase().includes(q) ||
          authorName(p.author).toLowerCase().includes(q),
      );
    }
    return items;
  }, [feed.data, tab, search]);

  const reloadAll = () => {
    feed.reload();
    communities.reload();
  };

  return (
    <div className={s.wrap} data-testid="community-view">
      <div className={s.scroll}>
        <div className={s.layout}>
          <div className={s.feedCol}>
            <header className={s.head}>
              <div className={s.tabs} role="tablist" aria-label="Feed">
                {(
                  [
                    ["foryou", "For you"],
                    ["following", "Following"],
                  ] as const
                ).map(([id, label]) => (
                  <button
                    key={id}
                    type="button"
                    role="tab"
                    aria-selected={tab === id}
                    className={`${s.tab} ${tab === id ? s.tabActive : ""}`}
                    onClick={() => setTab(id)}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <div className={s.headRow}>
                <div className={s.sortRow} role="group" aria-label="Sort">
                  {(
                    [
                      ["new", "New"],
                      ["top", "Top"],
                      ["hot", "Hot"],
                    ] as const
                  ).map(([id, label]) => (
                    <button
                      key={id}
                      type="button"
                      className={`${s.sortChip} ${sort === id ? s.sortChipActive : ""}`}
                      aria-pressed={sort === id}
                      onClick={() => setSort(id)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </header>

            {feed.loading ? <StateBox title="Loading feed" body="Fetching posts from Dubai-io…" /> : null}
            {feed.error ? (
              <StateBox
                title="Feed unavailable"
                body={`${feed.error} Start the API and try again.`}
                onRetry={feed.reload}
              />
            ) : null}
            {!feed.loading && !feed.error && posts.length === 0 ? (
              <StateBox
                title={tab === "following" ? "No posts from joined communities" : "No posts yet"}
                body={
                  tab === "following"
                    ? "Join a community from the list on the right — their posts show here."
                    : "When the backend is seeded, neighbour posts appear here. Join communities to see more."
                }
              />
            ) : null}

            {posts.map((post) => {
              const title = (post.text ?? "").split("\n")[0].slice(0, 120);
              const rest = (post.text ?? "").includes("\n") ? post.text!.slice(post.text!.indexOf("\n") + 1) : "";
              return (
                <button
                  key={post.id}
                  type="button"
                  className={s.post}
                  data-testid="feed-post"
                  onClick={() => setSelected(post.id)}
                >
                  <div className={s.postMeta}>
                    <Avatar label={authorEmoji(post.author)} size={36} />
                    <span>{post.community?.name ?? "Community"}</span>
                    {isDemoProvenance(post.provenance) ? <DemoPill /> : null}
                    {post.created_at ? <span>{formatWhen(post.created_at)}</span> : null}
                  </div>
                  <h3 className={s.postTitle}>{title || "Post"}</h3>
                  {rest ? <p className={s.postBody}>{rest.slice(0, 280)}{rest.length > 280 ? "…" : ""}</p> : null}
                  {mediaSrc(post.image) ? (
                    <img className={s.postImg} src={mediaSrc(post.image)!} alt="" loading="lazy" />
                  ) : null}
                  <div className={s.postFoot}>
                    <span>
                      <ArrowBigUp size={16} strokeWidth={1.75} aria-hidden /> {post.score ?? post.likes ?? 0}
                    </span>
                    <span>
                      <MessageCircle size={16} strokeWidth={1.75} aria-hidden /> {post.comments ?? 0}
                    </span>
                    {post.mine ? <span>Your post</span> : null}
                  </div>
                </button>
              );
            })}
          </div>

          <aside className={s.rail} aria-label="Discover">
            <SearchField
              placeholder="Search communities, posts…"
              value={search}
              onChange={setSearch}
            />
            <section className={s.panel}>
              <h2>Communities for you</h2>
              {communities.loading ? <p className={s.postBody}>Loading…</p> : null}
              {communities.error ? (
                <StateBox title="Communities unavailable" body={communities.error} onRetry={communities.reload} />
              ) : null}
              {(communities.data?.communities ?? []).slice(0, 6).map((c) => (
                <div key={c.id} className={s.commRow}>
                  <Avatar label={c.name} size={40} />
                  <div className={s.commBody}>
                    <div className={s.commName}>
                      {c.name}
                      {isDemoProvenance(c.provenance) ? <> <DemoPill /></> : null}
                    </div>
                    {c.about ? <p className={s.commAbout}>{c.about.slice(0, 100)}{c.about.length > 100 ? "…" : ""}</p> : null}
                    {typeof c.members === "number" ? (
                      <div className={s.commMeta}>{c.members.toLocaleString()} members</div>
                    ) : null}
                  </div>
                  <CommunityJoin community={c} onDone={reloadAll} />
                </div>
              ))}
              {(communities.data?.communities ?? []).length === 0 && !communities.loading && !communities.error ? (
                <p className={s.postBody}>No communities loaded.</p>
              ) : null}
            </section>
            <section className={s.panel}>
              <h2>Ask Dubai-io privately</h2>
              <p className={s.postBody} style={{ marginBottom: 12 }}>
                Switch to Assistant mode above for help — community posts are untrusted text.
              </p>
              <Button variant="secondary" onClick={() => setMode("assistant")}>
                Use Assistant tab
              </Button>
            </section>
          </aside>
        </div>
      </div>
      {selected ? <PostDetail postId={selected} onClose={() => setSelected(null)} /> : null}
    </div>
  );
}
