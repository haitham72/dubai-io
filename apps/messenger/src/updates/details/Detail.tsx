import { ExternalLink, MessageCircle, Share2 } from "lucide-react";
import { actions } from "../../store";
import type { MessengerTask } from "../../types";
import { Button } from "../../ui";
import { Retry, TaskStatus } from "../common";
import { ImageDetail } from "./ImageDetail";
import { VideoDetail } from "./VideoDetail";
import { FlightDetail } from "./FlightDetail";
import { ResearchDetail } from "./ResearchDetail";
import { EmailDetail } from "./EmailDetail";
import { EventDetail } from "./EventDetail";
import { EsignDocument } from "../../esign/Document";
import s from "../updates.module.css";

export type Notify = (text: string) => void;
export async function share(text: string, notify: Notify) {
  try { await navigator.clipboard.writeText(text); notify("Link copied"); }
  catch { notify("Couldn't copy. Try again with clipboard access enabled."); }
}
export function DetailActions({ openLabel, onOpen, onShare, onChat }: {
  openLabel: string; onOpen: () => void; onShare: () => void; onChat: () => void;
}) {
  return <div className={s.detailActions}>
    <Button icon={ExternalLink} variant="purple" onClick={onOpen}>{openLabel}</Button>
    <Button icon={Share2} onClick={onShare}>Share</Button>
    <Button icon={MessageCircle} onClick={onChat}>Use in chat</Button>
  </div>;
}
export function Detail({ task, now, lightbox, onLightbox, notify }: {
  task: MessengerTask; now: number; lightbox: boolean; onLightbox: (value: boolean) => void; notify: Notify;
}) {
  const result = task.result;
  const link = `${window.location.origin}/#update=${encodeURIComponent(task.id)}`;
  const sendCard = (icon: "flight" | "research" | "mail", title = task.title, subtitle = task.subtitle) => {
    actions.sendToChat({ kind: "card", icon, title, subtitle, taskId: task.id }); notify("Added to your open chat");
  };
  if (task.status !== "completed" || !result) return <div className={s.pending}>
    <TaskStatus task={task} now={now} />
    <p>{task.status === "failed" ? task.error ?? "This task couldn't finish." : task.status === "completed" ? "No preview is available for this result." : "Your result will appear here when it's ready."}</p>
    {task.status === "failed" && <Retry task={task} notify={notify} />}
  </div>;
  switch (result.type) {
    case "image": return <ImageDetail result={result} task={task} now={now} lightbox={lightbox} onLightbox={onLightbox} notify={notify} />;
    case "video": return <VideoDetail result={result} task={task} now={now} lightbox={lightbox} onLightbox={onLightbox} notify={notify} />;
    case "flight": return <FlightDetail result={result} notify={notify} actions={<DetailActions openLabel="View all flights"
      onOpen={() => actions.navigate("flights")} onShare={() => { void share(link, notify); }} onChat={() => sendCard("flight")} />} />;
    case "research": return <ResearchDetail result={result} notify={notify} link={link} sendCard={sendCard} />;
    case "email": return <EmailDetail result={result} notify={notify} link={link} sendCard={sendCard} />;
    case "esign": return <EsignDocument task={task} />;
    case "event": return <EventDetail result={result} notify={notify} />;
  }
}
