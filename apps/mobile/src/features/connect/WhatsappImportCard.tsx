import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import * as DocumentPicker from "expo-document-picker";
import type { Fetcher } from "../vault/vaultApi";
import { uploadIngestFile } from "./ingestApi";

export function WhatsappImportCard({ apiBaseUrl, sessionToken, fetcher }: {
  apiBaseUrl: string; sessionToken?: string | null; fetcher?: Fetcher;
}) {
  const [message, setMessage] = useState<string | null>(null);

  const pick = async () => {
    try {
      const picked = await DocumentPicker.getDocumentAsync({
        type: ["text/plain"], copyToCacheDirectory: true,
      });
      if (picked.canceled || !picked.assets?.length) return; // cancel: no-op
      const asset = picked.assets[0];
      if (!asset.name.toLowerCase().endsWith(".txt")) {
        setMessage("WhatsApp exports must be .txt files");
        return;
      }
      const res = await uploadIngestFile(apiBaseUrl, sessionToken, "whatsapp", asset, fetcher);
      setMessage(res.ok ? `Uploaded ${asset.name}${res.added !== null ? ` · ${res.added} new records` : ""}` : res.message);
    } catch {
      setMessage("Could not open the file picker");
    }
  };

  return (
    <View style={styles.card} testID="whatsapp-import">
      <Text style={styles.title}>WhatsApp Manual Export</Text>
      <Text style={styles.meta}>Export a chat as .txt on your phone, then upload it here. No linked-device automation.</Text>
      <Pressable style={styles.button} onPress={() => void pick()}>
        <Text style={styles.buttonText}>Pick WhatsApp .txt export</Text>
      </Pressable>
      {message ? <Text style={styles.meta}>{message}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { borderWidth: 1, borderColor: "#E8E8EC", borderRadius: 16, padding: 14, backgroundColor: "#FFFFFF", shadowOpacity: 0, elevation: 0, gap: 8 },
  title: { fontSize: 16, fontWeight: "700", color: "#1E2022" },
  meta: { fontSize: 12, color: "#5A5A5A" },
  button: { borderWidth: 1, borderColor: "#E8D5A3", borderRadius: 12, padding: 10, alignItems: "center", backgroundColor: "#FDF8EE", shadowOpacity: 0, elevation: 0 },
  buttonText: { fontWeight: "700", color: "#1E2022" },
});
