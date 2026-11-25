"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import RealPostCard from "@/components/RealPostCard";
import * as api from "@/lib/api";
import type { Group, Post } from "@/lib/types";
import { followedHandlesFrom, groupNameMap } from "@/lib/feed";
import { isSignedIn } from "@/lib/session";

export default function GroupPage() {
  const params = useParams<{ id: string }>();
  const gid = decodeURIComponent(String(params?.id ?? ""));
  const [group, setGroup] = useState<Group | null>(null);
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [state, setState] = useState<"loading" | "live" | "missing" | "signedout">("loading");
  const [notice, setNotice] = useState<string | null>(null);
  const [followed, setFollowed] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState("");
  const [postError, setPostError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn()) { setState("signedout"); return; }
    try {
      const [g, p, f] = await Promise.all([api.getGroup(gid), api.getGroupPosts(gid), api.getFollows().catch(() => [])]);
      setGroup(g); setPosts(p); setFollowed(followedHandlesFrom(f)); setState("live");
    } catch (e) {
      const status = (e as { status?: number })?.status ?? 0;
      setState(status === 404 ? "missing" : "missing");
      setNotice((e as Error).message || "This community is not visible to you.");
    }
  }, [gid]);

  useEffect(() => { void load(); }, [load]);

  async function toggleJoin() {
    if (!group || busy) return;
    setBusy(true); setNotice(null);
    try {
      if (group.is_member) {
        if (group.my_role === "owner") { setNotice("The group owner cannot leave their own group."); return; }
        await api.leaveGroup(group.id);
      } else {
        await api.joinGroup(group.id);
      }
      await load();
    } catch (e) {
      setNotice((e as Error).message || "Could not update membership");
    } finally { setBusy(false); }
  }

  async function submitPost() {
    if (!draft.trim() || busy) return;
    setBusy(true); setPostError(null);
    try {
      await api.createGroupPost(group!.id, draft.trim());
      setDraft("");
      await load();
    } catch (e) {
      setPostError((e as Error).message || "Could not post");
    } finally { setBusy(false); }
  }

  if (state === "signedout") {
    return (
      <section>
        <h1>Community</h1>
        <div className="notice" role="status">Sign in to see this community. <Link href="/signin">Sign in</Link></div>
      </section>
    );
  }
  if (state === "loading") return <section><h1>Community</h1><p className="empty">Loading…</p></section>;
  if (state === "missing" || !group) {
    return (
      <section>
        <h1>Community</h1>
        <div className="error" role="alert">{notice ?? "Community not found."} Private communities are hidden from non-members.</div>
        <Link href="/communities" className="action-box" style={{ display: "inline-block", maxWidth: 200 }}>All communities</Link>
      </section>
    );
  }

  const names = groupNameMap([group]);
  return (
    <section>
      <p><Link href="/communities">← All communities</Link></p>
      <h1>{group.name}</h1>
      <p className="sub">{group.description}</p>
      <p className="meta">
        {group.member_count ?? 0} members · {group.visibility}
        {group.visibility === "private" ? " · Invite only — private communities are hidden from non-members." : ""}
      </p>
      {group.provenance === "demo_fixture" && <DemoPillInline />}
      {notice && <div className="notice" role="status">{notice}</div>}
      <button type="button" className="action-box" style={{ maxWidth: 180 }} disabled={busy} onClick={toggleJoin}>
        {busy ? "…" : group.is_member ? "Leave" : group.visibility === "private" ? "Request invite" : "Join"}
      </button>

      {group.is_member && (
        <div className="user-box" style={{ marginTop: 16 }}>
          <label htmlFor="gp-text">Post to {group.name}</label>
          <textarea id="gp-text" value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="What's happening?" maxLength={2000} />
          {postError && <div className="error" role="alert" style={{ margin: "8px 0" }}>{postError}</div>}
          <button type="button" className="primary" disabled={busy || !draft.trim()} onClick={submitPost}>
            {busy ? "Posting…" : "Post"}
          </button>
        </div>
      )}

      <h2 style={{ marginTop: 24 }}>Posts</h2>
      <div className="feed-v2">
        {(posts ?? []).length === 0 && <p className="v2-empty">No posts in this community yet.</p>}
        {(posts ?? []).map((p) => (
          <RealPostCard key={p.id} post={p} groupName={names[p.group_id ?? ""] ?? group.name}
            following={followed.some((h) => h.toLowerCase() === p.author.handle.toLowerCase())}
            onChanged={() => void load()} />
        ))}
      </div>
    </section>
  );
}

function DemoPillInline() {
  return <p className="meta"><span className="demo-pill">Demo data</span></p>;
}
