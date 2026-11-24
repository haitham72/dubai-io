import React, { useCallback, useEffect, useState } from "react";
import { Linking, Pressable, StyleSheet, Switch, Text, View } from "react-native";
import type { Fetcher } from "../vault/vaultApi";
import {
  GOOGLE_SOURCES,
  getIngestStatus,
  pullSource,
  receiptValue,
  setSourceConsent,
  startSourceConnect,
  type GoogleSource,
  type IngestStatus,
} from "./ingestApi";

/** Per-source consent (default off), Google consent hand-off and honest ingest status. All via apps/api. */
export function SourcesCard({
  apiBaseUrl,
  sessionToken,
  fetcher,
  openUrl = (url: string) => Linking.openURL(url),
}: {
  apiBaseUrl: string;
  sessionToken?: string | null;
  fetcher?: Fetcher;
  openUrl?: (url: string) => Promise<unknown> | void;
}) {
  const [status, setStatus] = useState<IngestStatus | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  const refresh = useCallback(async () => {
    if (!sessionToken || !apiBaseUrl.trim()) return;
    const next = await getIngestStatus(apiBaseUrl, sessionToken, fetcher);
    setStatus(next);
    setLoaded(true);
  }, [apiBaseUrl, sessionToken, fetcher]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  if (!sessionToken) {
    return (
      <View style={styles.card} testID="sources-card">
        <Text style={styles.title}>Your data sources</Text>
        <Text style={styles.meta} testID="sources-signed-out">Sign in to connect Gmail, Calendar and YouTube.</Text>
      </View>
    );
  }

  async function toggle(source: GoogleSource, enabled: boolean) {
    setNotice(null);
    const ok = await setSourceConsent(apiBaseUrl, sessionToken as string, source, enabled, fetcher);
    if (!ok) setNotice("Could not change consent. Nothing was changed.");
    await refresh();
  }

  async function connect(source: GoogleSource) {
    setNotice(null);
    const res = await startSourceConnect(apiBaseUrl, sessionToken as string, source, fetcher);
    if (res.error || !res.url) {
      setNotice(res.error ?? "Could not start Google consent.");
      return;
    }
    await openUrl(res.url);
  }

  async function pull(source: GoogleSource) {
    setNotice(null);
    const res = await pullSource(apiBaseUrl, sessionToken as string, source, fetcher);
    setNotice(res.error ?? `${source}: ${res.added ?? 0} new records added.`);
    await refresh();
  }

  return (
    <View style={styles.card} testID="sources-card">
      <Text style={styles.title}>Your data sources</Text>
      <Text style={styles.meta}>Off by default. Each source needs your explicit consent and can be turned off any time.</Text>
      {!loaded ? <Text style={styles.meta} testID="sources-status-unavailable">Status not loaded yet.</Text> : null}
      {GOOGLE_SOURCES.map(({ id, label }) => {
        const s = status?.sources?.[id];
        const enabled = s?.enabled === true;
        const records = receiptValue(s?.records);
        return (
          <View key={id} style={styles.row} testID={`source-${id}`}>
            <View style={styles.rowHead}>
              <Text style={styles.name}>{label}</Text>
              <Switch value={enabled} onValueChange={(v) => void toggle(id, v)} testID={`consent-${id}`} />
            </View>
            {enabled ? (
              <View style={styles.actions}>
                <Text style={styles.meta}>
                  {s?.connected ? "Connected" : "Not connected"}
                  {records !== null ? ` · ${records} records` : ""}
                </Text>
                {!s?.connected ? (
                  <Pressable style={styles.button} onPress={() => void connect(id)} testID={`connect-${id}`}>
                    <Text style={styles.buttonText}>Connect {label}</Text>
                  </Pressable>
                ) : (
                  <Pressable style={styles.button} onPress={() => void pull(id)} testID={`pull-${id}`}>
                    <Text style={styles.buttonText}>Pull now</Text>
                  </Pressable>
                )}
              </View>
            ) : null}
          </View>
        );
      })}
      {status?.runner ? <Text style={styles.meta}>Extraction: {status.runner}{status.model ? ` (${status.model})` : ""}</Text> : null}
      {notice ? <Text style={styles.meta} testID="sources-notice">{notice}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 14, marginBottom: 12, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0, gap: 8 },
  title: { fontSize: 16, fontWeight: "700", color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A" },
  row: { gap: 6 },
  rowHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  name: { fontWeight: "600", color: "#1E2022" },
  actions: { gap: 6 },
  button: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 12, padding: 10, alignItems: "center", backgroundColor: "#FDF8EE", shadowOpacity: 0, elevation: 0 },
  buttonText: { fontWeight: "700", color: "#1E2022" },
});
