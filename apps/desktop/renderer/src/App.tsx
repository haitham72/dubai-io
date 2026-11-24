import { AppShell } from "./panels/AppShell";
import { DEMO_SESSIONS, resolveBridge } from "./ipc/bridge";

export function App() {
  return <AppShell bridge={resolveBridge()} sessions={DEMO_SESSIONS} />;
}
