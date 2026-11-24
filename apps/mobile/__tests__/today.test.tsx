import React from "react";
import { Dimensions, StyleSheet } from "react-native";
import { render } from "@testing-library/react-native";
import { cardViewportWidth } from "@dubai-io/design-tokens";
import { TodayView } from "../src/components/TodayView";

describe("Today", () => {
  it("renders 3:4 cards, a Because chip, and a Demo data pill", async () => {
    const view = await render(<TodayView onOpenSettings={() => undefined} demo />);

    expect(view.getByText("Good morning, Karim")).toBeTruthy();
    expect(view.getByText("Dubai · Monday, 23 Nov")).toBeTruthy();
    expect(view.getByText(/Because… you told me you track open-world releases/)).toBeTruthy();
    expect(view.getAllByText("Demo data").length).toBeGreaterThan(0);

    const card = view.getByTestId("today-card-gta");
    const style = StyleSheet.flatten(card.props.style);
    expect(style.aspectRatio).toBeCloseTo(3 / 4);
    expect(style.width).toBe(Math.round(Dimensions.get("window").width * cardViewportWidth));
    expect(style.shadowOpacity).toBe(0);
    expect(style.elevation).toBe(0);
  });
});
