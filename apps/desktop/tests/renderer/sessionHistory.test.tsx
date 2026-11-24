import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DEMO_SESSIONS, demoBridge, type DesktopBridge } from "../../renderer/src/ipc/bridge";
import { SessionHistoryPanel } from "../../renderer/src/panels/SessionHistoryPanel";

function bridge(): DesktopBridge {
  const base = demoBridge();
  return {
    ...base,
    scanSessions: vi.fn(base.scanSessions),
    resumeCommand: vi.fn(base.resumeCommand),
  };
}

describe("Session history", () => {
  beforeEach(() => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn(async () => undefined) } });
  });

  it("filters, searches, and pages without scanning before opt-in", async () => {
    const api = bridge();
    render(<SessionHistoryPanel bridge={api} sessions={DEMO_SESSIONS} pageSize={1} />);
    expect(api.scanSessions).not.toHaveBeenCalled();
    expect(screen.getByTestId("scan-sessions")).toBeDisabled();

    fireEvent.change(screen.getByTestId("session-search"), { target: { value: "shorebirds" } });
    expect(screen.getByText("Coastal birds reading list")).toBeTruthy();
    expect(screen.queryByText("Interface typography notes")).toBeNull();

    fireEvent.change(screen.getByTestId("session-search"), { target: { value: "" } });
    fireEvent.change(screen.getByTestId("agent-filter"), { target: { value: "codex" } });
    expect(screen.getByText("Coastal birds reading list")).toBeTruthy();
    expect(screen.queryByText("Morning layout pass")).toBeNull();

    fireEvent.change(screen.getByTestId("agent-filter"), { target: { value: "all" } });
    fireEvent.click(screen.getByTestId("page-next"));
    expect(screen.getByTestId("page-label").textContent).toMatch(/Page 2/);
    expect(screen.getAllByRole("listitem")).toHaveLength(1);

    fireEvent.click(screen.getByTestId("session-consent"));
    fireEvent.click(screen.getByTestId("scan-sessions"));
    expect(api.scanSessions).toHaveBeenCalledTimes(1);
  });

  it("copies a safe resume command and sends only after confirmation", async () => {
    const api = bridge();
    render(<SessionHistoryPanel bridge={api} sessions={DEMO_SESSIONS} pageSize={10} />);
    fireEvent.click(screen.getByTestId("copy-sess-typography"));
    expect(api.resumeCommand).toHaveBeenCalledWith({
      agentTool: "claude-code",
      sessionId: "sess-typography",
      cwd: "C:\\demo\\raseef",
    });
    expect(await screen.findByTestId("copied-command")).toHaveTextContent("claude --resume sess-typography");

    fireEvent.click(screen.getByLabelText(/Interface typography notes/));
    expect(screen.getByTestId("send-selected")).toBeDisabled();
    fireEvent.click(screen.getByTestId("session-consent"));
    fireEvent.click(screen.getByTestId("send-confirm"));
    fireEvent.click(screen.getByTestId("send-selected"));
    expect(api.scanSessions).toHaveBeenCalledTimes(1);
    expect(await screen.findByTestId("session-notice")).toHaveTextContent("Sent 1 selected sessions");
  });
});
