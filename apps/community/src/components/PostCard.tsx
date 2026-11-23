import type { Post } from "@/lib/types";
import { isDemo } from "@/lib/feed";
import DemoPill from "./DemoPill";

export default function PostCard({ post }: { post: Post }) {
  const name = post.author.display_name || post.author.handle;
  const reactions = post.reaction_count ?? post.reactions ?? 0;
  const comments = post.comment_count ?? post.comments ?? 0;
  return (
    <article className="post-card" data-testid="post-card">
      <header className="post-head">
        <div className="avatar" aria-hidden="true">{name.slice(0, 1).toUpperCase()}</div>
        <div>
          <div className="author">{name} <span className="handle">@{post.author.handle}</span></div>
          <div className="context">
            {post.group_name ? `in ${post.group_name}` : "Community"}
            {post.pinned ? " · Pinned" : ""}
            {post.as_of ? ` · ${post.as_of.slice(0, 10)}` : ""}
          </div>
        </div>
        {isDemo(post) && <DemoPill />}
      </header>
      <p className="post-text">{post.text}</p>
      {post.media_label && <div className="media" role="img" aria-label={post.media_label}>{post.media_label}</div>}
      {post.why && <p className="why"><span className="why-chip">Why this?</span> {post.why}</p>}
      <div className="actions">
        <button type="button" className="action-box" aria-pressed={!!post.reacted}>Like · {reactions}</button>
        <button type="button" className="action-box">Comment · {comments}</button>
        <button type="button" className="action-box" aria-pressed={!!post.bookmarked}>Save</button>
      </div>
    </article>
  );
}
