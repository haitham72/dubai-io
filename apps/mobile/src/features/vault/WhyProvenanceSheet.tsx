import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { loadWhy, type Fetcher, type WhyResult } from "./vaultApi";
import { KARIM_WHY_FIXTURE } from "./vaultFixtures";

export function WhyProvenanceSheet({ apiBaseUrl, owner, factId, onClose, fetcher, demo, sessionToken }: {
  apiBaseUrl: string; owner: string; factId: string | null;
  onClose?: () => void; fetcher?: Fetcher; demo?: boolean; sessionToken?: string | null;
}) {
  const [why, setWhy] = useState<WhyResult | null>(null);
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!factId) return;
    let live = true;
    loadWhy(apiBaseUrl, owner, factId, KARIM_WHY_FIXTURE, fetcher, { demo, sessionToken }).then((res) => {
      if (!live) return;
      setWhy(res.why); setIsDemo(res.isDemo); setError(res.error);
    });
    return () => { live = false; };
  }, [apiBaseUrl, owner, factId, fetcher, demo, sessionToken]);

  if (!factId) return null;
  return (
    <View style={styles.sheet} testID="why-sheet">
      <Text style={styles.title}>Why do you know this?</Text>
      {isDemo ? <Text style={styles.demoPill}>Demo data</Text> : null}
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {why ? (
        <>
          <Text style={styles.fact}>{why.text}</Text>
          {why.model === "your Claude" || why.cost_badge ? (
            <Text style={styles.badge}>your Claude{why.cost_badge ? ` · ${why.cost_badge}` : ""}</Text>
          ) : (
            <Text style={styles.meta}>Model: {why.model}</Text>
          )}
          <Text style={styles.meta}>provenance: {why.provenance}</Text>
          <Text style={styles.meta}>as_of: {why.as_of}</Text>
          {why.evidence.map((e) => (
            <View key={e.id} style={styles.evidence}>
              <Text style={styles.meta}>{e.source} · {e.as_of}</Text>
              <Text>{e.text}</Text>
            </View>
          ))}
        </>
      ) : null}
      {onClose ? <Pressable onPress={onClose}><Text style={styles.close}>Close</Text></Pressable> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  sheet: { backgroundColor: "#FAF8F5", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 16, shadowOpacity: 0, elevation: 0, gap: 6 },
  title: { fontSize: 17, fontWeight: "700", color: "#1E2022" },
  fact: { fontSize: 15, color: "#1E2022" },
  badge: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, backgroundColor: "#FDF8EE", fontSize: 12, fontWeight: "700" },
  demoPill: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", backgroundColor: "#FFFFFF" },
  meta: { fontSize: 12, color: "#5A5A5A" },
  evidence: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 12, padding: 10, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0 },
  error: { color: "#B3261E" },
  close: { color: "#2F80ED", fontWeight: "600" },
});
