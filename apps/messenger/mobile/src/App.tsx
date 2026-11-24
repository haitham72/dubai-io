import React, { useCallback, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaProvider, SafeAreaView } from "react-native-safe-area-context";
import { WebView, type WebViewMessageEvent } from "react-native-webview";
import type { ShouldStartLoadRequest, WebViewErrorEvent, WebViewHttpErrorEvent } from "react-native-webview/lib/WebViewTypes";
import { StatusBar } from "expo-status-bar";
import { Audio } from "expo-av";
import * as ImagePicker from "expo-image-picker";

import {
  buildWebViewBridgeScript,
  parseBridgeRequest,
  serializeBridgeEventToJs,
  type BridgePickedAsset,
  type BridgeResponse,
  type MediaPickFilter,
} from "./bridge";
import {
  deriveMessengerOrigin,
  deriveWsUrl,
  getConfiguredMessengerUrl,
  isAllowedMessengerNavigation,
  normalizeMessengerUrl,
  shouldOpenExternally,
} from "./config";

function mapMediaTypes(filter?: MediaPickFilter): ImagePicker.MediaType[] {
  if (filter === "videos") return ["videos"];
  if (filter === "all") return ["images", "videos"];
  return ["images"];
}

function mapPickerAssets(assets: ImagePicker.ImagePickerAsset[] | null | undefined): BridgePickedAsset[] {
  if (!assets) return [];
  return assets.map((asset) => ({
    uri: asset.uri,
    mimeType: asset.mimeType ?? undefined,
    width: asset.width,
    height: asset.height,
    fileName: asset.fileName ?? undefined,
    base64: asset.base64 ?? undefined,
  }));
}

export default function App() {
  const initialUrl = useMemo(() => getConfiguredMessengerUrl(process.env as Record<string, string | undefined>), []);
  const [activeUrl, setActiveUrl] = useState<string>(initialUrl);
  const [draftUrl, setDraftUrl] = useState<string>(initialUrl);
  const [showUrlBar, setShowUrlBar] = useState<boolean>(false);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [reloadNonce, setReloadNonce] = useState<number>(0);

  const webViewRef = useRef<WebView<unknown> | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);

  const allowedOrigin = useMemo(() => deriveMessengerOrigin(activeUrl), [activeUrl]);
  const wsPreviewUrl = useMemo(() => deriveWsUrl(activeUrl), [activeUrl]);
  const injectedBridgeJs = useMemo(() => buildWebViewBridgeScript(), []);

  const postToWebView = useCallback((payload: BridgeResponse) => {
    webViewRef.current?.injectJavaScript(serializeBridgeEventToJs(payload));
  }, []);

  const handleApplyUrl = useCallback(() => {
    try {
      const normalized = normalizeMessengerUrl(draftUrl);
      setUrlError(null);
      setLoadError(null);
      setActiveUrl(normalized);
      setDraftUrl(normalized);
      setShowUrlBar(false);
      setReloadNonce((n) => n + 1);
    } catch (err) {
      setUrlError(err instanceof Error ? err.message : "Invalid URL");
    }
  }, [draftUrl]);

  const handleRetry = useCallback(() => {
    setLoadError(null);
    setIsLoading(true);
    setReloadNonce((n) => n + 1);
    webViewRef.current?.reload();
  }, []);

  const handleShouldStartLoad = useCallback(
    (request: ShouldStartLoadRequest): boolean => {
      if (isAllowedMessengerNavigation(request.url, allowedOrigin)) {
        return true;
      }
      if (shouldOpenExternally(request.url, allowedOrigin)) {
        void Linking.openURL(request.url).catch(() => undefined);
      }
      return false;
    },
    [allowedOrigin],
  );

  const handleMicRequest = useCallback(
    async (requestId?: string) => {
      const perm = await Audio.requestPermissionsAsync();
      if (perm.granted) {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
      }
      postToWebView({
        type: "MIC_PERMISSION_RESULT",
        requestId,
        granted: perm.granted,
        status: perm.status,
        canAskAgain: perm.canAskAgain,
      });
    },
    [postToWebView],
  );

  const handleStartVoiceRecording = useCallback(
    async (requestId?: string) => {
      try {
        const perm = await Audio.requestPermissionsAsync();
        if (!perm.granted) {
          postToWebView({
            type: "VOICE_RECORDING_RESULT",
            requestId,
            status: "error",
            error: "Microphone permission denied",
          });
          return;
        }
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: true,
          playsInSilentModeIOS: true,
        });
        if (recordingRef.current) {
          await recordingRef.current.stopAndUnloadAsync().catch(() => undefined);
          recordingRef.current = null;
        }
        const { recording } = await Audio.Recording.createAsync(
          Audio.RecordingOptionsPresets.HIGH_QUALITY,
        );
        recordingRef.current = recording;
        postToWebView({
          type: "VOICE_RECORDING_RESULT",
          requestId,
          status: "started",
        });
      } catch (err) {
        postToWebView({
          type: "VOICE_RECORDING_RESULT",
          requestId,
          status: "error",
          error: err instanceof Error ? err.message : "Failed to start recording",
        });
      }
    },
    [postToWebView],
  );

  const handleStopVoiceRecording = useCallback(
    async (requestId?: string) => {
      const activeRecording = recordingRef.current;
      recordingRef.current = null;
      if (!activeRecording) {
        postToWebView({
          type: "VOICE_RECORDING_RESULT",
          requestId,
          status: "error",
          error: "No active recording",
        });
        return;
      }
      try {
        const status = await activeRecording.getStatusAsync();
        await activeRecording.stopAndUnloadAsync();
        await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
        postToWebView({
          type: "VOICE_RECORDING_RESULT",
          requestId,
          status: "stopped",
          uri: activeRecording.getURI() ?? undefined,
          durationMs: status.durationMillis,
        });
      } catch (err) {
        postToWebView({
          type: "VOICE_RECORDING_RESULT",
          requestId,
          status: "error",
          error: err instanceof Error ? err.message : "Failed to stop recording",
        });
      }
    },
    [postToWebView],
  );

  const handlePickMedia = useCallback(
    async (
      mode: "media" | "sticker",
      options: { requestId?: string; allowsEditing?: boolean; mediaTypes?: MediaPickFilter },
    ) => {
      try {
        const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!perm.granted) {
          postToWebView({
            type: "MEDIA_PICKED",
            requestId: options.requestId,
            mode,
            canceled: true,
            assets: [],
            error: "Photo library permission denied",
          });
          return;
        }
        const result = await ImagePicker.launchImageLibraryAsync({
          mediaTypes: mode === "sticker" ? ["images"] : mapMediaTypes(options.mediaTypes),
          allowsEditing: mode === "sticker" ? true : Boolean(options.allowsEditing),
          aspect: mode === "sticker" ? [1, 1] : undefined,
          quality: 0.85,
          base64: true,
        });
        postToWebView({
          type: "MEDIA_PICKED",
          requestId: options.requestId,
          mode,
          canceled: result.canceled,
          assets: mapPickerAssets(result.assets),
        });
      } catch (err) {
        postToWebView({
          type: "MEDIA_PICKED",
          requestId: options.requestId,
          mode,
          canceled: true,
          assets: [],
          error: err instanceof Error ? err.message : "Failed to open media picker",
        });
      }
    },
    [postToWebView],
  );

  const handleBridgeMessage = useCallback(
    (event: WebViewMessageEvent) => {
      const req = parseBridgeRequest(event.nativeEvent.data);
      if (!req) return;

      switch (req.type) {
        case "REQUEST_MIC":
          void handleMicRequest(req.requestId);
          break;
        case "START_VOICE_RECORDING":
          void handleStartVoiceRecording(req.requestId);
          break;
        case "STOP_VOICE_RECORDING":
          void handleStopVoiceRecording(req.requestId);
          break;
        case "PICK_MEDIA":
          void handlePickMedia("media", req);
          break;
        case "PICK_STICKER":
          void handlePickMedia("sticker", { requestId: req.requestId });
          break;
      }
    },
    [handleMicRequest, handlePickMedia, handleStartVoiceRecording, handleStopVoiceRecording],
  );

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.root} edges={["top", "left", "right", "bottom"]}>
        <StatusBar style="dark" />
        <View style={styles.topBar}>
          <Text style={styles.brand}>Messenger</Text>
          <View style={styles.topActions}>
            <Pressable
              accessibilityLabel="Configure LAN URL"
              onPress={() => setShowUrlBar((v) => !v)}
              style={styles.pillButton}
            >
              <Text style={styles.pillText}>{showUrlBar ? "Hide URL" : "LAN URL"}</Text>
            </Pressable>
            <Pressable
              accessibilityLabel="Reload Messenger"
              onPress={handleRetry}
              style={styles.pillButton}
            >
              <Text style={styles.pillText}>Reload</Text>
            </Pressable>
          </View>
        </View>

        {showUrlBar && (
          <View style={styles.urlDrawer}>
            <Text style={styles.urlLabel}>Messenger URL (WS: {wsPreviewUrl})</Text>
            <View style={styles.urlRow}>
              <TextInput
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                onChangeText={setDraftUrl}
                placeholder="http://192.168.1.50:5173"
                style={styles.urlInput}
                value={draftUrl}
              />
              <Pressable onPress={handleApplyUrl} style={styles.primaryButton}>
                <Text style={styles.primaryButtonText}>Connect</Text>
              </Pressable>
            </View>
            {urlError ? <Text style={styles.errorHint}>{urlError}</Text> : null}
          </View>
        )}

        <View style={styles.webContainer}>
          {loadError ? (
            <View style={styles.offlineCard}>
              <Text style={styles.offlineTitle}>Messenger is unreachable</Text>
              <Text style={styles.offlineSub}>{loadError}</Text>
              <Text style={styles.offlineUrl}>{activeUrl}</Text>
              <View style={styles.offlineActions}>
                <Pressable onPress={handleRetry} style={styles.primaryButton}>
                  <Text style={styles.primaryButtonText}>Retry</Text>
                </Pressable>
                <Pressable onPress={() => setShowUrlBar(true)} style={styles.secondaryButton}>
                  <Text style={styles.secondaryButtonText}>Change LAN URL</Text>
                </Pressable>
              </View>
            </View>
          ) : (
            <WebView<unknown>
              key={`${activeUrl}#${reloadNonce}`}
              ref={webViewRef}
              source={{ uri: activeUrl }}
              originWhitelist={[allowedOrigin, "about:blank"]}
              sharedCookiesEnabled
              javaScriptEnabled
              domStorageEnabled
              allowsInlineMediaPlayback
              mediaPlaybackRequiresUserAction={false}
              injectedJavaScriptBeforeContentLoaded={injectedBridgeJs}
              onShouldStartLoadWithRequest={handleShouldStartLoad}
              onMessage={handleBridgeMessage}
              onLoadStart={() => setIsLoading(true)}
              onLoadEnd={() => setIsLoading(false)}
              onError={(e: WebViewErrorEvent) => {
                setIsLoading(false);
                setLoadError(e.nativeEvent.description || "Connection error");
              }}
              onHttpError={(e: WebViewHttpErrorEvent) => {
                if (e.nativeEvent.statusCode >= 500) {
                  setIsLoading(false);
                  setLoadError(`Server returned HTTP ${e.nativeEvent.statusCode}`);
                }
              }}
              style={styles.webView}
            />
          )}

          {isLoading && !loadError ? (
            <View pointerEvents="none" style={styles.loadingBadge}>
              <ActivityIndicator size="small" color="#2563EB" />
            </View>
          ) : null}
        </View>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#eef3fa",
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "#eef3fa",
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#cbd5e1",
  },
  brand: {
    fontSize: 16,
    fontWeight: "700",
    color: "#0f172a",
  },
  topActions: {
    flexDirection: "row",
    gap: 8,
  },
  pillButton: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: "#ffffff",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "#cbd5e1",
  },
  pillText: {
    fontSize: 12,
    fontWeight: "600",
    color: "#1e293b",
  },
  urlDrawer: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: "#ffffff",
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: "#cbd5e1",
    gap: 6,
  },
  urlLabel: {
    fontSize: 12,
    color: "#475569",
  },
  urlRow: {
    flexDirection: "row",
    gap: 8,
    alignItems: "center",
  },
  urlInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 8,
    fontSize: 14,
    color: "#0f172a",
    backgroundColor: "#f8fafc",
  },
  errorHint: {
    fontSize: 12,
    color: "#dc2626",
  },
  webContainer: {
    flex: 1,
    position: "relative",
  },
  webView: {
    flex: 1,
    backgroundColor: "#eef3fa",
  },
  loadingBadge: {
    position: "absolute",
    top: 12,
    right: 12,
    backgroundColor: "rgba(255,255,255,0.92)",
    borderRadius: 999,
    padding: 8,
  },
  offlineCard: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 10,
  },
  offlineTitle: {
    fontSize: 20,
    fontWeight: "700",
    color: "#0f172a",
    textAlign: "center",
  },
  offlineSub: {
    fontSize: 14,
    color: "#475569",
    textAlign: "center",
  },
  offlineUrl: {
    fontSize: 12,
    color: "#64748b",
    textAlign: "center",
  },
  offlineActions: {
    flexDirection: "row",
    gap: 10,
    marginTop: 8,
  },
  primaryButton: {
    backgroundColor: "#2563EB",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 10,
  },
  primaryButtonText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "600",
  },
  secondaryButton: {
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#cbd5e1",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 10,
  },
  secondaryButtonText: {
    color: "#1e293b",
    fontSize: 14,
    fontWeight: "600",
  },
});
