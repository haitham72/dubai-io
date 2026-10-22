"use client";

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
import {
  ApiError,
  apiPost,
  authorName,
  type FeedComment,
  type Post,
} from "@/lib/api";
import { useApi } from "@/lib/use-api";

interface Threaded extends FeedComment {
  replies: Threaded[];
}

function threadify(flat: FeedComment[]): Threaded[] {
  const byId = new Map<string, Threaded>();
  for (const comment of flat) byId.set(comment.id, { ...comment, replies: [] });
  const roots: Threaded[] = [];
  for (const node of byId.values()) {
    const parent =
      node.parent_id != null ? byId.get(node.parent_id) : undefined;
    if (parent && parent.id !== node.id) parent.replies.push(node);
    else roots.push(node);
  }
  return roots;
}

function ReplyNode({
  node,
  depth,
  onReply,
}: {
  node: Threaded;
  depth: number;
  onReply: (comment: FeedComment) => void;
}) {
  const [open, setOpen] = useState(depth < 2);
  return (
    <li
      className="rowCard"
      style={depth > 0 ? { marginLeft: Math.min(depth, 3) * 20 } : undefined}
    >
      <div className="rowMeta">
        <span>{authorName(node.author)}</span>
        {node.created_at ? <span>{node.created_at}</span> : null}
        {node.provenance === "demo_fixture" ? <DemoPill /> : null}
        <Provenance value={node.provenance} />
      </div>
      <p style={{ marginTop: 8 }}>{node.text}</p>
      <div className="rowMeta">
        <button type="button" className="chip" onClick={() => onReply(node)}>
          Reply
        </button>
        {node.replies.length > 0 ? (
          <button
            type="button"
            className="chip"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            {open
              ? "Hide replies"
              : `Show ${node.replies.length} repl${node.replies.length === 1 ? "y" : "ies"}`}
          </button>
        ) : null}
      </div>
      {open && node.replies.length > 0 ? (
        <ul className="listRows" style={{ marginTop: 12 }}>
          {node.replies.map((child) => (
            <ReplyNode
              key={child.id}
              node={child}
              depth={depth + 1}
              onReply={onReply}
            />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

export default function PostDetail({ postId }: { postId: string }) {
  const post = useApi<Post>(`/api/posts/${encodeURIComponent(postId)}`);
  const comments = useApi<{ comments?: FeedComment[] }>(
    `/api/posts/${encodeURIComponent(postId)}/comments`,
  );
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<FeedComment | null>(null);
  const [sending, setSending] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function submit(event?: React.FormEvent) {
    event?.preventDefault();
    const text = draft.trim();
    if (!text || sending) return;
    setSending(true);
    setNotice(null);
    try {
      await apiPost(`/api/posts/${encodeURIComponent(postId)}/comments`, {
        text,
        parent_id: replyTo?.id ?? null,
      });
      setDraft("");
      setReplyTo(null);
      setNotice("Posted. Replies from demo personas may follow.");
      comments.reload();
    } catch (err) {
      setNotice(
        err instanceof ApiError
          ? `Could not post (${err.status}): ${err.message}`
          : "Could not post.",
      );
    } finally {
      setSending(false);
    }
  }

  const tree = threadify(comments.data?.comments ?? []);

  return (
    <>
      <div className="appHead">
        <BackLink href="/app/feed" label="Feed" />
        <h1>Post</h1>
        <p>
          Community content is untrusted: questions, answers and disagreements
          from demo personas — not guidance from Dubai-io.{" "}
          {post.data?.provenance === "demo_fixture" ? <DemoPill /> : null}
        </p>
      </div>
      {post.loading ? <LoadingState label="Loading post…" /> : null}
      {post.error ? (
        <ErrorState message={`Post unavailable: ${post.error}`} onRetry={post.reload} />
      ) : null}
      {post.data ? (
        <SectionCard title={authorName(post.data.author)}>
          <p style={{ fontSize: "1.05rem", lineHeight: 1.65 }}>
            {post.data.text}
          </p>
          <div className="rowMeta">
            {post.data.created_at ? <span>{post.data.created_at}</span> : null}
            <Provenance value={post.data.provenance} />
          </div>
        </SectionCard>
      ) : null}
      <SectionCard
        title="Replies"
        action={
          <button type="button" className="chip" onClick={() => comments.reload()}>
            Refresh
          </button>
        }
      >
        {comments.loading ? <LoadingState label="Loading replies…" /> : null}
        {comments.error ? (
          <ErrorState
            message={`Replies unavailable: ${comments.error}`}
            onRetry={comments.reload}
          />
        ) : null}
        {tree.length === 0 && !comments.loading && !comments.error ? (
          <EmptyState title="No replies yet" body="Be the first to reply below." />
        ) : (
          <ul className="listRows">
            {tree.map((node) => (
              <ReplyNode key={node.id} node={node} depth={0} onReply={setReplyTo} />
            ))}
          </ul>
        )}
        {notice ? (
          <p role="status" style={{ color: "var(--muted)" }}>
            {notice}
          </p>
        ) : null}
        <form className="inlineForm" onSubmit={submit}>
          <input
            className="textInput"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={
              replyTo
                ? `Reply to ${authorName(replyTo.author)}…`
                : "Write a reply…"
            }
            maxLength={500}
            aria-label={
              replyTo ? `Reply to ${authorName(replyTo.author)}` : "Write a reply"
            }
          />
          {replyTo ? (
            <button
              type="button"
              className="btnGhost"
              onClick={() => setReplyTo(null)}
            >
              Cancel
            </button>
          ) : null}
          <button
            type="submit"
            className="btnPrimary"
            disabled={sending || !draft.trim()}
          >
            {sending ? "Posting…" : "Reply"}
          </button>
        </form>
      </SectionCard>
    </>
  );
}
