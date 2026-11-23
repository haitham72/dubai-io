import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";

/** Renders only when a memory write was confirmed. `confirmed` false returns nothing. */
export function MemoryIngestedBadge({ confirmed, detail }: { confirmed: boolean; detail?: string }) {
  if (!confirmed) return null;
  return (
    <View style={styles.badge} testID="memory-ingested-badge" accessibilityRole="text">
      <Text style={styles.text}>✓ Ingested into Temporal Memory</Text>
      {detail ? <Text style={styles.detail}>{detail}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.canvas,
    borderColor: colors.ingested,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs,
  },
  text: {
    color: colors.ingested,
    fontSize: typography.caption,
    fontWeight: "700",
  },
  detail: {
    color: colors.muted,
    fontSize: 11,
    marginTop: 2,
  },
});
