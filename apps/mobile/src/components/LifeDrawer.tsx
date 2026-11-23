import React from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { lifeThemes, threadHistory } from "../lib/fixtures";
import { DemoPill } from "./DemoPill";

export function LifeDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <View style={styles.scrim} testID="life-drawer">
      <View style={styles.sheet}>
        <View style={styles.header}>
          <Text style={styles.brand}>Dubai-io Quest AI Companion</Text>
          <Pressable accessibilityRole="button" onPress={onClose} testID="life-drawer-close">
            <Text style={styles.close}>✕</Text>
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={styles.content}>
          <DemoPill />
          <Text style={styles.section}>My Dubai-io</Text>
          {lifeThemes.map((item) => (
            <View key={item.id} style={styles.row}>
              <Text style={styles.label}>{item.label}</Text>
              <Text style={styles.detail}>{item.detail}</Text>
            </View>
          ))}
          <Text style={styles.section}>History</Text>
          {threadHistory.map((item) => (
            <View key={item.id} style={styles.row}>
              <Text style={styles.label}>{item.label}</Text>
              <Text style={styles.detail}>{item.detail}</Text>
            </View>
          ))}
          <Text style={styles.note}>These rows are demo data until the service lists real threads.</Text>
        </ScrollView>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scrim: {
    ...noShadow,
    backgroundColor: "rgba(30, 32, 34, 0.28)",
    bottom: 0,
    left: 0,
    position: "absolute",
    right: 0,
    top: 0,
    zIndex: 5,
  },
  sheet: {
    ...noShadow,
    backgroundColor: colors.canvas,
    borderColor: colors.border,
    borderRightWidth: 0,
    borderWidth: 1,
    bottom: 0,
    position: "absolute",
    right: 0,
    top: 0,
    width: "86%",
  },
  header: {
    alignItems: "center",
    borderBottomColor: colors.borderHairline,
    borderBottomWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    padding: spacing.lg,
  },
  brand: {
    color: colors.ink,
    flex: 1,
    fontFamily: typography.serif,
    fontSize: typography.body,
  },
  close: {
    color: colors.ink,
    fontSize: 18,
    paddingHorizontal: spacing.sm,
  },
  content: {
    gap: spacing.sm,
    padding: spacing.lg,
  },
  section: {
    color: colors.muted,
    fontSize: typography.caption,
    fontWeight: "700",
    marginTop: spacing.md,
  },
  row: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.borderHairline,
    borderRadius: radii.chip,
    borderWidth: 1,
    padding: spacing.md,
  },
  label: {
    color: colors.ink,
    fontSize: typography.body,
  },
  detail: {
    color: colors.muted,
    fontSize: typography.caption,
    marginTop: 2,
  },
  note: {
    color: colors.muted,
    fontSize: typography.caption,
    marginTop: spacing.md,
  },
});
