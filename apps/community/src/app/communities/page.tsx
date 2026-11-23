"use client";
import { useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import { getGroups } from "@/lib/api";
import { seedGroups } from "@/lib/seed";
import type { Group } from "@/lib/types";

export default function CommunitiesPage() {
  const [groups, setGroups] = useState<Group[]>(seedGroups);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    getGroups()
      .then((g) => { if (live && g.length) setGroups(g); })
      .catch(() => { if (live) setNotice("Community service unavailable — showing demo preview communities below."); });
    return () => { live = false; };
  }, []);

  return (
    <section>
      <h1>Communities</h1>
      <p className="sub">Groups around shared interests and places.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {groups.length === 0 && <p className="empty">No communities yet.</p>}
      {groups.map((g) => (
        <article key={g.id} className="card">
          <h2>{g.name} {g.provenance === "demo_fixture" && <DemoPill />}</h2>
          <p>{g.description}</p>
          <p className="meta">
            {g.member_count ?? g.members ?? 0} members · {g.visibility}
            {g.visibility === "private" ? " · Invite only — private communities are hidden from non-members." : ""}
          </p>
          <button type="button" className="action-box" style={{ maxWidth: 180 }}>
            {g.is_member ? "Joined" : g.visibility === "private" ? "Request invite" : "Join"}
          </button>
        </article>
      ))}
    </section>
  );
}
