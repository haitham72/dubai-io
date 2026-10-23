import { describe, expect, test } from "vitest";
import { briefing, relTime, toThreads, type TodayResponse } from "../../unified/data/tasks";

const empty: TodayResponse = {
  needs_you: { tasks: [] }, running: { tasks: [] }, scheduled: { tasks: [] }, on_list: { tasks: [] }, paused: { tasks: [] }, completed: { tasks: [] },
};
const task = (id: string, outcome: string, extra: Record<string, unknown> = {}) => ({ id, outcome, status: "WAITING_USER", updated_at: "2026-10-23T09:00:00+04:00", ...extra });

describe("toThreads", () => {
  test("empty today gives the 3 labelled demo threads", () => {
    const t = toThreads(empty, []);
    expect(t.map((x) => x.id)).toEqual(["demo-ac", "demo-laundry", "demo-dewa"]);
    expect(t.every((x) => x.demo)).toBe(true);
    expect(t.map((x) => x.title)).toEqual(["AC repair", "Laundry pickup", "DEWA bill"]);
    expect(t.map((x) => x.preview)).toEqual(["needs your approval", "waiting for provider", "due Thursday"]);
  });

  test("real tasks come first, ordered by lane, demo follow", () => {
    const today: TodayResponse = {
      ...empty,
      on_list: { tasks: [task("t3", "Renew visa")] },
      running: { tasks: [task("t2", "Pressing order")] },
      needs_you: { tasks: [task("t1", "Approve AC visit")] },
    };
    const t = toThreads(today, []);
    expect(t.slice(0, 3).map((x) => [x.id, x.lane, x.demo])).toEqual([
      ["t1", "needs_you", false], ["t2", "running", false], ["t3", "on_list", false],
    ]);
    expect(t.slice(3).map((x) => x.id)).toEqual(["demo-ac", "demo-laundry", "demo-dewa"]);
    expect(t[0].title).toBe("Approve AC visit");
  });

  test("scheduled sits between running and on_list; a task in two lanes shows once", () => {
    const today: TodayResponse = {
      ...empty,
      scheduled: { tasks: [task("s1", "Check back")] },
      on_list: { tasks: [task("s1", "Check back"), task("o1", "Other")] },
      running: { tasks: [task("r1", "Running")] },
    };
    expect(toThreads(today, []).filter((x) => !x.demo).map((x) => [x.id, x.lane])).toEqual([["r1", "running"], ["s1", "scheduled"], ["o1", "on_list"]]);
  });

  test("dismissed demo ids are removed", () => {
    expect(toThreads(empty, ["demo-ac"]).map((x) => x.id)).toEqual(["demo-laundry", "demo-dewa"]);
  });

  test("completed tasks are not listed as open threads", () => {
    const today: TodayResponse = { ...empty, completed: { tasks: [task("c1", "Done thing", { status: "COMPLETED" })] } };
    expect(toThreads(today, []).some((x) => x.id === "c1")).toBe(false);
  });
});

describe("briefing", () => {
  test("picks first needs_you, most recent other, first scheduled", () => {
    const today: TodayResponse = {
      ...empty,
      needs_you: { tasks: [task("n1", "Approve", { updated_at: "2026-10-23T08:00:00+04:00" })] },
      running: { tasks: [task("r1", "Old", { updated_at: "2026-10-22T08:00:00+04:00" }), task("r2", "Newest", { updated_at: "2026-10-23T09:30:00+04:00" })] },
      scheduled: { tasks: [task("s1", "Later", { updated_at: "2026-10-21T08:00:00+04:00" })] },
    };
    const b = briefing(toThreads(today, ["demo-ac", "demo-laundry", "demo-dewa"]));
    expect([b.needsYou?.id, b.changed?.id, b.due?.id]).toEqual(["n1", "r2", "s1"]);
  });

  test("empty today briefs from the demo threads", () => {
    const b = briefing(toThreads(empty, []));
    expect([b.needsYou?.id, b.changed?.id, b.due?.id]).toEqual(["demo-ac", "demo-laundry", "demo-dewa"]);
  });

  test("nothing at all gives an empty briefing", () => {
    expect(briefing([])).toEqual({});
  });
});

describe("relTime", () => {
  const now = Date.parse("2026-10-23T10:00:00+04:00");
  test("minutes, hours, days", () => {
    expect(relTime("2026-10-23T09:48:00+04:00", now)).toBe("12m");
    expect(relTime("2026-10-23T09:00:00+04:00", now)).toBe("1h");
    expect(relTime("2026-10-21T10:00:00+04:00", now)).toBe("2d");
    expect(relTime("", now)).toBe("");
  });
});
