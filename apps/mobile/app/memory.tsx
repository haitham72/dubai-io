import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { PillarFallback } from "../src/components/PillarFallback";
import { useApiSettings } from "../src/lib/api-settings";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";
import { vaultScreen } from "../src/lib/feature-slots";

export default function MemoryRoute() {
  const { apiBaseUrl } = useApiSettings();
  const Screen = vaultScreen;
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      {Screen ? (
        <Screen ownerId={DEMO_OWNER_ID} apiBaseUrl={apiBaseUrl} demo />
      ) : (
        <PillarFallback
          title="Memory"
          body="The knowledge vault lands with the Memory screen. No facts are shown as verified from this shell."
        />
      )}
    </SafeAreaView>
  );
}
