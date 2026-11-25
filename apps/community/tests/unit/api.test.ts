import { afterEach, describe, expect, test, vi } from "vitest";
import * as api from "@/lib/api";
import { setSessionToken } from "@/lib/session";

afterEach(() => {
  vi.unstubAllGlobals();
  setSessionToken(null);
});

type FetchMock = ReturnType<typeof vi.fn>;

function stubFetch(status = 200, body: unknown = {}) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => new Response(JSON.stringify(body), {
    status, headers: { "content-type": "application/json" },
  })) as FetchMock;
  vi.stubGlobal("fetch", fn);
  return fn;
}

const calls = (f: FetchMock): [string, RequestInit][] =>
  f.mock.calls.map((c) => [String(c[0]), (c[1] ?? {}) as RequestInit]);
const lastCall = (f: FetchMock) => {
  const all = calls(f);
  return { url: all[all.length - 1][0], init: all[all.length - 1][1] };
};

describe("api client: requests hit the real /api/community surface", () => {
  test("getFeed unwraps posts and sends the session header", async () => {
    setSessionToken("tok-1");
    const f = stubFetch(200, { posts: [{ id: "p1", text: "hi", author: { handle: "a" } }] });
    const posts = await api.getFeed(10);
    expect(posts).toHaveLength(1);
    const { url, init } = lastCall(f);
    expect(url).toContain("/api/community/feed?limit=10");
    expect((init.headers as Record<string, string>)["X-App-Session"]).toBe("tok-1");
  });

  test("createPost posts text to /api/community/posts", async () => {
    const f = stubFetch(200, { post: { id: "p2" } });
    await api.createPost("hello", "g1");
    const { url, init } = lastCall(f);
    expect(url).toContain("/api/community/posts");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ text: "hello", group_id: "g1" });
  });

  test("updatePost and deletePost use PUT/DELETE on the post id", async () => {
    const f = stubFetch(200, { post: { id: "p3" } });
    await api.updatePost("p3", "edited");
    await api.deletePost("p3");
    const seq = calls(f).map(([url, init]) => [url, init.method ?? "GET"]);
    expect(seq[0][0]).toContain("/api/community/posts/p3");
    expect(seq[0][1]).toBe("PUT");
    expect(seq[1][1]).toBe("DELETE");
  });

  test("comments list and create with parent_id for threads", async () => {
    const f = stubFetch(200, { comments: [{ id: "c1", parent_id: null }] });
    await api.getComments("p1");
    expect(lastCall(f).url).toContain("/api/community/posts/p1/comments");
    const f2 = stubFetch(200, { comment: { id: "c2", parent_id: "c1" } });
    await api.addComment("p1", "reply", "c1");
    const { init } = lastCall(f2);
    expect(JSON.parse(String(init.body))).toEqual({ text: "reply", parent_id: "c1" });
  });

  test("toggleReaction posts a kind and returns the server count", async () => {
    const f = stubFetch(200, { post_id: "p1", kind: "like", reacted: true, count: 3 });
    const r = await api.toggleReaction("p1", "like");
    expect(r.count).toBe(3);
    const { url, init } = lastCall(f);
    expect(url).toContain("/api/community/posts/p1/reactions");
    expect(JSON.parse(String(init.body))).toEqual({ kind: "like" });
  });

  test("bookmark add/remove hit the bookmarks route", async () => {
    const f = stubFetch(200, {});
    await api.addBookmark("p1");
    await api.removeBookmark("p1");
    const methods = calls(f).map(([, init]) => init.method ?? "GET");
    expect(methods).toEqual(["POST", "DELETE"]);
    expect(calls(f)[0][0]).toContain("/api/community/posts/p1/bookmarks");
  });

  test("follows use /api/community/follows/{handle}", async () => {
    const f = stubFetch(200, { follows: [{ handle: "bob_dxb" }] });
    const follows = await api.getFollows();
    expect(follows[0].handle).toBe("bob_dxb");
    await api.follow("bob_dxb");
    await api.unfollow("bob_dxb");
    const seq = calls(f).slice(1).map(([url, init]) => [init.method ?? "GET", url]);
    expect(seq[0]).toEqual(["POST", expect.stringContaining("/api/community/follows/bob_dxb")]);
    expect(seq[1]).toEqual(["DELETE", expect.stringContaining("/api/community/follows/bob_dxb")]);
  });

  test("profiles: mine GET/PUT and public GET by handle", async () => {
    const f = stubFetch(200, { profile: { handle: "alice_dxb" } });
    await api.getMyProfile();
    await api.getProfile("alice_dxb");
    await api.upsertProfile({ handle: "alice_dxb", age_band: "18+" });
    const urls = calls(f).map(([url]) => url);
    expect(urls[0]).toContain("/api/community/profiles/me");
    expect(urls[1]).toContain("/api/community/profiles/alice_dxb");
    expect(urls[2]).toContain("/api/community/profiles/me");
    expect(calls(f)[2][1].method).toBe("PUT");
  });

  test("groups: list, detail, create, join, leave, group posts", async () => {
    const f = stubFetch(200, { groups: [{ id: "g1" }] });
    await api.getGroups();
    await api.getGroup("g1");
    await api.createGroup({ name: "Writers", visibility: "public" });
    await api.joinGroup("g1");
    await api.leaveGroup("g1");
    await api.getGroupPosts("g1");
    await api.createGroupPost("g1", "hi group");
    const seq = calls(f).map(([url, init]) => [url, init.method ?? "GET"]);
    expect(seq.map((s) => s[1])).toEqual(["GET", "GET", "POST", "POST", "POST", "GET", "POST"]);
    expect(seq[1][0]).toContain("/api/community/groups/g1");
    expect(seq[4][0]).toContain("/api/community/groups/g1/leave");
    expect(seq[5][0]).toContain("/api/community/groups/g1/posts");
  });

  test("discovery, search and inbox endpoints", async () => {
    const f = stubFetch(200, { items: [], notifications: [], unread_count: 2 });
    const d = await api.getDiscovery(5);
    expect(d.items).toEqual([]);
    expect(lastCall(f).url).toContain("/api/community/discovery?limit=5");
    await api.searchCommunity("walks");
    expect(lastCall(f).url).toContain("/api/community/search?q=walks");
    const n = await api.getNotifications();
    expect(n.unread_count).toBe(2);
    expect(lastCall(f).url).toContain("/api/community/inbox");
    await api.markNotificationRead("n1");
    await api.markAllNotificationsRead();
    expect(lastCall(f).url).toContain("/api/community/notifications/read-all");
  });

  test("memory consent read/write and forget", async () => {
    const f = stubFetch(200, { read_enabled: false, write_enabled: false, allow_interest_export: false, default_off: true });
    const c = await api.getMemoryConsent();
    expect(c.default_off).toBe(true);
    await api.setMemoryConsent({ read_enabled: true, write_enabled: false, allow_interest_export: false });
    expect(lastCall(f).init.method).toBe("POST");
    await api.forgetMemory();
    expect(lastCall(f).url).toContain("/api/community/memory/forget");
  });
});

describe("api client: honest errors", () => {
  test("non-2xx surfaces the API detail and status", async () => {
    stubFetch(403, { detail: "Community is adults-only (18+)." });
    try {
      await api.getFeed();
      expect.unreachable();
    } catch (e) {
      expect(e).toBeInstanceOf(api.ApiError);
      expect((e as api.ApiError).status).toBe(403);
      expect((e as Error).message).toContain("18+");
    }
  });

  test("network failure is an ApiError with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("ECONNREFUSED"); }));
    await expect(api.getFeed()).rejects.toMatchObject({ status: 0 });
  });
});
