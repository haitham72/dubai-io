import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { ChatView } from "../src/components/ChatView";
import { useApiSettings } from "../src/lib/api-settings";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";

export default function ChatRoute() {
  const { apiBaseUrl } = useApiSettings();
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      <ChatView ownerId={DEMO_OWNER_ID} apiBaseUrl={apiBaseUrl} />
    </SafeAreaView>
  );
}
