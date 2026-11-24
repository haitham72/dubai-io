import { fireEvent, render, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { demoBridge, type DesktopBridge } from "../../renderer/src/ipc/bridge";
import { AnalyticsPanel } from "../../renderer/src/panels/AnalyticsPanel";

describe("analytics panel", () => {
  it("shows the 36% to 73% jump, seven themes, the privacy shield, and the sync toggle", async () => {
    const base = demoBridge();
    const api: DesktopBridge = {
      ...base,
      syncStatus: vi.fn(base.syncStatus),
      syncConfigure: vi.fn(base.syncConfigure),
      syncRun: vi.fn(async () => ({
        enabledSources: ["chrome", "edge", "claude-code", "codex"] as const,
        intervalMinutes: 60 as const,
        syncOnFocus: true,
        lastSyncAt: "2026-11-24T04:00:00Z",
        enqueued: 2,
      })),
    };
    render(<AnalyticsPanel bridge={api} fetcher={async () => { throw new Error("offline"); }} />);
    await waitFor(() => expect(screenText()).toMatch(/36%/));
    expect(screenText()).toMatch(/73%/);
    expect(screenText()).toMatch(/Demo data/);
    for (const theme of ["career", "learning", "projects", "people-family", "events", "home-money", "travel"]) {
      expect(document.querySelector(`[data-testid="theme-${theme}"]`)).toBeTruthy();
    }
    expect(screenText()).toMatch(/People & family/);
    expect(screenText()).toMatch(/Home & money/);
    expect(screenText()).toMatch(/rising_21d/);
    expect(screenText()).toMatch(/3 sensitive items held back/);
    expect(screenText()).toMatch(/health: 2/);
    expect(screenText()).not.toMatch(/Diabetes|Prayer|password/);
    expect(screenText()).toMatch(/\$0 app cost/);

    fireEvent.click(document.querySelector("[data-testid='sync-toggle']") as HTMLButtonElement);
    await waitFor(() => expect(api.syncConfigure).toHaveBeenCalledWith({
      enabledSources: ["chrome", "edge", "claude-code", "codex"],
      intervalMinutes: 60,
      syncOnFocus: true,
    }));
    expect(api.syncRun).toHaveBeenCalledOnce();
  });
});

function screenText(): string {
  return document.body.textContent ?? "";
}
