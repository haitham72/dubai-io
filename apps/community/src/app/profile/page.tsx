"use client";
import { useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import MemoryPanel from "@/components/MemoryPanel";
import { getMyProfile } from "@/lib/api";
import { seedProfile } from "@/lib/seed";
import type { Profile } from "@/lib/types";

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(seedProfile);
  const [notice, setNotice] = useState<string | null>(null);
  const [noProfile, setNoProfile] = useState(false);

  useEffect(() => {
    let live = true;
    getMyProfile()
      .then((p) => {
        if (!live) return;
        if (p?.handle) { setProfile(p); setNoProfile(false); } else setNoProfile(true);
      })
      .catch(() => { if (live) setNotice("Community service unavailable — showing the demo preview profile below."); });
    return () => { live = false; };
  }, []);

  return (
    <section>
      <h1>Profile</h1>
      <p className="sub">Your public community identity.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {noProfile ? (
        <article className="card" data-testid="no-profile">
          <h2>No profile yet</h2>
          <p>You have not created a community profile. It stays private until you create one.</p>
        </article>
      ) : (
      <article className="card">
        <h2>{profile.display_name || profile.handle} <span className="handle">@{profile.handle}</span> {profile.provenance === "demo_fixture" && <DemoPill />}</h2>
        <p>{profile.bio}</p>
        <p className="meta">{profile.area}{profile.interests?.length ? ` · ${profile.interests.join(", ")}` : ""} · {profile.privacy}</p>
        <button type="button" className="action-box" style={{ maxWidth: 180 }} onClick={() => setNotice("Message: Messaging lives in the Messenger app")}>Message</button>
      </article>
      )}
      <MemoryPanel />
    </section>
  );
}
