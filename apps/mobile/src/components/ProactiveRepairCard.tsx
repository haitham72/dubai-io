import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import type { RepairPing } from "../lib/types";
import { DemoPill } from "./DemoPill";

export function ProactiveRepairCard({
  ping,
  accepted,
  onAccept,
}: {
  ping: RepairPing;
  accepted: boolean;
  onAccept: () => void;
}) {
  return (
    <View style={styles.card} testID="repair-card">
      {ping.demo ? <DemoPill /> : null}
      <Text style={styles.kicker}>{ping.title}</Text>
      <Text style={styles.body}>{ping.body}</Text>
      <Pressable
        accessibilityRole="button"
        disabled={accepted}
        onPress={onAccept}
        style={[styles.button, accepted && styles.buttonDone]}
        testID="apology-accepted"
      >
        <Text style={styles.buttonText}>{accepted ? "Apology Accepted 👍" : "Apology Accepted 👍"}</Text>
      </Pressable>
      {accepted ? (
        <Text style={styles.note}>Acknowledged on this device. Memory was not changed until the service confirms it.</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...noShadow,
    backgroundColor: colors.repairSurface,
    borderColor: colors.gold.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  kicker: {
    color: colors.gold.metallic,
    fontSize: typography.caption,
    fontWeight: "700",
  },
  body: {
    color: colors.ink,
    fontSize: typography.body,
    lineHeight: 22,
  },
  button: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.gold.primary,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  buttonDone: {
    backgroundColor: colors.gold.metallic,
  },
  buttonText: {
    color: colors.canvas,
    fontWeight: "700",
  },
  note: {
    color: colors.muted,
    fontSize: typography.caption,
  },
});
