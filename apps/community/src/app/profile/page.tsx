"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import MemoryPanel from "@/components/MemoryPanel";
import * as api from "@/lib/api";
import { seedProfile } from "@/lib/seed";
import type { Profile } from "@/lib/types";
import { isSignedIn } from "@/lib/session";

const AGE_BANDS = [
  { value: "18+", label: "18 or older" },
  { value: "18-24", label: "18–24" },
  { value: "25-34", label: "25–34" },
  { value: "35-44", label: "35–44" },
  { value: "45-54", label: "45–54" },
  { value: "55+", label: "55+" },
  { value: "under-18", label: "Under 18 (will be refused — adults only)" },
];
const PRIVACY = [
  { value: "public", label: "Public" },
  { value: "followers", label: "Followers only" },
  { value: "private", label: "Private" },
];

export default function ProfilePage() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [demo, setDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [editing, setEditing] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn()) { setSignedIn(false); setDemo(true); setProfile(seedProfile); setLoadFailed(false); return; }
    setSignedIn(true);
    try {
      const p = await api.getMyProfile();
      setDemo(false); setProfile(p); setNotice(null); setLoadFailed(false);
    } catch (e) {
      // Signed-in users never see fixture data: show the honest error instead.
      setDemo(false); setProfile(null); setLoadFailed(true);
      setNotice(`Could not load your profile — ${(e as Error).message || "community service unavailable"}.`);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  return (
    <section>
      <h1>Profile</h1>
      <p className="sub">Your public community identity.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {signedIn === false && (
        <div className="notice" role="status">Sign in to manage your community profile. <Link href="/signin">Sign in</Link></div>
      )}
      {signedIn && !profile && !demo && !loadFailed && (
        <article className="card" data-testid="no-profile">
          <h2>No profile yet</h2>
          <p>You have not created a community profile. It stays private until you create one.</p>
        </article>
      )}
      {profile && !editing && (
        <article className="card">
          <h2>
            {profile.display_name || profile.handle}{" "}
            <span className="handle">@{profile.handle}</span>{" "}
            {demo && <DemoPill />}
          </h2>
          <p>{profile.bio}</p>
          <p className="meta">
            {profile.area}{profile.interests?.length ? ` · ${profile.interests.join(", ")}` : ""} · {profile.privacy}
          </p>
          {signedIn && !demo && (
            <button type="button" className="action-box" style={{ maxWidth: 180 }} onClick={() => setEditing(true)}>Edit profile</button>
          )}
          {demo && (
            <button type="button" className="action-box" style={{ maxWidth: 180 }}
              onClick={() => setNotice("Message: Messaging lives in the Messenger app")}>Message</button>
          )}
        </article>
      )}
      {signedIn && editing && (
        <ProfileForm
          initial={profile}
          onSaved={(p) => { setProfile(p); setEditing(false); }}
          onCancel={() => setEditing(false)}
        />
      )}
      {!profile && signedIn && !demo && !loadFailed && (
        <ProfileForm initial={null} onSaved={(p) => { setProfile(p); setLoadFailed(false); }} onCancel={() => {}} creating />
      )}
      <MemoryPanel />
    </section>
  );
}

function ProfileForm({ initial, onSaved, onCancel, creating = false }: {
  initial: Profile | null; onSaved: (p: Profile) => void; onCancel: () => void; creating?: boolean;
}) {
  const [handle, setHandle] = useState(initial?.handle ?? "");
  const [displayName, setDisplayName] = useState(initial?.display_name ?? "");
  const [bio, setBio] = useState(initial?.bio ?? "");
  const [area, setArea] = useState(initial?.area ?? "");
  const [interests, setInterests] = useState((initial?.interests ?? []).join(", "));
  const [ageBand, setAgeBand] = useState("18+");
  const [privacy, setPrivacy] = useState<"public" | "private" | "followers">((initial?.privacy as "public" | "private" | "followers") ?? "public");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    setBusy(true); setError(null);
    try {
      const p = await api.upsertProfile({
        handle: handle.trim(),
        display_name: displayName.trim(),
        bio: bio.trim(),
        area: area.trim(),
        interests: interests.split(",").map((s) => s.trim()).filter(Boolean),
        age_band: ageBand,
        privacy,
      });
      onSaved(p);
    } catch (e) {
      setError((e as Error).message || "Could not save profile");
    } finally { setBusy(false); }
  }

  return (
    <article className="card" data-testid="profile-form">
      <h2>{creating ? "Create your profile" : "Edit profile"}</h2>
      <div className="user-box">
        <label htmlFor="pf-handle">Handle</label>
        <input id="pf-handle" value={handle} onChange={(e) => setHandle(e.target.value)} maxLength={30} placeholder="3-30 chars: a-z, 0-9, _" />
        <label htmlFor="pf-name" style={{ marginTop: 8, display: "block" }}>Display name</label>
        <input id="pf-name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} maxLength={80} />
        <label htmlFor="pf-bio" style={{ marginTop: 8, display: "block" }}>Bio</label>
        <input id="pf-bio" value={bio} onChange={(e) => setBio(e.target.value)} maxLength={500} />
        <label htmlFor="pf-area" style={{ marginTop: 8, display: "block" }}>Area</label>
        <input id="pf-area" value={area} onChange={(e) => setArea(e.target.value)} maxLength={80} placeholder="e.g. Dubai Marina" />
        <label htmlFor="pf-interests" style={{ marginTop: 8, display: "block" }}>Interests (comma separated)</label>
        <input id="pf-interests" value={interests} onChange={(e) => setInterests(e.target.value)} placeholder="reading, walking" />
        <label htmlFor="pf-age" style={{ marginTop: 8, display: "block" }}>Age band</label>
        <select id="pf-age" value={ageBand} onChange={(e) => setAgeBand(e.target.value)}>
          {AGE_BANDS.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
        </select>
        <label htmlFor="pf-privacy" style={{ marginTop: 8, display: "block" }}>Who can see your profile details</label>
        <select id="pf-privacy" value={privacy} onChange={(e) => setPrivacy(e.target.value as typeof privacy)}>
          {PRIVACY.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      <button type="button" className="primary" disabled={busy || !handle.trim()} onClick={submit}>
        {busy ? "Saving…" : creating ? "Create profile" : "Save"}
      </button>
      {!creating && <button type="button" className="action-box" style={{ maxWidth: 120, marginLeft: 8 }} onClick={onCancel}>Cancel</button>}
      <p className="meta" style={{ marginTop: 10 }}>Community is adults-only (18+). Under-18 bands are refused by the server.</p>
    </article>
  );
}
