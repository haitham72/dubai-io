import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { loadVault, type Fetcher, type VaultData, type VaultEntity, type VaultFact } from "./vaultApi";
import { KARIM_VAULT_FIXTURES } from "./vaultFixtures";
import { PeoplePlacesConstellation } from "./PeoplePlacesConstellation";
import { SubjectsConstellation } from "./SubjectsConstellation";
import { UserAnalyticsCard } from "./UserAnalyticsCard";
import { WhyProvenanceSheet } from "./WhyProvenanceSheet";

export type Poster = (url: string, body: unknown) => Promise<{ ok: boolean; status: number }>;

function toldLabel(provenance?: string): { mark: string; words: string } {
  if (provenance === "user_supplied") return { mark: "✓ ", words: "You told me" };
  return { mark: "", words: "I noticed" };
}

export function VaultScreen({ apiBaseUrl, owner, fetcher, initialData, poster, demo }: {
  apiBaseUrl: string; owner: string; fetcher?: Fetcher; initialData?: VaultData;
  poster?: Poster; demo?: boolean;
}) {
  const [tab, setTab] = useState<"subjects" | "people">("subjects");
  const [data, setData] = useState<VaultData>(initialData ?? {
    themes: [], people: [], places: [], orgs: [], projects: [], facts: [],
    suggestions: [], hiddenByGroup: {}, isDemo: false, demoData: false, error: null,
  });
  const [selectedFact, setSelectedFact] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const width = useWindowDimensions().width;
  const wide = width >= 960;

  useEffect(() => {
    if (initialData) return;
    let live = true;
    loadVault(apiBaseUrl, owner, KARIM_VAULT_FIXTURES, fetcher, { demo }).then((d) => { if (live) setData(d); });
    return () => { live = false; };
  }, [apiBaseUrl, owner, fetcher, initialData, demo]);

  const base = `${apiBaseUrl.replace(/\/$/, "")}/v1/owners/${encodeURIComponent(owner)}`;
  const allPeople = [...data.people, ...data.places, ...(data.projects ?? []), ...data.orgs];
  const hiddenMore = Object.values(data.hiddenByGroup ?? {}).reduce((sum, n) => sum + n, 0);

  async function confirmTier(entityId: string) {
    const url = `${base}/vault/people/${encodeURIComponent(entityId)}/tier`;
    const send = poster ?? (async (target: string, body: unknown) => {
      const res = await fetch(target, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      return { ok: res.ok, status: res.status };
    });
    await send(url, { tier: "T1" });
  }

  return (
    <ScrollView style={styles.screen} contentContainerStyle={[styles.column, wide && styles.columnWide]} testID="vault-screen">
      <Text style={styles.title}>Memory Vault</Text>
      {data.error ? <Text style={styles.error}>{data.error}</Text> : null}
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
          {data.facts.map((fact) => (
            <FactRow key={fact.id} fact={fact} onPress={() => setSelectedFact(fact.id)} />
          ))}
          {data.themes.map((theme) => {
            const label = toldLabel(theme.provenance);
            return (
              <Text key={theme.id} style={styles.meta}>
                {label.mark}{theme.label} — {theme.fact_count} facts
              </Text>
            );
          })}
          {hiddenMore > 0 ? <Text style={styles.meta}>+{hiddenMore} more</Text> : null}
        </>
      ) : (
        <>
          <PeoplePlacesConstellation people={allPeople} />
          <Text style={styles.section}>Relationships</Text>
          {allPeople.map((person) => (
            <PersonRow key={person.id} person={person} />
          ))}
          {(data.suggestions ?? []).filter((item) => !dismissed.includes(item.id)).map((item) => (
            <View key={item.id} style={styles.row}>
              <Text>I noticed {item.name} may be {item.suggested}</Text>
              <Pressable testID={`confirm-${item.id}`} onPress={() => confirmTier(item.id)}><Text>Confirm</Text></Pressable>
              <Pressable onPress={() => setDismissed((ids) => [...ids, item.id])}><Text>Not now</Text></Pressable>
            </View>
          ))}
        </>
      )}
      <WhyProvenanceSheet apiBaseUrl={apiBaseUrl} owner={owner} factId={selectedFact}
        fetcher={fetcher} onClose={() => setSelectedFact(null)} />
    </ScrollView>
  );
}

function FactRow({ fact, onPress }: { fact: VaultFact; onPress: () => void }) {
  const label = toldLabel(fact.provenance);
  return (
    <Pressable style={styles.row} onPress={onPress}>
      <Text>{label.mark}{fact.text}</Text>
      <Text style={styles.meta}>{label.words}</Text>
      {fact.provenance !== "user_supplied" ? (
        <View style={styles.actions}>
          <Text>Confirm</Text><Text>Edit</Text><Text>Not true</Text><Text>Forget</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

function PersonRow({ person }: { person: VaultEntity }) {
  const stated = person.provenance === "user_supplied";
  const tier = person.closeness_tier
    ? ` · ${person.closeness_tier}${person.closeness_tier === "T1" ? " Inner Circle" : ""}`
    : "";
  return (
    <Text style={styles.rowText}>
      {stated ? "✓ " : ""}{stated ? "You told me " : "I noticed "}
      {person.name}{tier}
      {person.place_type ? ` · ${person.place_type}` : ""}
      {person.relation_to_user ? ` · ${person.relation_to_user}` : ""}
    </Text>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#FFFFFF", padding: 16 },
  column: { width: "100%" },
  columnWide: { maxWidth: 880, alignSelf: "center" },
  error: { marginTop: 8, color: "#9B2C2C" },
  actions: { flexDirection: "row", gap: 12, marginTop: 6 },
  title: { fontSize: 22, fontWeight: "800", color: "#1E2022" },
  section: { fontSize: 16, fontWeight: "700", marginTop: 16, color: "#1E2022" },
  segmented: { flexDirection: "row", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, overflow: "hidden", marginVertical: 12, shadowOpacity: 0, elevation: 0 },
  segment: { flex: 1, alignItems: "center", paddingVertical: 8, backgroundColor: "#FAF8F5" },
  segmentOn: { backgroundColor: "#FDF8EE" },
  row: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 12, padding: 10, marginTop: 8, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0 },
  rowText: { fontSize: 14, marginTop: 8, color: "#1E2022" },
  meta: { fontSize: 13, marginTop: 6, color: "#5A5A5A" },
  });
