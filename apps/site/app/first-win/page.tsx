import type { Metadata } from "next";
import { FunnelShell } from "@/components/funnel";
import FirstTask from "./task";

export const metadata: Metadata = {
  title: "Your first task",
  description: "Add one task to your Dubai-io list. Nothing is sent.",
};

export default function FirstWin() {
  return (
    <FunnelShell step={2} skipHref="/dashboard" skipLabel="Skip for now">
      <FirstTask />
    </FunnelShell>
  );
}
