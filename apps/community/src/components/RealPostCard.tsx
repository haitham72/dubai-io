"use client";

import Link from "next/link";
import { useState } from "react";
import {
  Bookmark,
  MessageCircle,
  MoreHorizontal,
  Pencil,
  Repeat2,
  Trash2,
} from "lucide-react";
import * as api from "@/lib/api";
import type { Comment as ApiComment } from "@/lib/api";
import { extractHashtags, timeLabel } from "@/lib/feed";
import type { Post } from "@/lib/types";

const REPORT_REASONS = [
  "Spam",
  "Harassment",
  "Misinformation",
  "Safety concern",
  "Other",
] as const;

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
  onInteract,
  why,
}: {
  post: Post;
  groupName?: string;
  following?: boolean;
  onFollowChange?: (handle: string, following: boolean) => void;
  onChanged?: () => void;
  onInteract?: (eventType: string, post: Post) => void;
  why?: string;
}) {
  const initialScore = post.score ?? post.reaction_count ?? post.reactions ?? 0;
  const initialVote = post.my_vote ?? (post.reacted ? 1 : 0);

  const [myVote, setMyVote] = useState<number>(initialVote);
  const [score, setScore] = useState<number>(initialScore);
  const [bookmarked, setBookmarked] = useState(!!post.bookmarked);
  const [repostCount, setRepostCount] = useState(post.repost_count ?? 0);
  const [commentCount, setCommentCount] = useState(post.comment_count ?? post.comments ?? 0);

  const [open, setOpen] = useState(false);
  const [comments, setComments] = useState<ApiComment[] | null>(null);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const [replyDraft, setReplyDraft] = useState("");

  const [repostOpen, setRepostOpen] = useState(false);
  const [quoteText, setQuoteText] = useState("");
  const [repostStatus, setRepostStatus] = useState<string | null>(null);

  const [menuOpen, setMenuOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);
  const [reportReason, setReportReason] = useState<string>(REPORT_REASONS[0]);
  const [reportDetail, setReportDetail] = useState("");
  const [safetyStatus, setSafetyStatus] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(post.text);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [followState, setFollowState] = useState(following);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = post.author.handle;
  const canFollow = !post.mine && !!handle && handle !== "you";
  const time = timeLabel(post.created_at ?? post.as_of);
  const whyLabel = why ?? post.why_this ?? post.why;
  const tags = extractHashtags(post.text, post.tags);

  async function castVote(target: 1 | -1) {
    if (busy) return;
    setBusy(true);
    setError(null);
    const prevVote = myVote;
    const prevScore = score;
    const nextVote: 1 | -1 | 0 = prevVote === target ? 0 : target;
    setMyVote(nextVote);
    setScore(prevScore + (nextVote - prevVote));
    try {
      const r = await api.votePost(post.id, nextVote);
      setMyVote(r.my_vote ?? nextVote);
      setScore(r.score ?? prevScore + (nextVote - prevVote));
      if (nextVote !== 0) onInteract?.(nextVote === 1 ? "upvote" : "downvote", post);
    } catch (e) {
      setMyVote(prevVote);
      setScore(prevScore);
      setError((e as Error).message || "Vote failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleBookmark() {
    if (busy) return;
    setBusy(true);
    setError(null);
    const was = bookmarked;
    setBookmarked(!was);
    try {
      if (was) await api.removeBookmark(post.id);
      else {
        await api.addBookmark(post.id);
        onInteract?.("save", post);
      }
    } catch (e) {
      setBookmarked(was);
      setError((e as Error).message || "Bookmark failed");
    } finally {
      setBusy(false);
    }
  }

  async function toggleFollow() {
    if (busy || !canFollow) return;
    setBusy(true);
    setError(null);
    const was = followState;
    setFollowState(!was);
    onFollowChange?.(handle, !was);
    try {
      if (was) await api.unfollow(handle);
      else await api.follow(handle);
    } catch (e) {
      setFollowState(was);
      onFollowChange?.(handle, was);
      setError((e as Error).message || "Follow failed");
    } finally {
      setBusy(false);
    }
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
    setBusy(true);
    setError(null);
    try {
      const c = await api.addComment(post.id, text.trim(), parentId);
      setComments((prev) => [...(prev ?? []), c]);
      setCommentCount((n) => n + 1);
      clear();
      setReplyTo(null);
      onInteract?.("reply", post);
    } catch (e) {
      setError((e as Error).message || "Reply failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitRepost() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setRepostStatus(null);
    try {
      await api.repostPost(post.id, quoteText.trim() || undefined, post.group_id ?? undefined);
      setQuoteText("");
      setRepostOpen(false);
      setRepostCount((n) => n + 1);
      setRepostStatus("Posted");
      onInteract?.("repost", post);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Repost failed");
    } finally {
      setBusy(false);
    }
  }

  async function submitReport() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setSafetyStatus(null);
    try {
      await api.reportTarget("post", post.id, reportReason, reportDetail);
      setReportOpen(false);
      setReportDetail("");
      setSafetyStatus("Report submitted for review.");
    } catch (e) {
      setError((e as Error).message || "Report failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleMuteAuthor() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setMenuOpen(false);
    try {
      await api.muteTarget("owner", handle);
      setSafetyStatus(`Muted @${handle}.`);
      onInteract?.("hide", post);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Mute failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleMuteTag(tag: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    setMenuOpen(false);
    try {
      await api.muteTarget("tag", tag);
      setSafetyStatus(`Muted #${tag}.`);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Mute tag failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleBlockAuthor() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setMenuOpen(false);
    try {
      await api.blockUser(handle);
      setSafetyStatus(`Blocked @${handle}.`);
      onInteract?.("hide", post);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Block failed");
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!editText.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.updatePost(post.id, editText.trim());
      setEditing(false);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Edit failed");
    } finally {
      setBusy(false);
    }
  }

  async function removePost() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.deletePost(post.id);
      onChanged?.();
    } catch (e) {
      setError((e as Error).message || "Delete failed");
      setConfirmDelete(false);
    } finally {
      setBusy(false);
    }
  }

  const allComments = comments ?? [];
  const commentIds = new Set(allComments.map((c) => c.id));
  const topLevel = allComments.filter((c) => !c.parent_id || !commentIds.has(c.parent_id));
  const repliesFor = (id: string) => allComments.filter((c) => c.parent_id === id);

  return (
    <article className="v2-card" data-testid="post-card" data-post-id={post.id}>
      <header className="v2-cardhead">
        <span className="v2-mark" aria-hidden="true">
          {initial(post)}
        </span>
        <div>
          <div className="v2-name">
            <Link href={`/u/${encodeURIComponent(handle)}`}>{authorName(post)}</Link>
            {post.flair && (
              <span className="v2-flair" data-testid="post-flair">
                {post.flair}
              </span>
            )}
            {canFollow && (
              <button
                type="button"
                className="v2-follow"
                aria-pressed={followState}
                onClick={toggleFollow}
                disabled={busy}
              >
                {followState ? "Following" : "Follow"}
              </button>
            )}
          </div>
          <div className="v2-meta">
            @{handle}
            {time ? ` · ${time}` : ""}
            {groupName ? ` · ${groupName}` : ""}
            {post.provenance === "demo_fixture" && (
              <>
                {" · "}
                <span className="v2-demo">Demo data</span>
              </>
            )}
          </div>
        </div>
      </header>

      {whyLabel && (
        <div className="v2-chips">
          <span className="v2-why" data-testid="why-chip">
            {whyLabel}
          </span>
        </div>
      )}

      {editing ? (
        <div>
          <textarea
            className="v2-editbox"
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            maxLength={2000}
            aria-label="Edit post"
          />
          <div className="v2-actions">
            <button
              type="button"
              className="v2-pill"
              onClick={saveEdit}
              disabled={busy || !editText.trim()}
            >
              Save
            </button>
            <button
              type="button"
              className="v2-pill"
              onClick={() => {
                setEditing(false);
                setEditText(post.text);
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <p className="v2-body">{post.text}</p>
      )}

      {(post.repost_of_id || post.repost_of) && (
        <div className="v2-quote-box" data-testid="quoted-post">
          {post.repost_of ? (
            <>
              <div className="v2-meta">
                Quoted @{post.repost_of.author.handle}
                {post.repost_of.flair ? ` · ${post.repost_of.flair}` : ""}
              </div>
              <p className="v2-body">{post.repost_of.text}</p>
            </>
          ) : (
            <div className="v2-meta">Reposted from #{post.repost_of_id}</div>
          )}
        </div>
      )}

      {tags.length > 0 && (
        <div className="v2-tags" data-testid="post-tags">
          {tags.map((tag) => (
            <Link
              key={tag}
              href={`/t/${encodeURIComponent(tag)}`}
              className="v2-tag-pill"
            >
              #{tag}
            </Link>
          ))}
        </div>
      )}

      <div className="v2-actions">
        <button
          type="button"
          className="v2-vote-btn"
          aria-label="Upvote"
          aria-pressed={myVote === 1}
          onClick={() => castVote(1)}
          disabled={busy}
        >
          <span aria-hidden="true">▲</span>
          <span className="v2-count" data-testid="vote-score">
            {score}
          </span>
        </button>
        <button
          type="button"
          className="v2-vote-btn"
          aria-label="Downvote"
          aria-pressed={myVote === -1}
          onClick={() => castVote(-1)}
          disabled={busy}
        >
          <span aria-hidden="true">▼</span>
        </button>
        <span className="v2-rule" aria-hidden="true" />
        <button
          type="button"
          aria-label="Comments"
          aria-expanded={open}
          onClick={() => (open ? setOpen(false) : loadComments())}
        >
          <MessageCircle size={18} aria-hidden="true" />
          <span className="v2-count">{commentCount}</span>
        </button>
        <button
          type="button"
          aria-label="Repost"
          aria-expanded={repostOpen}
          onClick={() => {
            setRepostOpen((v) => !v);
            setRepostStatus(null);
          }}
          disabled={busy}
        >
          <Repeat2 size={18} aria-hidden="true" />
          {repostCount > 0 && <span className="v2-count">{repostCount}</span>}
        </button>
        <button
          type="button"
          aria-label="Bookmark"
          aria-pressed={bookmarked}
          onClick={toggleBookmark}
          disabled={busy}
        >
          <Bookmark
            size={18}
            aria-hidden="true"
            fill={bookmarked ? "currentColor" : "none"}
          />
        </button>
        {post.mine && !editing && (
          <>
            <button
              type="button"
              aria-label="Edit post"
              onClick={() => setEditing(true)}
            >
              <Pencil size={16} aria-hidden="true" />
            </button>
            {confirmDelete ? (
              <button
                type="button"
                aria-label="Confirm delete"
                onClick={removePost}
                disabled={busy}
              >
                Delete?
              </button>
            ) : (
              <button
                type="button"
                aria-label="Delete post"
                onClick={() => setConfirmDelete(true)}
              >
                <Trash2 size={16} aria-hidden="true" />
              </button>
            )}
          </>
        )}
        <div className="v2-menu-wrap">
          <button
            type="button"
            aria-label="More actions"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((v) => !v)}
          >
            <MoreHorizontal size={18} aria-hidden="true" />
          </button>
          {menuOpen && (
            <div className="v2-menu" role="menu" data-testid="post-menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  setReportOpen(true);
                }}
              >
                Report post
              </button>
              {!post.mine && (
                <>
                  <button type="button" role="menuitem" onClick={handleMuteAuthor}>
                    Mute author
                  </button>
                  <button type="button" role="menuitem" onClick={handleBlockAuthor}>
                    Block author
                  </button>
                </>
              )}
              {tags.length > 0 && (
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => handleMuteTag(tags[0])}
                >
                  Mute #{tags[0]}
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {repostOpen && (
        <div className="v2-repost-box" data-testid="repost-box">
          <div className="v2-meta">Repost or add a quote to @{handle}&apos;s post</div>
          <textarea
            value={quoteText}
            onChange={(e) => setQuoteText(e.target.value)}
            placeholder="Add a note (optional)…"
            aria-label="Quote commentary"
            maxLength={2000}
          />
          <div className="v2-actions">
            <button
              type="button"
              className="v2-pill"
              onClick={submitRepost}
              disabled={busy}
            >
              {busy ? "Posting…" : "Post repost"}
            </button>
            <button
              type="button"
              className="v2-pill"
              onClick={() => setRepostOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {reportOpen && (
        <div className="v2-report-box" data-testid="report-box">
          <div className="v2-meta">Report post for review</div>
          <select
            aria-label="Report reason"
            value={reportReason}
            onChange={(e) => setReportReason(e.target.value)}
          >
            {REPORT_REASONS.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <input
            type="text"
            aria-label="Report details"
            value={reportDetail}
            onChange={(e) => setReportDetail(e.target.value)}
            placeholder="Optional details…"
            maxLength={500}
          />
          <div className="v2-actions">
            <button
              type="button"
              className="v2-pill"
              onClick={submitReport}
              disabled={busy}
            >
              Submit report
            </button>
            <button
              type="button"
              className="v2-pill"
              onClick={() => setReportOpen(false)}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {repostStatus && (
        <p className="v2-status-ok" role="status">
          {repostStatus}
        </p>
      )}
      {safetyStatus && (
        <p className="v2-status-ok" role="status">
          {safetyStatus}
        </p>
      )}
      {error && (
        <p className="v2-error" role="alert">
          {error}
        </p>
      )}

      {open && (
        <div className="v2-thread" data-testid="comment-thread">
          {allComments.length === 0 && <p className="v2-meta">No replies yet.</p>}
          {topLevel.map((c) => (
            <CommentBranch
              key={c.id}
              comment={c}
              repliesFor={repliesFor}
              replyTo={replyTo}
              setReplyTo={setReplyTo}
              replyDraft={replyDraft}
              setReplyDraft={setReplyDraft}
              onSubmitReply={(parentId, text, clear) =>
                submitComment(parentId, text, clear)
              }
              busy={busy}
              depth={0}
            />
          ))}
          <ReplyBox
            value={draft}
            onChange={setDraft}
            onSubmit={() => submitComment(null, draft, () => setDraft(""))}
            busy={busy}
            placeholder="Write a reply…"
          />
        </div>
      )}
    </article>
  );
}

function CommentBranch({
  comment,
  repliesFor,
  replyTo,
  setReplyTo,
  replyDraft,
  setReplyDraft,
  onSubmitReply,
  busy,
  depth,
}: {
  comment: ApiComment;
  repliesFor: (id: string) => ApiComment[];
  replyTo: string | null;
  setReplyTo: (id: string | null) => void;
  replyDraft: string;
  setReplyDraft: (v: string) => void;
  onSubmitReply: (parentId: string | null, text: string, clear: () => void) => void;
  busy: boolean;
  depth: number;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [vote, setVote] = useState<number>(comment.my_vote ?? 0);
  const [score, setScore] = useState<number>(comment.score ?? 0);
  const [voteErr, setVoteErr] = useState<string | null>(null);
  const children = repliesFor(comment.id);

  async function voteOnComment(target: 1 | -1) {
    const prevVote = vote;
    const prevScore = score;
    const nextVote: 1 | -1 | 0 = prevVote === target ? 0 : target;
    setVote(nextVote);
    setScore(prevScore + (nextVote - prevVote));
    setVoteErr(null);
    try {
      const r = await api.voteComment(comment.id, nextVote);
      setVote(r.my_vote ?? nextVote);
      setScore(r.score ?? prevScore + (nextVote - prevVote));
    } catch (e) {
      setVote(prevVote);
      setScore(prevScore);
      setVoteErr((e as Error).message || "Vote failed");
    }
  }

  return (
    <div
      className={depth > 0 ? "v2-comment v2-comment-reply" : "v2-comment"}
      data-testid="comment-branch"
    >
      <div className="v2-commentrow">
        <button
          type="button"
          className="v2-collapse-btn"
          aria-expanded={!collapsed}
          aria-label={collapsed ? "Expand thread" : "Collapse thread"}
          onClick={() => setCollapsed((v) => !v)}
        >
          {collapsed ? "[ + ]" : "[ - ]"}
        </button>
        <span className="v2-mark v2-mark-sm" aria-hidden="true">
          {(comment.author.display_name || comment.author.handle || "?")
            .charAt(0)
            .toUpperCase()}
        </span>
        <div style={{ flex: 1 }}>
          <div className="v2-name">@{comment.author.handle}</div>
          {collapsed ? (
            <p className="v2-meta">
              Branch collapsed ({children.length + 1}{" "}
              {children.length === 0 ? "comment" : "comments"})
            </p>
          ) : (
            <>
              <p className="v2-body">{comment.text}</p>
              <div className="v2-actions">
                <button
                  type="button"
                  className="v2-vote-btn"
                  aria-label="Upvote comment"
                  aria-pressed={vote === 1}
                  onClick={() => voteOnComment(1)}
                >
                  ▲ <span className="v2-count">{score}</span>
                </button>
                <button
                  type="button"
                  className="v2-vote-btn"
                  aria-label="Downvote comment"
                  aria-pressed={vote === -1}
                  onClick={() => voteOnComment(-1)}
                >
                  ▼
                </button>
                <button
                  type="button"
                  className="v2-replybtn"
                  onClick={() => {
                    setReplyTo(comment.id);
                    setReplyDraft("");
                  }}
                >
                  Reply
                </button>
              </div>
              {voteErr && (
                <p className="v2-error" role="alert">
                  {voteErr}
                </p>
              )}
            </>
          )}
        </div>
      </div>

      {!collapsed && replyTo === comment.id && (
        <ReplyBox
          value={replyDraft}
          onChange={setReplyDraft}
          onSubmit={() =>
            onSubmitReply(comment.id, replyDraft, () => setReplyDraft(""))
          }
          onCancel={() => setReplyTo(null)}
          busy={busy}
        />
      )}

      {!collapsed &&
        children.map((child) => (
          <CommentBranch
            key={child.id}
            comment={child}
            repliesFor={repliesFor}
            replyTo={replyTo}
            setReplyTo={setReplyTo}
            replyDraft={replyDraft}
            setReplyDraft={setReplyDraft}
            onSubmitReply={onSubmitReply}
            busy={busy}
            depth={depth + 1}
          />
        ))}
    </div>
  );
}

function ReplyBox({
  value,
  onChange,
  onSubmit,
  onCancel,
  busy,
  placeholder = "Reply…",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel?: () => void;
  busy: boolean;
  placeholder?: string;
}) {
  return (
    <div className="v2-replybox">
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        aria-label={placeholder}
        maxLength={2000}
        onKeyDown={(e) => {
          if (e.key === "Enter") onSubmit();
        }}
      />
      <button
        type="button"
        className="v2-pill"
        onClick={onSubmit}
        disabled={busy || !value.trim()}
      >
        Send
      </button>
      {onCancel && (
        <button type="button" className="v2-pill" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  );
}
