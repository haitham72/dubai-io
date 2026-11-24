import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";

export function DemoPill({ label = "Demo data" }: { label?: string }) {
  return (
    <View style={styles.pill} accessibilityRole="text">
      <Text style={styles.label}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  pill: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.gold.surface,
    borderColor: colors.gold.border,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  label: {
    color: colors.gold.primary,
    fontFamily: typography.sans,
    fontSize: typography.caption,
    fontWeight: "600",
  },
});
