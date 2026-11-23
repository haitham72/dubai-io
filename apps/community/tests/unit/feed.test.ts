import { describe, expect, test } from "vitest";
import { filterPostsByLane, isDemo } from "@/lib/feed";
import type { Post } from "@/lib/types";

const posts: Post[] = [
  { id: "a", text: "followed", author: { handle: "sara_m" }, provenance: "demo_fixture" },
  { id: "b", text: "group", author: { handle: "omar_k" }, group_id: "g1", provenance: "user_supplied" },
  { id: "c", text: "other group", author: { handle: "layla_a" }, group_id: "g2" },
  { id: "d", text: "mine", author: { handle: "you" }, mine: true },
];
const ctx = { followedHandles: ["sara_m"], joinedGroupIds: ["g1"] };

describe("filterPostsByLane", () => {
  test("following keeps followed authors and own posts only", () => {
    expect(filterPostsByLane(posts, "following", ctx).map((p) => p.id)).toEqual(["a", "d"]);
  });
  test("communities keeps joined-group posts only", () => {
    expect(filterPostsByLane(posts, "communities", ctx).map((p) => p.id)).toEqual(["b"]);
  });
  test("discover keeps everything and does not mutate input", () => {
    const out = filterPostsByLane(posts, "discover", ctx);
    expect(out.map((p) => p.id)).toEqual(["a", "b", "c", "d"]);
    expect(out).not.toBe(posts);
  });
  test("empty input stays empty in every lane", () => {
    expect(filterPostsByLane([], "following", ctx)).toEqual([]);
    expect(filterPostsByLane([], "discover", ctx)).toEqual([]);
  });
});

describe("isDemo", () => {
  test("only demo_fixture provenance is demo", () => {
    expect(isDemo({ provenance: "demo_fixture" })).toBe(true);
    expect(isDemo({ provenance: "user_supplied" })).toBe(false);
    expect(isDemo({})).toBe(false);
  });
});
