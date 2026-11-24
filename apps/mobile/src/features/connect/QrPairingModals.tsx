import React, { useMemo, useState } from "react";
import { Modal, Platform, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import QRCode from "qrcode";
import Svg, { Rect } from "react-native-svg";
import { parsePairingPayload } from "../../lib/auth";
import type { PairingStartOut } from "./connectApi";

export function QrCodeSvg({ value, size = 180 }: { value: string; size?: number }) {
  const matrix = useMemo(() => {
    const qr = QRCode.create(value, { errorCorrectionLevel: "M" });
    const count = qr.modules.size;
    const cells: Array<{ x: number; y: number }> = [];
    for (let r = 0; r < count; r += 1) {
      for (let c = 0; c < count; c += 1) {
        if (qr.modules.get(r, c)) cells.push({ x: c, y: r });
      }
    }
    return { count, cells };
  }, [value]);

  const cellSize = size / matrix.count;
  return (
    <View style={styles.qrFrame} testID="qr-code-svg">
      <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <Rect x={0} y={0} width={size} height={size} fill="#FFFFFF" />
        {matrix.cells.map((cell) => (
          <Rect
            key={`${cell.x}-${cell.y}`}
            x={cell.x * cellSize}
            y={cell.y * cellSize}
            width={cellSize}
            height={cellSize}
            fill="#1E2022"
          />
        ))}
      </Svg>
    </View>
  );
}

export function PairIphoneModal({
  visible,
  pairing,
  loading,
  error,
  onClose,
}: {
  visible: boolean;
  pairing: PairingStartOut | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}) {
  return (
    <Modal transparent animationType="fade" visible={visible} onRequestClose={onClose}>
      <View style={styles.scrim}>
        <View style={styles.modalCard} testID="pair-iphone-modal">
          <Text style={styles.modalTitle}>Pair your iPhone</Text>
          <Text style={styles.modalSub}>
            Scan this QR code in Dubai-io on your iPhone, or type the pairing code manually.
          </Text>
          {loading ? <Text style={styles.meta}>Generating pairing code…</Text> : null}
          {error ? <Text style={styles.error}>{error}</Text> : null}
          {pairing ? (
            <>
              <QrCodeSvg value={pairing.qr_payload} />
              <Text style={styles.codeLabel}>Manual code</Text>
              <Text style={styles.codeValue} selectable testID="pairing-code-text">
                {pairing.code}
              </Text>
              <Text style={styles.meta}>Expires in {pairing.ttl_seconds}s ({pairing.expires_at})</Text>
            </>
          ) : null}
          <Pressable style={styles.closeBtn} onPress={onClose} testID="close-pair-modal">
            <Text style={styles.closeText}>Done</Text>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

export function ScanQrModal({
  visible,
  onSubmitCode,
  onClose,
}: {
  visible: boolean;
  onSubmitCode: (codeOrPayload: string) => Promise<void>;
  onClose: () => void;
}) {
  const [manualCode, setManualCode] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scannedOnce, setScannedOnce] = useState(false);
  const [permission, requestPermission] = useCameraPermissions();

  async function submit(raw: string) {
    const parsed = parsePairingPayload(raw);
    if (!parsed) {
      setError("Enter or scan a valid pairing code.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await onSubmitCode(parsed);
      setManualCode("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not pair device.");
      setScannedOnce(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Modal transparent animationType="fade" visible={visible} onRequestClose={onClose}>
      <View style={styles.scrim}>
        <View style={styles.modalCard} testID="scan-qr-modal">
          <Text style={styles.modalTitle}>Pair with PC</Text>
          <Text style={styles.modalSub}>
            Scan the QR code shown on your PC, or enter the 8-character pairing code below.
          </Text>

          {Platform.OS !== "web" ? (
            permission?.granted ? (
              <View style={styles.cameraBox} testID="qr-camera-box">
                <CameraView
                  style={styles.camera}
                  barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
                  onBarcodeScanned={(event) => {
                    if (scannedOnce || submitting) return;
                    setScannedOnce(true);
                    void submit(event.data);
                  }}
                />
              </View>
            ) : (
              <Pressable style={styles.secondaryBtn} onPress={() => void requestPermission()} testID="grant-camera-btn">
                <Text style={styles.secondaryText}>Enable Camera to Scan QR</Text>
              </Pressable>
            )
          ) : null}

          <Text style={styles.codeLabel}>Pairing code</Text>
          <TextInput
            style={styles.input}
            value={manualCode}
            onChangeText={setManualCode}
            placeholder="ABCD2345"
            autoCapitalize="characters"
            autoCorrect={false}
            testID="pair-code-input"
          />
          {error ? (
            <Text style={styles.error} testID="pair-error">
              {error}
            </Text>
          ) : null}
          <View style={styles.actions}>
            <Pressable
              style={styles.primaryBtn}
              disabled={submitting}
              onPress={() => void submit(manualCode)}
              testID="pair-submit-btn"
            >
              <Text style={styles.primaryText}>{submitting ? "Pairing…" : "Pair device"}</Text>
            </Pressable>
            <Pressable style={styles.closeBtn} onPress={onClose} testID="close-scan-modal">
              <Text style={styles.closeText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  scrim: {
    flex: 1,
    backgroundColor: "rgba(30, 32, 34, 0.45)",
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
  },
  modalCard: {
    width: "100%",
    maxWidth: 380,
    backgroundColor: "#FFFFFF",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#E8D5A3",
    padding: 16,
    gap: 10,
  },
  modalTitle: { fontSize: 18, fontWeight: "800", color: "#1E2022" },
  modalSub: { fontSize: 13, color: "#5A5A5A", lineHeight: 18 },
  qrFrame: {
    alignSelf: "center",
    padding: 10,
    backgroundColor: "#FFFFFF",
    borderWidth: 1,
    borderColor: "#E8E8EC",
    borderRadius: 12,
  },
  cameraBox: {
    height: 180,
    borderRadius: 12,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#E8E8EC",
  },
  camera: { flex: 1 },
  codeLabel: { fontSize: 12, fontWeight: "700", color: "#5A5A5A" },
  codeValue: { fontSize: 22, fontWeight: "800", letterSpacing: 3, textAlign: "center", color: "#1E2022" },
  input: {
    borderWidth: 1,
    borderColor: "#E8E8EC",
    borderRadius: 12,
    padding: 10,
    backgroundColor: "#FAF8F5",
    color: "#1E2022",
    fontSize: 16,
  },
  meta: { fontSize: 12, color: "#5A5A5A", textAlign: "center" },
  error: { fontSize: 13, color: "#B3261E" },
  actions: { flexDirection: "row", gap: 10, justifyContent: "flex-end", marginTop: 4 },
  primaryBtn: {
    backgroundColor: "#C5A059",
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  primaryText: { color: "#FFFFFF", fontWeight: "700" },
  secondaryBtn: {
    borderWidth: 1,
    borderColor: "#E8D5A3",
    borderRadius: 12,
    padding: 10,
    alignItems: "center",
    backgroundColor: "#FDF8EE",
  },
  secondaryText: { color: "#1E2022", fontWeight: "700" },
  closeBtn: {
    borderWidth: 1,
    borderColor: "#E8E8EC",
    borderRadius: 999,
    paddingHorizontal: 16,
    paddingVertical: 10,
    alignSelf: "flex-end",
  },
  closeText: { color: "#1E2022", fontWeight: "600" },
});
