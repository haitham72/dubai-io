import { cardAspectRatio, colors, gold, noShadow, shadow, themes } from "@dubai-io/design-tokens";
import palette from "../../../packages/design-tokens/palette.json";

describe("design tokens", () => {
  it("matches the light palette and the six life-theme hues", () => {
    expect(colors.canvas).toBe("#FFFFFF");
    expect(colors.surface).toBe("#FAF8F5");
    expect(colors.userBubble).toBe("#1E2022");
    expect(colors.repairSurface).toBe("#FDF8EE");
    expect(gold).toEqual({
      primary: "#C5A059",
      metallic: "#D4AF37",
      surface: "#FDF8EE",
      border: "#E8D5A3",
    });
    expect(themes).toEqual({
      career: "#2F80ED",
      projects: "#9B51E0",
      learning: "#F2994A",
      gaming: "#EB5757",
      travel: "#00B4D8",
      health: "#27AE60",
    });
    expect(palette.colors.canvas).toBe(colors.canvas);
    expect(palette.colors.themes).toEqual(themes);
  });

  it("keeps card ratio at 3:4 and forbids shadows", () => {
    expect(cardAspectRatio).toBeCloseTo(3 / 4);
    expect(palette.cardAspectRatio).toBeCloseTo(3 / 4);
    expect(shadow).toBe("none");
    expect(palette.shadow).toBe("none");
    expect(noShadow.shadowOpacity).toBe(0);
    expect(noShadow.elevation).toBe(0);
    expect(noShadow.shadowRadius).toBe(0);
  });
});
