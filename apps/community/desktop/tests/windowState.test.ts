import { describe, expect, it } from "vitest";
import {
  DEFAULT_WINDOW_STATE,
  parseWindowState,
} from "../electron/windowState";

describe("parseWindowState", () => {
  it("falls back to defaults on invalid JSON", () => {
    expect(parseWindowState("not json")).toEqual(DEFAULT_WINDOW_STATE);
  });

  it("clamps minimum width and height and preserves valid coordinates", () => {
    expect(
      parseWindowState(
        JSON.stringify({ width: 200, height: 100, x: 40, y: 80, isMaximized: true }),
      ),
    ).toEqual({
      width: 640,
      height: 480,
      x: 40,
      y: 80,
      isMaximized: true,
    });
  });
});
