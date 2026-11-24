import React, { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { Tabs, usePathname, useRouter } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { colors, noShadow, radii, spacing, typography } from "@dubai-io/design-tokens";
import { CapsuleDock } from "../src/components/CapsuleDock";
import { ApiSettingsProvider } from "../src/lib/api-settings";
import { AuthProvider } from "../src/lib/auth";
import { DOCK_TABS, type PillarId } from "../src/lib/types";

function pillarFromPath(path: string): PillarId {
  if (path.startsWith("/chat")) return "chat";
  if (path.startsWith("/quests")) return "quests";
  if (path.startsWith("/memory")) return "memory";
  return "today";
}

function DockBar() {
  const router = useRouter();
  const pathname = usePathname();
  const [voiceOpen, setVoiceOpen] = useState(false);
  return (
    <>
      <CapsuleDock
        tabs={DOCK_TABS}
        active={pillarFromPath(pathname)}
        onTabPress={(tab) => router.push(tab.href)}
        onVoicePress={() => setVoiceOpen(true)}
      />
      <Modal transparent animationType="fade" visible={voiceOpen} onRequestClose={() => setVoiceOpen(false)}>
        <View style={styles.scrim}>
          <View style={styles.card} testID="voice-preview">
            <Text style={styles.title}>Voice capture preview</Text>
            <Text style={styles.body}>
              Speech-to-text is not connected. Nothing was recorded and nothing was transcribed.
            </Text>
            <Pressable accessibilityRole="button" onPress={() => setVoiceOpen(false)} style={styles.close}>
              <Text style={styles.closeText}>Close</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <ApiSettingsProvider>
        <AuthProvider>
          <StatusBar style="dark" />
          <Tabs screenOptions={{ headerShown: false }} tabBar={() => <DockBar />}>
            <Tabs.Screen name="index" options={{ title: "Today" }} />
            <Tabs.Screen name="chat" options={{ title: "Chat" }} />
            <Tabs.Screen name="quests" options={{ title: "Quests" }} />
            <Tabs.Screen name="memory" options={{ title: "Memory" }} />
            <Tabs.Screen name="connect" options={{ href: null, title: "Connect" }} />
          </Tabs>
        </AuthProvider>
      </ApiSettingsProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  scrim: {
    ...noShadow,
    alignItems: "center",
    backgroundColor: "rgba(30, 32, 34, 0.35)",
    flex: 1,
    justifyContent: "center",
    padding: spacing.lg,
  },
  card: {
    ...noShadow,
    backgroundColor: colors.canvas,
    borderColor: colors.gold.border,
    borderRadius: radii.card,
    borderWidth: 1,
    gap: spacing.md,
    padding: spacing.lg,
  },
  title: {
    color: colors.ink,
    fontFamily: typography.serif,
    fontSize: typography.title,
  },
  body: {
    color: colors.ink,
    fontSize: typography.body,
    lineHeight: 22,
  },
  close: {
    ...noShadow,
    alignSelf: "flex-start",
    backgroundColor: colors.gold.primary,
    borderRadius: radii.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  closeText: {
    color: colors.canvas,
    fontWeight: "700",
  },
});
