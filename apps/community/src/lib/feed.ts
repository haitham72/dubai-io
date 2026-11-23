import type { Lane, Post } from "./types";

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
