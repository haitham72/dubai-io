import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { DemoPill } from "../../components/DemoPill";
import { REVEAL_FACTS } from "./completeness";

type Verdict = "confirm" | "edit" | "not-true" | "lower";

export function InitialRevealCard() {
  const [verdicts, setVerdicts] = useState<Record<string, Verdict>>({});
  return (
    <View style={styles.card} testID="initial-reveal">
      <DemoPill />
      <Text style={styles.title}>Here is what I know about you for now…</Text>
      {REVEAL_FACTS.map((fact) => (
        <View key={fact.id} style={styles.fact} testID={`reveal-${fact.id}`}>
          <Text style={styles.theme}>{fact.theme}</Text>
          <Text>{fact.text}</Text>
          <Text style={styles.meta}>src: {fact.src} · as_of: {fact.asOf} · provenance: demo_fixture</Text>
          <View style={styles.actions}>
            {(["confirm", "edit", "not-true", "lower"] as Verdict[]).map((action) => (
              <Pressable
                key={action}
                accessibilityRole="button"
                onPress={() => setVerdicts((prev) => ({ ...prev, [fact.id]: action }))}
                style={styles.action}
              >
                <Text>{action === "not-true" ? "Not true" : action === "confirm" ? "Confirm" : action === "edit" ? "Edit" : "Lower"}</Text>
              </Pressable>
            ))}
          </View>
          {verdicts[fact.id] ? (
            <Text testID={`verdict-${fact.id}`}>
              {verdicts[fact.id] === "confirm" ? "You told me this is right" : `Marked ${verdicts[fact.id]}`}
            </Text>
          ) : null}
        </View>
      ))}
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
  title: { color: colors.ink, fontFamily: typography.serif, fontSize: typography.title },
  fact: {
    ...noShadow,
    borderColor: colors.border,
    borderRadius: radii.chip,
    borderWidth: 1,
    gap: spacing.xs,
    padding: spacing.sm,
  },
  theme: { color: colors.muted, fontSize: typography.caption, fontWeight: "700" },
  meta: { color: colors.muted, fontSize: typography.caption },
  actions: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  action: {
    ...noShadow,
    borderColor: colors.gold.border,
    borderRadius: radii.pill,
    borderWidth: 1,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.xs,
  },
});
