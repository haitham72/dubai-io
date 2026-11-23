"use client";
import { useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import { getMyProfile } from "@/lib/api";
import { seedProfile } from "@/lib/seed";
import type { Profile } from "@/lib/types";

const TOGGLES = [
  { id: "interests", label: "Share my interests with Community", hint: "Used only to order Discover results." },
  { id: "saved", label: "Remember discussions I save", hint: "Saved posts can be recalled later." },
  { id: "posts", label: "Remember my public posts", hint: "Only posts you authored, with provenance." },
] as const;

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(seedProfile);
  const [notice, setNotice] = useState<string | null>(null);
  const [on, setOn] = useState<Record<string, boolean>>({ interests: true, saved: false, posts: false });

  useEffect(() => {
    let live = true;
    getMyProfile()
      .then((p) => { if (live && p?.handle) setProfile(p); })
      .catch(() => { if (live) setNotice("Community service unavailable — showing the demo preview profile below."); });
    return () => { live = false; };
  }, []);

  return (
    <section>
      <h1>Profile</h1>
      <p className="sub">Your public community identity.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      <article className="card">
        <h2>{profile.display_name || profile.handle} <span className="handle">@{profile.handle}</span> {profile.provenance === "demo_fixture" && <DemoPill />}</h2>
        <p>{profile.bio}</p>
        <p className="meta">{profile.area}{profile.interests?.length ? ` · ${profile.interests.join(", ")}` : ""} · {profile.privacy}</p>
        <button type="button" className="action-box" style={{ maxWidth: 180 }} onClick={() => setNotice("Message: Messaging lives in the Messenger app")}>Message</button>
      </article>
      <article className="card">
        <h2>Connected Memory</h2>
        <p className="ai-text">Choose what Community may remember. These toggles are a preview only in this build — changing them here does not save anything yet.</p>
        {TOGGLES.map((t) => (
          <div key={t.id} className="toggle-row">
            <span>{t.label}<br /><span className="meta">{t.hint}</span></span>
            <button type="button" role="switch" aria-checked={!!on[t.id]} className="action-box" style={{ maxWidth: 90 }}
              onClick={() => setOn((prev) => ({ ...prev, [t.id]: !prev[t.id] }))}>
              {on[t.id] ? "On" : "Off"}
            </button>
          </div>
        ))}
        <button type="button" className="action-box" style={{ maxWidth: 200, marginTop: 14 }}>Forget connected memory</button>
        <p className="meta">Forget removes connected signals from Community. Preview only — no data is deleted from this screen yet.</p>
      </article>
    </section>
  );
}
