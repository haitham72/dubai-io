import type { Lane, Post } from "./types";
import type { DiscoveryItem, DiscoveryResult } from "./api";

export const POST_FLAIRS = [
  "Question",
  "Recommendation",
  "Event",
  "Warning",
  "Housing",
] as const;

export const DUBAI_AREAS = [
  "Dubai Marina",
  "JLT",
  "DIFC",
  "Downtown Dubai",
  "Business Bay",
  "Jumeirah",
  "Al Quoz",
  "Deira",
  "Bur Dubai",
] as const;

export function isDemo(post: { provenance?: string }): boolean {
  return post.provenance === "demo_fixture";
}

/** Extract unique normalized hashtag slugs (lowercase, without `#`) from post.tags and post.text. */
export function extractHashtags(text: string, existingTags?: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  const add = (raw: string) => {
    const clean = raw.trim().replace(/^#+/, "").toLowerCase();
    if (!clean || !/^[a-z0-9_]{2,40}$/.test(clean) || seen.has(clean)) return;
    seen.add(clean);
    out.push(clean);
  };
  for (const t of existingTags ?? []) add(t);
  const re = /(?:^|[\s(])#([a-zA-Z0-9_]{2,40})\b/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text || "")) !== null) add(m[1]);
  return out;
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

export type FeedSort = "hot" | "top" | "new" | "rising" | "controversial";

const postTime = (p: Post): number => {
  const t = Date.parse(p.created_at ?? p.as_of ?? "");
  return Number.isNaN(t) ? 0 : t;
};
const postScore = (p: Post): number => p.score ?? p.reaction_count ?? p.reactions ?? 0;
const postComments = (p: Post): number => p.comment_count ?? p.comments ?? 0;

function hotScore(p: Post): number {
  const s = postScore(p);
  const order = Math.log10(Math.max(1, Math.abs(s)));
  const sign = s > 0 ? 1 : s < 0 ? -1 : 0;
  const sec = postTime(p) / 1000;
  return sign * order + sec / 45000;
}

function risingScore(p: Post): number {
  const ageHours = Math.max(0.5, (Date.now() - postTime(p)) / 3_600_000);
  return (postScore(p) + postComments(p) * 1.5 + 1) / Math.pow(ageHours + 2, 1.4);
}

function controversialScore(p: Post): number {
  const ups = p.upvotes ?? Math.max(0, postScore(p));
  const downs = p.downvotes ?? 0;
  const total = ups + downs + postComments(p);
  if (ups === 0 && downs === 0) return postComments(p);
  const balance = Math.min(ups, downs) / Math.max(1, Math.max(ups, downs));
  return total * (0.5 + balance);
}

/** Sort real feed posts across Hot, Top, New, Rising, Controversial. */
export function sortPosts(posts: Post[], sort: FeedSort): Post[] {
  const copy = [...posts];
  if (sort === "top") {
    copy.sort((a, b) => postScore(b) - postScore(a) || postTime(b) - postTime(a));
  } else if (sort === "hot") {
    copy.sort((a, b) => hotScore(b) - hotScore(a) || postComments(b) - postComments(a));
  } else if (sort === "rising") {
    copy.sort((a, b) => risingScore(b) - risingScore(a) || postTime(b) - postTime(a));
  } else if (sort === "controversial") {
    copy.sort((a, b) => controversialScore(b) - controversialScore(a) || postComments(b) - postComments(a));
  } else {
    copy.sort((a, b) => postTime(b) - postTime(a) || String(b.id).localeCompare(String(a.id)));
  }
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
