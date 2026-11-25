import type { Lane, Post } from "./types";
import type { DiscoveryItem, DiscoveryResult } from "./api";

export function isDemo(post: { provenance?: string }): boolean {
  return post.provenance === "demo_fixture";
}

export function filterPostsByLane(
  posts: Post[],
  lane: Lane,
  ctx: { followedHandles?: string[]; joinedGroupIds?: string[] } = {},
): Post[] {
  const followed = new Set((ctx.followedHandles ?? []).map((h) => h.toLowerCase()));
  const joined = new Set(ctx.joinedGroupIds ?? []);
  if (lane === "following") {
    return posts.filter((p) => p.mine || followed.has(p.author.handle.toLowerCase()));
  }
  if (lane === "communities") {
    return posts.filter((p) => !!p.group_id && joined.has(p.group_id));
  }
  return [...posts];
}

export type FeedSort = "new" | "top" | "hot";

const postTime = (p: Post): number => {
  const t = Date.parse(p.created_at ?? p.as_of ?? "");
  return Number.isNaN(t) ? 0 : t;
};
const postReactions = (p: Post): number => p.reaction_count ?? p.reactions ?? 0;
const postComments = (p: Post): number => p.comment_count ?? p.comments ?? 0;

/** Sort real feed posts. "new" keeps the API's created_at-desc order; ties fall back to id for stability. */
export function sortPosts(posts: Post[], sort: FeedSort): Post[] {
  const copy = [...posts];
  if (sort === "top") copy.sort((a, b) => postReactions(b) - postReactions(a) || postTime(b) - postTime(a));
  else if (sort === "hot") copy.sort((a, b) => postComments(b) - postComments(a) || postReactions(b) - postReactions(a));
  else copy.sort((a, b) => postTime(b) - postTime(a) || String(b.id).localeCompare(String(a.id)));
  return copy;
}

/** Compact relative time for real posts ("2h", "3d", "5w"); empty string when unknown. */
export function timeLabel(iso: string | undefined): string {
  if (!iso) return "";
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return "";
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return "now";
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  const d = Math.floor(h / 24);
  if (d < 7) return `${d}d`;
  const w = Math.floor(d / 7);
  if (w < 5) return `${w}w`;
  return new Date(t).toISOString().slice(0, 10);
}

export function followedHandlesFrom(entries: { handle: string | null }[]): string[] {
  return entries.map((e) => e.handle).filter((h): h is string => !!h);
}

export function joinedGroupIdsFrom(groups: { id: string; is_member?: boolean }[]): string[] {
  return groups.filter((g) => g.is_member).map((g) => g.id);
}

export function groupNameMap(groups: { id: string; name: string }[]): Record<string, string> {
  return Object.fromEntries(groups.map((g) => [g.id, g.name]));
}

/** Discovery "For you" items split into post refs (need a full fetch) and group cards. */
export function splitDiscovery(items: DiscoveryItem[]): { postIds: string[]; groups: DiscoveryItem[] } {
  const postIds: string[] = [];
  const groups: DiscoveryItem[] = [];
  for (const it of items) {
    if (it.kind === "post" || it.post_id) {
      const id = it.post_id ?? it.id;
      if (id && !postIds.includes(id)) postIds.push(id);
    } else if (it.kind === "group" || it.group_id || it.name) {
      groups.push(it);
    }
  }
  return { postIds, groups };
}

/** Honest state for the feed: real data, demo fallback, or a hard offline notice. */
export type FeedState = "loading" | "live" | "empty" | "demo";
export function feedState(input: {
  loading: boolean; signedIn: boolean; apiFailed: boolean; postCount: number;
}): FeedState {
  if (input.loading) return "loading";
  if (!input.signedIn || input.apiFailed) return "demo";
  return input.postCount > 0 ? "live" : "empty";
}

export function discoveryIsColdStart(result: DiscoveryResult | null): boolean {
  return !!result && (result.source === "local_cm_profile" && !!result.reason);
}
