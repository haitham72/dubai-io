import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { buildLanHint } from "../config/url";

export interface OfflineFallbackProps {
  targetUrl: string;
  errorDetail: string | null;
  onRetry: () => void;
  onOpenSettings: () => void;
}

export function OfflineFallback({
  targetUrl,
  errorDetail,
  onRetry,
  onOpenSettings,
}: OfflineFallbackProps): React.JSX.Element {
  return (
    <View style={styles.container} testID="offline-fallback">
      <View style={styles.card}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>Connection Needed</Text>
        </View>
        <Text style={styles.title}>Cannot reach Community</Text>
        <Text style={styles.body}>
          {errorDetail || "The Community server did not respond."}
        </Text>

        <View style={styles.urlBox}>
          <Text style={styles.urlLabel}>Target URL</Text>
          <Text style={styles.urlValue} selectable>
            {targetUrl}
          </Text>
        </View>

        <Text style={styles.hint}>{buildLanHint(targetUrl)}</Text>

        <View style={styles.actions}>
          <Pressable
            onPress={onRetry}
            style={({ pressed }) => [
              styles.primaryButton,
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Retry connection"
          >
            <Text style={styles.primaryLabel}>Retry</Text>
          </Pressable>

          <Pressable
            onPress={onOpenSettings}
            style={({ pressed }) => [
              styles.secondaryButton,
              pressed && styles.pressed,
            ]}
            accessibilityRole="button"
            accessibilityLabel="Edit Server URL"
          >
            <Text style={styles.secondaryLabel}>Server URL</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#f3f6f8",
    justifyContent: "center",
    padding: 20,
  },
  card: {
    backgroundColor: "#ffffff",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#e4ebf0",
    padding: 22,
  },
  badge: {
    alignSelf: "flex-start",
    backgroundColor: "#e7f5f7",
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    marginBottom: 12,
  },
  badgeText: {
    color: "#128c9b",
    fontSize: 12,
    fontWeight: "600",
  },
  title: {
    color: "#15202b",
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 8,
  },
  body: {
    color: "#6a7784",
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 14,
  },
  urlBox: {
    backgroundColor: "#f3f6f8",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#e4ebf0",
    padding: 12,
    marginBottom: 12,
  },
  urlLabel: {
    color: "#6a7784",
    fontSize: 11,
    fontWeight: "600",
    textTransform: "uppercase",
    marginBottom: 4,
  },
  urlValue: {
    color: "#15202b",
    fontSize: 13,
    fontWeight: "600",
  },
  hint: {
    color: "#3d5563",
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 18,
  },
  actions: {
    flexDirection: "row",
    gap: 10,
  },
  primaryButton: {
    flex: 1,
    backgroundColor: "#128c9b",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  primaryLabel: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "600",
  },
  secondaryButton: {
    backgroundColor: "#eef3f6",
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  secondaryLabel: {
    color: "#15202b",
    fontSize: 15,
    fontWeight: "600",
  },
  pressed: {
    opacity: 0.85,
  },
});
