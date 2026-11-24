// An agent result, full size in the Messenger AI workspace (replaces the old Updates tray detail).
import { useEffect, useState } from "react";
import { MessageCircle } from "lucide-react";
import type { MessengerTask } from "../types";
import { Button } from "../ui";
import { TaskIcon, TaskStatus } from "../updates/common";
import { Detail } from "../updates/details/Detail";
import { useNow } from "./Activity";
import { ai } from "./state";
import v from "./taskview.module.css";

export function TaskView({ task }: { task: MessengerTask }) {
  const now = useNow();
  const [lightbox, setLightbox] = useState(false);
  const [notice, setNotice] = useState<{ text: string; until: number } | null>(null);
  useEffect(() => { setLightbox(false); setNotice(null); }, [task.id]);
  useEffect(() => {
    const close = (e: KeyboardEvent) => { if (e.key === "Escape" && !lightbox) ai.openTask(null); };
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [lightbox]);
  return <div className={v.view}>
    <header className={v.header}>
      <TaskIcon type={task.type} />
      <div className={v.heading}><strong>{task.title}</strong><span>{task.subtitle}</span></div>
      <TaskStatus task={task} now={now} />
      <Button icon={MessageCircle} onClick={() => ai.openTask(null)}>Back to chat</Button>
    </header>
    <div className={v.body}>
      <div className={v.content} key={task.id}>
        <Detail task={task} now={now} lightbox={lightbox} onLightbox={setLightbox}
          notify={(text) => setNotice({ text, until: Date.now() + 3500 })} />
      </div>
    </div>
    {notice && notice.until > now && <div className={v.toast} role="status">{notice.text}</div>}
  </div>;
}
