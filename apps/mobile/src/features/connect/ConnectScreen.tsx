import React, { useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from "react-native";
import type { Fetcher } from "../vault/vaultApi";
import {
  LOCALHOST_WARNING, isLocalhostUrl, loadSettings, saveSettings,
  startGoogleOAuth, testConnection, type ConnectionStatus,
} from "./connectApi";
import { CompletenessRingCard } from "./CompletenessRingCard";
import { InitialRevealCard } from "./InitialRevealCard";
import { WhatsappImportCard } from "./WhatsappImportCard";
import { YoutubeOnboardingCard } from "./YoutubeOnboardingCard";

export function ConnectScreen({ apiBaseUrl: initialUrl, owner: initialOwner, fetcher }: {
  apiBaseUrl?: string; owner?: string; fetcher?: Fetcher;
}) {
  const [apiBaseUrl, setApiBaseUrl] = useState(initialUrl ?? "http://192.168.1.10:8000");
  const [owner, setOwner] = useState(initialOwner ?? "karim");
  const [demo, setDemo] = useState(false);
  const [status, setStatus] = useState<ConnectionStatus>("unknown");
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    if (initialUrl) return;
    let live = true;
    loadSettings().then((s) => {
      if (!live) return;
      if (s.apiBaseUrl) setApiBaseUrl(s.apiBaseUrl);
      setOwner(s.owner); setDemo(s.demo);
    });
    return () => { live = false; };
  }, [initialUrl]);

  const localhost = isLocalhostUrl(apiBaseUrl);

  return (
    <ScrollView style={styles.screen} testID="connect-screen">
      <Text style={styles.title}>Connect</Text>
      <CompletenessRingCard />
      <InitialRevealCard />
      <Text style={styles.label}>API Server URL</Text>
      <TextInput style={styles.input} value={apiBaseUrl} onChangeText={setApiBaseUrl}
        autoCapitalize="none" autoCorrect={false} placeholder="http://192.168.x.x:8000" />
      {localhost ? <Text style={styles.warning}>{LOCALHOST_WARNING}</Text> : null}
      <Text style={styles.label}>Owner</Text>
      <TextInput style={styles.input} value={owner} onChangeText={setOwner} autoCapitalize="none" />
      <View style={styles.row}>
        <Text>Demo mode</Text>
        <Switch value={demo} onValueChange={setDemo} />
      </View>
      {demo ? <Text style={styles.demoPill}>Demo data</Text> : null}
      <Pressable style={styles.button} onPress={() => {
        void saveSettings(apiBaseUrl, owner, demo).then(() => setSaved("Saved"));
      }}>
        <Text style={styles.buttonText}>Save settings</Text>
      </Pressable>
      {saved ? <Text style={styles.meta}>{saved}</Text> : null}
      <Pressable style={styles.button} onPress={() => {
        setStatus("unknown");
        void testConnection(apiBaseUrl, fetcher).then(setStatus);
      }}>
        <Text style={styles.buttonText}>Test Connection</Text>
      </Pressable>
      <Text style={styles.meta}>
        {status === "reachable" ? "Server reachable" : status === "offline" ? "Offline — server unreachable" : "Not tested yet"}
      </Text>
      <Pressable style={styles.button} onPress={() => void startGoogleOAuth(apiBaseUrl)}>
        <Text style={styles.buttonText}>Connect Google</Text>
      </Pressable>
      <YoutubeOnboardingCard apiBaseUrl={apiBaseUrl} owner={owner} fetcher={fetcher} />
      <WhatsappImportCard apiBaseUrl={apiBaseUrl} owner={owner} fetcher={fetcher} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#FFFFFF", padding: 16 },
  title: { fontSize: 22, fontWeight: "800", color: "#1E2022", marginBottom: 12 },
  label: { fontSize: 13, fontWeight: "600", marginTop: 12, color: "#1E2022" },
  input: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 12, padding: 10, marginTop: 6, backgroundColor: "#FAF8F5" },
  warning: { color: "#B3261E", marginTop: 6, fontSize: 13 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 12 },
  button: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 12, padding: 10, alignItems: "center", backgroundColor: "#FDF8EE", marginTop: 12, shadowOpacity: 0, elevation: 0 },
  buttonText: { fontWeight: "700", color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A", marginTop: 6 },
  demoPill: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", backgroundColor: "#FAF8F5", marginTop: 8 },
});
