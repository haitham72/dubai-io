import { createRoot } from "react-dom/client";
import { act } from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import UsageProfilePanel, { type UsageApi } from "@/components/UsageProfilePanel";
import SafetyPanel, { type SafetyApi } from "@/components/SafetyPanel";

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

afterEach(() => {
  document.body.innerHTML = "";
});

describe("UsageProfilePanel D19 / D19b controls", () => {
  test("renders active and lowered buckets and wires Lower, Restore, Recall topic, and Settings", async () => {
    const state = {
      context_aware_enabled: true,
      buckets: [
        {
          topic_key: "padel",
          topic_label: "Padel",
          time_bucket: "evening",
          area_coarse: "Dubai Marina",
          weight: 0.82,
          status: "active",
        },
        {
          topic_key: "housing",
          topic_label: "Housing",
          time_bucket: "workday",
          area_coarse: "DIFC",
          weight: 0.01,
          status: "lowered",
          lowered_at: "2026-11-25T10:00:00Z",
        },
      ],
    };

    const api: UsageApi = {
      getUsageProfile: vi.fn(async () => ({ ...state, buckets: state.buckets.map((b) => ({ ...b })) })),
      lowerUsageTopic: vi.fn(async (k: string) => {
        const target = state.buckets.find((b) => b.topic_key === k)!;
        target.weight = 0.01;
        target.status = "lowered";
        return target;
      }),
      restoreUsageTopic: vi.fn(async (k: string) => {
        const target = state.buckets.find((b) => b.topic_key === k)!;
        target.weight = 0.5;
        target.status = "active";
        delete target.lowered_at;
        return target;
      }),
      recallUsageTopic: vi.fn(async (k?: string) => {
        const target = state.buckets.find((b) => b.topic_key === k);
        if (target) {
          target.weight = 0.35;
          target.status = "active";
          delete target.lowered_at;
        }
        return { recalled: target ? [target] : [] };
      }),
      setUsageSettings: vi.fn(async (enabled: boolean) => {
        state.context_aware_enabled = enabled;
        return { context_aware_enabled: enabled };
      }),
    };

    const el = document.createElement("div");
    document.body.appendChild(el);
    await act(async () => {
      createRoot(el).render(<UsageProfilePanel api={api} />);
    });

    const rows = el.querySelectorAll("[data-testid=usage-bucket]");
    expect(rows).toHaveLength(2);
    expect(rows[0].textContent).toContain("Active");
    expect(rows[1].textContent).toContain("Lowered (0.01)");

    // Lower active bucket
    const lowerBtn = [...rows[0].querySelectorAll("button")].find((b) => b.textContent === "Lower")!;
    await act(async () => {
      lowerBtn.click();
    });
    expect(api.lowerUsageTopic).toHaveBeenCalledWith("padel");

    // Recall lowered bucket (D19b)
    const rowsAfter = el.querySelectorAll("[data-testid=usage-bucket]");
    const recallBtn = [...rowsAfter[1].querySelectorAll("button")].find(
      (b) => b.textContent === "Recall topic",
    )!;
    await act(async () => {
      recallBtn.click();
    });
    expect(api.recallUsageTopic).toHaveBeenCalledWith("housing", "housing");
    expect(el.querySelectorAll("[data-testid=usage-bucket]")[1].textContent).toContain("Active");

    // Restore lowered bucket
    const rowsAfter2 = el.querySelectorAll("[data-testid=usage-bucket]");
    const restoreBtn = [...rowsAfter2[0].querySelectorAll("button")].find(
      (b) => b.textContent === "Restore",
    )!;
    await act(async () => {
      restoreBtn.click();
    });
    expect(api.restoreUsageTopic).toHaveBeenCalledWith("padel");

    // Toggle context-aware switch
    const sw = el.querySelector("button[role=switch]") as HTMLButtonElement;
    await act(async () => {
      sw.click();
    });
    expect(api.setUsageSettings).toHaveBeenCalledWith(false);
  });
});

describe("SafetyPanel block & mute management", () => {
  test("lists blocked users and muted targets and supports Unblock / Unmute", async () => {
    const api: SafetyApi = {
      getSafety: vi.fn(async () => ({
        blocked: [{ handle: "bad_actor", display_name: "Bad Actor" }],
        mutes: [{ kind: "tag", target: "spam" }],
      })),
      unblockUser: vi.fn(async () => {}),
      unmuteTarget: vi.fn(async () => {}),
    };

    const el = document.createElement("div");
    document.body.appendChild(el);
    await act(async () => {
      createRoot(el).render(<SafetyPanel api={api} />);
    });

    expect(el.textContent).toContain("@bad_actor");
    expect(el.textContent).toContain("#spam");

    const unblockBtn = [...el.querySelectorAll("button")].find((b) => b.textContent === "Unblock")!;
    await act(async () => {
      unblockBtn.click();
    });
    expect(api.unblockUser).toHaveBeenCalledWith("bad_actor");
    expect(el.textContent).not.toContain("@bad_actor");

    const unmuteBtn = [...el.querySelectorAll("button")].find((b) => b.textContent === "Unmute")!;
    await act(async () => {
      unmuteBtn.click();
    });
    expect(api.unmuteTarget).toHaveBeenCalledWith("tag", "spam");
    expect(el.textContent).not.toContain("#spam");
  });
});
