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
  id: "p1", text: "Hello community", author: { handle: "alice_dxb", display_name: "Alice" },
  created_at: "2026-11-24T10:00:00Z", provenance: "user_supplied",
  reaction_count: 2, comment_count: 0,
};

function stubFetch(handler: (url: string, init?: RequestInit) => { status?: number; body?: unknown }) {
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const r = handler(url, init);
    return new Response(JSON.stringify(r.body ?? {}), {
      status: r.status ?? 200, headers: { "content-type": "application/json" },
    });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

async function mount(post: Post, props: Partial<Parameters<typeof RealPostCard>[0]> = {}) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => { root.render(<RealPostCard post={post} {...props} />); });
  return el;
}
const btn = (el: HTMLElement, label: string) =>
  el.querySelector(`button[aria-label="${label}"]`) as HTMLButtonElement | null;

afterEach(() => vi.unstubAllGlobals());

describe("RealPostCard honest states", () => {
  test("like toggles via /reactions and shows the server count", async () => {
    const f = stubFetch(() => ({ body: { reacted: true, count: 3, reactions: 3 } }));
    const el = await mount(basePost);
    await act(async () => { btn(el, "Like")!.click(); });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/posts/p1/reactions");
    expect(btn(el, "Like")!.getAttribute("aria-pressed")).toBe("true");
    expect(el.querySelector(".v2-count")!.textContent).toBe("3");
  });

  test("a failed like reverts the optimistic count and shows the error", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "reaction store down" } }));
    const el = await mount(basePost);
    await act(async () => { btn(el, "Like")!.click(); });
    expect(btn(el, "Like")!.getAttribute("aria-pressed")).toBe("false");
    expect(el.querySelector(".v2-count")!.textContent).toBe("2");
    expect(el.querySelector("[role=alert]")!.textContent).toContain("reaction store down");
  });

  test("comments load failure shows the API error, not an empty thread", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "comments unavailable" } }));
    const el = await mount(basePost);
    await act(async () => { btn(el, "Comments")!.click(); });
    expect(el.querySelector("[data-testid=comment-thread]")).not.toBeNull();
    expect(el.querySelector("[role=alert]")!.textContent).toContain("comments unavailable");
  });

  test("replying to a deleted post surfaces the API's error", async () => {
    stubFetch((url) => url.includes("/comments")
      ? { status: 404, body: { detail: "Post not found or deleted" } }
      : { body: { comments: [] } });
    const el = await mount(basePost);
    await act(async () => { btn(el, "Comments")!.click(); });
    const input = el.querySelector(".v2-replybox input") as HTMLInputElement;
    await act(async () => {
      // React controlled input: set value via native setter
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")!.set!;
      setter.call(input, "still here?");
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    const send = [...el.querySelectorAll<HTMLButtonElement>(".v2-replybox button")].find((b) => b.textContent === "Send")!;
    await act(async () => { send.click(); });
    expect(el.querySelector("[role=alert]")!.textContent).toContain("Post not found or deleted");
  });

  test("own post shows edit/delete; delete hits DELETE and refreshes", async () => {
    const f = stubFetch(() => ({ body: {} }));
    const onChanged = vi.fn();
    const el = await mount({ ...basePost, mine: true }, { onChanged });
    expect(btn(el, "Edit post")).not.toBeNull();
    expect(btn(el, "Delete post")).not.toBeNull();
    await act(async () => { btn(el, "Delete post")!.click(); });
    await act(async () => { btn(el, "Confirm delete")!.click(); });
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
    await act(async () => { followBtn.click(); });
    expect(String(f.mock.calls[0][0])).toContain("/api/community/follows/alice_dxb");
    expect((f.mock.calls[0][1] as RequestInit).method).toBe("POST");
    expect(followBtn.textContent).toBe("Following");
  });

  test("a failed follow reverts and shows the error", async () => {
    stubFetch(() => ({ status: 500, body: { detail: "follow failed" } }));
    const el = await mount(basePost);
    const followBtn = [...el.querySelectorAll("button.v2-follow")][0] as HTMLButtonElement;
    await act(async () => { followBtn.click(); });
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
