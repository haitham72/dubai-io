import React from "react";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { TodayView } from "../src/components/TodayView";
import { useApiSettings } from "../src/lib/api-settings";
import { useAuth } from "../src/lib/auth";

export default function TodayRoute() {
  const router = useRouter();
  const { apiBaseUrl } = useApiSettings();
  const { session, demoMode } = useAuth();
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      <TodayView
        onOpenSettings={() => router.push("/connect")}
        apiBaseUrl={apiBaseUrl}
        sessionToken={session?.sessionToken ?? null}
        displayName={session?.displayName ?? null}
        demo={demoMode}
      />
    </SafeAreaView>
  );
}
