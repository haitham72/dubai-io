import { createRoot } from "react-dom/client";
import { act } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import RealPostCard from "@/components/RealPostCard";
import type { Post } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const basePost: Post = {
  id: "p1",
  text: "Hello community #dubaimarina #padel",
  flair: "Recommendation",
  author: { handle: "alice_dxb", display_name: "Alice" },
  created_at: "2026-11-24T10:00:00Z",
  provenance: "user_supplied",
  score: 2,
  reaction_count: 2,
  comment_count: 0,
};

function stubFetch(handler: (url: string, init?: RequestInit) => { status?: number; body?: unknown }) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const r = handler(url, init);
    return new Response(JSON.stringify(r.body ?? {}), {
      status: r.status ?? 200,
      headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

async function mount(post: Post, props: Partial<Parameters<typeof RealPostCard>[0]> = {}) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => {
    root.render(<RealPostCard post={post} {...props} />);
  });
  return el;
}

const btn = (el: HTMLElement, label: string) =>
  el.querySelector(`button[aria-label="${label}"]`) as HTMLButtonElement | null;

afterEach(() => {
  vi.unstubAllGlobals();
  document.body.innerHTML = "";
});

describe("RealPostCard Facebook/Reddit parity + honest states", () => {
  test("upvote and downvote call /vote and update score from server", async () => {
    const f = stubFetch(() => ({ body: { score: 3, my_vote: 1 } }));
    const el = await mount(basePost);
    await act(async () => {
      btn(el, "Upvote")!.click();
    });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/posts/p1/vote");
    expect(JSON.parse(String((f.mock.calls[0][1] as RequestInit).body))).toEqual({ value: 1 });
    expect(btn(el, "Upvote")!.getAttribute("aria-pressed")).toBe("true");
    expect(el.querySelector("[data-testid=vote-score]")!.textContent).toBe("3");
  });

  test("a failed vote reverts the optimistic score and shows the error", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "vote store down" } }));
    const el = await mount(basePost);
    await act(async () => {
      btn(el, "Downvote")!.click();
    });
    expect(btn(el, "Downvote")!.getAttribute("aria-pressed")).toBe("false");
    expect(el.querySelector("[data-testid=vote-score]")!.textContent).toBe("2");
    expect(el.querySelector("[role=alert]")!.textContent).toContain("vote store down");
  });

  test("renders optional flair pill and clickable #hashtag pills linking to /t/[tag]", async () => {
    const el = await mount(basePost);
    expect(el.querySelector("[data-testid=post-flair]")!.textContent).toBe("Recommendation");
    const links = [...el.querySelectorAll<HTMLAnchorElement>("[data-testid=post-tags] a")];
    expect(links.map((a) => a.textContent)).toEqual(["#dubaimarina", "#padel"]);
    expect(links.map((a) => a.getAttribute("href"))).toEqual(["/t/dubaimarina", "/t/padel"]);
  });

  test("repost quote box posts via /repost and shows Posted; failed repost shows error", async () => {
    const f = stubFetch(() => ({ body: { post: { id: "rp1" } } }));
    const onChanged = vi.fn();
    const el = await mount(basePost, { onChanged });
    await act(async () => {
      btn(el, "Repost")!.click();
    });
    expect(el.querySelector("[data-testid=repost-box]")).not.toBeNull();
    const ta = el.querySelector("[data-testid=repost-box] textarea") as HTMLTextAreaElement;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value")!.set!;
      setter.call(ta, "Joining at 7pm!");
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const postBtn = [...el.querySelectorAll<HTMLButtonElement>("[data-testid=repost-box] button")].find(
      (b) => b.textContent === "Post repost",
    )!;
    await act(async () => {
      postBtn.click();
    });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/posts/p1/repost");
    expect(el.querySelector("[role=status]")!.textContent).toBe("Posted");
    expect(onChanged).toHaveBeenCalled();

    // Failed repost never shows Posted
    stubFetch(() => ({ status: 403, body: { detail: "Cannot repost private group post" } }));
    const el2 = await mount(basePost);
    await act(async () => {
      btn(el2, "Repost")!.click();
    });
    const postBtn2 = [...el2.querySelectorAll<HTMLButtonElement>("[data-testid=repost-box] button")].find(
      (b) => b.textContent === "Post repost",
    )!;
    await act(async () => {
      postBtn2.click();
    });
    expect(el2.textContent).not.toContain("Posted");
    expect(el2.querySelector("[role=alert]")!.textContent).toContain("Cannot repost private group post");
  });

  test("renders quoted post preview when repost_of_id or repost_of is set", async () => {
    const el = await mount({
      ...basePost,
      repost_of_id: "orig-1",
      repost_of: {
        id: "orig-1",
        text: "Original Marina update",
        author: { handle: "omar_k" },
        flair: "Event",
      },
    });
    const quoted = el.querySelector("[data-testid=quoted-post]")!;
    expect(quoted.textContent).toContain("@omar_k");
    expect(quoted.textContent).toContain("Original Marina update");
  });

  test("overflow menu supports Report post, Mute author, and Block author", async () => {
    const f = stubFetch(() => ({ body: {} }));
    const onChanged = vi.fn();
    const el = await mount(basePost, { onChanged });
    await act(async () => {
      btn(el, "More actions")!.click();
    });
    const items = [...el.querySelectorAll<HTMLButtonElement>("[data-testid=post-menu] button")];
    expect(items.map((i) => i.textContent)).toContain("Report post");
    expect(items.map((i) => i.textContent)).toContain("Mute author");
    expect(items.map((i) => i.textContent)).toContain("Block author");

    await act(async () => {
      items.find((i) => i.textContent === "Block author")!.click();
    });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/blocks/alice_dxb");
    expect(onChanged).toHaveBeenCalled();

    // Open menu again and submit Report
    await act(async () => {
      btn(el, "More actions")!.click();
    });
    const reportMenuBtn = [...el.querySelectorAll<HTMLButtonElement>("[data-testid=post-menu] button")].find(
      (i) => i.textContent === "Report post",
    )!;
    await act(async () => {
      reportMenuBtn.click();
    });
    const submitReport = [...el.querySelectorAll<HTMLButtonElement>("[data-testid=report-box] button")].find(
      (b) => b.textContent === "Submit report",
    )!;
    await act(async () => {
      submitReport.click();
    });
    expect(String(f.mock.calls[1][0])).toContain("/api/community/reports");
  });

  test("collapsible nested comment branches toggle [ - ] / [ + ] and vote on comments", async () => {
    const f = stubFetch((url) =>
      url.includes("/comments/c1/vote")
        ? { body: { score: 4, my_vote: 1 } }
        : {
            body: {
              comments: [
                { id: "c1", post_id: "p1", owner: "u2", parent_id: null, text: "Top comment", author: { handle: "bob" }, score: 3 },
                { id: "c2", post_id: "p1", owner: "u3", parent_id: "c1", text: "Nested reply", author: { handle: "sara" } },
              ],
            },
          },
    );
    const el = await mount(basePost);
    await act(async () => {
      btn(el, "Comments")!.click();
    });
    expect(el.textContent).toContain("Nested reply");
    await act(async () => {
      btn(el, "Upvote comment")!.click();
    });
    expect(String(f.mock.calls[1][0])).toContain("/api/community/comments/c1/vote");

    await act(async () => {
      btn(el, "Collapse thread")!.click();
    });
    expect(el.textContent).not.toContain("Nested reply");
    expect(btn(el, "Expand thread")!.textContent).toBe("[ + ]");
  });

  test("comments load failure shows the API error, not an empty thread", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "comments unavailable" } }));
    const el = await mount(basePost);
    await act(async () => {
      btn(el, "Comments")!.click();
    });
    expect(el.querySelector("[data-testid=comment-thread]")).not.toBeNull();
    expect(el.querySelector("[role=alert]")!.textContent).toContain("comments unavailable");
  });

  test("replying to a deleted post surfaces the API's error", async () => {
    stubFetch((url) =>
      url.includes("/comments")
        ? { status: 404, body: { detail: "Post not found or deleted" } }
        : { body: { comments: [] } },
    );
    const el = await mount(basePost);
    await act(async () => {
      btn(el, "Comments")!.click();
    });
    const input = el.querySelector(".v2-replybox input") as HTMLInputElement;
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
      setter.call(input, "still here?");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const send = [...el.querySelectorAll<HTMLButtonElement>(".v2-replybox button")].find(
      (b) => b.textContent === "Send",
    )!;
    await act(async () => {
      send.click();
    });
    expect(el.querySelector("[role=alert]")!.textContent).toContain("Post not found or deleted");
  });

  test("own post shows edit/delete; delete hits DELETE and refreshes", async () => {
    const f = stubFetch(() => ({ body: {} }));
    const onChanged = vi.fn();
    const el = await mount({ ...basePost, mine: true }, { onChanged });
    expect(btn(el, "Edit post")).not.toBeNull();
    expect(btn(el, "Delete post")).not.toBeNull();
    await act(async () => {
      btn(el, "Delete post")!.click();
    });
    await act(async () => {
      btn(el, "Confirm delete")!.click();
    });
    const del = f.mock.calls.find((c) => (c[1] as RequestInit).method === "DELETE");
    expect(del).toBeTruthy();
    expect(String(del![0])).toContain("/api/community/posts/p1");
    expect(onChanged).toHaveBeenCalled();
  });

  test("follow button calls /follows/{handle} and flips state", async () => {
    const f = stubFetch(() => ({}));
    const el = await mount(basePost);
    const followBtn = [...el.querySelectorAll("button.v2-follow")][0] as HTMLButtonElement;
    expect(followBtn.textContent).toBe("Follow");
    await act(async () => {
      followBtn.click();
    });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/follows/alice_dxb");
    expect((f.mock.calls[0][1] as RequestInit).method).toBe("POST");
    expect(followBtn.textContent).toBe("Following");
  });

  test("a failed follow reverts and shows the error", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "follow failed" } }));
    const el = await mount(basePost);
    const followBtn = [...el.querySelectorAll("button.v2-follow")][0] as HTMLButtonElement;
    await act(async () => {
      followBtn.click();
    });
    expect(followBtn.textContent).toBe("Follow");
    expect(el.querySelector("[role=alert]")!.textContent).toContain("follow failed");
  });

  test("Why-this chip renders only when the API supplied one", async () => {
    const el = await mount(basePost, { why: "Because you follow Alice" });
    expect(el.querySelector(".v2-why")!.textContent).toBe("Because you follow Alice");
    const el2 = await mount(basePost);
    expect(el2.querySelector(".v2-why")).toBeNull();
  });
});
