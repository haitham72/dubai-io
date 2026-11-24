import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { DemoPill } from "../../components/DemoPill";
import {
  GOOGLE_SIGN_IN, PC_SETUP_LINK, completenessBanner, completenessPct,
  type CompletenessSources,
} from "./completeness";

export function CompletenessRingCard({
  sources = GOOGLE_SIGN_IN,
  onExplore,
}: {
  sources?: CompletenessSources;
  onExplore?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const pct = completenessPct(sources);
  return (
    <View style={styles.card} testID="completeness-ring">
      <DemoPill />
      <View style={styles.ring}>
        <Text style={styles.pct}>{pct}%</Text>
      </View>
      <Text style={styles.banner} testID="completeness-banner">{completenessBanner(sources)}</Text>
      <Pressable
        accessibilityRole="button"
        onPress={() => setCopied(true)}
        style={styles.primary}
        testID="pair-desktop"
      >
        <Text style={styles.primaryText}>Pair Desktop / Copy PC Setup Link</Text>
      </Pressable>
      {copied ? <Text testID="setup-link">{PC_SETUP_LINK}</Text> : null}
      <Pressable
        accessibilityRole="button"
        onPress={onExplore}
        style={styles.secondary}
        testID="explore-app-now"
      >
        <Text style={styles.secondaryText}>Explore App Now</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...noShadow,
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.sm,
    marginTop: spacing.md,
    padding: spacing.lg,
  },
  ring: {
    ...noShadow,
    alignItems: "center",
    alignSelf: "flex-start",
    borderColor: colors.gold.primary,
    borderRadius: 48,
    borderWidth: 1,
    height: 72,
    justifyContent: "center",
    width: 72,
  },
  pct: {
    color: colors.gold.primary,
    fontFamily: typography.serif,
    fontSize: typography.title,
    fontWeight: "700",
  },
  banner: { color: colors.ink, fontSize: typography.body, lineHeight: 22 },
  primary: {
    ...noShadow,
    backgroundColor: colors.gold.surface,
    borderColor: colors.gold.border,
    borderRadius: radii.chip,
    borderWidth: 1,
    padding: spacing.sm,
  },
  primaryText: { color: colors.ink, fontWeight: "700" },
  secondary: {
    ...noShadow,
    backgroundColor: colors.canvas,
    borderColor: colors.border,
    borderRadius: radii.chip,
    borderWidth: 1,
    padding: spacing.sm,
  },
  secondaryText: { color: colors.ink, fontWeight: "700" },
});
