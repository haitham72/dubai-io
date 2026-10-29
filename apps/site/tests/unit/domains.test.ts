import { describe, expect, test } from "vitest";
import { classifyDomain, groupByDomain, SERVICE_CATEGORIES } from "../../unified/data/domains";

describe("classifyDomain", () => {
  test("routes household maintenance and bills", () => {
    expect(classifyDomain("AC not cooling").domain).toBe("household");
    expect(classifyDomain("AC not cooling").category).toBe("ac");
    expect(classifyDomain("DEWA bill reminder").domain).toBe("household");
    expect(classifyDomain("DEWA bill reminder").category).toBe("bills");
    expect(classifyDomain("KHDA school shortlist").category).toBe("schools");
  });

  test("routes places and trips", () => {
    expect(classifyDomain("Coffee near me").domain).toBe("places");
    expect(classifyDomain("Plan Mamzar beach trip").domain).toBe("places");
  });

  test("routes service catalog jobs", () => {
    expect(classifyDomain("Laundry pickup tomorrow").domain).toBe("services");
    expect(classifyDomain("Laundry pickup tomorrow").category).toBe("laundry");
  });

  test("routes work follow-ups", () => {
    expect(classifyDomain("Draft the Gmail reply").domain).toBe("work");
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
    expect(SERVICE_CATEGORIES.length).toBeLessThanOrEqual(15);
  });
});

describe("groupByDomain", () => {
  test("keeps domain order and drops empty sections", () => {
    const groups = groupByDomain([
      { id: "a", domain: "services" as const },
      { id: "b", domain: "household" as const },
      { id: "c", domain: "services" as const },
    ]);
    expect(groups.map((g) => [g.domain, g.items.map((i) => i.id)])).toEqual([
      ["household", ["b"]],
      ["services", ["a", "c"]],
    ]);
  });
});
