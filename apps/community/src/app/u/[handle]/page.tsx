"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { Profile } from "@/lib/types";
import { isSignedIn } from "@/lib/session";

export default function UserProfilePage() {
  const params = useParams<{ handle: string }>();
  const handle = decodeURIComponent(String(params?.handle ?? ""));
  const [profile, setProfile] = useState<Profile | null>(null);
  const [state, setState] = useState<"loading" | "live" | "missing" | "signedout">("loading");
  const [following, setFollowing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isSignedIn()) { setState("signedout"); return; }
    try {
      const [p, follows] = await Promise.all([
        api.getProfile(handle),
        api.getFollows().catch(() => [] as { handle: string | null }[]),
      ]);
      setProfile(p);
      setFollowing(follows.some((f) => (f.handle ?? "").toLowerCase() === handle.toLowerCase()));
      setState("live");
    } catch (e) {
      setState((e as { status?: number })?.status === 404 ? "missing" : "missing");
      setError((e as Error).message || "Profile not found");
    }
  }, [handle]);

  useEffect(() => { void load(); }, [load]);

  async function toggleFollow() {
    if (busy) return;
    setBusy(true); setError(null);
    const was = following;
    setFollowing(!was);
    try {
      if (was) await api.unfollow(handle); else await api.follow(handle);
    } catch (e) {
      setFollowing(was);
      setError((e as Error).message || "Follow failed");
    } finally { setBusy(false); }
  }

  if (state === "signedout") {
    return (
      <section>
        <h1>Profile</h1>
        <div className="notice" role="status">Sign in to see profiles. <Link href="/signin">Sign in</Link></div>
      </section>
    );
  }
  if (state === "loading") return <section><h1>Profile</h1><p className="empty">Loading…</p></section>;
  if (state === "missing" || !profile) {
    return (
      <section>
        <h1>Profile</h1>
        <div className="error" role="alert">{error ?? "Profile not found"}</div>
      </section>
    );
  }

  return (
    <section>
      <p><Link href="/">← Feed</Link></p>
      <article className="card" data-testid="user-profile">
        <h2>{profile.display_name || profile.handle} <span className="handle">@{profile.handle}</span></h2>
        <p>{profile.bio}</p>
        <p className="meta">
          {profile.area}{profile.interests?.length ? ` · ${profile.interests.join(", ")}` : ""} · {profile.privacy}
        </p>
        {profile.mine ? (
          <p className="meta">This is your profile. <Link href="/profile">Edit it</Link></p>
        ) : (
          <button type="button" className="action-box" style={{ maxWidth: 160 }} disabled={busy}
            aria-pressed={following} onClick={toggleFollow}>
            {busy ? "…" : following ? "Following" : "Follow"}
          </button>
        )}
        {error && <div className="error" role="alert">{error}</div>}
      </article>
    </section>
  );
}
