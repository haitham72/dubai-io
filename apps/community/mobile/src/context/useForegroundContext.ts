import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { AppState, type AppStateStatus } from "react-native";
import type { WebView } from "react-native-webview";
import {
  buildManualContextClassification,
  classifyUserState,
  snapAreaPromptNote,
  type ForegroundSample,
  type ManualContextOverride,
  type UserStateClassification,
} from "./userStateClassifier";

export interface CommunityContextPayload extends UserStateClassification {
  contextAwareEnabled: boolean;
  override: ManualContextOverride | null;
  foregroundActive: boolean;
}

export interface UseForegroundContextOptions {
  webViewRef: RefObject<WebView<object> | null>;
  initialEnabled?: boolean;
}

export interface UseForegroundContextResult {
  contextAwareEnabled: boolean;
  setContextAwareEnabled: (enabled: boolean) => void;
  manualOverride: ManualContextOverride | null;
  setManualOverride: (override: ManualContextOverride | null) => void;
  classification: UserStateClassification;
  payload: CommunityContextPayload;
  sensorsAvailable: boolean;
  privacyNote: string;
  syncToWebView: () => void;
}

interface ExpoSubscription {
  remove?: () => void;
}

interface ExpoAccelerometerModule {
  isAvailableAsync?: () => Promise<boolean>;
  requestPermissionsAsync?: () => Promise<{ granted?: boolean }>;
  setUpdateInterval?: (intervalMs: number) => void;
  addListener?: (
    cb: (data: { x: number; y: number; z: number }) => void,
  ) => ExpoSubscription;
}

interface ExpoDeviceMotionModule {
  isAvailableAsync?: () => Promise<boolean>;
  requestPermissionsAsync?: () => Promise<{ granted?: boolean }>;
  setUpdateInterval?: (intervalMs: number) => void;
  addListener?: (
    cb: (data: { rotation?: { beta?: number; gamma?: number } }) => void,
  ) => ExpoSubscription;
}

interface ExpoPedometerModule {
  isAvailableAsync?: () => Promise<boolean>;
  requestPermissionsAsync?: () => Promise<{ granted?: boolean }>;
  watchStepCount?: (
    cb: (result: { steps: number }) => void,
  ) => ExpoSubscription;
}

interface ExpoSensorsModule {
  Accelerometer?: ExpoAccelerometerModule;
  DeviceMotion?: ExpoDeviceMotionModule;
  Pedometer?: ExpoPedometerModule;
}

interface ExpoLocationModule {
  Accuracy?: { Balanced?: number };
  requestForegroundPermissionsAsync?: () => Promise<{ status?: string }>;
  watchPositionAsync?: (
    options: {
      accuracy?: number;
      timeInterval?: number;
      distanceInterval?: number;
    },
    cb: (location: { coords?: { speed?: number | null } }) => void,
  ) => Promise<ExpoSubscription>;
}

const ACCEL_WINDOW_SIZE = 12;
const RAD_TO_DEG = 180 / Math.PI;

function optionalRequire<T>(moduleName: string): T | null {
  try {
    // Indirect reference keeps Expo/Metro bundling from failing when optional packages are not installed.
    const dynamicRequire =
      typeof require === "function" ? require : undefined;
    if (!dynamicRequire) {
      return null;
    }
    return dynamicRequire(moduleName) as T;
  } catch {
    return null;
  }
}

function computeStdDev(values: number[]): number | undefined {
  if (values.length < 2) {
    return undefined;
  }
  const mean = values.reduce((acc, v) => acc + v, 0) / values.length;
  const variance =
    values.reduce((acc, v) => acc + (v - mean) * (v - mean), 0) /
    values.length;
  return Math.sqrt(variance);
}

/**
 * Serializes the context payload into an injected JS snippet that dispatches
 * the `dubai:community-context` window CustomEvent inside the Community WebView.
 */
export function buildWebViewContextDispatchScript(
  payload: CommunityContextPayload,
): string {
  const serialized = JSON.stringify(payload);
  return `(function(){try{window.dispatchEvent(new CustomEvent("dubai:community-context",{detail:${serialized}}));}catch(e){}true;})();`;
}

/**
 * Pushes the latest ephemeral foreground context to the Community WebView over
 * both `postMessage` and a DOM `CustomEvent`.
 */
export function publishContextToWebView(
  webViewRef: RefObject<WebView<object> | null>,
  payload: CommunityContextPayload,
): void {
  const webView = webViewRef.current;
  if (!webView) {
    return;
  }
  try {
    webView.postMessage(
      JSON.stringify({ type: "dubai.community.context", payload }),
    );
    webView.injectJavaScript(buildWebViewContextDispatchScript(payload));
  } catch {
    // WebView may be unmounted or mid-reload; safe to ignore.
  }
}

function inactiveClassification(): UserStateClassification {
  return {
    userState: "unknown",
    confidence: 0,
    source: "unavailable",
    asOf: new Date().toISOString(),
  };
}

export function useForegroundContext({
  webViewRef,
  initialEnabled = false,
}: UseForegroundContextOptions): UseForegroundContextResult {
  const [contextAwareEnabled, setContextAwareEnabled] =
    useState(initialEnabled);
  const [manualOverride, setManualOverride] =
    useState<ManualContextOverride | null>(null);
  const [appState, setAppState] = useState<AppStateStatus>(
    () => (AppState.currentState as AppStateStatus | null | undefined) ?? "active",
  );
  const [sensorsAvailable, setSensorsAvailable] = useState(false);
  const [classification, setClassification] = useState<UserStateClassification>(
    () => inactiveClassification(),
  );

  const sampleRef = useRef<ForegroundSample>({
    optIn: false,
    hasPermission: false,
  });
  const accelMagnitudesRef = useRef<number[]>([]);
  const stepWindowStartRef = useRef<number>(Date.now());

  const foregroundActive = appState === "active";

  useEffect(() => {
    const subscription = AppState.addEventListener("change", (nextState) => {
      setAppState(nextState);
    });
    return () => {
      subscription.remove();
    };
  }, []);

  useEffect(() => {
    const shouldSense =
      contextAwareEnabled && foregroundActive && manualOverride === null;

    if (!contextAwareEnabled || !foregroundActive) {
      sampleRef.current = { optIn: false, hasPermission: false };
      accelMagnitudesRef.current = [];
      setSensorsAvailable(false);
      setClassification(inactiveClassification());
      return;
    }

    if (manualOverride !== null) {
      sampleRef.current = { optIn: true, hasPermission: false };
      accelMagnitudesRef.current = [];
      setClassification(buildManualContextClassification(manualOverride));
      return;
    }

    if (!shouldSense) {
      return;
    }

    let cancelled = false;
    const subscriptions: ExpoSubscription[] = [];

    const recompute = (): void => {
      if (cancelled) {
        return;
      }
      setClassification(classifyUserState(sampleRef.current));
    };

    const startForegroundSensors = async (): Promise<void> => {
      const sensors = optionalRequire<ExpoSensorsModule>("expo-sensors");
      const location = optionalRequire<ExpoLocationModule>("expo-location");

      if (!sensors && !location) {
        if (!cancelled) {
          setSensorsAvailable(false);
          sampleRef.current = { optIn: true, hasPermission: false };
          recompute();
        }
        return;
      }

      let anyPermissionGranted = false;
      sampleRef.current = { optIn: true, hasPermission: false };
      accelMagnitudesRef.current = [];
      stepWindowStartRef.current = Date.now();

      try {
        const accel = sensors?.Accelerometer;
        if (accel && (await accel.isAvailableAsync?.())) {
          const perm = accel.requestPermissionsAsync
            ? await accel.requestPermissionsAsync()
            : { granted: true };
          if (!cancelled && perm.granted !== false && accel.addListener) {
            anyPermissionGranted = true;
            accel.setUpdateInterval?.(500);
            subscriptions.push(
              accel.addListener(({ x, y, z }) => {
                const mag = Math.sqrt(x * x + y * y + z * z);
                const buf = accelMagnitudesRef.current;
                buf.push(mag);
                if (buf.length > ACCEL_WINDOW_SIZE) {
                  buf.shift();
                }
                const std = computeStdDev(buf);
                if (std !== undefined) {
                  sampleRef.current = {
                    ...sampleRef.current,
                    hasPermission: true,
                    accelMagnitudeStd: std,
                  };
                  recompute();
                }
              }),
            );
          }
        }
      } catch {
        // Accelerometer optional in Expo Go.
      }

      try {
        const motion = sensors?.DeviceMotion;
        if (motion && (await motion.isAvailableAsync?.())) {
          const perm = motion.requestPermissionsAsync
            ? await motion.requestPermissionsAsync()
            : { granted: true };
          if (!cancelled && perm.granted !== false && motion.addListener) {
            anyPermissionGranted = true;
            motion.setUpdateInterval?.(750);
            subscriptions.push(
              motion.addListener((data) => {
                const beta = data.rotation?.beta;
                if (typeof beta === "number" && Number.isFinite(beta)) {
                  sampleRef.current = {
                    ...sampleRef.current,
                    hasPermission: true,
                    pitchDeg: Math.abs(beta * RAD_TO_DEG),
                  };
                  recompute();
                }
              }),
            );
          }
        }
      } catch {
        // DeviceMotion optional in Expo Go.
      }

      try {
        const pedometer = sensors?.Pedometer;
        if (pedometer && (await pedometer.isAvailableAsync?.())) {
          const perm = pedometer.requestPermissionsAsync
            ? await pedometer.requestPermissionsAsync()
            : { granted: true };
          if (!cancelled && perm.granted !== false && pedometer.watchStepCount) {
            anyPermissionGranted = true;
            subscriptions.push(
              pedometer.watchStepCount(({ steps }) => {
                const elapsedMin = Math.max(
                  (Date.now() - stepWindowStartRef.current) / 60000,
                  1 / 60,
                );
                sampleRef.current = {
                  ...sampleRef.current,
                  hasPermission: true,
                  stepCadencePerMin: steps / elapsedMin,
                };
                recompute();
              }),
            );
          }
        }
      } catch {
        // Pedometer optional in Expo Go.
      }

      try {
        if (
          location?.requestForegroundPermissionsAsync &&
          location?.watchPositionAsync
        ) {
          const perm = await location.requestForegroundPermissionsAsync();
          if (!cancelled && perm.status === "granted") {
            anyPermissionGranted = true;
            const sub = await location.watchPositionAsync(
              {
                accuracy: location.Accuracy?.Balanced,
                timeInterval: 5000,
                distanceInterval: 10,
              },
              (pos) => {
                // Only extract scalar speed; raw lat/lng coordinates are discarded immediately.
                const rawSpeed = pos.coords?.speed;
                const speedMps =
                  typeof rawSpeed === "number" &&
                  Number.isFinite(rawSpeed) &&
                  rawSpeed >= 0
                    ? rawSpeed
                    : undefined;
                sampleRef.current = {
                  ...sampleRef.current,
                  hasPermission: true,
                  speedMps,
                };
                recompute();
              },
            );
            if (cancelled) {
              sub.remove?.();
            } else {
              subscriptions.push(sub);
            }
          }
        }
      } catch {
        // Foreground location optional in Expo Go.
      }

      if (!cancelled) {
        setSensorsAvailable(anyPermissionGranted);
        sampleRef.current = {
          ...sampleRef.current,
          optIn: true,
          hasPermission: anyPermissionGranted,
        };
        recompute();
      }
    };

    void startForegroundSensors();

    return () => {
      cancelled = true;
      for (const sub of subscriptions) {
        try {
          sub.remove?.();
        } catch {
          // Ignore cleanup failures.
        }
      }
    };
  }, [contextAwareEnabled, foregroundActive, manualOverride]);

  const payload = useMemo<CommunityContextPayload>(
    () => ({
      ...classification,
      contextAwareEnabled,
      override: manualOverride,
      foregroundActive,
    }),
    [classification, contextAwareEnabled, foregroundActive, manualOverride],
  );

  const syncToWebView = useCallback(() => {
    publishContextToWebView(webViewRef, payload);
  }, [payload, webViewRef]);

  useEffect(() => {
    syncToWebView();
  }, [syncToWebView]);

  const privacyNote = useMemo(() => snapAreaPromptNote(), []);

  return {
    contextAwareEnabled,
    setContextAwareEnabled,
    manualOverride,
    setManualOverride,
    classification,
    payload,
    sensorsAvailable,
    privacyNote,
    syncToWebView,
  };
}
