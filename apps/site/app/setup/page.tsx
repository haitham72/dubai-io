import type { Metadata } from "next";
import { FunnelShell } from "@/components/funnel";
import SetupWizard from "./wizard";

export const metadata: Metadata = {
  title: "Set up Dubai-io",
  description: "Tell Dubai-io your area, household and services. Skip any question.",
};

export default function Setup() {
  return (
    <FunnelShell step={1} skipHref="/first-win" skipLabel="Skip setup">
      <SetupWizard />
    </FunnelShell>
  );
}
