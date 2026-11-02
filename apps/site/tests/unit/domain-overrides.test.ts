import { describe, expect, test } from "vitest";
import { applyDomainOverrides } from "../../unified/data/domain-overrides";
import type { TaskThread } from "../../unified/data/tasks";

const base = (partial: Partial<TaskThread> & Pick<TaskThread, "id" | "domain">): TaskThread => ({
  title: "t",
  status: "",
  lane: "on_list",
  preview: "",
  at: "",
  unread: false,
  demo: false,
  category: null,
  ...partial,
});

describe("applyDomainOverrides", () => {
  test("moves a thread into another domain without changing others", () => {
    const threads = [
      base({ id: "a", domain: "household" }),
      base({ id: "b", domain: "lifestyle" }),
    ];
    const next = applyDomainOverrides(threads, { a: "travel" });
    expect(next.map((t) => [t.id, t.domain])).toEqual([
      ["a", "travel"],
      ["b", "lifestyle"],
    ]);
  });

  test("ignores unknown override ids", () => {
    const threads = [base({ id: "a", domain: "general" })];
    expect(applyDomainOverrides(threads, { missing: "career" })[0].domain).toBe("general");
  });
});
