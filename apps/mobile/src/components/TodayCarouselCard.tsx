import React from "react";
import { Image, StyleSheet, Text, View } from "react-native";
import { cardAspectRatio, colors, noShadow, radii, spacing, themes, typography } from "@dubai-io/design-tokens";
import type { TodayCard } from "../lib/types";
import { DemoPill } from "./DemoPill";

export function TodayCarouselCard({ card, width }: { card: TodayCard; width: number }) {
  return (
    <View
      testID={`today-card-${card.id}`}
      style={[styles.card, { width, aspectRatio: cardAspectRatio, borderColor: themes[card.tone] }]}
    >
      {card.imageUrl ? (
        <Image source={{ uri: card.imageUrl }} style={styles.image} resizeMode="cover" testID={`today-img-${card.id}`} />
      ) : (
        <View style={[styles.band, { backgroundColor: themes[card.tone] }]} />
      )}
      <View style={styles.body}>
        <View style={styles.chipRow}>
          {card.demo ? <DemoPill /> : null}
          {card.source ? (
            <View style={styles.sourceChip} testID={`today-source-${card.id}`}>
              <Text style={styles.sourceText}>{card.source}</Text>
            </View>
          ) : null}
          {card.asOf ? <Text style={styles.asOf}>{card.asOf}</Text> : null}
        </View>
        {card.eyebrow ? <Text style={styles.eyebrow}>{card.eyebrow}</Text> : null}
        <Text style={styles.title}>{card.title}</Text>
        {card.subtitle ? <Text style={styles.subtitle}>{card.subtitle}</Text> : null}
        {card.because ? (
          <View style={styles.because} testID={`because-${card.id}`}>
            <Text style={styles.becauseText}>Because… {card.because}</Text>
          </View>
        ) : null}
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
  image: {
    height: 120,
    width: "100%",
  },
  body: {
    flex: 1,
    gap: spacing.sm,
    padding: spacing.lg,
  },
  chipRow: {
    alignItems: "center",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.xs,
  },
  sourceChip: {
    ...noShadow,
    backgroundColor: colors.gold.surface,
    borderColor: colors.gold.border,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  sourceText: {
    color: colors.gold.primary,
    fontSize: 11,
    fontWeight: "700",
  },
  asOf: {
    color: colors.muted,
    fontSize: 11,
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
  subtitle: {
    color: colors.muted,
    fontSize: typography.caption,
    lineHeight: 18,
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
