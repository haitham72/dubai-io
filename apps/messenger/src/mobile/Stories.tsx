// Messenger stories: every agentic task is a story circle above the chats (like the old app's story row).
//   "+ Ask"  — start a new task (voice)
//   running  — live progress ring · new result — glowing Messenger ring · seen — grey ring
// Tap a circle: its card scales up out of the circle; swipe left/right between tasks, scroll the card for details.
// Finished images/videos share ONE "Studio" story: a card stacking them vertically (tap one → TikTok-style feed).
// × on that card removes the whole stack (it flies off); swiping still pages between stories like any other card.
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { ChevronLeft, ChevronRight, Download, Heart, Maximize2, MessageCircle, Play, Plane, Plus, X } from "lucide-react";
import { EsignDocument } from "../esign/Document";
import { feed, useFeed } from "./feedState";
import { actions, useStore } from "../store";
import type { MessengerTask } from "../types";
import { taskIcons, relativeTime } from "../updates/common";
import { EventPictures, eventChatItem } from "../updates/details/EventDetail";
import { voice } from "../voice/state";
import { Activity, tone } from "./DynamicIsland";
import { ORB } from "./parts";
import s from "./stories.module.css";

const label: Record<MessengerTask["type"], string> = { image: "Image", video: "Video", flight: "Flight", research: "Research", email: "Email", esign: "e-Sign", event: "Event" };
const isRunning = (t: MessengerTask) => t.status === "running" || t.status === "queued";
const isMedia = (t: MessengerTask) => t.status === "completed" && (t.result?.type === "image" || t.result?.type === "video");
const mediaUrl = (t: MessengerTask) => t.result?.type === "image" ? t.result.imageUrl : t.result?.type === "video" ? t.result.videoUrl : "";

/** One story in the row: a single task, or the stack of every finished image/video. */
interface Story { id: string; task?: MessengerTask; media?: MessengerTask[] }
const STACK = "studio-stack";

function toStories(tasks: MessengerTask[]): Story[] {
  const media = tasks.filter(isMedia);
  const out: Story[] = [];
  for (const t of tasks) {
    if (!isMedia(t)) out.push({ id: t.id, task: t });
    else if (t === media[0]) out.push({ id: STACK, media });
  }
  return out;
}

export function MessengerStories({ onOpenUpdates }: { onOpenUpdates: (taskId?: string) => void }) {
  const all = useStore((st) => st.tasks);
  const tasks = useMemo(() => all.filter((t) => !t.dismissed), [all]);
  const stories = useMemo(() => toStories(tasks), [tasks]);
  const [open, setOpen] = useState<{ index: number; from: DOMRect } | null>(null);
  const circles = useRef<Record<string, HTMLButtonElement | null>>({});
  const unread = tasks.filter((t) => t.unread).length;
  const running = tasks.filter(isRunning).length;
  const summary = [unread && `${unread} new`, running && `${running} running`].filter(Boolean).join(" · ") || "All caught up";

  return (
    <section className={s.band} aria-label="Messenger">
      <button className={s.bandHead} onClick={() => onOpenUpdates()}>
        <b>Messenger</b><span>{summary}</span>
        <span className={s.seeAll}>See all<ChevronRight size={16} strokeWidth={2} /></span>
      </button>
      <div className={s.row}>
        <button className={s.story} onClick={voice.start}>
          <span className={`${s.ring} ${s.ringNew}`}><span className={s.face}><img src={ORB} alt="" /></span></span>
          <span className={s.plus}><Plus size={14} strokeWidth={3} /></span>
          <span className={s.name}>Ask Messenger</span>
        </button>
        {stories.map((story, i) => {
          if (story.media) {
            const top = story.media[0];
            const fresh = story.media.some((t) => t.unread);
            return (
              <button key={story.id} ref={(el) => { circles.current[story.id] = el; }} className={`${s.story} ${tone[top.type]}`}
                onClick={(e) => setOpen({ index: i, from: e.currentTarget.querySelector(`.${s.face}`)!.getBoundingClientRect() })}>
                <span className={`${s.ring} ${fresh ? s.ringNewResult : s.ringSeen}`}>
                  <span className={s.face}>
                    {top.result?.type === "video" ? <video src={`${mediaUrl(top)}#t=1.2`} muted playsInline preload="metadata" /> : <img src={mediaUrl(top)} alt="" />}
                  </span>
                </span>
                {story.media.length > 1 && <span className={s.count}>{story.media.length}</span>}
                <span className={s.name}>Studio</span>
              </button>
            );
          }
          const t = story.task!;
          const I = taskIcons[t.type];
          const thumb = t.result?.type === "image" ? t.result.imageUrl : t.result?.type === "event" ? t.result.event.images[0] : undefined;
          const pct = isRunning(t) ? t.progress ?? 30 : 100;
          return (
            <button key={t.id} ref={(el) => { circles.current[t.id] = el; }} className={`${s.story} ${tone[t.type]}`}
              onClick={(e) => setOpen({ index: i, from: e.currentTarget.querySelector(`.${s.face}`)!.getBoundingClientRect() })}>
              <span className={`${s.ring} ${isRunning(t) ? s.ringRun : t.unread ? s.ringNewResult : s.ringSeen}`} style={{ "--pct": pct } as React.CSSProperties}>
                <span className={s.face}>
                  {thumb ? <img src={thumb} alt="" />
                    : t.result?.type === "video" ? <video src={`${t.result.videoUrl}#t=1.2`} muted playsInline preload="metadata" />
                    : <I size={26} strokeWidth={1.75} />}
                </span>
              </span>
              <span className={s.name}>{isRunning(t) && t.progress != null ? `${label[t.type]} ${Math.round(t.progress)}%` : t.result?.type === "event" ? t.result.event.when : label[t.type]}</span>
            </button>
          );
        })}
      </div>
      {open && (
        <StoryViewer stories={stories} start={open.index} from={open.from}
          circleOf={(id) => circles.current[id]?.querySelector<HTMLElement>(`.${s.face}`)?.getBoundingClientRect() ?? open.from}
          onClose={() => setOpen(null)} onOpenUpdates={onOpenUpdates} />
      )}
    </section>
  );
}

/** Tapped story → ONE native card scales up out of the circle. Swipe left/right (or ‹ ›) and the content slides to the
 *  next task inside the same card; dots at the bottom show where you are. Scroll for details; pull down (or ×, or the
 *  backdrop) and the card shrinks back into the current task's circle. */
const PIVOT = "50% 140%"; // the removed stack rotates around a point below the card as it flies off

function StoryViewer({ stories, start, from, circleOf, onClose, onOpenUpdates }: {
  stories: Story[]; start: number; from: DOMRect; circleOf: (id: string) => DOMRect;
  onClose: () => void; onOpenUpdates: (id?: string) => void;
}) {
  const [index, setIndex] = useState(start);
  const [dir, setDir] = useState<"next" | "prev" | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const pane = useRef<HTMLDivElement>(null);
  const backdrop = useRef<HTMLButtonElement>(null);
  const closing = useRef(false);
  const flinging = useRef(false);
  const drag = useRef<{ x: number; y: number; axis?: "x" | "y"; pull: boolean } | null>(null);

  /** The card posed as the circle: its top square, fully rounded, scaled onto the circle. */
  const asCircle = (el: HTMLElement, circle: DOMRect) => {
    const r = el.getBoundingClientRect();
    return {
      transform: `translate(${circle.left - r.left}px, ${circle.top - r.top}px) scale(${circle.width / r.width})`,
      clipPath: `inset(0px 0px ${Math.max(0, r.height - r.width)}px 0px round ${r.width / 2}px)`,
    };
  };
  const asCard = { transform: "translate(0px, 0px) scale(1)", clipPath: "inset(0px 0px 0px 0px round 38px)" };

  const opened = useRef(false);
  useLayoutEffect(() => {
    if (opened.current) return; // StrictMode re-runs effects; measuring mid-animation would cancel the scale-up
    opened.current = true;
    card.current!.animate([asCircle(card.current!, from), asCard], { duration: 560, easing: "cubic-bezier(0.2, 0.95, 0.25, 1)" });
    backdrop.current?.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 400 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const close = () => {
    const el = card.current, story = stories[index];
    if (closing.current || !el) return;
    closing.current = true;
    el.style.transform = "";
    if (!story) { onClose(); return; }
    el.animate([asCard, asCircle(el, circleOf(story.id))], { duration: 440, easing: "cubic-bezier(0.4, 0, 0.2, 1)", fill: "forwards" }).finished.then(onClose);
    backdrop.current?.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 440, fill: "forwards" });
  };

  const go = (to: number) => {
    if (to < 0 || to >= stories.length || to === index) return;
    setDir(to > index ? "next" : "prev");
    setIndex(to);
  };
  useEffect(() => {
    const st = stories[index];
    for (const t of st?.media ?? (st?.task ? [st.task] : [])) if (t.unread) actions.updateTask(t.id, { unread: false });
  }, [index]); // eslint-disable-line react-hooks/exhaustive-deps

  // Removing the stack shortens the list: stay on the story that slid into place, or close if none are left.
  useEffect(() => {
    if (!stories.length) onClose();
    else if (index >= stories.length) setIndex(stories.length - 1);
  }, [stories.length]); // eslint-disable-line react-hooks/exhaustive-deps

  /** × on the Studio stack: the card flies off, the stack is removed and the next story comes in. */
  const removeStack = () => {
    const el = card.current, media = stories[index]?.media;
    if (!el || !media || flinging.current) return;
    flinging.current = true;
    const sign = -1;
    el.style.transition = "none";
    el.animate([{ transform: el.style.transform || "none" }, { transform: `translateX(${sign * 130}%) rotate(${sign * 16}deg)` }].map((k) => ({ ...k, transformOrigin: PIVOT })),
      { duration: 320, easing: "cubic-bezier(0.4, 0, 1, 1)", fill: "forwards" }).finished.then((a) => {
      media.forEach((t) => actions.dismissTask(t.id));
      a.cancel(); el.style.transform = ""; el.style.transition = ""; el.style.transformOrigin = ""; flinging.current = false;
      el.animate([{ opacity: 0, transform: "scale(0.94)" }, { opacity: 1, transform: "none" }], { duration: 260, easing: "ease-out" });
    });
  };

  // One gesture handler for the card: horizontal = page between tasks, vertical at the top = pull to close.
  const reset = () => {
    if (card.current) card.current.style.transform = "";
    if (pane.current) pane.current.style.transform = "";
  };
  const onDown = (e: React.PointerEvent) => {
    if ((e.target as Element).closest("[aria-roledescription=carousel]")) return; // swiping pictures, not stories
    const page = pane.current?.querySelector<HTMLElement>(`.${s.page}`);
    drag.current = { x: e.clientX, y: e.clientY, pull: !page || page.scrollTop <= 0 };
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current; if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    d.axis ??= Math.abs(dx) > 10 ? "x" : Math.abs(dy) > 10 ? "y" : undefined;
    if (d.axis === "x" && pane.current) pane.current.style.transform = `translateX(${dx * 0.5}px)`;
    if (d.axis === "y" && d.pull && dy > 0 && card.current) card.current.style.transform = `translateY(${dy * 0.6}px) scale(${1 - Math.min(dy, 300) / 1500})`;
  };
  const onUp = (e: React.PointerEvent) => {
    const d = drag.current; drag.current = null; if (!d) return;
    const dx = e.clientX - d.x, dy = e.clientY - d.y;
    reset();
    if (d.axis === "x" && Math.abs(dx) > 60) go(index + (dx < 0 ? 1 : -1));
    else if (d.axis === "y" && d.pull && dy > 110) close();
  };

  const story = stories[index];
  if (!story) return null;
  return (
    <div className={s.viewer} role="dialog" aria-label="Messenger tasks">
      <button ref={backdrop} className={s.backdrop} aria-label="Close" onClick={close} />
      <div ref={card} className={s.card} onPointerDown={onDown} onPointerMove={onMove} onPointerUp={onUp} onPointerCancel={() => { drag.current = null; reset(); }}>
        <div ref={pane} className={s.pane}>
          <div key={story.id} className={`${s.slide} ${dir === "next" ? s.fromRight : dir === "prev" ? s.fromLeft : ""}`}>
            {story.media
              ? <StackPage media={story.media} onRemove={removeStack} onClose={close} />
              : <TaskPage task={story.task!} onClose={close} onOpenUpdates={(id) => { onClose(); onOpenUpdates(id); }} />}
          </div>
        </div>
        <nav className={s.crumbs} aria-label="Tasks">
          <button className={s.crumbBtn} aria-label="Previous" disabled={index === 0} onClick={() => go(index - 1)}><ChevronLeft size={20} strokeWidth={2} /></button>
          <span className={s.dots}>
            {stories.map((st, i) => <button key={st.id} aria-label={st.task?.title ?? "Studio"} aria-current={i === index} className={i === index ? s.dotOn : ""} onClick={() => go(i)} />)}
          </span>
          <button className={s.crumbBtn} aria-label="Next" disabled={index === stories.length - 1} onClick={() => go(index + 1)}><ChevronRight size={20} strokeWidth={2} /></button>
        </nav>
      </div>
    </div>
  );
}

/** The Studio stack: every finished image/video in one card, stacked vertically. Tap one → full-screen feed. */
function StackPage({ media, onRemove, onClose }: { media: MessengerTask[]; onRemove: () => void; onClose: () => void }) {
  const liked = useFeed((f) => f.liked);
  const latest = media[0];
  return (
    <div className={s.page}>
      <div className={s.grabber} />
      <header className={s.pageHead}>
        <img src={ORB} alt="" />
        <span><b>Messenger Studio</b><small>{media.length} {media.length === 1 ? "creation" : "creations"} · {relativeTime(latest.completedAt ?? latest.startedAt, Date.now())}</small></span>
        <button className={s.x} aria-label="Remove this stack" onClick={onRemove}><X size={20} strokeWidth={2} /></button>
      </header>
      <div className={s.stack}>
        {media.map((t) => (
          <button key={t.id} className={s.stackItem} onClick={() => { onClose(); feed.open(t.id); }}>
            {t.result?.type === "video"
              ? <video className={s.stackMedia} src={mediaUrl(t)} autoPlay muted loop playsInline />
              : <img className={s.stackMedia} src={mediaUrl(t)} alt="" loading="lazy" />}
            <span className={s.stackLabel}>
              {t.result?.type === "video" && <Play size={14} strokeWidth={2.2} fill="currentColor" />}
              {t.title}
            </span>
            {liked[t.id] && <span className={s.stackFav}><Heart size={16} strokeWidth={2.2} fill="currentColor" /></span>}
          </button>
        ))}
      </div>
    </div>
  );
}

/** One task as a scrollable page: hero visual, details, actions. */
function TaskPage({ task, onClose, onOpenUpdates }: { task: MessengerTask; onClose: () => void; onOpenUpdates: (id: string) => void }) {
  const r = task.status === "completed" ? task.result : undefined;
  const media = r?.type === "image" || r?.type === "video";
  const [pick, setPick] = useState(""); // the event picture showing, which "Use in chat" shares
  return (
    <div className={s.page}>
      <div className={s.grabber} />
      <header className={s.pageHead}>
        <img src={ORB} alt="" />
        <span><b>{task.title}</b><small>Messenger · {relativeTime(task.completedAt ?? task.startedAt, Date.now())}</small></span>
        <button className={s.x} aria-label="Close" onClick={onClose}><X size={20} strokeWidth={2} /></button>
      </header>

      {media && (
        <button className={s.heroBtn} aria-label="Open in Messenger Studio" onClick={() => { onClose(); feed.open(task.id); }}>
          {r.type === "image" ? <img className={s.hero} src={r.imageUrl} alt={r.prompt} /> : <video className={s.hero} src={r.videoUrl} autoPlay muted loop playsInline />}
          <span className={s.heroHint}><Maximize2 size={14} strokeWidth={2.2} />Full screen</span>
        </button>
      )}
      {r?.type === "event" && <EventPictures event={r.event} onPick={setPick} className={s.eventStory} />}
      {!media && r?.type !== "esign" && r?.type !== "event" && <div className={`${s.live} ${tone[task.type]}`}><Activity task={task} now={Date.now()} big /></div>}

      <div className={s.details}>
        {r?.type === "image" && <p className={s.prompt}>{r.prompt}</p>}
        {r?.type === "video" && <p className={s.prompt}>{task.subtitle}</p>}
        {r?.type === "flight" && r.flights.map((f) => (
          <div key={f.id} className={s.fareRow}>
            <span><b>{f.fromTime} → {f.toTime}</b><small>{f.airline} · {f.flightNo} · {f.duration} · {f.stops ? `${f.stops} stop` : "Nonstop"}</small></span>
            <b>{f.currency} {f.price.toLocaleString()}</b>
          </div>
        ))}
        {r?.type === "research" && r.items.map((it) => (
          <section key={it.id}>
            <h3 className={s.h3}>{it.title}</h3>
            <p className={s.meta}>{it.summary}</p>
            <ol className={s.list}>{it.findings.map((x) => <li key={x}>{x}</li>)}</ol>
          </section>
        ))}
        {r?.type === "email" && r.drafts.map((d) => (
          <section key={d.id}><h3 className={s.h3}>{d.subject}</h3><p className={s.meta}>To {d.to}</p><p className={s.body}>{d.body}</p></section>
        ))}
        {r?.type === "esign" && <EsignDocument task={task} />}
        {r?.type === "event" && <>
          {r.event.titleAr && <p className={s.prompt} dir="rtl" lang="ar">{r.event.titleAr}</p>}
          <p className={s.meta}>{r.event.summary} · {r.event.source}</p>
        </>}
        {!r && task.status !== "failed" && <p className={s.meta}>{task.subtitle}. Messenger posts the result here and in the island when it&apos;s ready.</p>}
        {task.status === "failed" && <p className={s.meta}>{task.error ?? "This task couldn't finish."}</p>}
      </div>

      <div className={s.actions}>
        {r?.type === "image" && <>
          <button className={s.primary} onClick={() => { actions.sendToChat({ kind: "image", url: r.imageUrl }); onClose(); }}><MessageCircle size={18} />Use in chat</button>
          <a className={s.ghost} href={r.imageUrl} target="_blank" rel="noreferrer"><Download size={18} />Save</a>
        </>}
        {r?.type === "video" && <button className={s.primary} onClick={() => { actions.sendToChat({ kind: "video", url: r.videoUrl, caption: r.title }); onClose(); }}><MessageCircle size={18} />Use in chat</button>}
        {r?.type === "flight" && <>
          <button className={s.primary} onClick={() => { actions.sendToChat({ kind: "card", icon: "flight", title: task.title, subtitle: task.subtitle }); onClose(); }}><MessageCircle size={18} />Use in chat</button>
          <button className={s.ghost} onClick={() => { onClose(); actions.navigate("flights"); }}><Plane size={18} />All flights</button>
        </>}
        {r?.type === "event" && <>
          <button className={s.primary} onClick={() => { actions.sendToChat(eventChatItem(r.event, pick)); onClose(); }}><MessageCircle size={18} />Use in chat</button>
          <button className={s.ghost} onClick={() => onOpenUpdates(task.id)}><ChevronRight size={18} />Open</button>
        </>}
        {(r?.type === "research" || r?.type === "email") && <>
          <button className={s.primary} onClick={() => { actions.sendToChat({ kind: "card", icon: r.type === "email" ? "mail" : "research", title: task.title, subtitle: task.subtitle, taskId: task.id }); onClose(); }}><MessageCircle size={18} />Use in chat</button>
          <button className={s.ghost} onClick={() => onOpenUpdates(task.id)}><ChevronRight size={18} />Open</button>
        </>}
      </div>
    </div>
  );
}

