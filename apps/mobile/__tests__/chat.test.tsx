import React from "react";
import { fireEvent, render, waitFor } from "@testing-library/react-native";
import { ChatView } from "../src/components/ChatView";
import type { MemoryTurnConfirmation } from "../src/lib/types";

const confirmed: MemoryTurnConfirmation = {
  ok: true,
  applied: true,
  appliedFactIds: ["fact-gaming"],
  reply: "Saved the formatting preference.",
  trust: "T1",
  topic: "gaming/preferences",
  demo: false,
  warning: null,
};

const offline: MemoryTurnConfirmation = {
  ok: false,
  applied: false,
  appliedFactIds: [],
  reply: "The service is unreachable. This reply is demo data.",
  demo: true,
  warning: "offline",
};

describe("Chat memory badge", () => {
  it("hides the ingested badge on the synthetic thread", async () => {
    const view = await render(<ChatView demo />);
    expect(view.queryByTestId("memory-ingested-badge")).toBeNull();
    expect(view.queryByText(/Ingested into Temporal Memory/)).toBeNull();
    expect(view.getByText("Apology Accepted 👍")).toBeTruthy();
  });

  it("shows the badge only after a confirmed memory write", async () => {
    const sendTurn = jest.fn(async () => confirmed);
    const view = await render(<ChatView sendTurn={sendTurn} />);

    await fireEvent.changeText(view.getByTestId("chat-input"), "Remember that I like structured reports");
    await fireEvent.press(view.getByTestId("chat-send"));

    expect(await view.findByTestId("memory-ingested-badge")).toBeTruthy();
    expect(view.getByText("✓ Ingested into Temporal Memory")).toBeTruthy();
    expect(view.getByText("trust: T1 · topic: gaming/preferences")).toBeTruthy();
    expect(sendTurn).toHaveBeenCalledTimes(1);
  });

  it("omits the badge when the turn fails", async () => {
    const sendTurn = jest.fn(async () => {
      throw new Error("network down");
    });
    const view = await render(<ChatView sendTurn={sendTurn} />);
    await fireEvent.changeText(view.getByTestId("chat-input"), "hello");
    await fireEvent.press(view.getByTestId("chat-send"));

    await waitFor(() => {
      expect(view.getByText(/Nothing was ingested/)).toBeTruthy();
    });
    expect(view.queryByTestId("memory-ingested-badge")).toBeNull();
  });

  it("omits the badge when the turn stays on demo fallback", async () => {
    const sendTurn = jest.fn(async () => offline);
    const view = await render(<ChatView sendTurn={sendTurn} />);
    await fireEvent.changeText(view.getByTestId("chat-input"), "still offline");
    await fireEvent.press(view.getByTestId("chat-send"));
    await waitFor(() => {
      expect(view.getByText("The service is unreachable. This reply is demo data.")).toBeTruthy();
    });
    expect(view.queryByTestId("memory-ingested-badge")).toBeNull();
  });
});
