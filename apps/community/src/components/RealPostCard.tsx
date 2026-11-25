"use client";

import Link from "next/link";
import { useState } from "react";
import { Bookmark, Heart, MessageCircle, Pencil, Trash2 } from "lucide-react";
import * as api from "@/lib/api";
import type { Post } from "@/lib/types";
import { timeLabel } from "@/lib/feed";
import type { Comment as ApiComment } from "@/lib/api";

function authorName(post: Post): string {
  return post.author.display_name || post.author.handle;
}

function initial(post: Post): string {
  return (authorName(post) || "?").trim().charAt(0).toUpperCase();
}

export default function RealPostCard({
  post,
  groupName,
  following = false,
  onFollowChange,
  onChanged,
  why,
}: {
  post: Post;
  groupName?: string;
  following?: boolean;
  onFollowChange?: (handle: string, following: boolean) => void;
  onChanged?: () => void;
  why?: string;
}) {
  const [reacted, setReacted] = useState(!!post.reacted);
  const [reactions, setReactions] = useState(post.reaction_count ?? post.reactions ?? 0);
  const [bookmarked, setBookmarked] = useState(!!post.bookmarked);
  const [commentCount, setCommentCount] = useState(post.comment_count ?? post.comments ?? 0);
  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<ApiComment[] | null>(null);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyDraft, setReplyDraft] = useState("");
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(post.text);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [followState, setFollowState] = useState(following);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = post.author.handle;
  const canFollow = !post.mine && !!handle && handle !== "you";
  const time = timeLabel(post.created_at ?? post.as_of);

  async function toggleLike() {
    if (busy) return;
    setBusy(true); setError(null);
    const wasReacted = reacted;
    const wasCount = reactions;
    setReacted(!wasReacted);
    setReactions(wasCount + (wasReacted ? -1 : 1));
    try {
      const r = await api.toggleReaction(post.id, "like");
      setReacted(!!r.reacted);
      setReactions(r.count ?? r.reactions ?? reactions);
    } catch (e) {
      setReacted(wasReacted); setReactions(wasCount);
      setError((e as Error).message || "Like failed");
    } finally { setBusy(false); }
  }

  async function toggleBookmark() {
    if (busy) return;
    setBusy(true); setError(null);
    const was = bookmarked;
    setBookmarked(!was);
    try {
      if (was) await api.removeBookmark(post.id); else await api.addBookmark(post.id);
    } catch (e) {
      setBookmarked(was);
      setError((e as Error).message || "Bookmark failed");
    } finally { setBusy(false); }
  }

  async function toggleFollow() {
    if (busy || !canFollow) return;
    setBusy(true); setError(null);
    const was = followState;
    setFollowState(!was);
    onFollowChange?.(handle, !was);
    try {
      if (was) await api.unfollow(handle); else await api.follow(handle);
    } catch (e) {
      setFollowState(was);
      onFollowChange?.(handle, was);
      setError((e as Error).message || "Follow failed");
    } finally { setBusy(false); }
  }

  async function loadComments() {
    setOpen(true);
    if (comments !== null) return;
    try {
      setComments(await api.getComments(post.id));
    } catch (e) {
      setComments([]);
      setError((e as Error).message || "Could not load replies");
    }
  }

  async function submitComment(parentId: string | null, text: string, clear: () => void) {
    if (!text.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      const c = await api.addComment(post.id, text.trim(), parentId);
      setComments((prev) => [...(prev ?? []), c]);
      setCommentCount((n) => n + 1);
      clear();
      setReplyTo(null);
    } catch (e) {
      setError((e as Error).message || "Reply failed");
    } finally { setBusy(false); }
  }

  async function saveEdit() {
    if (!editText.trim() || busy) return;
    setBusy(true); setError(null);
    try {
      await api.updatePost(post.id, editText.trim());
      setEditing(false);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Edit failed");
    } finally { setBusy(false); }
  }

  async function removePost() {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      await api.deletePost(post.id);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Delete failed");
      setConfirmDelete(false);
    } finally { setBusy(false); }
  }

  const topLevel = (comments ?? []).filter((c) => !c.parent_id);
  const repliesFor = (id: string) => (comments ?? []).filter((c) => c.parent_id === id);

  return (
    <article className="v2-card" data-testid="post-card" data-post-id={post.id}>
      <header className="v2-cardhead">
        <span className="v2-mark" aria-hidden="true">{initial(post)}</span>
        <div>
          <div className="v2-name">
            <Link href={`/u/${encodeURIComponent(handle)}`}>{authorName(post)}</Link>
            {canFollow && (
              <button type="button" className="v2-follow" aria-pressed={followState} onClick={toggleFollow} disabled={busy}>
                {followState ? "Following" : "Follow"}
              </button>
            )}
          </div>
          <div className="v2-meta">
            @{handle}{time ? ` · ${time}` : ""}{groupName ? ` · ${groupName}` : ""}
            {post.provenance === "demo_fixture" && <> · <span className="v2-demo">Demo data</span></>}
          </div>
        </div>
      </header>
      {why && <div className="v2-chips"><span className="v2-why">{why}</span></div>}
      {editing ? (
        <div>
          <textarea className="v2-editbox" value={editText} onChange={(e) => setEditText(e.target.value)} maxLength={2000} aria-label="Edit post" />
          <div className="v2-actions">
            <button type="button" className="v2-pill" onClick={saveEdit} disabled={busy || !editText.trim()}>Save</button>
            <button type="button" className="v2-pill" onClick={() => { setEditing(false); setEditText(post.text); }}>Cancel</button>
          </div>
        </div>
      ) : (
        <p className="v2-body">{post.text}</p>
      )}
      <div className="v2-actions">
        <button type="button" aria-label="Like" aria-pressed={reacted} onClick={toggleLike} disabled={busy}>
          <Heart size={18} aria-hidden="true" fill={reacted ? "currentColor" : "none"} /><span className="v2-count">{reactions}</span>
        </button>
        <button type="button" aria-label="Bookmark" aria-pressed={bookmarked} onClick={toggleBookmark} disabled={busy}>
          <Bookmark size={18} aria-hidden="true" fill={bookmarked ? "currentColor" : "none"} />
        </button>
        <span className="v2-rule" aria-hidden="true" />
        <button type="button" aria-label="Comments" aria-expanded={open} onClick={() => (open ? setOpen(false) : loadComments())}>
          <MessageCircle size={18} aria-hidden="true" /><span className="v2-count">{commentCount}</span>
        </button>
        {post.mine && !editing && (
          <>
            <button type="button" aria-label="Edit post" onClick={() => setEditing(true)}><Pencil size={16} aria-hidden="true" /></button>
            {confirmDelete ? (
              <button type="button" aria-label="Confirm delete" onClick={removePost} disabled={busy}>Delete?</button>
            ) : (
              <button type="button" aria-label="Delete post" onClick={() => setConfirmDelete(true)}><Trash2 size={16} aria-hidden="true" /></button>
            )}
          </>
        )}
      </div>
      {error && <p className="v2-error" role="alert">{error}</p>}
      {open && (
        <div className="v2-thread" data-testid="comment-thread">
          {(comments ?? []).length === 0 && <p className="v2-meta">No replies yet.</p>}
          {topLevel.map((c) => (
            <div key={c.id} className="v2-comment">
              <CommentRow c={c} />
              {repliesFor(c.id).map((r) => (
                <div key={r.id} className="v2-comment v2-comment-reply"><CommentRow c={r} /></div>
              ))}
              {replyTo === c.id ? (
                <ReplyBox value={replyDraft} onChange={setReplyDraft} onSubmit={() => submitComment(c.id, replyDraft, () => setReplyDraft(""))} onCancel={() => setReplyTo(null)} busy={busy} />
              ) : (
                <button type="button" className="v2-replybtn" onClick={() => { setReplyTo(c.id); setReplyDraft(""); }}>Reply</button>
              )}
            </div>
          ))}
          <ReplyBox value={draft} onChange={setDraft} onSubmit={() => submitComment(null, draft, () => setDraft(""))} busy={busy} placeholder="Write a reply…" />
        </div>
      )}
    </article>
  );
}

function CommentRow({ c }: { c: ApiComment }) {
  return (
    <div className="v2-commentrow">
      <span className="v2-mark v2-mark-sm" aria-hidden="true">{(c.author.display_name || c.author.handle || "?").charAt(0).toUpperCase()}</span>
      <div>
        <div className="v2-name">@{c.author.handle}</div>
        <p className="v2-body">{c.text}</p>
      </div>
    </div>
  );
}

function ReplyBox({ value, onChange, onSubmit, onCancel, busy, placeholder = "Reply…" }: {
  value: string; onChange: (v: string) => void; onSubmit: () => void; onCancel?: () => void; busy: boolean; placeholder?: string;
}) {
  return (
    <div className="v2-replybox">
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} aria-label={placeholder} maxLength={2000}
        onKeyDown={(e) => { if (e.key === "Enter") onSubmit(); }} />
      <button type="button" className="v2-pill" onClick={onSubmit} disabled={busy || !value.trim()}>Send</button>
      {onCancel && <button type="button" className="v2-pill" onClick={onCancel}>Cancel</button>}
    </div>
  );
}
