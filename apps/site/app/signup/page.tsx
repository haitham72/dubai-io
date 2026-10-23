import type { Metadata } from "next";
import { FunnelShell } from "@/components/funnel";
import SignupForm from "./form";

export const metadata: Metadata = {
  title: "Start with Dubai-io",
  description: "Open a private session in this browser and set up Dubai-io.",
};

export default function Signup() {
  return (
    <FunnelShell step={0} skipHref="/demo" skipLabel="Try the demo instead">
      <SignupForm />
    </FunnelShell>
  );
}
