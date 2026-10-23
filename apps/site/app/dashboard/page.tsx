import type { Metadata } from "next";
import { FunnelShell } from "@/components/funnel";
import Handoff from "./handoff";

export const metadata: Metadata = {
  title: "You are set up",
  description: "Open Dubai-io with what you have told it so far.",
};

export default function Dashboard() {
  return (
    <FunnelShell step={3} skipHref="/" skipLabel="Back to the site">
      <Handoff />
    </FunnelShell>
  );
}
