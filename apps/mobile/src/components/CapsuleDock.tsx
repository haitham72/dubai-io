import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import type { DockTab, PillarId } from "../lib/types";

export function CapsuleDock({
  tabs,
  active,
  onTabPress,
  onVoicePress,
}: {
  tabs: DockTab[];
  active: PillarId;
  onTabPress: (tab: DockTab) => void;
  onVoicePress: () => void;
}) {
  const left = tabs.filter((tab) => tab.id === "today" || tab.id === "chat");
  const right = tabs.filter((tab) => tab.id === "quests" || tab.id === "memory");
  return (
    <View style={styles.wrap} testID="capsule-dock">
      <View style={styles.capsule}>
        {left.map((tab) => (
          <DockItem key={tab.id} tab={tab} active={active === tab.id} onPress={() => onTabPress(tab)} />
        ))}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Voice capture"
          onPress={onVoicePress}
          style={styles.orb}
          testID="voice-orb"
        >
          <View style={styles.wave}>
            {[8, 14, 10, 16, 9].map((height, index) => (
              <View key={index} style={[styles.bar, { height }]} />
            ))}
          </View>
        </Pressable>
        {right.map((tab) => (
          <DockItem key={tab.id} tab={tab} active={active === tab.id} onPress={() => onTabPress(tab)} />
        ))}
      </View>
    </View>
  );
}

function DockItem({ tab, active, onPress }: { tab: DockTab; active: boolean; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="button" onPress={onPress} style={styles.item} testID={`dock-${tab.id}`}>
      <Text style={[styles.label, active && styles.labelActive]}>{tab.label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    ...noShadow,
    backgroundColor: "transparent",
    paddingBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
  },
  capsule: {
    ...noShadow,
    alignItems: "center",
    backgroundColor: colors.card,
    borderColor: colors.border,
    borderRadius: radii.dock,
    borderWidth: 1,
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
  },
  item: {
    ...noShadow,
    flex: 1,
    alignItems: "center",
    paddingVertical: spacing.sm,
  },
  label: {
    color: colors.muted,
    fontFamily: typography.sans,
    fontSize: 12,
    fontWeight: "600",
  },
  labelActive: {
    color: colors.gold.primary,
  },
  orb: {
    ...noShadow,
    alignItems: "center",
    backgroundColor: colors.gold.primary,
    borderRadius: radii.orb,
    height: 56,
    justifyContent: "center",
    marginTop: -28,
    width: 56,
  },
  wave: {
    alignItems: "center",
    flexDirection: "row",
    gap: 2,
  },
  bar: {
    backgroundColor: colors.canvas,
    borderRadius: 1,
    width: 2,
  },
});
