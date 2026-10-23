"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FunnelError, funnelStyles as s } from "@/components/funnel";
import { apiGet, describeError } from "@/lib/api";

interface SessionInfo {
  user_id?: string;
  mode?: string;
}

export default function SignupForm() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      // GET /api/session sets the anonymous session cookie. Nothing else.
      await apiGet<SessionInfo>("/api/session");
      router.push("/setup");
    } catch (err) {
      setError(describeError(err));
      setBusy(false);
    }
  }

  return (
    <>
      <h1>Start with a private session.</h1>
      <p className={s.lede}>
        Dubai-io opens a session in this browser, so it can remember what you
        tell it. It takes a second, then three short questions.
      </p>

      <div className={s.panel}>
        <h2>What this is, and is not</h2>
        <ul>
          <li>It is an anonymous session. No account is created.</li>
          <li>There is no email, password or card.</li>
          <li>
            Real sign-in is not built yet. If you clear this browser&apos;s
            data, you start fresh.
          </li>
        </ul>
      </div>

      {error ? (
        <FunnelError message={error} onRetry={start} busy={busy} />
      ) : null}

      <div className={s.actions}>
        <button
          type="button"
          className={s.btnPrimary}
          onClick={start}
          disabled={busy}
        >
          {busy ? "Opening session" : "Start setup"}
        </button>
        <Link href="/demo" className={s.textBtn}>
          Skip, try the demo
        </Link>
      </div>
    </>
  );
}
