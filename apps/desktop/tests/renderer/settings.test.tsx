import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { demoBridge, type DesktopBridge } from "../../renderer/src/ipc/bridge";
import { SettingsPanel } from "../../renderer/src/panels/SettingsPanel";

describe("Owner hook", () => {
  it("passes a non-empty model and leaves source consent off", async () => {
    const base = demoBridge();
    const api: DesktopBridge = { ...base, hookToggle: vi.fn(base.hookToggle) };
    render(<SettingsPanel bridge={api} />);
    expect(screen.getByTestId("consent-chrome")).not.toBeChecked();
    expect(screen.getByTestId("consent-claude")).not.toBeChecked();
    expect(screen.getByTestId("consent-codex")).not.toBeChecked();

    fireEvent.click(screen.getByTestId("hook-toggle"));
    expect(api.hookToggle).not.toHaveBeenCalled();
    expect(screen.getByTestId("hook-error")).toHaveTextContent(/Choose a model/);

    fireEvent.change(screen.getByTestId("model-picker"), { target: { value: "claude-sonnet-4-5" } });
    fireEvent.click(screen.getByTestId("hook-toggle"));
    expect(api.hookToggle).toHaveBeenCalledWith({
      enabled: true,
      model: "claude-sonnet-4-5",
      owner: "karim",
    });
    expect(await screen.findByTestId("hook-status")).toHaveTextContent("claude-sonnet-4-5");
  });
});
