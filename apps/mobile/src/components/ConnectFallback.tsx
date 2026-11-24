import React, { useState } from "react";
import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { localhostWarning } from "../lib/api";
import { DemoPill } from "./DemoPill";

export function ConnectFallback({
  apiBaseUrl,
  onApiBaseUrlChange,
}: {
  apiBaseUrl: string;
  onApiBaseUrlChange: (url: string) => void;
}) {
  const [draft, setDraft] = useState(apiBaseUrl);
  const warning = localhostWarning(draft);

  return (
    <View style={styles.page} testID="connect-fallback">
      <DemoPill />
      <Text style={styles.title}>Connect</Text>
      <Text style={styles.body}>
        Settings for this phone. Google, WhatsApp, and YouTube onboarding arrive with the Connect screen. Nothing here is connected yet.
      </Text>
      <Text style={styles.label}>API base URL</Text>
      <TextInput
        autoCapitalize="none"
        autoCorrect={false}
        onChangeText={setDraft}
        placeholder="http://192.168.1.20:8000"
        placeholderTextColor={colors.muted}
        style={styles.input}
        testID="api-base-input"
        value={draft}
      />
      {warning ? (
        <Text style={styles.warning} testID="localhost-warning">
          {warning}
        </Text>
      ) : null}
      <Pressable
        accessibilityRole="button"
        onPress={() => onApiBaseUrlChange(draft)}
        style={styles.save}
        testID="save-api-base"
      >
        <Text style={styles.saveText}>Save API URL</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  page: {
    ...noShadow,
    backgroundColor: colors.canvas,
    gap: spacing.md,
    padding: spacing.lg,
  },
  title: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.title,
  },
  body: {
    color: colors.ink,
    fontSize: typography.body,
    lineHeight: 22,
  },
  label: {
    color: colors.muted,
    fontSize: typography.caption,
    fontWeight: "700",
    marginTop: spacing.md,
  },
  input: {
    ...noShadow,
    borderColor: colors.border,
    borderRadius: radii.chip,
    borderWidth: 1,
    color: colors.ink,
    fontSize: typography.body,
    padding: spacing.md,
  },
  warning: {
    color: colors.themes.gaming,
    fontSize: typography.caption,
  },
  save: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.gold.primary,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  saveText: {
    color: colors.canvas,
    fontWeight: "700",
  },
});
