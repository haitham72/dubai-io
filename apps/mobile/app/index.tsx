import React from "react";
import { useRouter } from "expo-router";
import { SafeAreaView } from "react-native-safe-area-context";
import { colors } from "@dubai-io/design-tokens";
import { TodayView } from "../src/components/TodayView";

export default function TodayRoute() {
  const router = useRouter();
  return (
    <SafeAreaView edges={["top"]} style={{ flex: 1, backgroundColor: colors.canvas }}>
      <TodayView onOpenSettings={() => router.push("/connect")} />
    </SafeAreaView>
  );
}
