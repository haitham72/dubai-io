import { describe, expect, it, vi } from "vitest";
import type { RefObject } from "react";
import type { WebView } from "react-native-webview";

vi.mock("react-native", () => ({
  AppState: {
    currentState: "active",
    addEventListener: vi.fn(() => ({ remove: vi.fn() })),
  },
}));

import {
  buildManualContextClassification,
  classifyUserState,
  snapAreaPromptNote,
} from "../src/context/userStateClassifier";
import {
  buildWebViewContextDispatchScript,
  publishContextToWebView,
  type CommunityContextPayload,
} from "../src/context/useForegroundContext";

const FIXED_NOW = new Date("2026-11-25T10:00:00.000Z");

describe("classifyUserState", () => {
  it("returns unknown with confidence 0 and unavailable source when opt-in is off", () => {
    const result = classifyUserState(
      {
        optIn: false,
        hasPermission: true,
        speedMps: 14,
        stepCadencePerMin: 150,
        accelMagnitudeStd: 0.6,
        pitchDeg: 15,
      },
      FIXED_NOW,
    );

    expect(result).toEqual({
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf: FIXED_NOW.toISOString(),
    });
  });

  it("returns unknown with confidence 0 when permission is missing or no telemetry is present", () => {
    expect(
      classifyUserState(
        {
          optIn: true,
          hasPermission: false,
          stepCadencePerMin: 90,
        },
        FIXED_NOW,
      ),
    ).toEqual({
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf: FIXED_NOW.toISOString(),
    });

    expect(
      classifyUserState(
        {
          optIn: true,
          hasPermission: true,
        },
        FIXED_NOW,
      ),
    ).toEqual({
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf: FIXED_NOW.toISOString(),
    });
  });

  it("classifies driving when foreground speedMps >= 5.5", () => {
    const result = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        speedMps: 5.5,
        accelMagnitudeStd: 0.03,
        stepCadencePerMin: 0,
      },
      FIXED_NOW,
    );

    expect(result.userState).toBe("driving");
    expect(result.source).toBe("expo_sensors");
    expect(result.confidence).toBeGreaterThanOrEqual(0.8);
  });

  it("classifies running when cadence >= 135 or accelMagnitudeStd >= 0.45", () => {
    const byCadence = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        stepCadencePerMin: 135,
        accelMagnitudeStd: 0.2,
      },
      FIXED_NOW,
    );
    expect(byCadence.userState).toBe("running");
    expect(byCadence.source).toBe("expo_sensors");

    const byAccel = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.45,
        stepCadencePerMin: 110,
      },
      FIXED_NOW,
    );
    expect(byAccel.userState).toBe("running");
  });

  it("classifies walking when cadence >= 30 or accelMagnitudeStd >= 0.12", () => {
    const byCadence = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        stepCadencePerMin: 30,
        accelMagnitudeStd: 0.05,
      },
      FIXED_NOW,
    );
    expect(byCadence.userState).toBe("walking");
    expect(byCadence.source).toBe("expo_sensors");

    const byAccel = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.12,
        stepCadencePerMin: 8,
      },
      FIXED_NOW,
    );
    expect(byAccel.userState).toBe("walking");
  });

  it("classifies sitting vs standing only when low-motion and pitchDeg are reliable", () => {
    const sitting = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.02,
        stepCadencePerMin: 0,
        pitchDeg: 20,
      },
      FIXED_NOW,
    );
    expect(sitting.userState).toBe("sitting");
    expect(sitting.confidence).toBeGreaterThanOrEqual(0.7);
    expect(sitting.source).toBe("expo_sensors");

    const standing = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.03,
        stepCadencePerMin: 2,
        pitchDeg: 55,
      },
      FIXED_NOW,
    );
    expect(standing.userState).toBe("standing");
    expect(standing.confidence).toBeGreaterThanOrEqual(0.7);
    expect(standing.source).toBe("expo_sensors");
  });

  it("falls back honestly to stationary when pitchDeg is missing or ambiguous", () => {
    const missingPitch = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.02,
        stepCadencePerMin: 0,
      },
      FIXED_NOW,
    );
    expect(missingPitch.userState).toBe("stationary");
    expect(missingPitch.confidence).toBeLessThan(0.7);

    const ambiguousPitch = classifyUserState(
      {
        optIn: true,
        hasPermission: true,
        accelMagnitudeStd: 0.02,
        stepCadencePerMin: 0,
        pitchDeg: 44,
      },
      FIXED_NOW,
    );
    expect(ambiguousPitch.userState).toBe("stationary");
    expect(ambiguousPitch.confidence).toBeLessThan(0.7);
  });
});

describe("manual overrides, privacy note, and WebView bridge", () => {
  it("builds manual quick-state overrides and paused state cleanly", () => {
    expect(buildManualContextClassification("sitting", FIXED_NOW)).toEqual({
      userState: "sitting",
      confidence: 1,
      source: "user_override",
      asOf: FIXED_NOW.toISOString(),
    });
    expect(buildManualContextClassification("paused", FIXED_NOW)).toEqual({
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf: FIXED_NOW.toISOString(),
    });
  });

  it("documents Rule 8 and Rule 9 safeguards in snapAreaPromptNote", () => {
    const note = snapAreaPromptNote();
    expect(note).toContain("Raw GPS coordinates are never saved");
    expect(note).toContain("Rule 8");
    expect(note).toContain("Rule 9");
  });

  it("dispatches dubai.community.context via postMessage and CustomEvent script", () => {
    const postMessage = vi.fn();
    const injectJavaScript = vi.fn();
    const webViewRef = {
      current: { postMessage, injectJavaScript },
    } as unknown as RefObject<WebView<object> | null>;

    const payload: CommunityContextPayload = {
      userState: "walking",
      confidence: 0.88,
      source: "expo_sensors",
      asOf: FIXED_NOW.toISOString(),
      contextAwareEnabled: true,
      override: null,
      foregroundActive: true,
    };

    publishContextToWebView(webViewRef, payload);

    expect(postMessage).toHaveBeenCalledTimes(1);
    expect(JSON.parse(postMessage.mock.calls[0][0] as string)).toEqual({
      type: "dubai.community.context",
      payload,
    });

    const script = buildWebViewContextDispatchScript(payload);
    expect(injectJavaScript).toHaveBeenCalledWith(script);
    expect(script).toContain("dubai:community-context");
    expect(script).toContain('"userState":"walking"');
  });
});
