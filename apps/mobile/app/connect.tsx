import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { ConnectFallback } from "../src/components/ConnectFallback";
import { useApiSettings } from "../src/lib/api-settings";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";
import { connectScreen } from "../src/lib/feature-slots";

export default function ConnectRoute() {
  const settings = useApiSettings();
  const Screen = connectScreen;
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      {Screen ? (
        <Screen
          ownerId={DEMO_OWNER_ID}
          apiBaseUrl={settings.apiBaseUrl}
          demo
          localhostWarning={settings.warning}
          onApiBaseUrlChange={settings.setApiBaseUrl}
        />
      ) : (
        <ConnectFallback apiBaseUrl={settings.apiBaseUrl} onApiBaseUrlChange={settings.setApiBaseUrl} />
      )}
    </SafeAreaView>
  );
}
