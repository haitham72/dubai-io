import { afterEach, describe, expect, test, vi } from "vitest";
import * as api from "@/lib/api";
import { setSessionToken } from "@/lib/session";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  setSessionToken(null);
});

type FetchMock = ReturnType<typeof vi.fn>;

function stubFetch(status = 200, body: unknown = {}) {
  const fn = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
    new Response(JSON.stringify(body), {
      status,
      headers: { "content-type": "application/json" },
    }),
  ) as FetchMock;
  vi.stubGlobal("fetch", fn);
  return fn;
}

const calls = (f: FetchMock): [string, RequestInit][] =>
  f.mock.calls.map((c) => [String(c[0]), (c[1] ?? {}) as RequestInit]);
const lastCall = (f: FetchMock) => {
  const all = calls(f);
  return { url: all[all.length - 1][0], init: all[all.length - 1][1] };
};

describe("resolveApiBase LAN + localhost behavior", () => {
  test("rewrites localhost API base to browser LAN hostname when accessed over Wi-Fi", () => {
    expect(api.resolveApiBase(undefined, "10.5.3.228")).toBe("http://10.5.3.228:8060");
    expect(api.resolveApiBase("http://localhost:8060", "192.168.1.44")).toBe(
      "http://192.168.1.44:8060",
    );
    expect(api.resolveApiBase("http://127.0.0.1:8060", "10.5.3.228")).toBe(
      "http://10.5.3.228:8060",
    );
  });

  test("keeps localhost in SSR, localhost, and test environments", () => {
    expect(api.resolveApiBase(undefined, "localhost")).toBe("http://localhost:8060");
    expect(api.resolveApiBase(undefined, "127.0.0.1")).toBe("http://localhost:8060");
    expect(api.resolveApiBase("http://127.0.0.1:54321", "127.0.0.1")).toBe(
      "http://127.0.0.1:54321",
    );
    expect(api.resolveApiBase("https://api.dubai-io.test", "10.5.3.228")).toBe(
      "https://api.dubai-io.test",
    );
  });
});

describe("api client: requests hit the real /api/community surface", () => {
  test("getFeed unwraps posts, passes sort/tag, and sends the session header", async () => {
    setSessionToken("tok-1");
    const f = stubFetch(200, { posts: [{ id: "p1", text: "hi", author: { handle: "a" } }] });
    const posts = await api.getFeed(10, "hot", "#DubaiMarina");
    expect(posts).toHaveLength(1);
    const { url, init } = lastCall(f);
    expect(url).toContain("/api/community/feed?limit=10");
    expect(url).toContain("sort=hot");
    expect(url).toContain("tag=dubaimarina");
    expect((init.headers as Record<string, string>)["X-App-Session"]).toBe("tok-1");
  });

  test("createPost posts text, flair, and tags to /api/community/posts", async () => {
    const f = stubFetch(200, { post: { id: "p2" } });
    await api.createPost("hello", "g1");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({ text: "hello", group_id: "g1" });

    await api.createPost("padel tonight #padel", null, { flair: "Event", tags: ["padel"] });
    const { url, init } = lastCall(f);
    expect(url).toContain("/api/community/posts");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({
      text: "padel tonight #padel",
      flair: "Event",
      tags: ["padel"],
    });
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

  test("votePost, voteComment, getTrendingTags, and repostPost hit expected routes", async () => {
    const f = stubFetch(200, { score: 5, my_vote: 1, tags: [{ tag: "padel", count: 4 }], post: { id: "r1" } });
    const vp = await api.votePost("p1", 1);
    expect(vp.score).toBe(5);
    expect(lastCall(f).url).toContain("/api/community/posts/p1/vote");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({ value: 1 });

    await api.voteComment("c1", -1);
    expect(lastCall(f).url).toContain("/api/community/comments/c1/vote");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({ value: -1 });

    const tags = await api.getTrendingTags(8);
    expect(tags[0].tag).toBe("padel");
    expect(lastCall(f).url).toContain("/api/community/tags/trending?limit=8");

    const rp = await api.repostPost("p1", "great point", "g1");
    expect(rp.id).toBe("r1");
    expect(lastCall(f).url).toContain("/api/community/posts/p1/repost");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({
      text: "great point",
      group_id: "g1",
    });
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

  test("block, mute, safety, report, and moderation routes", async () => {
    const f = stubFetch(200, {
      blocked: [{ handle: "spam_bot" }],
      mutes: [{ kind: "tag", target: "crypto" }],
      events: [{ id: "ev1", target_type: "post", target_id: "p1", status: "flagged" }],
    });
    await api.blockUser("spam_bot");
    expect(lastCall(f).init.method).toBe("POST");
    expect(lastCall(f).url).toContain("/api/community/blocks/spam_bot");

    await api.unblockUser("spam_bot");
    expect(lastCall(f).init.method).toBe("DELETE");

    await api.muteTarget("tag", "crypto");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({ kind: "tag", target: "crypto" });

    await api.unmuteTarget("tag", "crypto");
    expect(lastCall(f).init.method).toBe("DELETE");
    expect(lastCall(f).url).toContain("/api/community/mutes?kind=tag&target=crypto");

    const safety = await api.getSafety();
    expect(safety.blocked).toHaveLength(1);
    expect(safety.mutes).toHaveLength(1);

    await api.reportTarget("post", "p1", "Spam", "Repeated link");
    expect(lastCall(f).url).toContain("/api/community/reports");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({
      target_type: "post",
      target_id: "p1",
      reason: "Spam",
      detail: "Repeated link",
    });

    const queue = await api.getModerationQueue("g1");
    expect(queue).toHaveLength(1);
    expect(lastCall(f).url).toContain("/api/community/moderation/queue?group_id=g1");

    await api.resolveModeration("ev1", "remove");
    expect(lastCall(f).url).toContain("/api/community/moderation/ev1/resolve");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({ decision: "remove" });
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

  test("discovery with context, search, and inbox endpoints", async () => {
    const f = stubFetch(200, { items: [], notifications: [], unread_count: 2 });
    const d = await api.getDiscovery(5, {
      area_coarse: "DIFC",
      user_state: "walking",
      device_class: "mobile_ios",
    });
    expect(d.items).toEqual([]);
    expect(lastCall(f).url).toContain("/api/community/discovery?limit=5");
    expect(lastCall(f).url).toContain("area_coarse=DIFC");
    expect(lastCall(f).url).toContain("user_state=walking");

    await api.searchCommunity("walks");
    expect(lastCall(f).url).toContain("/api/community/search?q=walks");
    const n = await api.getNotifications();
    expect(n.unread_count).toBe(2);
    expect(lastCall(f).url).toContain("/api/community/inbox");
    await api.markNotificationRead("n1");
    await api.markAllNotificationsRead();
    expect(lastCall(f).url).toContain("/api/community/notifications/read-all");
  });

  test("split memory consent, lowerCommunityMemory, and forgetMemory", async () => {
    const f = stubFetch(200, {
      read_enabled: false,
      remember_saved_discussions: false,
      remember_public_posts: false,
      allow_interest_export: false,
      default_off: true,
    });
    const c = await api.getMemoryConsent();
    expect(c.default_off).toBe(true);
    await api.setMemoryConsent({
      read_enabled: true,
      remember_saved_discussions: true,
      remember_public_posts: false,
      allow_interest_export: false,
    });
    expect(lastCall(f).init.method).toBe("POST");
    expect(JSON.parse(String(lastCall(f).init.body))).toEqual({
      read_enabled: true,
      remember_saved_discussions: true,
      remember_public_posts: false,
      allow_interest_export: false,
    });
    await api.lowerCommunityMemory();
    expect(lastCall(f).url).toContain("/api/community/memory/lower");
    await api.forgetMemory();
    expect(lastCall(f).url).toContain("/api/community/memory/forget");
  });

  test("context heartbeat, events, and D19/D19b usage profile routes", async () => {
    const f = stubFetch(200, {
      context: { area_coarse: "Dubai Marina", user_state: "driving" },
      context_aware_enabled: true,
      buckets: [{ topic_key: "padel", weight: 0.82 }],
    });
    const ctx = await api.sendContextHeartbeat({
      area_coarse: "Dubai Marina",
      user_state: "driving",
    });
    expect(ctx.user_state).toBe("driving");
    expect(lastCall(f).url).toContain("/api/community/context/heartbeat");

    await api.getCurrentContext();
    expect(lastCall(f).url).toContain("/api/community/context/current");

    await api.logInteractionEvent({ event_type: "upvote", post_id: "p1" });
    expect(lastCall(f).url).toContain("/api/community/events");

    const up = await api.getUsageProfile(true);
    expect(up.buckets).toHaveLength(1);
    expect(lastCall(f).url).toContain("/api/community/usage/profile?include_lowered=true");

    await api.lowerUsageTopic("padel");
    expect(lastCall(f).url).toContain("/api/community/usage/lower");
    await api.restoreUsageTopic("padel");
    expect(lastCall(f).url).toContain("/api/community/usage/restore");
    await api.recallUsageTopic("padel", "padel");
    expect(lastCall(f).url).toContain("/api/community/usage/recall");
    await api.setUsageSettings(false);
    expect(lastCall(f).url).toContain("/api/community/usage/settings");
    expect(lastCall(f).init.method).toBe("PUT");
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
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );
    await expect(api.getFeed()).rejects.toMatchObject({ status: 0 });
  });
});

describe("getApiBase: LAN Wi-Fi host vs localhost fallback", () => {
  test("returns localhost fallback on localhost, 127.0.0.1, or unset hostname", () => {
    vi.stubGlobal("location", { hostname: "localhost", protocol: "http:" });
    expect(api.getApiBase()).toBe("http://localhost:8060");

    vi.stubGlobal("location", { hostname: "127.0.0.1", protocol: "http:" });
    expect(api.getApiBase()).toBe("http://localhost:8060");

    vi.stubGlobal("location", { hostname: "", protocol: "http:" });
    expect(api.getApiBase()).toBe("http://localhost:8060");
  });

  test("derives LAN API URL on non-loopback host and uses it dynamically in request()", async () => {
    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "http:" });
    expect(api.getApiBase()).toBe("http://192.168.1.50:8060");

    const f = stubFetch(200, { posts: [] });
    await api.getFeed(5);
    expect(lastCall(f).url).toBe("http://192.168.1.50:8060/api/community/feed?limit=5");

    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "https:" });
    expect(api.getApiBase()).toBe("https://192.168.1.50:8060");
  });

  test("prefers NEXT_PUBLIC_CM_API env var and strips trailing slashes", () => {
    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "http:" });
    vi.stubEnv("NEXT_PUBLIC_CM_API", " https://community.example.test/// ");
    expect(api.getApiBase()).toBe("https://community.example.test");
  });

  test("rewrites loopback NEXT_PUBLIC_CM_API to LAN host while preserving port and protocol", () => {
    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "http:" });
    vi.stubEnv("NEXT_PUBLIC_CM_API", "http://localhost:8060");
    expect(api.getApiBase()).toBe("http://192.168.1.50:8060");

    vi.stubEnv("NEXT_PUBLIC_CM_API", "http://127.0.0.1:8060/");
    expect(api.getApiBase()).toBe("http://192.168.1.50:8060");

    vi.stubGlobal("location", { hostname: "192.168.1.50", protocol: "https:" });
    vi.stubEnv("NEXT_PUBLIC_CM_API", "http://localhost:8060");
    expect(api.getApiBase()).toBe("https://192.168.1.50:8060");

    vi.stubGlobal("location", { hostname: "localhost", protocol: "http:" });
    expect(api.getApiBase()).toBe("http://localhost:8060");
  });
});
