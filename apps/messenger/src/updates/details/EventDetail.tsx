// A UAE event from Diwan: what and when, and up to three pictures (Supabase Storage via the agents service).
import { useState } from "react";
import { CalendarPlus, MessageCircle } from "lucide-react";
import { actions } from "../../store";
import type { TaskResult } from "../../types";
import { Button } from "../../ui";
import type { Notify } from "./Detail";
import { EventPictures, eventChatItem } from "./EventPictures";
import s from "../updates.module.css";

export { EventPictures, eventChatItem } from "./EventPictures";

export function EventDetail({ result, notify }: { result: Extract<TaskResult, { type: "event" }>; notify: Notify }) {
  const e = result.event;
  const [pick, setPick] = useState("");
  const date = new Date(`${e.date}T00:00:00`).toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  // Wide (desktop tray): pictures left, as tall as the tray allows; text and actions right. Narrow: stacked.
  return <div className={s.eventDetail}><div className={s.eventGrid}>
    <EventPictures event={e} onPick={setPick} className={s.eventMedia} />
    <div className={s.eventText}>
    <span className={s.eventWhen}>{e.when} · {date}</span>
    <h3>{e.title}</h3>
    {e.titleAr && <p className={s.eventAr} dir="rtl" lang="ar">{e.titleAr}</p>}
    {e.summary && <p>{e.summary}</p>}
    <small className={s.eventSource}>{e.source}</small>
    <div className={s.detailActions}>
      <Button icon={MessageCircle} variant="purple" onClick={() => {
        actions.sendToChat(eventChatItem(e, pick));
        notify("Added to your open chat");
      }}>Use in chat</Button>
      <Button icon={CalendarPlus} onClick={() => {
        actions.addEvent({ title: e.title, start: `${e.date}T00:00:00`, end: `${e.date}T23:59:00`, calendar: "personal", notes: `${e.source}` });
        notify("Added to your calendar");
      }}>Add to calendar</Button>
    </div>
    </div>
  </div></div>;
}
