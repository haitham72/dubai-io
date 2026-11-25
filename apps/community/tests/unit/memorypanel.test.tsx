import { createRoot } from "react-dom/client";
import { act } from "react";
import { describe, expect, test, vi } from "vitest";
import MemoryPanel, { type MemoryApi } from "@/components/MemoryPanel";

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const off = {
  read_enabled: false,
  write_enabled: false,
  remember_saved_discussions: false,
  remember_public_posts: false,
  allow_interest_export: false,
  default_off: true,
  as_of: "2026-11-24T10:00:00+00:00",
};

async function mount(api: MemoryApi) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => {
    root.render(<MemoryPanel api={api} />);
  });
  return el;
}

const sw = (el: HTMLElement, label: string) =>
  el.querySelector(`button[role=switch][aria-label="${label}"]`) as HTMLButtonElement;
const FIRST = "Use my interests to order Discover";
const SAVED_SW = "Remember my saved discussions";
const POSTS_SW = "Remember my public posts";

describe("MemoryPanel split consent + D19 lower weight", () => {
  test("starts from server state (off) and split switches turn on only after server answers", async () => {
    let resolve!: (v: typeof off) => void;
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn(() => new Promise<typeof off>((r) => { resolve = r; })) as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("false");
    expect(sw(el, SAVED_SW).getAttribute("aria-checked")).toBe("false");
    expect(sw(el, POSTS_SW).getAttribute("aria-checked")).toBe("false");

    await act(async () => {
      sw(el, SAVED_SW).click();
    });
    expect(api.setMemoryConsent).toHaveBeenCalledWith({
      read_enabled: false,
      remember_saved_discussions: true,
      remember_public_posts: false,
      write_enabled: true,
      allow_interest_export: false,
    });
    expect(sw(el, SAVED_SW).getAttribute("aria-checked")).toBe("false"); // not optimistic
    expect(sw(el, SAVED_SW).textContent).toBe("Saving…");

    await act(async () => {
      resolve({
        ...off,
        remember_saved_discussions: true,
        write_enabled: true,
        default_off: false,
        as_of: "2026-11-24T10:05:00+00:00",
      });
    });
    expect(sw(el, SAVED_SW).getAttribute("aria-checked")).toBe("true");
    expect(sw(el, POSTS_SW).getAttribute("aria-checked")).toBe("false");
    expect(el.querySelector("[data-testid=consent-meta]")!.textContent).toContain("10:05");
  });

  test("a failed toggle keeps the old state and shows the error", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => ({ ...off, read_enabled: true, default_off: false }),
      setMemoryConsent: async () => {
        throw new Error("Memory bridge is not configured");
      },
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    await act(async () => {
      sw(el, FIRST).click();
    });
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("true");
    expect(el.textContent).toContain("Not changed: Memory bridge is not configured");
  });

  test("Lower weight reduces preference weights to 0.01 via lowerCommunityMemory", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
      lowerCommunityMemory: vi.fn(async () => ({ w_min: 0.01, weights_lowered: 4, as_of: "T" })),
    };
    const el = await mount(api);
    const btn = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Lower weight on preferences"),
    )!;
    await act(async () => {
      btn.click();
    });
    expect(api.lowerCommunityMemory).toHaveBeenCalled();
    expect(el.querySelector("[data-testid=lower-memory-result]")!.textContent).toContain("0.01");
  });

  test("Delete my data shows server counts only after the response", async () => {
    let resolve!: (v: unknown) => void;
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn(() => new Promise((r) => { resolve = r; })) as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    const btn = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Delete my data"),
    )!;
    await act(async () => {
      btn.click();
    });
    expect(el.querySelector("[data-testid=forget-result]")).toBeNull();
    await act(async () => {
      resolve({ records_forgotten: 3, facts_erased: 2, as_of: "T" });
    });
    expect(el.querySelector("[data-testid=forget-result]")!.textContent).toContain(
      "3 record(s) and 2 fact(s)",
    );
  });

  test("a failed Delete my data reports the failure and no success text", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: async () => {
        throw new Error("Community service unavailable");
      },
    };
    const el = await mount(api);
    const btn = [...el.querySelectorAll("button")].find((b) =>
      b.textContent?.includes("Delete my data"),
    )!;
    await act(async () => {
      btn.click();
    });
    expect(el.querySelector("[data-testid=forget-result]")).toBeNull();
    expect(el.textContent).toContain("Delete my data did not complete: Community service unavailable");
  });

  test("when the status cannot load the switches are disabled and say so", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => {
        throw new Error("down");
      },
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    expect(el.textContent).toContain("Memory status unavailable: down");
    expect(sw(el, FIRST).disabled).toBe(true);
  });
});
