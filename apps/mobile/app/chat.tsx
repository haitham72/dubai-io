import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { ChatView } from "../src/components/ChatView";
import { useApiSettings } from "../src/lib/api-settings";
import { useAuth } from "../src/lib/auth";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";

export default function ChatRoute() {
  const { apiBaseUrl } = useApiSettings();
  const { session, demoMode } = useAuth();
  const ownerId = demoMode ? DEMO_OWNER_ID : session?.userId ?? "";
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      <ChatView
        ownerId={ownerId}
        apiBaseUrl={apiBaseUrl}
        sessionToken={session?.sessionToken ?? null}
        demo={demoMode}
      />
    </SafeAreaView>
  );
}
