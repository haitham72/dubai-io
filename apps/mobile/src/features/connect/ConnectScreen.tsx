import React, { useCallback, useEffect, useState } from "react";
import { Pressable, ScrollView, StyleSheet, Switch, Text, TextInput, View } from "react-native";
import { useAuthOptional } from "../../lib/auth";
import type { AuthSession } from "../../lib/types";
import type { Fetcher } from "../vault/vaultApi";
import {
  LOCALHOST_WARNING,
  isLocalhostUrl,
  listActiveSessions,
  loadSettings,
  revokeDeviceSession,
  saveSettings,
  startDevicePairing,
  startGoogleSignIn,
  testConnection,
  type ConnectionStatus,
  type DeviceSessionInfo,
  type PairingStartOut,
} from "./connectApi";
import { CompletenessRingCard } from "./CompletenessRingCard";
import { InitialRevealCard } from "./InitialRevealCard";
import { PairIphoneModal, ScanQrModal } from "./QrPairingModals";
import { SourcesCard } from "./SourcesCard";
import { WhatsappImportCard } from "./WhatsappImportCard";
import { YoutubeOnboardingCard } from "./YoutubeOnboardingCard";

export function ConnectScreen({
  apiBaseUrl: initialUrl,
  owner: initialOwner,
  demo: initialDemo,
  session: initialSession,
  onApiBaseUrlChange,
  fetcher,
}: {
  apiBaseUrl?: string;
  owner?: string;
  demo?: boolean;
  session?: AuthSession | null;
  onApiBaseUrlChange?: (url: string) => void;
  fetcher?: Fetcher;
}) {
  const auth = useAuthOptional();
  const [apiBaseUrl, setApiBaseUrl] = useState(initialUrl ?? "http://192.168.1.10:8000");
  const [localDemo, setLocalDemo] = useState(initialDemo ?? false);
  const [status, setStatus] = useState<ConnectionStatus>("unknown");
  const [saved, setSaved] = useState<string | null>(null);

  const [sessions, setSessions] = useState<DeviceSessionInfo[]>([]);
  const [sessionsError, setSessionsError] = useState<string | null>(null);
  const [pairOpen, setPairOpen] = useState(false);
  const [pairing, setPairing] = useState<PairingStartOut | null>(null);
  const [pairLoading, setPairLoading] = useState(false);
  const [pairError, setPairError] = useState<string | null>(null);
  const [scanOpen, setScanOpen] = useState(false);
  const [accountError, setAccountError] = useState<string | null>(null);

  const activeSession = initialSession !== undefined ? initialSession : auth?.session ?? null;
  const demo = initialDemo !== undefined ? initialDemo : auth ? auth.demoMode : localDemo;
  const effectiveOwner = activeSession?.userId ?? initialOwner ?? (demo ? "karim" : "");

  useEffect(() => {
    if (initialUrl) return;
    let live = true;
    loadSettings().then((s) => {
      if (!live) return;
      if (s.apiBaseUrl) setApiBaseUrl(s.apiBaseUrl);
      if (initialDemo === undefined && !auth) setLocalDemo(s.demo);
    });
    return () => {
      live = false;
    };
  }, [initialUrl, initialDemo, auth]);

  const refreshDevices = useCallback(async () => {
    if (!activeSession?.sessionToken || !apiBaseUrl.trim()) {
      setSessions([]);
      return;
    }
    try {
      setSessionsError(null);
      const list = await listActiveSessions(apiBaseUrl, activeSession.sessionToken, fetcher);
      setSessions(list);
    } catch (err) {
      setSessionsError(err instanceof Error ? err.message : "Could not load signed-in devices");
    }
  }, [activeSession?.sessionToken, apiBaseUrl, fetcher]);

  useEffect(() => {
    if (activeSession?.sessionToken) {
      void refreshDevices();
    } else {
      setSessions([]);
    }
  }, [activeSession?.sessionToken, refreshDevices]);

  const localhost = isLocalhostUrl(apiBaseUrl);

  async function onPairIphone() {
    if (!activeSession?.sessionToken) return;
    setPairOpen(true);
    setPairLoading(true);
    setPairError(null);
    setPairing(null);
    try {
      const out = await startDevicePairing(apiBaseUrl, activeSession.sessionToken, fetcher);
      setPairing(out);
    } catch (err) {
      setPairError(err instanceof Error ? err.message : "Failed to start pairing");
    } finally {
      setPairLoading(false);
    }
  }

  async function onRevokeSession(sessionId: string) {
    if (!activeSession?.sessionToken) return;
    try {
      await revokeDeviceSession(apiBaseUrl, activeSession.sessionToken, sessionId, fetcher);
      if (sessionId === activeSession.sessionId && auth) {
        await auth.signOut();
      } else {
        await refreshDevices();
      }
    } catch (err) {
      setSessionsError(err instanceof Error ? err.message : "Could not revoke device");
    }
  }

  function handleDemoToggle(next: boolean) {
    setLocalDemo(next);
    auth?.setDemoMode(next);
  }

  return (
    <ScrollView style={styles.screen} testID="connect-screen">
      <Text style={styles.title}>Connect</Text>

      <View style={styles.card} testID="account-card">
        <Text style={styles.sectionTitle}>Account</Text>
        {auth?.authError || accountError ? (
          <Text style={styles.warning} testID="account-error">
            {auth?.authError ?? accountError}
          </Text>
        ) : null}
        {activeSession ? (
          <>
            <Text style={styles.accountName} testID="signed-in-name">
              {activeSession.displayName ?? "Signed-in account"}
            </Text>
            {activeSession.email ? (
              <Text style={styles.meta} testID="signed-in-email">
                {activeSession.email}
              </Text>
            ) : null}
            <Pressable style={styles.button} onPress={() => void onPairIphone()} testID="pair-iphone-btn">
              <Text style={styles.buttonText}>Pair your iPhone</Text>
            </Pressable>
            <Pressable
              style={styles.button}
              onPress={() => void (auth ? auth.signOut(apiBaseUrl) : Promise.resolve())}
              testID="sign-out-btn"
            >
              <Text style={styles.buttonText}>Sign out</Text>
            </Pressable>

            <Text style={styles.label}>Signed-in devices</Text>
            {sessionsError ? <Text style={styles.warning}>{sessionsError}</Text> : null}
            {sessions.map((s) => (
              <View key={s.session_id} style={styles.deviceRow} testID={`device-row-${s.session_id}`}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.deviceLabel}>
                    {s.device_label || s.app_id}
                    {s.is_current ? " · This device" : ""}
                  </Text>
                  <Text style={styles.meta}>{s.created_at}</Text>
                </View>
                <Pressable
                  style={styles.revokeBtn}
                  onPress={() => void onRevokeSession(s.session_id)}
                  testID={`revoke-${s.session_id}`}
                >
                  <Text style={styles.revokeText}>Revoke</Text>
                </Pressable>
              </View>
            ))}
          </>
        ) : (
          <>
            <Text style={styles.meta} testID="signed-out-label">
              Not signed in. Sign in with Google on PC or scan a pairing QR code on your iPhone.
            </Text>
            <Pressable
              style={styles.button}
              onPress={() => {
                setAccountError(null);
                void startGoogleSignIn(apiBaseUrl).catch((err: unknown) => {
                  setAccountError(err instanceof Error ? err.message : "Could not open Google sign-in");
                });
              }}
              testID="google-signin-btn"
            >
              <Text style={styles.buttonText}>Sign in with Google</Text>
            </Pressable>
            <Pressable style={styles.button} onPress={() => setScanOpen(true)} testID="scan-qr-btn">
              <Text style={styles.buttonText}>Scan QR to Pair iPhone</Text>
            </Pressable>
          </>
        )}
      </View>

      <CompletenessRingCard />
      <InitialRevealCard />

      <Text style={styles.label}>API Server URL</Text>
      <TextInput
        style={styles.input}
        value={apiBaseUrl}
        onChangeText={setApiBaseUrl}
        autoCapitalize="none"
        autoCorrect={false}
        placeholder="http://192.168.x.x:8000"
      />
      {localhost ? <Text style={styles.warning}>{LOCALHOST_WARNING}</Text> : null}

      <View style={styles.row}>
        <Text>Demo mode</Text>
        <Switch value={demo} onValueChange={handleDemoToggle} testID="demo-mode-switch" />
      </View>
      {demo ? <Text style={styles.demoPill}>Demo data</Text> : null}

      <Pressable
        style={styles.button}
        onPress={() => {
          onApiBaseUrlChange?.(apiBaseUrl);
          void saveSettings(apiBaseUrl, effectiveOwner, demo).then(() => setSaved("Saved"));
        }}
      >
        <Text style={styles.buttonText}>Save settings</Text>
      </Pressable>
      {saved ? <Text style={styles.meta}>{saved}</Text> : null}

      <Pressable
        style={styles.button}
        onPress={() => {
          setStatus("unknown");
          void testConnection(apiBaseUrl, fetcher).then(setStatus);
        }}
      >
        <Text style={styles.buttonText}>Test Connection</Text>
      </Pressable>
      <Text style={styles.meta}>
        {status === "reachable" ? "Server reachable" : status === "offline" ? "Offline — server unreachable" : "Not tested yet"}
      </Text>

      <SourcesCard apiBaseUrl={apiBaseUrl} sessionToken={activeSession?.sessionToken ?? null} fetcher={fetcher} />

      <YoutubeOnboardingCard apiBaseUrl={apiBaseUrl} sessionToken={activeSession?.sessionToken ?? null} fetcher={fetcher} />
      <WhatsappImportCard apiBaseUrl={apiBaseUrl} sessionToken={activeSession?.sessionToken ?? null} fetcher={fetcher} />

      <PairIphoneModal
        visible={pairOpen}
        pairing={pairing}
        loading={pairLoading}
        error={pairError}
        onClose={() => setPairOpen(false)}
      />
      <ScanQrModal
        visible={scanOpen}
        onSubmitCode={async (code, scannedBase) => {
          if (!auth) throw new Error("Auth provider is required to store paired session.");
          await auth.completePairing(scannedBase ?? apiBaseUrl, code);
          if (scannedBase) {
            setApiBaseUrl(scannedBase);
            onApiBaseUrlChange?.(scannedBase);
            await saveSettings(scannedBase, effectiveOwner, demo);
          }
        }}
        onClose={() => setScanOpen(false)}
      />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: "#FFFFFF", padding: 16 },
  title: { fontSize: 22, fontWeight: "800", color: "#1E2022", marginBottom: 12 },
  card: {
    borderWidth: 1,
    borderColor: "#E8E8EC",
    borderRadius: 16,
    padding: 14,
    marginBottom: 12,
    backgroundColor: "#FAF8F5",
  },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#1E2022", marginBottom: 4 },
  accountName: { fontSize: 16, fontWeight: "700", color: "#1E2022" },
  deviceRow: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#E8E8EC",
    borderRadius: 12,
    padding: 10,
    marginTop: 8,
    backgroundColor: "#FFFFFF",
  },
  deviceLabel: { fontSize: 14, fontWeight: "600", color: "#1E2022" },
  revokeBtn: {
    borderWidth: 1,
    borderColor: "#B3261E",
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  revokeText: { color: "#B3261E", fontSize: 12, fontWeight: "700" },
  label: { fontSize: 13, fontWeight: "600", marginTop: 12, color: "#1E2022" },
  input: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 12, padding: 10, marginTop: 6, backgroundColor: "#FAF8F5" },
  warning: { color: "#B3261E", marginTop: 6, fontSize: 13 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: 12 },
  button: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 12, padding: 10, alignItems: "center", backgroundColor: "#FDF8EE", marginTop: 12, shadowOpacity: 0, elevation: 0 },
  buttonText: { fontWeight: "700", color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A", marginTop: 6 },
  demoPill: { alignSelf: "flex-start", borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3, fontSize: 12, fontWeight: "700", backgroundColor: "#FAF8F5", marginTop: 8 },
});
