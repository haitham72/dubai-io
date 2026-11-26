export type UserState =
  | "stationary"
  | "sitting"
  | "standing"
  | "walking"
  | "running"
  | "driving"
  | "unknown";

export type UserStateSource = "expo_sensors" | "user_override" | "unavailable";

export type ManualContextOverride =
  | "sitting"
  | "walking"
  | "driving"
  | "paused";

export interface ForegroundSample {
  accelMagnitudeStd?: number;
  stepCadencePerMin?: number;
  speedMps?: number;
  pitchDeg?: number;
  hasPermission?: boolean;
  optIn?: boolean;
}

export interface UserStateClassification {
  userState: UserState;
  confidence: number;
  source: UserStateSource;
  asOf: string;
}

function isFiniteNonNegative(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/**
 * Classifies an ephemeral foreground motion/location sample into a coarse user state.
 * Never infers sitting/standing without reliable low-motion and pitch evidence.
 */
export function classifyUserState(
  sample: ForegroundSample,
  now: Date = new Date(),
): UserStateClassification {
  const asOf = now.toISOString();

  if (!sample.optIn || !sample.hasPermission) {
    return {
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf,
    };
  }

  const speedMps = isFiniteNonNegative(sample.speedMps)
    ? sample.speedMps
    : undefined;
  const cadence = isFiniteNonNegative(sample.stepCadencePerMin)
    ? sample.stepCadencePerMin
    : undefined;
  const accelStd = isFiniteNonNegative(sample.accelMagnitudeStd)
    ? sample.accelMagnitudeStd
    : undefined;
  const pitchDeg = isFiniteNumber(sample.pitchDeg)
    ? sample.pitchDeg
    : undefined;

  if (
    speedMps === undefined &&
    cadence === undefined &&
    accelStd === undefined &&
    pitchDeg === undefined
  ) {
    return {
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf,
    };
  }

  if (speedMps !== undefined && speedMps >= 5.5) {
    return {
      userState: "driving",
      confidence: speedMps >= 10 ? 0.94 : 0.86,
      source: "expo_sensors",
      asOf,
    };
  }

  const highCadence = cadence !== undefined && cadence >= 135;
  const highAccel = accelStd !== undefined && accelStd >= 0.45;
  if (highCadence || highAccel) {
    return {
      userState: "running",
      confidence: highCadence && highAccel ? 0.92 : 0.84,
      source: "expo_sensors",
      asOf,
    };
  }

  const walkingCadence = cadence !== undefined && cadence >= 30;
  const walkingAccel = accelStd !== undefined && accelStd >= 0.12;
  if (walkingCadence || walkingAccel) {
    return {
      userState: "walking",
      confidence: walkingCadence && walkingAccel ? 0.88 : 0.78,
      source: "expo_sensors",
      asOf,
    };
  }

  const hasMotionTelemetry = accelStd !== undefined || cadence !== undefined;
  const isLowAccel = accelStd === undefined || accelStd < 0.08;
  const isLowCadence = cadence === undefined || cadence < 10;

  if (hasMotionTelemetry && isLowAccel && isLowCadence) {
    if (pitchDeg !== undefined) {
      if (pitchDeg < 35) {
        return {
          userState: "sitting",
          confidence: 0.75,
          source: "expo_sensors",
          asOf,
        };
      }
      if (pitchDeg >= 55) {
        return {
          userState: "standing",
          confidence: 0.75,
          source: "expo_sensors",
          asOf,
        };
      }
      return {
        userState: "stationary",
        confidence: 0.58,
        source: "expo_sensors",
        asOf,
      };
    }

    return {
      userState: "stationary",
      confidence: 0.65,
      source: "expo_sensors",
      asOf,
    };
  }

  return {
    userState: "stationary",
    confidence: 0.55,
    source: "expo_sensors",
    asOf,
  };
}

/**
 * Builds a classification result from an explicit user quick-state override.
 */
export function buildManualContextClassification(
  override: ManualContextOverride,
  now: Date = new Date(),
): UserStateClassification {
  const asOf = now.toISOString();
  if (override === "paused") {
    return {
      userState: "unknown",
      confidence: 0,
      source: "unavailable",
      asOf,
    };
  }
  return {
    userState: override,
    confidence: 1,
    source: "user_override",
    asOf,
  };
}

/**
 * Returns the privacy and scope notice shown alongside adaptive context controls.
 */
export function snapAreaPromptNote(): string {
  return "Adaptive context runs only in the foreground when you opt in. Raw GPS coordinates are never saved, zero background geofencing runs (Rule 8), and userState is ephemeral session context only — zero health or fitness tracking (Rule 9).";
}
