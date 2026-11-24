import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { PillarFallback } from "../src/components/PillarFallback";
import { useApiSettings } from "../src/lib/api-settings";
import { useAuth } from "../src/lib/auth";
import { vaultScreen } from "../src/lib/feature-slots";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";

export default function MemoryRoute() {
  const { apiBaseUrl } = useApiSettings();
  const { session, demoMode } = useAuth();
  const Screen = vaultScreen;
  const ownerId = demoMode ? DEMO_OWNER_ID : session?.userId ?? "";
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      {Screen ? (
        <Screen
          ownerId={ownerId}
          apiBaseUrl={apiBaseUrl}
          demo={demoMode}
          sessionToken={session?.sessionToken ?? null}
        />
      ) : (
        <PillarFallback
          title="Memory"
          body="The knowledge vault lands with the Memory screen. No facts are shown as verified from this shell."
        />
      )}
    </SafeAreaView>
  );
}
