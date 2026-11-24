import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { DemoPill } from "../../components/DemoPill";
import {
  LIFE_SPINES, OWNER_HOOK_FACTS, RISING_INTEREST, RULE9_HELD_BACK, SIGNAL_MIX,
} from "../connect/completeness";

export function UserAnalyticsCard({ demo }: { demo: boolean }) {
  return (
    <View style={styles.card} testID="user-analytics">
      {demo ? <DemoPill /> : null}
      <Text style={styles.title}>User analytics</Text>
      <Text style={styles.section}>Life-theme distribution</Text>
      {LIFE_SPINES.map((spine) => (
        <Text key={spine.id} testID={`spine-${spine.id}`}>
          {spine.label} · {spine.count}
        </Text>
      ))}
      <Text testID="rising-interests">{RISING_INTEREST}</Text>
      <Text style={styles.section}>Cross-source signal mix</Text>
      {SIGNAL_MIX.map((row) => (
        <Text key={row.source} testID={`mix-${row.source}`}>{row.source}: {row.count}</Text>
      ))}
      <Text testID="rule9-shield">
        {RULE9_HELD_BACK} sensitive items held back — health, faith, politics, credentials never inferred
      </Text>
      <Text testID="owner-hook-cost">
        {OWNER_HOOK_FACTS} facts on the owner hook · $0 app cost
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.xs,
    marginTop: spacing.md,
    padding: spacing.lg,
  },
  title: { color: colors.ink, fontFamily: typography.serif, fontSize: typography.title },
  section: { color: colors.ink, fontWeight: "700", marginTop: spacing.sm },
});
