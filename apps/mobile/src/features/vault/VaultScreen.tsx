import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import { loadVault, type Fetcher, type VaultData } from "./vaultApi";
import { KARIM_VAULT_FIXTURES } from "./vaultFixtures";
import { PeoplePlacesConstellation } from "./PeoplePlacesConstellation";
import { SubjectsConstellation } from "./SubjectsConstellation";
import { UserAnalyticsCard } from "./UserAnalyticsCard";
import { WhyProvenanceSheet } from "./WhyProvenanceSheet";

export function VaultScreen({ apiBaseUrl, owner, fetcher, initialData }: {
  apiBaseUrl: string; owner: string; fetcher?: Fetcher; initialData?: VaultData;
}) {
  const [tab, setTab] = useState<"subjects" | "people">("subjects");
  const [data, setData] = useState<VaultData>(initialData ?? KARIM_VAULT_FIXTURES);
  const [selectedFact, setSelectedFact] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) return;
    let live = true;
    loadVault(apiBaseUrl, owner, KARIM_VAULT_FIXTURES, fetcher).then((d) => { if (live) setData(d); });
    return () => { live = false; };
  }, [apiBaseUrl, owner, fetcher, initialData]);

  const allPeople = [...data.people, ...data.places, ...data.orgs];
  return (
    <ScrollView style={styles.screen} testID="vault-screen">
      <Text style={styles.title}>Memory Vault</Text>
      <UserAnalyticsCard demo={data.isDemo} />
      <View style={styles.segmented}>
        <Pressable style={[styles.segment, tab === "subjects" && styles.segmentOn]} onPress={() => setTab("subjects")}>
          <Text>Subjects</Text>
        </Pressable>
        <Pressable style={[styles.segment, tab === "people" && styles.segmentOn]} onPress={() => setTab("people")}>
          <Text>People & Places</Text>
        </Pressable>
      </View>

      {tab === "subjects" ? (
        <>
          <SubjectsConstellation themes={data.themes} />
          <Text style={styles.section}>Key Knowledge</Text>
          {data.facts.map((f) => (
            <Pressable key={f.id} style={styles.row} onPress={() => setSelectedFact(f.id)}>
              <Text>✓ {f.text}</Text>
            </Pressable>
          ))}
          {data.themes.map((t) => (
            <Text key={t.id} style={styles.meta}>✓ {t.label} — {t.fact_count} facts</Text>
          ))}
        </>
      ) : (
        <>
          <PeoplePlacesConstellation people={allPeople} />
          <Text style={styles.section}>Relationships</Text>
          {allPeople.map((p) => (
            <Text key={p.id} style={styles.rowText}>
              ✓ {p.name}{p.closeness_tier ? ` · ${p.closeness_tier}${p.closeness_tier === "T1" ? " Inner Circle" : ""}` : ""}
              {p.relation_to_user ? ` · ${p.relation_to_user}` : ""}
            </Text>
          ))}
        </>
      )}
      <WhyProvenanceSheet apiBaseUrl={apiBaseUrl} owner={owner} factId={selectedFact}
        fetcher={fetcher} onClose={() => setSelectedFact(null)} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#FFFFFF", padding: 16 },
  title: { fontSize: 22, fontWeight: "800", color: "#1E2022" },
  section: { fontSize: 16, fontWeight: "700", marginTop: 16, color: "#1E2022" },
  segmented: { flexDirection: "row", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, overflow: "hidden", marginVertical: 12, shadowOpacity: 0, elevation: 0 },
  segment: { flex: 1, alignItems: "center", paddingVertical: 8, backgroundColor: "#FAF8F5" },
  segmentOn: { backgroundColor: "#FDF8EE" },
  row: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 12, padding: 10, marginTop: 8, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0 },
  rowText: { fontSize: 14, marginTop: 8, color: "#1E2022" },
  meta: { fontSize: 13, marginTop: 6, color: "#5A5A5A" },
  });
