import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { buildSubjectNodes, type SubjectNode } from "./vaultApi";

export function SubjectsConstellation({ themes, onSelect, size = 320 }: {
  themes: SubjectNode[]; onSelect?: (id: string) => void; size?: number;
}) {
  const nodes = buildSubjectNodes(themes, size);
  return (
    <View style={styles.wrap} testID="subjects-constellation">
      <Svg width={size} height={size}>
        {nodes.map((n) => (
          <Circle key={n.id} cx={n.x} cy={n.y} r={n.r} fill={n.color} onPress={() => onSelect?.(n.id)} />
        ))}
      </Svg>
      {nodes.map((n) => (
        <Pressable key={`label-${n.id}`} onPress={() => onSelect?.(n.id)} accessibilityLabel={n.label}>
          <Text style={[styles.label, { color: n.color }]}>{n.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 8, shadowOpacity: 0, elevation: 0 },
  label: { fontSize: 12, fontWeight: "600" },
});
