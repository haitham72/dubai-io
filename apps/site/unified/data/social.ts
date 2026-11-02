/** Loose API shapes for feed, chats and memory (optional fields for graceful degradation). */

export interface Author {
  name?: string;
  handle?: string;
  emoji?: string;
  avatar?: string | null;
}

export interface Post {
  id: string;
  community?: { id?: string; name?: string; handle?: string; joined?: boolean };
  author?: Author | string;
  text?: string;
  image?: string | null;
  created_at?: string;
  provenance?: string;
  comments?: number;
  likes?: number;
  score?: number;
  mine?: boolean;
}

export interface FeedComment {
  id: string;
  author?: Author | string;
  text?: string;
  created_at?: string;
  provenance?: string;
  parent_id?: string | null;
  mine?: boolean;
}

export interface Community {
  id: string;
  name: string;
  handle?: string;
  about?: string;
  members?: number;
  joined?: boolean;
  provenance?: string;
}

export interface ChatThread {
  id: string;
  title?: string;
  kind?: string;
  unread?: number;
  last?: string;
  last_author?: string;
  at?: string;
}

export interface ChatMessage {
  id?: string;
  author?: string;
  text?: string;
  at?: string;
  created_at?: string;
  provenance?: string;
  mine?: boolean;
  avatar?: string | null;
}

export interface ToldFact {
  key?: string;
  value?: string;
}

export function isDemoProvenance(p?: string): boolean {
  return p === "demo_fixture" || p === "ai_demo";
}

export function authorName(author?: Author | string | null): string {
  if (!author) return "Someone";
  if (typeof author === "string") return author;
  return author.name ?? author.handle ?? "Someone";
}

export function authorEmoji(author?: Author | string | null): string {
  if (!author || typeof author === "string") return "🙂";
  return author.emoji ?? "🙂";
}

/** Map API paths like `media/food.jpg` to static copies under `/images/media/`. */
export function mediaSrc(path?: string | null): string | null {
  if (!path) return null;
  const name = path.replace(/^\/?media\//, "");
  return `/images/media/${name}`;
}

export function formatWhen(iso?: string): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return iso;
  const diff = Date.now() - t;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 48) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 14) return `${days}d ago`;
  return new Date(t).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export const TOLD_LABELS: Record<string, string> = {
  area: "Area",
  household: "Household",
  services: "Services",
  clothing_size: "Clothing size",
  language: "Language",
};
