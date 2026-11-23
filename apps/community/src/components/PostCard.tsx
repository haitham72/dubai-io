import { ArrowDown, ArrowUp, Link2, MessageCircle, MoreHorizontal } from "lucide-react";
import type { FeedCard } from "@/lib/feedFixture";

export default function PostCard({ post, header = "person" }: { post: FeedCard; header?: "person" | "community" }) {
  const person = header === "person";
  const image = person ? post.author.avatar : post.community.image;
  const name = person ? post.author.display_name : post.community.name;
  const meta = person ? `@${post.author.handle} · ${post.time_label}` : `${post.community.members} · ${post.time_label}`;
  return (
    <article className="v2-card" data-testid="post-card">
      <header className="v2-cardhead">
        <img className="v2-avatar-sm" src={image} alt="" />
        <div>
          <div className="v2-name">{name}</div>
          <div className="v2-meta">{meta}</div>
        </div>
        {post.provenance === "demo_fixture" && <span className="v2-demo">Demo data</span>}
      </header>
      {post.title && <h2 className="v2-title">{post.title}</h2>}
      <p className="v2-body">{post.text}</p>
      {post.media_url && <img className="v2-media" src={post.media_url} alt="Demo photo attached to this post" />}
      <Actions votes={post.votes} comments={post.comments} />
      {post.reply && (
        <div className="v2-reply">
          <header className="v2-cardhead">
            <div className="v2-mark" aria-hidden="true">D</div>
            <div>
              <div className="v2-name">{post.reply.name} <span className="v2-ai">AI</span></div>
            </div>
          </header>
          <p className="v2-body">{post.reply.text}</p>
          <div className="v2-chips">
            {post.reply.estimate && <span className="v2-chip">Estimate</span>}
            {post.reply.source && <span className="v2-chip"><Link2 size={12} aria-hidden="true" />{post.reply.source}</span>}
          </div>
          <Actions votes={post.reply.votes ?? 0} comments={0} commentLabel="Reply" />
        </div>
      )}
    </article>
  );
}

function Actions({ votes, comments, commentLabel = "" }: { votes: number; comments: number; commentLabel?: string }) {
  return (
    <div className="v2-actions">
      <button type="button" aria-label="Upvote"><ArrowUp size={18} aria-hidden="true" /><span className="v2-count">{votes}</span></button>
      <button type="button" aria-label="Downvote"><ArrowDown size={18} aria-hidden="true" /></button>
      <span className="v2-rule" aria-hidden="true" />
      <button type="button" aria-label="Comments"><MessageCircle size={18} aria-hidden="true" /><span className="v2-count">{commentLabel || comments}</span></button>
      <button type="button" className="v2-spacer" aria-label="More"><MoreHorizontal size={18} aria-hidden="true" /></button>
    </div>
  );
}
