import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from "react-native";
import { useAuthOptional } from "../../lib/auth";
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

export function VaultScreen({ apiBaseUrl, owner, fetcher, initialData, poster, demo: propDemo, sessionToken: propSessionToken }: {
  apiBaseUrl: string; owner: string; fetcher?: Fetcher; initialData?: VaultData;
  poster?: Poster; demo?: boolean; sessionToken?: string | null;
}) {
  const auth = useAuthOptional();
  const demo = propDemo ?? auth?.demoMode ?? false;
  const sessionToken = propSessionToken !== undefined ? propSessionToken : auth?.session?.sessionToken ?? null;
  const [tab, setTab] = useState<"subjects" | "people">("subjects");
  const [data, setData] = useState<VaultData>(initialData ?? {
    themes: [], people: [], places: [], orgs: [], projects: [], facts: [],
    suggestions: [], hiddenByGroup: {}, isDemo: false, demoData: false, error: null,
  });
  const [loweredOnly, setLoweredOnly] = useState(false);
  const [confirmDeletion, setConfirmDeletion] = useState(false);
  const [privacyStatus, setPrivacyStatus] = useState<string | null>(null);
  const [privacyBusy, setPrivacyBusy] = useState(false);
  const [selectedFact, setSelectedFact] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const width = useWindowDimensions().width;
  const wide = width >= 960;

  useEffect(() => {
    if (initialData) return;
    let live = true;
    loadVault(apiBaseUrl, owner, KARIM_VAULT_FIXTURES, fetcher, { demo, sessionToken, loweredOnly }).then((d) => { if (live) setData(d); });
    return () => { live = false; };
  }, [apiBaseUrl, owner, fetcher, initialData, demo, sessionToken, loweredOnly]);

  const base = `${apiBaseUrl.replace(/\/$/, "")}/api/vault`;
  const allPeople = [...data.people, ...data.places, ...(data.projects ?? []), ...data.orgs];
  const hiddenMore = Object.values(data.hiddenByGroup ?? {}).reduce((sum, n) => sum + n, 0);

  const send: Poster = poster ?? (async (target, body) => {
    const headers: Record<string, string> = { "content-type": "application/json" };
    if (sessionToken) headers["X-App-Session"] = sessionToken;
    const res = await fetch(target, { method: "POST", headers, body: JSON.stringify(body) });
    return { ok: res.ok, status: res.status };
  });

  async function confirmTier(entityId: string) {
    await send(`${base}/people/${encodeURIComponent(entityId)}/tier`, { tier: "T1" });
  }

  async function toggleLower(fact: VaultFact) {
    setPrivacyBusy(true);
    try {
      const res = await send(`${base}/lower`, { fact_id: fact.id, lower: !fact.lowered });
      if (!res.ok) throw new Error(`Memory update failed (${res.status}).`);
      setData(await loadVault(apiBaseUrl, owner, KARIM_VAULT_FIXTURES, fetcher, { demo, sessionToken, loweredOnly }));
      setPrivacyStatus(fact.lowered ? "Restore requested." : "Memory lowered.");
    } catch (error) {
      setPrivacyStatus(error instanceof Error ? error.message : "Memory update failed.");
    } finally {
      setPrivacyBusy(false);
    }
  }

  async function deleteMyData() {
    setPrivacyBusy(true);
    try {
      const res = await send(`${apiBaseUrl.replace(/\/$/, "")}/api/identity/delete-my-data`, { confirm: true });
      if (!res.ok) throw new Error(`Account deletion did not complete (${res.status}).`);
      setSelectedFact(null);
      setData({ themes: [], people: [], places: [], orgs: [], projects: [], facts: [], suggestions: [],
        hiddenByGroup: {}, isDemo: false, demoData: false, error: null });
      setPrivacyStatus("Your data was removed from external access.");
      await auth?.signOut();
    } catch (error) {
      setPrivacyStatus(error instanceof Error ? error.message : "Account deletion did not complete.");
    } finally {
      setConfirmDeletion(false);
      setPrivacyBusy(false);
    }
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
          <Pressable accessibilityRole="button" onPress={() => setLoweredOnly(!loweredOnly)}>
            <Text>{loweredOnly ? "Show all memories" : "Show Lowered"}</Text>
          </Pressable>
          {data.facts.filter((fact) => !loweredOnly || fact.lowered).map((fact) => (
            <FactRow key={fact.id} fact={fact} onPress={() => setSelectedFact(fact.id)}
              onToggle={!demo && sessionToken && !privacyBusy ? () => void toggleLower(fact) : undefined} />
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
      <Text style={styles.section}>Privacy & Memory FAQ</Text>
      <Text>Lower dims a memory without deleting it. Restore removes that override.</Text>
      <Text>Delete my data removes owner data from external queries and the Redis cache immediately.
        An isolated de-identified training backup is retained. It excludes Google Workspace and YouTube data.</Text>
      {sessionToken && !demo ? (
        confirmDeletion ? (
          <View style={styles.actions}>
            <Text>Delete your data and sign out all devices?</Text>
            <Pressable disabled={privacyBusy} accessibilityRole="button" onPress={() => void deleteMyData()}>
              <Text>Confirm deletion</Text>
            </Pressable>
            <Pressable disabled={privacyBusy} accessibilityRole="button" onPress={() => setConfirmDeletion(false)}>
              <Text>Cancel</Text>
            </Pressable>
          </View>
        ) : (
          <Pressable accessibilityRole="button" onPress={() => setConfirmDeletion(true)}><Text>Delete my data</Text></Pressable>
        )
      ) : null}
      {privacyStatus ? <Text accessibilityLiveRegion="polite">{privacyStatus}</Text> : null}
      <WhyProvenanceSheet apiBaseUrl={apiBaseUrl} owner={owner} factId={selectedFact}
        fetcher={fetcher} demo={demo} sessionToken={sessionToken} onClose={() => setSelectedFact(null)} />
    </ScrollView>
  );
}

function FactRow({ fact, onPress, onToggle }: { fact: VaultFact; onPress: () => void; onToggle?: () => void }) {
  const label = toldLabel(fact.provenance);
  return (
    <Pressable style={styles.row} onPress={onPress}>
      <Text>{label.mark}{fact.text}</Text>
      <Text style={styles.meta}>{label.words}</Text>
      {fact.provenance !== "user_supplied" ? (
        <View style={styles.actions}>
          <Text>Confirm</Text><Text>Edit</Text><Text>Not true</Text>
        </View>
      ) : null}
      {fact.lowered ? <Text style={styles.meta}>Lowered</Text> : null}
      {onToggle ? (
        <Pressable accessibilityRole="button" onPress={(event) => { event.stopPropagation(); onToggle(); }}>
          <Text>{fact.lowered ? "Restore" : "Lower"}</Text>
        </Pressable>
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
