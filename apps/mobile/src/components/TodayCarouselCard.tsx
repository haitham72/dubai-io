import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { cardAspectRatio, colors, noShadow, radii, spacing, themes, typography } from "@dubai-io/design-tokens";
import type { TodayCard } from "../lib/types";
import { DemoPill } from "./DemoPill";

export function TodayCarouselCard({ card, width }: { card: TodayCard; width: number }) {
  return (
    <View
      testID={`today-card-${card.id}`}
      style={[styles.card, { width, aspectRatio: cardAspectRatio, borderColor: themes[card.tone] }]}
    >
      <View style={[styles.band, { backgroundColor: themes[card.tone] }]} />
      <View style={styles.body}>
        {card.demo ? <DemoPill /> : null}
        {card.eyebrow ? <Text style={styles.eyebrow}>{card.eyebrow}</Text> : null}
        <Text style={styles.title}>{card.title}</Text>
        <View style={styles.because} testID={`because-${card.id}`}>
          <Text style={styles.becauseText}>Because… {card.because}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    ...noShadow,
    backgroundColor: colors.card,
    borderRadius: radii.card,
    borderWidth: 1,
    overflow: "hidden",
  },
  band: {
    height: 12,
  },
  body: {
    flex: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  eyebrow: {
    color: colors.gold.primary,
    fontFamily: typography.sans,
    fontSize: typography.caption,
    fontWeight: "700",
  },
  title: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.body,
  },
  because: {
    ...noShadow,
    backgroundColor: colors.surface,
    borderColor: colors.borderHairline,
    borderRadius: radii.chip,
    borderWidth: 1,
    marginTop: "auto",
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
  becauseText: {
    color: colors.ink,
    fontSize: typography.caption,
  },
});
