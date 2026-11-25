"use client";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import * as api from "@/lib/api";
import { seedNotifications } from "@/lib/seed";
import type { Notification } from "@/lib/types";
import { isSignedIn } from "@/lib/session";

export default function InboxPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [isDemo, setIsDemo] = useState(false);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [handoff, setHandoff] = useState(false);

  const load = useCallback(async () => {
    if (!isSignedIn()) {
      setSignedIn(false); setIsDemo(true); setItems(seedNotifications);
      setNotice("Sign in to see your real notifications. Showing the demo preview below.");
      return;
    }
    setSignedIn(true);
    try {
      const r = await api.getNotifications();
      setItems(r.notifications); setIsDemo(false); setNotice(null);
    } catch {
      setIsDemo(true); setItems(seedNotifications);
      setNotice("Community service unavailable — showing demo preview notifications below.");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function markRead(id: string) {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true, read: true } : n)));
    try { await api.markNotificationRead(id); } catch { /* local preview state only */ }
  }

  async function markAll() {
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true, read: true })));
    try { await api.markAllNotificationsRead(); } catch { /* local preview state only */ }
  }

  return (
    <section>
      <h1>Inbox</h1>
      <p className="sub">Notifications only — replies, mentions and community updates.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {signedIn === false && <div className="notice" role="status">Sign in to see real notifications. <Link href="/signin">Sign in</Link></div>}
      {items.length === 0 && signedIn && <p className="empty">No notifications yet.</p>}
      {items.some((n) => !(n.is_read ?? n.read)) && (
        <button type="button" className="action-box" style={{ maxWidth: 160, marginBottom: 10 }} onClick={markAll}>Mark all read</button>
      )}
      {items.map((n) => {
        const read = n.is_read ?? n.read ?? false;
        return (
          <article key={n.id} className="card notif">
            <span className={read ? "dot read" : "dot"} aria-hidden="true" />
            <div>
              <p style={{ margin: 0 }}><strong>@{n.actor ?? "someone"}</strong> {n.text ?? n.kind ?? "sent an update"}</p>
              <p className="meta">{n.kind ?? n.type ?? "notification"}{n.created_at ? ` · ${n.created_at.slice(0, 10)}` : ""}</p>
              {!read && <button type="button" className="action-box" style={{ maxWidth: 160 }} onClick={() => markRead(n.id)}>Mark read</button>}
            </div>
            {isDemo && <DemoPill />}
          </article>
        );
      })}
      <div className="card">
        <h2>Messages</h2>
        <p>Private messaging is not part of this inbox.</p>
        <button type="button" className="action-box" style={{ maxWidth: 180 }} onClick={() => setHandoff(true)}>Message</button>
        {handoff && <div className="notice" role="status">Messaging lives in the Messenger app</div>}
      </div>
    </section>
  );
}
