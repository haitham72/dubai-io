"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import * as api from "@/lib/api";
import { seedGroups } from "@/lib/seed";
import type { Group } from "@/lib/types";
import { isSignedIn } from "@/lib/session";

export default function CommunitiesPage() {
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [groups, setGroups] = useState<Group[]>([]);
  const [demo, setDemo] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [groupError, setGroupError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn()) { setSignedIn(false); setDemo(true); setGroups(seedGroups); return; }
    setSignedIn(true); setDemo(false);
    try {
      setGroups(await api.getGroups());
    } catch {
      setDemo(true); setGroups(seedGroups);
      setNotice("Community service unavailable — showing demo preview communities below.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function toggleJoin(g: Group) {
    if (busyId) return;
    setBusyId(g.id); setGroupError(null);
    try {
      if (g.is_member) {
        if (g.my_role === "owner") { setGroupError(`${g.name}: the group owner cannot leave their own group.`); return; }
        await api.leaveGroup(g.id);
      } else {
        await api.joinGroup(g.id);
      }
      await load();
    } catch (e) {
      setGroupError((e as Error).message || "Could not update membership");
    } finally { setBusyId(null); }
  }

  return (
    <section>
      <h1>Communities</h1>
      <p className="sub">Groups around shared interests and places.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {groupError && <div className="error" role="alert">{groupError}</div>}
      {signedIn && (
        <button type="button" className="action-box" style={{ maxWidth: 200, marginBottom: 14 }} onClick={() => setShowCreate((v) => !v)}>
          {showCreate ? "Close" : "Create a community"}
        </button>
      )}
      {showCreate && signedIn && <CreateGroupForm onCreated={() => { setShowCreate(false); void load(); }} />}
      {signedIn === false && (
        <div className="notice" role="status">Sign in to see and join real communities. <Link href="/signin">Sign in</Link></div>
      )}
      {signedIn !== null && groups.length === 0 && !demo && <p className="empty">No communities yet.</p>}
      {groups.map((g) => (
        <article key={g.id} className="card">
          <h2>
            <Link href={`/communities/${encodeURIComponent(g.id)}`}>{g.name}</Link>{" "}
            {demo && g.provenance === "demo_fixture" && <DemoPill />}
          </h2>
          <p>{g.description}</p>
          <p className="meta">
            {g.member_count ?? g.members ?? 0} members · {g.visibility}
            {g.visibility === "private" ? " · Invite only — private communities are hidden from non-members." : ""}
          </p>
          {!demo && (
            <button type="button" className="action-box" style={{ maxWidth: 180 }} disabled={busyId === g.id}
              onClick={() => toggleJoin(g)}>
              {busyId === g.id ? "…" : g.is_member ? "Leave" : g.visibility === "private" ? "Request invite" : "Join"}
            </button>
          )}
          {demo && (
            <button type="button" className="action-box" style={{ maxWidth: 180 }}>
              {g.is_member ? "Joined" : g.visibility === "private" ? "Request invite" : "Join"}
            </button>
          )}
        </article>
      ))}
    </section>
  );
}

function CreateGroupForm({ onCreated }: { onCreated: () => void }) {
  const [name, setName] = useState("");
  const [handle, setHandle] = useState("");
  const [description, setDescription] = useState("");
  const [visibility, setVisibility] = useState<"public" | "private">("public");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit() {
    if (!name.trim()) { setError("Give the community a name first."); return; }
    setBusy(true); setError(null);
    try {
      await api.createGroup({
        name: name.trim(),
        ...(handle.trim() ? { handle: handle.trim() } : {}),
        description: description.trim(),
        visibility,
      });
      onCreated();
    } catch (e) {
      setError((e as Error).message || "Could not create the community");
    } finally { setBusy(false); }
  }

  return (
    <article className="card" data-testid="create-group">
      <h2>New community</h2>
      <div className="user-box">
        <label htmlFor="cg-name">Name</label>
        <input id="cg-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={100} />
        <label htmlFor="cg-handle" style={{ marginTop: 8, display: "block" }}>Handle (optional)</label>
        <input id="cg-handle" value={handle} onChange={(e) => setHandle(e.target.value)} maxLength={40} placeholder="my-community" />
        <label htmlFor="cg-desc" style={{ marginTop: 8, display: "block" }}>Description</label>
        <input id="cg-desc" value={description} onChange={(e) => setDescription(e.target.value)} maxLength={500} />
        <label htmlFor="cg-vis" style={{ marginTop: 8, display: "block" }}>Visibility</label>
        <select id="cg-vis" value={visibility} onChange={(e) => setVisibility(e.target.value as "public" | "private")}>
          <option value="public">Public — anyone can find and join</option>
          <option value="private">Private — invite and moderator approval only</option>
        </select>
      </div>
      {error && <div className="error" role="alert">{error}</div>}
      <button type="button" className="primary" disabled={busy} onClick={submit}>{busy ? "Creating…" : "Create"}</button>
    </article>
  );
}
