import React from "react";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { PillarFallback } from "../src/components/PillarFallback";
import { useApiSettings } from "../src/lib/api-settings";
import { DEMO_OWNER_ID } from "../src/lib/fixtures";
import { questsScreen } from "../src/lib/feature-slots";

export default function QuestsRoute() {
  const { apiBaseUrl } = useApiSettings();
  const Screen = questsScreen;
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      {Screen ? (
        <Screen ownerId={DEMO_OWNER_ID} apiBaseUrl={apiBaseUrl} demo />
      ) : (
        <PillarFallback
          title="Quests"
          body="Goal cards land with the Quests screen. This shell never marks a milestone done."
        />
      )}
    </SafeAreaView>
  );
}
