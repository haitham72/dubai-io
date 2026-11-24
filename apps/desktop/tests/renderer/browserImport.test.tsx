import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { demoBridge, type DesktopBridge } from "../../renderer/src/ipc/bridge";
import { BrowserImportPanel } from "../../renderer/src/panels/BrowserImportPanel";

function bridge(): DesktopBridge {
  const base = demoBridge();
  return {
    ...base,
    previewBrowser: vi.fn(base.previewBrowser),
    importBrowser: vi.fn(base.importBrowser),
  };
}

describe("Browser import consent", () => {
  it("shows domain counts from preview and imports only after confirmation", async () => {
    const api = bridge();
    render(<BrowserImportPanel bridge={api} />);
    expect(screen.getByTestId("history-disclaimer")).toHaveTextContent(
      "History & Bookmarks only — Cookies, Passwords & Autofill are NEVER touched",
    );
    expect(screen.getByText(/Banking, health, and government portals/)).toBeTruthy();
    expect(screen.getByTestId("import-history")).toBeDisabled();

    fireEvent.click(screen.getByTestId("preview-history"));
    expect(await screen.findByText("research.example: 3")).toBeTruthy();
    expect(screen.getByText("docs.example: 2")).toBeTruthy();
    expect(api.previewBrowser).toHaveBeenCalledTimes(1);
    expect(api.importBrowser).not.toHaveBeenCalled();
    expect(screen.getByTestId("import-history")).toBeDisabled();

    fireEvent.click(screen.getByTestId("import-confirm"));
    fireEvent.click(screen.getByTestId("import-history"));
    expect(api.importBrowser).toHaveBeenCalledWith({ browser: "chrome", profileName: "Default", consent: true });
    expect(await screen.findByTestId("import-result")).toHaveTextContent("Records created: 0");
  });
});
