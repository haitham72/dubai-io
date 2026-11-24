import { createRoot } from "react-dom/client";
import { act } from "react";
import { describe, expect, test, vi } from "vitest";
import MemoryPanel, { type MemoryApi } from "@/components/MemoryPanel";

(globalThis as unknown as { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

const off = { read_enabled: false, write_enabled: false, allow_interest_export: false, default_off: true, as_of: "2026-11-24T10:00:00+00:00" };

async function mount(api: MemoryApi) {
  const el = document.createElement("div");
  document.body.appendChild(el);
  const root = createRoot(el);
  await act(async () => { root.render(<MemoryPanel api={api} />); });
  return el;
}
const sw = (el: HTMLElement, label: string) => el.querySelector(`button[role=switch][aria-label="${label}"]`) as HTMLButtonElement;
const FIRST = "Use my interests to order Discover";

describe("MemoryPanel", () => {
  test("starts from the server state (off) and a toggle turns on only after the server answers", async () => {
    let resolve!: (v: typeof off) => void;
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn(() => new Promise<typeof off>((r) => { resolve = r; })) as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("false");
    await act(async () => { sw(el, FIRST).click(); });
    expect(api.setMemoryConsent).toHaveBeenCalledWith({ read_enabled: true, write_enabled: false, allow_interest_export: false });
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("false"); // not optimistic
    expect(sw(el, FIRST).textContent).toBe("Saving…");
    await act(async () => { resolve({ ...off, read_enabled: true, default_off: false, as_of: "2026-11-24T10:05:00+00:00" }); });
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("true");
    expect(el.querySelector("[data-testid=consent-meta]")!.textContent).toContain("10:05");
  });

  test("a failed toggle keeps the old state and shows the error", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => ({ ...off, read_enabled: true, default_off: false }),
      setMemoryConsent: async () => { throw new Error("Memory bridge is not configured"); },
      forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    await act(async () => { sw(el, FIRST).click(); });
    expect(sw(el, FIRST).getAttribute("aria-checked")).toBe("true");
    expect(el.textContent).toContain("Not changed: Memory bridge is not configured");
  });

  test("Forget shows the server counts only after the response", async () => {
    let resolve!: (v: unknown) => void;
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: vi.fn(() => new Promise((r) => { resolve = r; })) as unknown as MemoryApi["forgetMemory"],
    };
    const el = await mount(api);
    const btn = [...el.querySelectorAll("button")].find((b) => b.textContent?.includes("Forget connected memory"))!;
    await act(async () => { btn.click(); });
    expect(el.querySelector("[data-testid=forget-result]")).toBeNull();
    await act(async () => { resolve({ records_forgotten: 3, facts_erased: 2, as_of: "T" }); });
    expect(el.querySelector("[data-testid=forget-result]")!.textContent).toContain("3 record(s) and 2 fact(s)");
  });

  test("a failed Forget reports the failure and no success text", async () => {
    const api: MemoryApi = {
      getMemoryConsent: async () => off,
      setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"],
      forgetMemory: async () => { throw new Error("Community service unavailable"); },
    };
    const el = await mount(api);
    const btn = [...el.querySelectorAll("button")].find((b) => b.textContent?.includes("Forget connected memory"))!;
    await act(async () => { btn.click(); });
    expect(el.querySelector("[data-testid=forget-result]")).toBeNull();
    expect(el.textContent).toContain("Forget did not complete: Community service unavailable");
  });

  test("when the status cannot load the switches are disabled and say so", async () => {
    const api: MemoryApi = { getMemoryConsent: async () => { throw new Error("down"); }, setMemoryConsent: vi.fn() as unknown as MemoryApi["setMemoryConsent"], forgetMemory: vi.fn() as unknown as MemoryApi["forgetMemory"] };
    const el = await mount(api);
    expect(el.textContent).toContain("Memory status unavailable: down");
    expect(sw(el, FIRST).disabled).toBe(true);
  });
});
