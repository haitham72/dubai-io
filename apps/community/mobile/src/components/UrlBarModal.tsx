import React, { useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { normalizeCommunityUrl } from "../config/url";

export interface UrlBarModalProps {
  visible: boolean;
  currentUrl: string;
  defaultUrl: string;
  onSave: (normalizedUrl: string) => void;
  onReset: () => void;
  onClose: () => void;
}

export function UrlBarModal({
  visible,
  currentUrl,
  defaultUrl,
  onSave,
  onReset,
  onClose,
}: UrlBarModalProps): React.JSX.Element {
  const [draft, setDraft] = useState(currentUrl);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (visible) {
      setDraft(currentUrl);
      setValidationError(null);
    }
  }, [visible, currentUrl]);

  const handleSave = (): void => {
    const result = normalizeCommunityUrl(draft);
    if (!result.ok) {
      setValidationError(result.error);
      return;
    }
    setValidationError(null);
    onSave(result.url);
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <Text style={styles.title}>Community Server URL</Text>
          <Text style={styles.subtitle}>
            Use your PC&apos;s LAN IP (for example http://192.168.1.42:3060) or a
            Cloudflare Tunnel https:// URL.
          </Text>

          <TextInput
            value={draft}
            onChangeText={setDraft}
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="url"
            placeholder="http://192.168.1.42:3060"
            placeholderTextColor="#6a7784"
            style={styles.input}
          />

          {validationError ? (
            <Text style={styles.error}>{validationError}</Text>
          ) : null}

          <View style={styles.checklist}>
            <Text style={styles.checkHeading}>LAN Setup Checklist</Text>
            <Text style={styles.checkLine}>
              1. Run PC script: apps/community/scripts/start-shells.ps1
            </Text>
            <Text style={styles.checkLine}>
              2. Ensure inbound TCP port 3060 is allowed in Windows Firewall
            </Text>
            <Text style={styles.checkLine}>
              3. Scan the Expo QR code in Expo Go on the same Wi-Fi
            </Text>
            <Text style={styles.checkDefault}>Default: {defaultUrl}</Text>
          </View>

          <View style={styles.row}>
            <Pressable onPress={handleSave} style={styles.saveBtn}>
              <Text style={styles.saveText}>Save &amp; Load</Text>
            </Pressable>
            <Pressable onPress={onReset} style={styles.resetBtn}>
              <Text style={styles.resetText}>Reset</Text>
            </Pressable>
            <Pressable onPress={onClose} style={styles.cancelBtn}>
              <Text style={styles.cancelText}>Close</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(21, 32, 43, 0.45)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: "#ffffff",
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 32,
  },
  title: {
    color: "#15202b",
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 6,
  },
  subtitle: {
    color: "#6a7784",
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 14,
  },
  input: {
    borderWidth: 1,
    borderColor: "#e4ebf0",
    backgroundColor: "#f3f6f8",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 11,
    color: "#15202b",
    fontSize: 15,
    marginBottom: 8,
  },
  error: {
    color: "#b91c1c",
    fontSize: 13,
    marginBottom: 10,
  },
  checklist: {
    backgroundColor: "#f3f6f8",
    borderRadius: 12,
    padding: 12,
    marginTop: 4,
    marginBottom: 16,
  },
  checkHeading: {
    color: "#15202b",
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 4,
  },
  checkLine: {
    color: "#3d5563",
    fontSize: 12,
    lineHeight: 18,
  },
  checkDefault: {
    color: "#6a7784",
    fontSize: 11,
    marginTop: 6,
  },
  row: {
    flexDirection: "row",
    gap: 8,
  },
  saveBtn: {
    flex: 1,
    backgroundColor: "#128c9b",
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
  },
  saveText: {
    color: "#ffffff",
    fontWeight: "600",
    fontSize: 14,
  },
  resetBtn: {
    backgroundColor: "#eef3f6",
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
  },
  resetText: {
    color: "#15202b",
    fontWeight: "600",
    fontSize: 14,
  },
  cancelBtn: {
    backgroundColor: "#ffffff",
    borderWidth: 1,
    borderColor: "#e4ebf0",
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 14,
    alignItems: "center",
  },
  cancelText: {
    color: "#6a7784",
    fontWeight: "600",
    fontSize: 14,
  },
});
