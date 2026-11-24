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

describe("Desktop sign-in control", () => {
  it("shows Not signed in, signs in through the bridge, shows the email, then signs out", async () => {
    const base = demoBridge();
    const signedIn = { signedIn: true, userId: "u1", displayName: "Test", email: "o@example.test", hasDeviceToken: true };
    const signedOut = { signedIn: false, userId: null, displayName: null, email: null, hasDeviceToken: false };
    const api: DesktopBridge = {
      ...base,
      authStatus: vi.fn(async () => signedOut),
      authSignIn: vi.fn(async () => signedIn),
      authSignOut: vi.fn(async () => signedOut),
    };
    render(<SettingsPanel bridge={api} />);
    expect(await screen.findByTestId("auth-status")).toHaveTextContent("Not signed in");
    fireEvent.click(screen.getByTestId("auth-toggle"));
    expect(await screen.findByText(/Signed in as o@example.test/)).toBeTruthy();
    expect(screen.getByTestId("auth-toggle")).toHaveTextContent("Sign out");
    fireEvent.click(screen.getByTestId("auth-toggle"));
    expect(await screen.findByText("Not signed in")).toBeTruthy();
    expect(api.authSignOut).toHaveBeenCalled();
  });

  it("shows an honest error when sign-in fails", async () => {
    const api: DesktopBridge = { ...demoBridge(), authSignIn: async () => { throw new Error("Google sign-in timed out"); } };
    render(<SettingsPanel bridge={api} />);
    fireEvent.click(await screen.findByTestId("auth-toggle"));
    expect(await screen.findByTestId("auth-error")).toHaveTextContent("timed out");
    expect(screen.getByTestId("auth-status")).toHaveTextContent("Not signed in");
  });
});
