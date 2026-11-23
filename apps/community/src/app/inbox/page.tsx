"use client";
import { useEffect, useState } from "react";
import DemoPill from "@/components/DemoPill";
import { getNotifications, markNotificationRead } from "@/lib/api";
import { seedNotifications } from "@/lib/seed";
import type { Notification } from "@/lib/types";

export default function InboxPage() {
  const [items, setItems] = useState<Notification[]>(seedNotifications);
  const [isDemo, setIsDemo] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [handoff, setHandoff] = useState(false);

  useEffect(() => {
    let live = true;
    getNotifications()
      .then((r) => { if (live && r.notifications.length) { setItems(r.notifications); setIsDemo(false); } })
      .catch(() => { if (live) setNotice("Community service unavailable — showing demo preview notifications below."); });
    return () => { live = false; };
  }, []);

  async function markRead(id: string) {
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true, read: true } : n)));
    try { await markNotificationRead(id); } catch { /* local preview state only */ }
  }

  return (
    <section>
      <h1>Inbox</h1>
      <p className="sub">Notifications only — replies, mentions and community updates.</p>
      {notice && <div className="notice" role="status">{notice}</div>}
      {items.length === 0 && <p className="empty">No notifications yet.</p>}
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
