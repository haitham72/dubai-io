import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import DemoPill from "@/components/DemoPill";
import PostCard from "@/components/PostCard";
import type { Post } from "@/lib/types";

const demoPost: Post = {
  id: "1", text: "Hello neighbours", author: { handle: "sara_m", display_name: "Sara M." },
  group_name: "Weekend Walks", provenance: "demo_fixture", as_of: "2026-11-23T00:00:00Z",
  reactions: 3, comments: 2, why: "You follow Sara.",
};

describe("PostCard", () => {
  test("renders author, context, text, media order and actions", () => {
    const html = renderToStaticMarkup(<PostCard post={{ ...demoPost, media_label: "Sunrise (demo image)" }} />);
    expect(html).toContain("Sara M.");
    expect(html).toContain("@sara_m");
    expect(html).toContain("in Weekend Walks");
    expect(html).toContain("Hello neighbours");
    expect(html.indexOf("Hello neighbours")).toBeLessThan(html.indexOf("Sunrise (demo image)"));
    expect(html).toContain("Like");
    expect(html).toContain("Comment");
    expect(html).toContain("Save");
  });

  test("shows Demo data pill and subordinate Why this? chip for demo posts", () => {
    const html = renderToStaticMarkup(<PostCard post={demoPost} />);
    expect(html).toContain("Demo data");
    expect(html).toContain("Why this?");
    expect(html).toContain("You follow Sara.");
  });

  test("omits demo pill for user-supplied posts", () => {
    const html = renderToStaticMarkup(<PostCard post={{ ...demoPost, provenance: "user_supplied" }} />);
    expect(html).not.toContain("Demo data");
  });
});

describe("DemoPill", () => {
  test("renders default and custom labels", () => {
    expect(renderToStaticMarkup(<DemoPill />)).toContain("Demo data");
    expect(renderToStaticMarkup(<DemoPill label="Demo trigger" />)).toContain("Demo trigger");
  });
});
