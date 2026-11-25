import { useEffect, useMemo, useState } from "react";
import { BrainCircuit } from "lucide-react";
import { Button } from "../../ui";
import { useStore } from "../../store";
import { createMemoryClient, type LowerResult, type MemoryClient, type MemoryState } from "../../apiclient/memory";
import { Group, Row, ToggleRow } from "../shared";

/** Settings > Memory. Everything shown (switch, saved items, results) is what the server returned. */
export function MemorySection({ client }: { client: MemoryClient }) {
  const [data, setData] = useState<MemoryState | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [lowerResult, setLowerResult] = useState<LowerResult | null>(null);

  useEffect(() => {
    let live = true;
    client.state().then((d) => { if (live) setData(d); }).catch((e: Error) => { if (live) setLoadError(e.message); });
    return () => { live = false; };
  }, [client]);

  async function setConsent(enabled: boolean) {
    if (busy) return;
    setBusy(true); setError(null);
    try {
      const r = await client.setConsent(enabled);
      setData((d) => (d ? { ...d, enabled: r.enabled, as_of: r.as_of } : d)); // from the response only
    } catch (e) { setError(`Not changed: ${(e as Error).message}`); } finally { setBusy(false); }
  }

  async function setLowered(recordId: string, lower: boolean) {
    if (busy) return;
    setBusy(true); setError(null); setLowerResult(null);
    try {
      setLowerResult(await client.setLowered(recordId, lower));
      setData(await client.state()); // the list is re-read from the server, not edited locally
    } catch (e) { setError(`Memory update did not complete: ${(e as Error).message}`); } finally { setBusy(false); }
  }

  return (
    <Group title="Memory">
      {loadError && <p role="alert">Memory status unavailable: {loadError}</p>}
      {!data && !loadError && <p>Loading memory status…</p>}
      {data && <>
        <ToggleRow label="Let Messenger extract memories" on={data.enabled} onChange={setConsent}
          detail={`Off by default. Messages are never saved without your tap. As of ${data.as_of || "not set yet"}.`} />
        {data.items.length === 0 && <Row icon={BrainCircuit} label="Nothing saved from Messenger" />}
        {data.items.map((i) => (
          <Row key={i.record_id} icon={BrainCircuit}
            label={i.text ?? "(the original message was deleted)"}
            value={`${i.written_by_you ? "You wrote this" : "Another member wrote this"} · saved ${i.saved_at}${i.provenance ? ` · ${i.provenance}` : ""}`}>
            <Button onClick={() => setLowered(i.record_id, !i.lowered)} disabled={busy}>{i.lowered ? "Restore" : "Lower"}</Button>
          </Row>
        ))}
      </>}
      {error && <p role="alert">{error}</p>}
      {lowerResult && <p role="status" data-testid="forget-result">Server reports {lowerResult.records_lowerResultten} record(s) and {lowerResult.facts_erased} fact(s) lowerResultten (as of {lowerResult.as_of}).</p>}
    </Group>
  );
}

export default function MemorySettings() {
  const token = useStore((st) => (st.mode === "real" && st.auth.status === "signed_in" ? st.auth.sessionToken : null));
  const client = useMemo(() => (token ? createMemoryClient(token) : null), [token]);
  if (!client) {
    return <Group title="Memory"><Row icon={BrainCircuit} label="Sign in to manage memory" value="Memory is off until you sign in and turn it on" /></Group>;
  }
  return <MemorySection client={client} />;
}
