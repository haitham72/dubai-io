import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { buildPeopleNodes, type VaultEntity } from "./vaultApi";

export function PeoplePlacesConstellation({ people, onSelect, size = 320 }: {
  people: VaultEntity[]; onSelect?: (id: string) => void; size?: number;
}) {
  const nodes = buildPeopleNodes(people, size);
  const hasT1 = people.some((p) => p.closeness_tier === "T1");
  return (
    <View style={styles.wrap} testID="people-constellation">
      {hasT1 ? <Text style={styles.t1Badge}>T1 Inner Circle</Text> : null}
      <Svg width={size} height={size}>
        {hasT1 ? <Circle testID="t1-ring" cx={size / 2} cy={size / 2} r={42} fill="none" stroke="#E8D5A3" strokeWidth={1} /> : null}
        <Circle cx={size / 2} cy={size / 2} r={88} fill="none" stroke="#E8E8EC" strokeWidth={1} />
        {nodes.map((n) => (
          <Circle key={n.id} cx={n.x} cy={n.y} r={n.r} fill={n.color} onPress={() => onSelect?.(n.id)} />
        ))}
      </Svg>
      {people.map((p) => (
        <Pressable key={p.id} onPress={() => onSelect?.(p.id)}>
          <Text style={styles.label}>
            {p.name}{p.closeness_tier ? ` · ${p.closeness_tier}` : ""}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 8, shadowOpacity: 0, elevation: 0 },
  t1Badge: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", color: "#8A6D1F", backgroundColor: "#FDF8EE" },
  label: { fontSize: 13, color: "#1E2022" },
});
