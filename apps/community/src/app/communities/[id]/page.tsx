"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import RealPostCard from "@/components/RealPostCard";
import * as api from "@/lib/api";
import type { ModerationEvent } from "@/lib/api";
import { followedHandlesFrom, groupNameMap } from "@/lib/feed";
import { isSignedIn } from "@/lib/session";
import type { Group, Post } from "@/lib/types";

export default function GroupPage() {
  const params = useParams<{ id: string }>();
  const gid = decodeURIComponent(String(params?.id ?? ""));
  const [group, setGroup] = useState<Group | null>(null);
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [queue, setQueue] = useState<ModerationEvent[]>([]);
  const [tab, setTab] = useState<"posts" | "reports">("posts");
  const [state, setState] = useState<"loading" | "live" | "missing" | "signedout">("loading");
  const [notice, setNotice] = useState<string | null>(null);
  const [followed, setFollowed] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [postError, setPostError] = useState<string | null>(null);
  const [modError, setModError] = useState<string | null>(null);

  const isModerator =
    group?.my_role === "owner" || group?.my_role === "moderator";

  const load = useCallback(async () => {
    if (!isSignedIn()) {
      setState("signedout");
      return;
    }
    try {
      const [g, p, f] = await Promise.all([
        api.getGroup(gid),
        api.getGroupPosts(gid),
        api.getFollows().catch(() => []),
      ]);
      setGroup(g);
      setPosts(p);
      setFollowed(followedHandlesFrom(f));
      setState("live");
      if (g.my_role === "owner" || g.my_role === "moderator") {
        api
          .getModerationQueue(g.id)
          .then((evs) => setQueue(evs))
          .catch(() => setQueue([]));
      }
    } catch (e) {
      setState("missing");
      setNotice((e as Error).message || "This community is not visible to you.");
    }
  }, [gid]);

  useEffect(() => {
    void load();
  }, [load]);

  async function toggleJoin() {
    if (!group || busy) return;
    setBusy(true);
    setNotice(null);
    try {
      if (group.is_member) {
        if (group.my_role === "owner") {
          setNotice("The group owner cannot leave their own group.");
          return;
        }
        await api.leaveGroup(group.id);
      } else {
        await api.joinGroup(group.id);
      }
      await load();
    } catch (e) {
      setNotice((e as Error).message || "Could not update membership");
    } finally {
      setBusy(false);
    }
  }

  async function submitPost() {
    if (!draft.trim() || busy) return;
    setBusy(true);
    setPostError(null);
    try {
      await api.createGroupPost(group!.id, draft.trim());
      setDraft("");
      await load();
    } catch (e) {
      setPostError((e as Error).message || "Could not post");
    } finally {
      setBusy(false);
    }
  }

  async function resolveReport(eventId: string, decision: "keep" | "remove" | "restore") {
    if (busy) return;
    setBusy(true);
    setModError(null);
    try {
      const res = await api.resolveModeration(eventId, decision);
      setQueue((prev) =>
        prev.map((ev) =>
          ev.id === eventId
            ? {
                ...ev,
                ...(res.event ?? {}),
                status: res.event?.status ?? res.target_state ?? decision,
                target_state: res.target_state ?? res.event?.target_state ?? decision,
              }
            : ev,
        ),
      );
      if (decision === "remove" || decision === "restore") {
        const refreshed = await api.getGroupPosts(gid).catch(() => null);
        if (refreshed) setPosts(refreshed);
      }
    } catch (e) {
      setModError((e as Error).message || "Could not resolve report");
    } finally {
      setBusy(false);
    }
  }

  if (state === "signedout") {
    return (
      <section>
        <h1>Community</h1>
        <div className="notice" role="status">
          Sign in to see this community. <Link href="/signin">Sign in</Link>
        </div>
      </section>
    );
  }
  if (state === "loading") {
    return (
      <section>
        <h1>Community</h1>
        <p className="empty">Loading…</p>
      </section>
    );
  }
  if (state === "missing" || !group) {
    return (
      <section>
        <h1>Community</h1>
        <div className="error" role="alert">
          {notice ?? "Community not found."} Private communities are hidden from non-members.
        </div>
        <Link
          href="/communities"
          className="action-box"
          style={{ display: "inline-block", maxWidth: 200 }}
        >
          All communities
        </Link>
      </section>
    );
  }

  const names = groupNameMap([group]);
  return (
    <section>
      <p>
        <Link href="/communities">← All communities</Link>
      </p>
      <h1>{group.name}</h1>
      <p className="sub">{group.description}</p>
      <p className="meta">
        {group.member_count ?? 0} members · {group.visibility}
        {group.visibility === "private"
          ? " · Invite only — private communities are hidden from non-members."
          : ""}
      </p>
      {group.provenance === "demo_fixture" && <DemoPillInline />}
      {notice && (
        <div className="notice" role="status">
          {notice}
        </div>
      )}
      <button
        type="button"
        className="action-box"
        style={{ maxWidth: 180 }}
        disabled={busy}
        onClick={toggleJoin}
      >
        {busy
          ? "…"
          : group.is_member
            ? "Leave"
            : group.visibility === "private"
              ? "Request invite"
              : "Join"}
      </button>

      {isModerator && (
        <div className="lanes" role="tablist" aria-label="Community tabs">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "posts"}
            className={tab === "posts" ? "lane-btn active" : "lane-btn"}
            onClick={() => setTab("posts")}
          >
            Posts
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "reports"}
            className={tab === "reports" ? "lane-btn active" : "lane-btn"}
            onClick={() => {
              setTab("reports");
              api
                .getModerationQueue(group.id)
                .then(setQueue)
                .catch((e) => setModError((e as Error).message || "Queue unavailable"));
            }}
          >
            Moderator Reports ({queue.filter((q) => q.status === "flagged").length})
          </button>
        </div>
      )}

      {tab === "posts" && (
        <>
          {group.is_member && (
            <div className="user-box" style={{ marginTop: 16 }}>
              <label htmlFor="gp-text">Post to {group.name}</label>
              <textarea
                id="gp-text"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="What's happening?"
                maxLength={2000}
              />
              {postError && (
                <div className="error" role="alert" style={{ margin: "8px 0" }}>
                  {postError}
                </div>
              )}
              <button
                type="button"
                className="primary"
                disabled={busy || !draft.trim()}
                onClick={submitPost}
              >
                {busy ? "Posting…" : "Post"}
              </button>
            </div>
          )}

          <h2 style={{ marginTop: 24 }}>Posts</h2>
          <div className="feed-v2">
            {(posts ?? []).length === 0 && (
              <p className="v2-empty">No posts in this community yet.</p>
            )}
            {(posts ?? []).map((p) => (
              <RealPostCard
                key={p.id}
                post={p}
                groupName={names[p.group_id ?? ""] ?? group.name}
                following={followed.some(
                  (h) => h.toLowerCase() === p.author.handle.toLowerCase(),
                )}
                onChanged={() => void load()}
              />
            ))}
          </div>
        </>
      )}

      {tab === "reports" && isModerator && (
        <section data-testid="moderation-queue" style={{ marginTop: 16 }}>
          <h2>Moderator Reports</h2>
          {modError && (
            <div className="error" role="alert">
              {modError}
            </div>
          )}
          {queue.length === 0 ? (
            <p className="empty">No moderation reports in this community.</p>
          ) : (
            queue.map((ev) => (
              <article key={ev.id} className="card" data-testid="moderation-item">
                <div className="meta">
                  <strong>
                    {ev.target_type} · {ev.target_id}
                  </strong>{" "}
                  · status: {ev.target_state ?? ev.status}
                  {ev.is_minor && " · Priority"}
                </div>
                <p>
                  {ev.label ? `[${ev.label}] ` : ""}
                  {ev.evidence || "Flagged for human review"}
                </p>
                <div className="actions">
                  <button
                    type="button"
                    className="action-box"
                    disabled={busy}
                    onClick={() => resolveReport(ev.id, "keep")}
                  >
                    Keep
                  </button>
                  <button
                    type="button"
                    className="action-box"
                    disabled={busy}
                    onClick={() => resolveReport(ev.id, "remove")}
                  >
                    Remove
                  </button>
                  <button
                    type="button"
                    className="action-box"
                    disabled={busy}
                    onClick={() => resolveReport(ev.id, "restore")}
                  >
                    Restore
                  </button>
                </div>
              </article>
            ))
          )}
        </section>
      )}
    </section>
  );
}

function DemoPillInline() {
  return (
    <p className="meta">
      <span className="demo-pill">Demo data</span>
    </p>
  );
}
