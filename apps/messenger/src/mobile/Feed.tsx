// Messenger Studio feed: every generated image/video full-screen, swiped vertically like TikTok/Reels.
// Right rail: like · report · share · use in chat. Bottom: the prompt + (images only) a floating "Prompt your edits…"
// Feed slides. Image edits are not part of this app.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { Flag, Heart, MessageCircle, Share, Volume2, VolumeX, X } from "lucide-react";
import { actions, useStore } from "../store";
import type { MessengerTask } from "../types";
import { relativeTime } from "../updates/common";
import { feed, useFeed } from "./feedState";
import { ORB } from "./parts";
import { Sheet } from "./Sheet";
import s from "./feed.module.css";

const REASONS = ["Inaccurate or misleading", "Offensive or unsafe", "Copyright or likeness", "Low quality", "Something else"];
const isMedia = (t: MessengerTask) => t.status === "completed" && (t.result?.type === "image" || t.result?.type === "video") && !t.dismissed;

export function MediaFeed() {
  const openAt = useFeed((f) => f.openAt);
  const all = useStore((st) => st.tasks);
  const items = useMemo(() => all.filter(isMedia), [all]);
  if (!openAt || !items.length) return null;
  return <FeedView items={items} startId={openAt} />;
}

function FeedView({ items, startId }: { items: MessengerTask[]; startId: string }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [current, setCurrent] = useState(Math.max(0, items.findIndex((t) => t.id === startId)));
  const [muted, setMuted] = useState(true);
  const [report, setReport] = useState<MessengerTask | null>(null);
  const [toast, setToast] = useState("");

  useLayoutEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = current * el.clientHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => { if (!toast) return; const id = window.setTimeout(() => setToast(""), 2600); return () => window.clearTimeout(id); }, [toast]);

  const onScroll = () => {
    const el = scroller.current!;
    const i = Math.round(el.scrollTop / el.clientHeight);
    if (i !== current) setCurrent(i);
  };

  return (
    <div className={s.feed} role="dialog" aria-label="Messenger Studio">
      <div ref={scroller} className={s.scroller} onScroll={onScroll}>
        {items.map((t, i) => (
          <Slide key={t.id} task={t} active={i === current} muted={muted}
            onReport={() => setReport(t)} notify={setToast} />
        ))}
      </div>

      <header className={s.top}>
        <button className={s.round} aria-label="Close" onClick={feed.close}><X size={22} strokeWidth={2} /></button>
        <span className={s.brand}><img src={ORB} alt="" />Messenger Studio</span>
        <button className={s.round} aria-label={muted ? "Unmute" : "Mute"} onClick={() => setMuted(!muted)}>
          {muted ? <VolumeX size={20} strokeWidth={2} /> : <Volume2 size={20} strokeWidth={2} />}
        </button>
      </header>

      {report && (
        <Sheet label="Report" tall={false} onClose={() => setReport(null)}>
          <h2 className={s.sheetTitle}>Report this generation</h2>
          <p className={s.sheetSub}>Messenger reviews reports to improve its models. Nothing is shared with other people.</p>
          <div className={s.reasons}>
            {REASONS.map((r) => (
              <button key={r} onClick={() => { setReport(null); setToast("Thanks — reported. Messenger will review it."); }}>
                <Flag size={18} strokeWidth={1.75} />{r}
              </button>
            ))}
          </div>
        </Sheet>
      )}
      {toast && <div className={s.toast} role="status">{toast}</div>}
    </div>
  );
}

function Slide({ task, active, muted, onReport, notify }: {
  task: MessengerTask; active: boolean; muted: boolean; onReport: () => void; notify: (t: string) => void;
}) {
  const r = task.result as Extract<NonNullable<MessengerTask["result"]>, { type: "image" | "video" }>;
  const liked = useFeed((f) => !!f.liked[task.id]);
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const v = video.current; if (!v) return;
    if (active) void v.play().catch(() => {}); else { v.pause(); v.currentTime = 0; }
  }, [active]);

  const url = r.type === "image" ? r.imageUrl : r.videoUrl;

  return (
    <section className={s.slide}>
      {r.type === "image"
        ? <img className={s.media} src={url} alt={r.prompt} />
        : <video ref={video} className={s.media} src={url} muted={muted} loop playsInline preload="metadata" />}
      <div className={s.shade} />

      <div className={s.rail}>
        <button className={`${s.railBtn} ${liked ? s.liked : ""}`} aria-pressed={liked} onClick={() => feed.toggleLike(task.id)}>
          <Heart size={30} strokeWidth={1.75} fill={liked ? "currentColor" : "none"} /><span>{liked ? "Liked" : "Like"}</span>
        </button>
        <button className={s.railBtn} onClick={() => { actions.sendToChat(r.type === "image" ? { kind: "image", url } : { kind: "video", url, caption: r.title }); feed.close(); }}>
          <MessageCircle size={28} strokeWidth={1.75} /><span>Use</span>
        </button>
        <button className={s.railBtn} onClick={async () => {
          try { await navigator.clipboard.writeText(url); notify("Link copied"); } catch { notify("Couldn't copy the link"); }
        }}>
          <Share size={28} strokeWidth={1.75} /><span>Share</span>
        </button>
        <button className={s.railBtn} onClick={onReport}><Flag size={26} strokeWidth={1.75} /><span>Report</span></button>
      </div>

      <div className={s.bottom}>
        <p className={s.meta}>{relativeTime(task.completedAt ?? task.startedAt, Date.now())}</p>
        <p className={s.prompt}>{r.prompt}</p>
      </div>
    </section>
  );
}
