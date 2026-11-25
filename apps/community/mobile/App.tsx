import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Constants from "expo-constants";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { WebView, type WebViewNavigation, type WebViewProps } from "react-native-webview";
import { OfflineFallback } from "./src/components/OfflineFallback";
import { UrlBarModal } from "./src/components/UrlBarModal";
import {
  classifyNavigation,
  getConfiguredCommunityUrl,
} from "./src/config/url";
import { useForegroundContext } from "./src/context/useForegroundContext";
import type { ManualContextOverride } from "./src/context/userStateClassifier";
import {
  clearUrlOverride,
  loadUrlOverride,
  saveUrlOverride,
} from "./src/storage/urlOverride";

const OVERRIDE_OPTIONS: ReadonlyArray<{
  label: string;
  value: ManualContextOverride | null;
}> = [
  { label: "Adaptive (Auto)", value: null },
  { label: "At desk / sitting", value: "sitting" },
  { label: "Walking", value: "walking" },
  { label: "Commuting / driving", value: "driving" },
  { label: "Paused", value: "paused" },
];

function CommunityShellScreen(): React.JSX.Element {
  const defaultUrl = useMemo(
    () =>
      getConfiguredCommunityUrl(
        process.env.EXPO_PUBLIC_COMMUNITY_URL,
        Constants.expoConfig?.extra?.communityUrl as string | undefined,
      ),
    [],
  );

  const webViewRef = useRef<WebView<object>>(null);
  const [activeUrl, setActiveUrl] = useState<string>(defaultUrl);
  const [reloadNonce, setReloadNonce] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [contextModalOpen, setContextModalOpen] = useState(false);

  const {
    contextAwareEnabled,
    setContextAwareEnabled,
    manualOverride,
    setManualOverride,
    classification,
    privacyNote,
    syncToWebView,
  } = useForegroundContext({ webViewRef });

  const isAdaptiveActive =
    contextAwareEnabled && manualOverride !== "paused";

  useEffect(() => {
    let mounted = true;
    void loadUrlOverride().then((override) => {
      if (mounted && override) {
        setActiveUrl(override);
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const handleRetry = useCallback(() => {
    setErrorDetail(null);
    setIsLoading(true);
    setReloadNonce((n) => n + 1);
    webViewRef.current?.reload();
  }, []);

  const handleSaveUrl = useCallback(async (nextUrl: string) => {
    await saveUrlOverride(nextUrl);
    setActiveUrl(nextUrl);
    setErrorDetail(null);
    setIsLoading(true);
    setReloadNonce((n) => n + 1);
    setSettingsOpen(false);
  }, []);

  const handleResetUrl = useCallback(async () => {
    await clearUrlOverride();
    setActiveUrl(defaultUrl);
    setErrorDetail(null);
    setIsLoading(true);
    setReloadNonce((n) => n + 1);
    setSettingsOpen(false);
  }, [defaultUrl]);

  const handleShouldStartLoad = useCallback(
    (request: WebViewNavigation): boolean => {
      const action = classifyNavigation(request.url, activeUrl);
      if (action === "in-app") {
        return true;
      }
      if (action === "external") {
        void Linking.openURL(request.url).catch(() => undefined);
      }
      return false;
    },
    [activeUrl],
  );

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "left", "right"]}>
      <StatusBar style="dark" />

      <View style={styles.topBar}>
        <View style={styles.brandRow}>
          <View style={styles.brandDot} />
          <Text style={styles.brandTitle} numberOfLines={1}>
            Dubai-io Community
          </Text>
          {isLoading && !errorDetail ? (
            <ActivityIndicator size="small" color="#128c9b" />
          ) : null}
        </View>

        <View style={styles.topActions}>
          <Pressable
            onPress={() => setContextModalOpen(true)}
            style={[
              styles.contextPill,
              isAdaptiveActive ? styles.contextPillActive : null,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Adaptive foreground context settings"
          >
            <Text
              style={[
                styles.contextPillText,
                isAdaptiveActive ? styles.contextPillTextActive : null,
              ]}
            >
              {isAdaptiveActive ? "Context: Adaptive" : "Context: Off"}
            </Text>
          </Pressable>
          <Pressable
            onPress={handleRetry}
            style={styles.topButton}
            accessibilityRole="button"
            accessibilityLabel="Reload Community"
          >
            <Text style={styles.topButtonText}>Reload</Text>
          </Pressable>
          <Pressable
            onPress={() => setSettingsOpen(true)}
            style={styles.topButton}
            accessibilityRole="button"
            accessibilityLabel="Server URL settings"
          >
            <Text style={styles.topButtonText}>URL</Text>
          </Pressable>
        </View>
      </View>

      {errorDetail ? (
        <OfflineFallback
          targetUrl={activeUrl}
          errorDetail={errorDetail}
          onRetry={handleRetry}
          onOpenSettings={() => setSettingsOpen(true)}
        />
      ) : (
        <WebView<object>
          key={`${activeUrl}:${reloadNonce}`}
          ref={webViewRef}
          source={{ uri: activeUrl }}
          style={styles.webview}
          sharedCookiesEnabled
          thirdPartyCookiesEnabled
          pullToRefreshEnabled
          allowsBackForwardNavigationGestures
          onLoadStart={() => setIsLoading(true)}
          onLoadEnd={() => {
            setIsLoading(false);
            syncToWebView();
          }}
          onShouldStartLoadWithRequest={handleShouldStartLoad}
          onError={(event: Parameters<NonNullable<WebViewProps["onError"]>>[0]) => {
            setIsLoading(false);
            setErrorDetail(
              event.nativeEvent.description ||
                "Could not connect to Community server.",
            );
          }}
          onHttpError={(
            event: Parameters<NonNullable<WebViewProps["onHttpError"]>>[0],
          ) => {
            if (event.nativeEvent.statusCode >= 500) {
              setIsLoading(false);
              setErrorDetail(
                `Server returned HTTP ${event.nativeEvent.statusCode}.`,
              );
            }
          }}
        />
      )}

      <UrlBarModal
        visible={settingsOpen}
        currentUrl={activeUrl}
        defaultUrl={defaultUrl}
        onSave={(url) => void handleSaveUrl(url)}
        onReset={() => void handleResetUrl()}
        onClose={() => setSettingsOpen(false)}
      />

      <Modal
        visible={contextModalOpen}
        animationType="slide"
        transparent
        onRequestClose={() => setContextModalOpen(false)}
      >
        <View style={styles.modalBackdrop}>
          <View style={styles.modalSheet}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Foreground Context</Text>
              <Pressable
                onPress={() => {
                  const next = !contextAwareEnabled;
                  setContextAwareEnabled(next);
                  if (next && manualOverride === "paused") {
                    setManualOverride(null);
                  }
                }}
                style={[
                  styles.contextPill,
                  contextAwareEnabled ? styles.contextPillActive : null,
                ]}
              >
                <Text
                  style={[
                    styles.contextPillText,
                    contextAwareEnabled ? styles.contextPillTextActive : null,
                  ]}
                >
                  {contextAwareEnabled ? "Enabled" : "Off"}
                </Text>
              </Pressable>
            </View>

            <Text style={styles.modalNote}>{privacyNote}</Text>

            <Text style={styles.modalSectionLabel}>
              Session State: {classification.userState} (
              {classification.source}, {Math.round(classification.confidence * 100)}
              %)
            </Text>

            <View style={styles.overrideList}>
              {OVERRIDE_OPTIONS.map((option) => {
                const selected =
                  contextAwareEnabled && manualOverride === option.value;
                return (
                  <Pressable
                    key={option.label}
                    onPress={() => {
                      if (option.value === "paused") {
                        setManualOverride("paused");
                      } else {
                        setContextAwareEnabled(true);
                        setManualOverride(option.value);
                      }
                    }}
                    style={[
                      styles.overrideChip,
                      selected ? styles.overrideChipActive : null,
                    ]}
                  >
                    <Text
                      style={[
                        styles.overrideChipText,
                        selected ? styles.overrideChipTextActive : null,
                      ]}
                    >
                      {option.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            <Pressable
              onPress={() => setContextModalOpen(false)}
              style={styles.modalCloseBtn}
            >
              <Text style={styles.modalCloseText}>Done</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

export default function App(): React.JSX.Element {
  return (
    <SafeAreaProvider>
      <CommunityShellScreen />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#ffffff",
  },
  topBar: {
    height: 44,
    paddingHorizontal: 14,
    backgroundColor: "#ffffff",
    borderBottomWidth: 1,
    borderBottomColor: "#e4ebf0",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brandRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    flex: 1,
  },
  brandDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: "#128c9b",
  },
  brandTitle: {
    color: "#15202b",
    fontSize: 15,
    fontWeight: "700",
    flexShrink: 1,
  },
  topActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  contextPill: {
    backgroundColor: "#eef3f6",
    paddingHorizontal: 9,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#d5e0e7",
  },
  contextPillActive: {
    backgroundColor: "#e2f5f7",
    borderColor: "#128c9b",
  },
  contextPillText: {
    color: "#3d5563",
    fontSize: 11,
    fontWeight: "600",
  },
  contextPillTextActive: {
    color: "#0e6d79",
  },
  topButton: {
    backgroundColor: "#eef3f6",
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
  },
  topButtonText: {
    color: "#15202b",
    fontSize: 12,
    fontWeight: "600",
  },
  webview: {
    flex: 1,
    backgroundColor: "#f3f6f8",
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(21, 32, 43, 0.45)",
    justifyContent: "flex-end",
  },
  modalSheet: {
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 32,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 10,
  },
  modalTitle: {
    color: "#15202b",
    fontSize: 18,
    fontWeight: "700",
  },
  modalNote: {
    color: "#3d5563",
    fontSize: 12,
    lineHeight: 17,
    backgroundColor: "#f3f6f8",
    borderRadius: 10,
    padding: 10,
    marginBottom: 12,
  },
  modalSectionLabel: {
    color: "#15202b",
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 8,
  },
  overrideList: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 8,
    marginBottom: 16,
  },
  overrideChip: {
    backgroundColor: "#eef3f6",
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: "#e4ebf0",
  },
  overrideChipActive: {
    backgroundColor: "#128c9b",
    borderColor: "#128c9b",
  },
  overrideChipText: {
    color: "#15202b",
    fontSize: 12,
    fontWeight: "600",
  },
  overrideChipTextActive: {
    color: "#ffffff",
  },
  modalCloseBtn: {
    backgroundColor: "#15202b",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  modalCloseText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "600",
  },
});
