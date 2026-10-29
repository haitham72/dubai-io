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
      base({ id: "b", domain: "services" }),
    ];
    const next = applyDomainOverrides(threads, { a: "places" });
    expect(next.map((t) => [t.id, t.domain])).toEqual([
      ["a", "places"],
      ["b", "services"],
    ]);
  });

  test("ignores unknown override ids", () => {
    const threads = [base({ id: "a", domain: "general" })];
    expect(applyDomainOverrides(threads, { missing: "work" })[0].domain).toBe("general");
  });
});
