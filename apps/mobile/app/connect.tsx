import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { ConnectFallback } from "../src/components/ConnectFallback";
import { useApiSettings } from "../src/lib/api-settings";
import { useAuth } from "../src/lib/auth";
import { connectScreen } from "../src/lib/feature-slots";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";

export default function ConnectRoute() {
  const settings = useApiSettings();
  const { session, demoMode } = useAuth();
  const Screen = connectScreen;
  const ownerId = demoMode ? DEMO_OWNER_ID : session?.userId ?? "";
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      {Screen ? (
        <Screen
          ownerId={ownerId}
          apiBaseUrl={settings.apiBaseUrl}
          demo={demoMode}
          sessionToken={session?.sessionToken ?? null}
          localhostWarning={settings.warning}
          onApiBaseUrlChange={settings.setApiBaseUrl}
        />
      ) : (
        <ConnectFallback apiBaseUrl={settings.apiBaseUrl} onApiBaseUrlChange={settings.setApiBaseUrl} />
      )}
    </SafeAreaView>
  );
}
