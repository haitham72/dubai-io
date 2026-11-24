import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import type { Fetcher } from "../vault/vaultApi";
import { loadRegion, saveRegion, startGoogleOAuth, uploadPickedFile, type YoutubeRegion } from "./connectApi";

type Progress = "Not connected" | "Syncing" | "Ready";

export function YoutubeOnboardingCard({ apiBaseUrl, owner, fetcher, initialRegion }: {
  apiBaseUrl: string; owner: string; fetcher?: Fetcher; initialRegion?: YoutubeRegion;
}) {
  const [region, setRegion] = useState<YoutubeRegion>(initialRegion ?? "UAE");
  const [status, setStatus] = useState<Progress>("Not connected");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (initialRegion) return;
    let live = true;
    loadRegion().then((r) => { if (live) setRegion(r); });
    return () => { live = false; };
  }, [initialRegion]);

  const choose = (r: YoutubeRegion) => { setRegion(r); void saveRegion(r); };

  const uploadTakeout = async () => {
    const picked = await DocumentPicker.getDocumentAsync({
      type: ["application/json", "application/zip"], copyToCacheDirectory: true,
    });
    if (picked.canceled || !picked.assets?.length) return; // cancel: no state change
    setStatus("Syncing");
    const ok = await uploadPickedFile(apiBaseUrl, owner, "takeout", picked.assets[0], fetcher);
    if (ok) { setStatus("Ready"); setMessage("Takeout uploaded"); }
    else { setStatus("Not connected"); setMessage("Upload failed — server unreachable"); }
  };

  return (
    <View style={styles.card} testID="youtube-onboarding">
      <Text style={styles.title}>YouTube Watch History</Text>
      <Text style={styles.meta}>Status: {status}</Text>
      <View style={styles.row}>
        <Pressable style={[styles.chip, region === "EEA" && styles.chipOn]} onPress={() => choose("EEA")}>
          <Text>EEA / UK / Switzerland</Text>
        </Pressable>
        <Pressable style={[styles.chip, region === "UAE" && styles.chipOn]} onPress={() => choose("UAE")}>
          <Text>UAE / Rest of World</Text>
        </Pressable>
      </View>

      <Text style={styles.step}>YouTube Data API v3 — uploads, liked, subscriptions, playlists</Text>
      <Pressable style={styles.button} onPress={() => void startGoogleOAuth(apiBaseUrl)}>
        <Text style={styles.buttonText}>Connect YouTube</Text>
      </Pressable>

      {region === "EEA" ? (
        <>
          <Text style={styles.step}>Google Data Portability API (dataportability.myactivity.youtube)</Text>
          <Pressable style={styles.button} onPress={() => void startGoogleOAuth(apiBaseUrl)}>
            <Text style={styles.buttonText}>Connect Data Portability</Text>
          </Pressable>
        </>
      ) : (
        <>
          <Text style={styles.step}>Google Takeout → Scheduled "Add to Drive" — Export every 2 months for 1 year (watch-history.json)</Text>
          <Text style={styles.meta}>Waiting for first Takeout drop in Drive</Text>
          <Pressable style={styles.button} onPress={() => void uploadTakeout()}>
            <Text style={styles.buttonText}>Upload Takeout JSON/ZIP now</Text>
          </Pressable>
        </>
      )}
      <Text style={styles.note}>
        Only daily Rule-9 interest counts are stored — sensitive topics are held back and never inferred.
      </Text>
      {message ? <Text style={styles.meta}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 14, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0, gap: 8 },
  title: { fontSize: 16, fontWeight: "700", color: "#1E2022" },
  row: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  chip: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, paddingHorizontal: 10, paddingVertical: 6, backgroundColor: "#FAF8F5" },
  chipOn: { backgroundColor: "#FDF8EE", borderColor: "#E8D5A3" },
  step: { fontSize: 14, color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A" },
  note: { fontSize: 12, color: "#5A5A5A" },
  button: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 12, padding: 10, alignItems: "center", backgroundColor: "#FDF8EE", shadowOpacity: 0, elevation: 0 },
  buttonText: { fontWeight: "700", color: "#1E2022" },
});
