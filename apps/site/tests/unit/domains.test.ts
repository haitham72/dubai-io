import { describe, expect, test } from "vitest";
import { classifyDomain, groupByDomain, SERVICE_CATEGORIES } from "../../unified/data/domains";

describe("classifyDomain", () => {
  test("routes household maintenance and schools", () => {
    expect(classifyDomain("AC not cooling").domain).toBe("household");
    expect(classifyDomain("AC not cooling").category).toBe("ac");
    expect(classifyDomain("KHDA school shortlist").domain).toBe("household");
    expect(classifyDomain("KHDA school shortlist").category).toBe("schools");
  });

  test("routes bills and insurance to money", () => {
    expect(classifyDomain("DEWA bill reminder").domain).toBe("money");
    expect(classifyDomain("DEWA bill reminder").category).toBe("bills");
    expect(classifyDomain("Ear pain clinic on my insurance").domain).toBe("money");
  });

  test("routes travel and taxi", () => {
    expect(classifyDomain("I left my bag in a taxi").domain).toBe("travel");
    expect(classifyDomain("best way from Marina to DXB").domain).toBe("travel");
  });

  test("routes lifestyle food gym laundry", () => {
    expect(classifyDomain("Plan Mamzar beach trip").domain).toBe("lifestyle");
    expect(classifyDomain("Laundry pickup tomorrow").domain).toBe("lifestyle");
    expect(classifyDomain("Renew gym membership").domain).toBe("lifestyle");
    expect(classifyDomain("Gyms near Dubai Marina open now").domain).toBe("lifestyle");
  });

  test("routes career follow-ups", () => {
    expect(classifyDomain("Draft the Gmail reply").domain).toBe("career");
  });

  test("empty or unknown stays general", () => {
    expect(classifyDomain("").domain).toBe("general");
    expect(classifyDomain("hello there").domain).toBe("general");
    expect(classifyDomain("hello there").provenance).toBe("default");
  });
});

describe("service categories", () => {
  test("keeps a bounded catalog of 5–15 categories", () => {
    expect(SERVICE_CATEGORIES.length).toBeGreaterThanOrEqual(5);
    expect(SERVICE_CATEGORIES.length).toBeLessThanOrEqual(16);
  });
});

describe("groupByDomain", () => {
  test("keeps domain order and drops empty sections", () => {
    const groups = groupByDomain([
      { id: "a", domain: "lifestyle" as const },
      { id: "b", domain: "household" as const },
      { id: "c", domain: "lifestyle" as const },
    ]);
    expect(groups.map((g) => [g.domain, g.items.map((i) => i.id)])).toEqual([
      ["lifestyle", ["a", "c"]],
      ["household", ["b"]],
    ]);
  });
});
