import { useCallback, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { Check, X } from "lucide-react";
import type { MirsalTask, TaskResult } from "../../types";
import { actions } from "../../store";
import { ICON, IconButton } from "../../ui";
import { relativeTime } from "../common";
import { DetailActions, share, type Notify } from "./Detail";
import s from "../updates.module.css";

function VideoLightbox({ url, title, onClose }: { url: string; title: string; onClose: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); e.stopImmediatePropagation(); onClose(); }
      if (e.key === "Tab") { e.preventDefault(); dialog.current?.querySelector<HTMLButtonElement>("button")?.focus(); }
    };
    window.addEventListener("keydown", key, true);
    return () => { window.removeEventListener("keydown", key, true); previous?.focus(); };
  }, [onClose]);
  return createPortal(<div className={s.lightboxBackdrop} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className={s.lightbox} ref={dialog} role="dialog" aria-modal="true" aria-label="Video preview">
      <header><strong>{title}</strong><IconButton icon={X} label="Close video preview" onClick={onClose} /></header>
      <video className={s.lightboxVideo} src={url} title={title} controls autoPlay playsInline preload="metadata" />
    </div>
  </div>, document.body);
}
export function VideoDetail({ result, task, now, lightbox, onLightbox, notify }: {
  result: Extract<TaskResult, { type: "video" }>; task: MirsalTask; now: number;
  lightbox: boolean; onLightbox: (value: boolean) => void; notify: Notify;
}) {
  const closeLightbox = useCallback(() => onLightbox(false), [onLightbox]);
  return <div className={s.imageContent}>
    <video className={s.previewVideo} src={result.videoUrl} title={result.title} controls playsInline preload="metadata" />
    <div className={s.imageMeta}><span>Generated {relativeTime(task.completedAt ?? task.startedAt, now).toLowerCase()}</span><span className={s.readyPill}><Check {...ICON} /> Ready</span></div>
    <DetailActions openLabel="Open" onOpen={() => onLightbox(true)}
      onShare={() => { void share(result.videoUrl, notify); }}
      onChat={() => { actions.sendToChat({ kind: "video", url: result.videoUrl, caption: result.title }); notify("Added to your open chat"); }} />
    {lightbox && <VideoLightbox url={result.videoUrl} title={result.title} onClose={closeLightbox} />}
  </div>;
}
