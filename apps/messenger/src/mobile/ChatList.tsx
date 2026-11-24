// Mobile Chats tab: large title, search, the full-width Messenger strip, filter chips, chat rows.
import { useState } from "react";
import { AudioLines, BellOff, CheckCheck, Plus, Search } from "lucide-react";
import { actions } from "../store";
import { ICON } from "../ui";
import { voice } from "../voice/state";
import { useChatList } from "../chats/list";
import { GlassButton, LargeTitle } from "./parts";
import { MessengerStories } from "./Stories";
import s from "./mobile.module.css";

const filters = ["All", "Unread", "Groups", "Favorites"] as const;
const groups = new Set(["travel", "family", "gaming", "study"]);

export function ChatList({ onOpenChat, onOpenUpdates }: { onOpenChat: (id: string) => void; onOpenUpdates: (taskId?: string) => void }) {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const list = useChatList().filter((c) =>
    c.contact.name.toLowerCase().includes(q.toLowerCase()) &&
    (filter === "All" || (filter === "Unread" && c.unread > 0) || (filter === "Groups" && (groups.has(c.id) || c.id.startsWith("group-"))) ||
      (filter === "Favorites" && ["arif", "sara", "family"].includes(c.id))));

  return (
    <div className={s.scroll}>
      <LargeTitle title="Chats">
        <GlassButton icon={AudioLines} label="Talk to Messenger" onClick={voice.start} />
        <GlassButton icon={Plus} label="New chat" primary />
      </LargeTitle>
      <label className={s.search}>
        <Search size={18} strokeWidth={ICON.strokeWidth} />
        <input placeholder="Search chats, tasks, files…" value={q} onChange={(e) => setQ(e.target.value)} />
      </label>

      <MessengerStories onOpenUpdates={onOpenUpdates} />

      <div className={s.chips} role="tablist">
        {filters.map((f) => (
          <button key={f} role="tab" aria-selected={f === filter} className={`${s.chip} ${f === filter ? s.chipOn : ""}`} onClick={() => setFilter(f)}>{f}</button>
        ))}
      </div>

      <div className={s.group}>
        {list.map((c) => (
          <button key={c.id} className={`${s.row} ${c.unread ? s.rowUnread : ""}`} onClick={() => { actions.openChat(c.id); onOpenChat(c.id); }}>
            <span className={s.av}>
              <img src={c.contact.avatar} alt="" />
              {c.contact.online && <span className={s.onlineDot} />}
            </span>
            <span className={s.rowBody}>
              <span className={s.rowLine}><span className={s.rowName}>{c.contact.name}</span><span className={s.rowTime}>{c.time}</span></span>
              <span className={s.rowLine}>
                <span className={s.rowPrev}>{c.preview}</span>
                {c.unread > 0 ? <span className={s.badge}>{c.unread}</span>
                  : c.muted ? <BellOff size={16} strokeWidth={ICON.strokeWidth} className={s.rowIcon} />
                    : <CheckCheck size={16} strokeWidth={ICON.strokeWidth} className={s.rowRead} />}
              </span>
            </span>
          </button>
        ))}
        {!list.length && <p className={s.empty}>No chats found.</p>}
      </div>
    </div>
  );
}
