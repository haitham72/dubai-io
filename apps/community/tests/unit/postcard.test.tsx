import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, test } from "vitest";
import DemoPill from "@/components/DemoPill";
import PostCard from "@/components/PostCard";
import { phonePosts } from "@/lib/feedFixture";

const post = {
  ...phonePosts[0],
  media_url: "/demo/jlt.jpg",
};

describe("PostCard", () => {
  test("renders a photo, title, relative time and icon actions", () => {
    const html = renderToStaticMarkup(<PostCard post={post} />);
    expect(html).toContain("Sara Khalid");
    expect(html).toContain("@sara_k");
    expect(html).toContain("2h");
    expect(html).not.toContain("2026-11-23");
    expect(html).toContain("Which nursery near Cluster D has space for January?");
    expect(html.indexOf("Which nursery")).toBeLessThan(html.indexOf("Demo photo attached"));
    expect(html).toContain("Upvote");
    expect(html).toContain("Downvote");
    expect(html).toContain("Comments");
    expect(html).not.toContain("Like");
  });

  test("shows a Demo data pill on fixture posts", () => {
    const html = renderToStaticMarkup(<PostCard post={phonePosts[0]} />);
    expect(html).toContain("Demo data");
  });

  test("omits the demo pill for a user-supplied post and shows the AI reply", () => {
    const html = renderToStaticMarkup(<PostCard post={{ ...phonePosts[0], provenance: "user_supplied", reply: { name: "Dubai-io", text: "Taxi fare is about AED 110.", estimate: true, source: "RTA taxi fares, as of Oct 2026" } }} />);
    expect(html).not.toContain("Demo data");
    expect(html).toContain(">AI<");
    expect(html).toContain("Estimate");
    expect(html).toContain("RTA taxi fares, as of Oct 2026");
  });
});

describe("DemoPill", () => {
  test("renders default and custom labels", () => {
    expect(renderToStaticMarkup(<DemoPill />)).toContain("Demo data");
    expect(renderToStaticMarkup(<DemoPill label="Demo trigger" />)).toContain("Demo trigger");
  });
});
