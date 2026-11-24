import React, { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useAuthOptional } from "../../lib/auth";
import type { Fetcher } from "../vault/vaultApi";
import { loadQuests, milestoneCounts, milestoneLabel, normalizeMilestoneState, type QuestsData } from "./questsApi";
import { KARIM_QUESTS_FIXTURES } from "./questsFixtures";

export function QuestsScreen({
  apiBaseUrl,
  owner,
  fetcher,
  initialData,
  demo: propDemo,
  sessionToken: propSessionToken,
}: {
  apiBaseUrl: string;
  owner: string;
  fetcher?: Fetcher;
  initialData?: QuestsData;
  demo?: boolean;
  sessionToken?: string | null;
}) {
  const auth = useAuthOptional();
  const demo = propDemo ?? auth?.demoMode ?? false;
  const sessionToken = propSessionToken !== undefined ? propSessionToken : auth?.session?.sessionToken ?? null;

  const [data, setData] = useState<QuestsData>(
    initialData ?? { quests: [], isDemo: false, demoData: false, error: null },
  );

  useEffect(() => {
    if (initialData) return;
    let live = true;
    loadQuests(apiBaseUrl, owner, KARIM_QUESTS_FIXTURES, fetcher, { demo, sessionToken }).then((d) => {
      if (live) setData(d);
    });
    return () => {
      live = false;
    };
  }, [apiBaseUrl, owner, fetcher, initialData, demo, sessionToken]);

  return (
    <ScrollView style={styles.screen} testID="quests-screen">
      <Text style={styles.title}>Quests</Text>
      {data.isDemo ? <Text style={styles.demoPill}>Demo data</Text> : null}
      {data.error ? <Text style={styles.error}>{data.error}</Text> : null}
      {!data.error && data.quests.length === 0 ? (
        <Text style={styles.empty} testID="quests-empty">
          No quests recorded yet.
        </Text>
      ) : null}
      {data.quests.map((quest) => {
        const counts = milestoneCounts(quest.milestones);
        return (
          <View key={quest.id} style={styles.card}>
            <Text style={styles.goal}>{quest.label}</Text>
            <Text style={styles.meta}>
              {counts.done} done · {counts.in_progress} in progress · {counts.planned} planned
            </Text>
            {quest.milestones.map((m) => {
              const state = normalizeMilestoneState(m);
              return (
                <View key={m.id} style={styles.chipRow}>
                  <Text style={styles.chip}>{milestoneLabel(state)}</Text>
                  <Text style={styles.milestone}>{m.title}</Text>
                </View>
              );
            })}
          </View>
        );
      })}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#FFFFFF", padding: 16 },
  title: { fontSize: 22, fontWeight: "800", color: "#1E2022" },
  card: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 14, marginTop: 12, backgroundColor: "#FAF8F5", shadowOpacity: 0, elevation: 0, gap: 8 },
  goal: { fontSize: 16, fontWeight: "700", color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A" },
  empty: { fontSize: 14, color: "#5A5A5A", marginTop: 12 },
  error: { fontSize: 13, color: "#9B2C2C", marginTop: 8 },
  chipRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  chip: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", backgroundColor: "#FDF8EE" },
  milestone: { fontSize: 14, color: "#1E2022" },
  demoPill: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", backgroundColor: "#FAF8F5", marginTop: 8 },
});
