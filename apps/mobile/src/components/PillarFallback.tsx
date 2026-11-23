import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, noShadow, spacing, typography } from "@dubai-io/design-tokens";
import { DemoPill } from "./DemoPill";

export function PillarFallback({ title, body }: { title: string; body: string }) {
  return (
    <View style={styles.page} testID={`pillar-fallback-${title}`}>
      <DemoPill />
      <Text style={styles.title}>{title}</Text>
      <Text style={styles.body}>{body}</Text>
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
});
