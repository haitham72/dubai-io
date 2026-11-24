import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
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
import {
  clearUrlOverride,
  loadUrlOverride,
  saveUrlOverride,
} from "./src/storage/urlOverride";

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
          onLoadEnd={() => setIsLoading(false)}
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
  },
  topActions: {
    flexDirection: "row",
    gap: 8,
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
});
