// Messenger's Dynamic Island — the primary place Messenger talks to you on iPhone 17 Pro Max.
// Modelled on real Live Activities and system sheets (screens/dynamic island/):
//   compact  — leading: type icon in a progress ring · camera · trailing: one big accent value
//   expanded — drops out of the island when a task starts/finishes; a layout per type
//              (flight arc JED ✈ DXB, video tick-bar %, image, research count). Swipe up to dismiss.
//   large    — tap: grows into a big card with the real result (image, playing video, fares) + actions
//   voice    — Siri-style: orb pulsing with your voice → what you said → Messenger's spoken answer
//   confirm  — Apple-Pay-style UAE PASS sheet for e-signing (mock): rows + "Confirm with Side Button"
// It drops down from just under the hardware island (the status bar stays native: dark clock on the light app).
import { useEffect, useMemo, useRef, useState } from "react";
import {
  BadgeCheck, ChevronRight, CircleAlert, Download, FileSignature, Fingerprint, LayoutList, MessageCircle, PenLine, Plane, ScanFace, ShieldCheck,
  CalendarHeart,
} from "lucide-react";
import { actions, useStore } from "../store";
import type { MessengerTask, TaskType } from "../types";
import { taskIcons } from "../updates/common";
import { EventPictures, eventChatItem } from "../updates/details/EventDetail";
import { esign, setIslandPresent, useEsign } from "../esign/state";
import { Signature } from "../esign/Document";
import { voice, useVoice } from "../voice/state";
import { ORB } from "./parts";
import s from "./island.module.css";

export const tone: Record<TaskType, string> = { flight: s.tFlight, video: s.tVideo, image: s.tImage, research: s.tResearch, email: s.tImage, esign: s.tSign, event: s.tResearch };
const BANNER_MS = { started: 3500, done: 7500 } as const;
/** The compact island sits just under the status bar and reserves this much at the top while work runs. */
const ISLAND_SPACE = "46px";

type Banner = { id: string; kind: keyof typeof BANNER_MS };
const isRunning = (t: MessengerTask) => t.status === "running" || t.status === "queued";

function elapsed(t: MessengerTask, now: number) {
  const sec = Math.max(0, Math.floor((now - t.startedAt) / 1000));
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}
/** The one big value on the compact island's trailing side. */
function trailingValue(t: MessengerTask) {
  if (t.status === "failed") return "Failed";
  if (t.result?.type === "flight" && t.result.flights[0]) return `${t.result.flights[0].currency} ${t.result.flights[0].price.toLocaleString()}`;
  if (t.status === "completed") return "Ready";
  return t.progress != null ? `${Math.round(t.progress)}%` : "Working";
}

export function DynamicIsland({ onOpen }: { onOpen: (taskId?: string) => void }) {
  const all = useStore((st) => st.tasks);
  const tasks = useMemo(() => all.filter((t) => !t.dismissed), [all]);
  const running = tasks.filter(isRunning);
  const [banner, setBanner] = useState<Banner | null>(null);
  const [largeId, setLargeId] = useState<string | null>(null);
  const [pick, setPick] = useState(""); // the event picture showing, which "Use in chat" shares
  useEffect(() => setPick(""), [largeId]);
  const [now, setNow] = useState(Date.now());
  const seen = useRef<Map<string, string> | null>(null);
  const dragY = useRef<number | null>(null);
  const signStage = useEsign((st) => st.stage);
  const voiceStage = useVoice((st) => st.stage);

  useEffect(() => { setIslandPresent(true); return () => setIslandPresent(false); }, []);

  // Expand on new work and on finished/signed work (never for tasks that were already there at load).
  useEffect(() => {
    const key = (t: MessengerTask) => `${t.status}|${t.result?.type === "esign" ? t.result.signedAt ?? "" : ""}`;
    if (!seen.current) { seen.current = new Map(tasks.map((t) => [t.id, key(t)])); return; }
    for (const t of tasks) {
      const before = seen.current.get(t.id);
      if (before === undefined && t.status !== "completed") setBanner({ id: t.id, kind: "started" });
      else if (before !== key(t) && (t.status === "completed" || t.status === "failed")) setBanner({ id: t.id, kind: "done" });
      seen.current.set(t.id, key(t));
    }
  }, [tasks]);

  useEffect(() => {
    if (!banner || largeId) return;
    const id = window.setTimeout(() => setBanner(null), BANNER_MS[banner.kind]);
    return () => window.clearTimeout(id);
  }, [banner, largeId]);

  useEffect(() => {
    if (!largeId && !running.length) return;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [largeId, running.length]);

  const busy = signStage !== "idle" || voiceStage !== "idle";
  const compact = !busy && !banner && !largeId && running.length > 0;
  useEffect(() => {
    document.documentElement.style.setProperty("--island-space", compact ? ISLAND_SPACE : "0px");
    return () => { document.documentElement.style.setProperty("--island-space", "0px"); };
  }, [compact]);

  const enlarge = (id: string) => { setLargeId(id); setBanner(null); };
  const shrink = () => setLargeId(null);

  /* Idle: the island is yesterday's (else today's) unread UAE event — never empty, never a random generation.
     Opening Updates marks it read, so it clears once seen; swipe up snoozes it for this session. */
  const eventTask = useMemo(() => {
    const evs = tasks.filter((t) => t.type === "event" && t.status === "completed" && t.unread);
    const rank = (t: MessengerTask) => {
      const when = t.result?.type === "event" ? t.result.event.when : "";
      return when === "Yesterday" ? 0 : when === "Today" ? 1 : 2;
    };
    return [...evs].sort((a, b) => rank(a) - rank(b))[0];
  }, [tasks]);
  const [hiddenEvent, setHiddenEvent] = useState<string | null>(null);
  const showEvent = !banner && !largeId && !running.length && eventTask && hiddenEvent !== eventTask.id
    ? eventTask : undefined;
  const liveTask = banner ? tasks.find((t) => t.id === banner.id) : showEvent;

  const swipe = {
    onPointerDown: (e: React.PointerEvent) => {
      if ((e.target as Element).closest("[aria-roledescription=carousel]")) return; // swiping pictures, not the island
      dragY.current = e.clientY;
    },
    onPointerUp: (e: React.PointerEvent) => {
      const dy = dragY.current == null ? 0 : e.clientY - dragY.current;
      dragY.current = null;
      if (dy < -24) { if (liveTask && !banner) setHiddenEvent(liveTask.id); setBanner(null); shrink(); }
    },
  };

  if (signStage !== "idle") return <SignConfirm />;
  if (voiceStage !== "idle") return <VoiceIsland />;

  /* ---------- large ---------- */
  const large = largeId ? tasks.find((t) => t.id === largeId) : undefined;
  if (large) {
    return (
      <>
        <button className={s.backdrop} aria-label="Close" onClick={shrink} />
        <div key={`l-${large.id}`} className={`${s.island} ${s.large} ${tone[large.type]} ${large.status === "completed" ? s.glow : ""}`}
          role="dialog" aria-label={large.title} {...swipe}>
          <span className={s.top} />
          <Header task={large} />
          <Activity task={large} now={now} big />
          <LargeMedia task={large} onPick={setPick} />
          <div className={s.actions}>
            <LargeActions task={large} pick={pick} done={shrink} onOpen={() => { shrink(); onOpen(large.id); }} />
            <button className={s.chip} onClick={() => { shrink(); onOpen(large.id); }}><LayoutList size={16} strokeWidth={2} />Updates</button>
          </div>
        </div>
      </>
    );
  }

  /* ---------- expanded (Live Activity) ---------- */
  const live = liveTask;
  if (live) {
    return (
      <button key={`b-${live.id}`} className={`${s.island} ${s.banner} ${tone[live.type]} ${live.status === "completed" ? s.glow : ""}`}
        aria-live="polite" onClick={() => (live.type === "esign" ? (setBanner(null), onOpen(live.id)) : enlarge(live.id))} {...swipe}>
        {/* iOS draws the clock and battery over this row — keep it empty */}
        <span className={s.top} />
        <Header task={live} />
        <Activity task={live} now={now} />
      </button>
    );
  }

  /* ---------- compact ---------- */
  if (!compact) return null;
  const lead = running[0];
  const I = taskIcons[lead.type];
  return (
    <button key="compact" className={`${s.island} ${s.compact} ${tone[lead.type]}`} onClick={() => enlarge(lead.id)}
      aria-label={`Messenger is working: ${lead.title}${running.length > 1 ? ` and ${running.length - 1} more` : ""}`}>
      <span className={s.lead}><Ring task={lead} size={28} /><I size={13} strokeWidth={2.4} /></span>
      <span className={s.camera} />
      <span className={s.trail}>{running.length > 1 ? `${running.length} tasks` : trailingValue(lead)}</span>
    </button>
  );
}

/* ================= voice (Siri-style) ================= */
function VoiceIsland() {
  const { stage, transcript, reply, level, error } = useVoice((v) => v);
  const line = stage === "listening" ? (transcript || "Listening…")
    : stage === "thinking" ? (transcript || "One moment…")
    : stage === "speaking" ? reply : error ?? "";
  return (
      <button className={`${s.island} ${s.voice} ${stage === "error" ? "" : s.glow}`} onClick={() => (stage === "listening" ? voice.stop() : voice.close())}
        aria-live="polite" aria-label={stage === "listening" ? "Stop listening" : "Close voice"}>
        <span className={s.voiceOrb} style={{ "--level": level } as React.CSSProperties}><img src={ORB} alt="" /></span>
        <span className={s.voiceText}>
          <small>{stage === "listening" ? "Messenger is listening" : stage === "thinking" ? "You said" : stage === "speaking" ? "Messenger" : "Messenger"}</small>
          <span className={stage === "thinking" ? s.dim : ""}>{line}</span>
          {stage === "thinking" && <i className={s.dots}><b /><b /><b /></i>}
        </span>
      </button>
  );
}

/* ================= UAE PASS confirm (Apple-Pay-style, mock) ================= */
function SignConfirm() {
  const { stage, signature } = useEsign((e) => e);
  return (
    <>
      <button className={s.backdrop} aria-label="Cancel" onClick={() => stage === "confirm" && esign.cancel()} />
      <div className={`${s.island} ${s.sheet}`} role="dialog" aria-label="Confirm signature with UAE PASS">
        <span className={s.top} />
        <span className={s.sheetHead}>
          <span className={s.uaepass}><Fingerprint size={20} strokeWidth={2} />UAE PASS</span>
          {stage === "confirm" && <button className={s.cancel} onClick={esign.cancel}>Cancel</button>}
        </span>
        <span className={s.payRow}><FileSignature size={22} strokeWidth={1.75} /><span><small>Document</small><b>e& yearly renewal</b><small>12 months · AED 300/month</small></span><ChevronRight size={18} /></span>
        <span className={s.payRow}><PenLine size={22} strokeWidth={1.75} /><span><small>Signed by</small>{signature && <Signature name={signature} className={s.paySig} />}</span></span>
        <span className={s.payRow}><ShieldCheck size={22} strokeWidth={1.75} /><span><small>Identity</small><b>Haitham Mohamed Ibrahim</b><small>Verified digital identity</small></span></span>
        {stage === "confirm" && (
          <button className={s.confirm} onClick={esign.confirm}><ScanFace size={30} strokeWidth={1.6} />Confirm with Side Button</button>
        )}
        {stage === "scanning" && <span className={`${s.confirm} ${s.scanning}`}><ScanFace size={30} strokeWidth={1.6} />Verifying with Face ID…</span>}
        {stage === "done" && <span className={`${s.confirm} ${s.doneOk}`}><BadgeCheck size={30} strokeWidth={1.8} />Signed</span>}
      </div>
    </>
  );
}

/* ================= Live Activity parts ================= */
/** Top row under the camera: what it is (left) and Messenger (right) — like "AA 1001 … FLIGHTY". */
function Header({ task }: { task: MessengerTask }) {
  const f = task.result?.type === "flight" ? task.result.flights[0] : undefined;
  const I = task.status === "failed" ? CircleAlert : taskIcons[task.type];
  return (
    <span className={s.header}>
      <span className={s.what}><I size={15} strokeWidth={2} />{f ? `${f.airline} · ${f.flightNo}` : task.title}</span>
      <span className={s.brand}><img src={ORB} alt="" />MESSENGER</span>
    </span>
  );
}

/** The type-specific Live Activity body (also used inside stories). */
export function Activity({ task, now, big }: { task: MessengerTask; now: number; big?: boolean }) {
  const r = task.status === "completed" ? task.result : undefined;

  if (task.status === "failed") {
    return <span className={s.row}><span className={s.stack}><b className={s.bad}>Couldn't finish</b><small>{task.error ?? task.subtitle}</small></span></span>;
  }

  if (r?.type === "flight" && r.flights[0]) {
    const f = r.flights[0];
    return (
      <span className={s.flight}>
        <span className={s.leg}><b>{f.fromCode}</b><i>{f.fromTime}</i></span>
        <span className={s.arcWrap}>
          <svg className={s.arc} viewBox="0 0 120 40" preserveAspectRatio="none" aria-hidden="true">
            <path d="M6 34 Q60 -4 114 34" className={s.arcDone} pathLength="100" strokeDasharray="52 100" />
            <path d="M6 34 Q60 -4 114 34" className={s.arcTodo} pathLength="100" strokeDasharray="1.5 3.5" strokeDashoffset="-52" />
          </svg>
          <Plane className={s.plane} size={20} strokeWidth={2} />
        </span>
        <span className={`${s.leg} ${s.legEnd}`}><b>{f.toCode}</b><i>{f.toTime}</i></span>
        <span className={s.flightFoot}>
          <span className={s.accent}>{f.bestPrice ? "Best price" : "From"} · {f.currency} {f.price.toLocaleString()}</span>
          <span>{f.stops ? `${f.stops} stop` : "Nonstop"} · {f.duration}</span>
        </span>
      </span>
    );
  }

  if (r?.type === "research") {
    const item = r.items[0];
    return (
      <span className={s.row}>
        <span className={`${s.bigNum} ${s.accent}`}>{item?.findings.length ?? 0}</span>
        <span className={s.stack}><b>key insights</b><small>{item?.title}</small></span>
        {!big && <span className={s.view}>Read</span>}
      </span>
    );
  }

  if (r?.type === "esign") {
    return (
      <span className={s.row}>
        <span className={s.thumb}>{r.signedAt ? <BadgeCheck size={28} strokeWidth={1.8} /> : <FileSignature size={26} strokeWidth={1.75} />}</span>
        <span className={s.stack}><b className={s.accent}>{r.signedAt ? "Signed with UAE PASS" : "Signature needed"}</b><small>e& yearly renewal · AED 300/month</small></span>
        <span className={s.view}>{r.signedAt ? "View" : "Sign"}</span>
      </span>
    );
  }

  if (r?.type === "event") {
    if (big) return <span className={s.caption}>{r.event.summary}</span>;
    return (
      <span className={s.row}>
        <span className={`${s.thumb} ${r.event.images[0] ? s.thumbPhoto : ""}`}>{r.event.images[0] ? <img src={r.event.images[0]} alt="" /> : <CalendarHeart size={26} strokeWidth={1.75} />}</span>
        <span className={s.stack}><b className={s.accent}>{r.event.when}</b><small>{r.event.title}</small></span>
        <span className={s.view}>View</span>
      </span>
    );
  }

  if (r?.type === "image" || r?.type === "video" || r?.type === "email") {
    if (big) return <span className={s.caption}>{task.subtitle}</span>;
    const I = taskIcons[task.type];
    return (
      <span className={s.row}>
        <span className={`${s.thumb} ${r.type !== "email" ? s.thumbPhoto : ""}`}>
          {r.type === "image" ? <img src={r.imageUrl} alt="" /> : r.type === "video" ? <video src={r.videoUrl} muted playsInline autoPlay loop /> : <I size={26} strokeWidth={1.75} />}
        </span>
        <span className={s.stack}><b className={s.accent}>Ready</b><small>{task.subtitle}</small></span>
        <span className={s.view}>View</span>
      </span>
    );
  }

  // running: espresso-style tick bar with one big value (real % when known)
  const pct = task.progress;
  const filled = pct == null ? -1 : Math.round((pct / 100) * 28);
  return (
    <span className={s.working}>
      <span className={`${s.ticks} ${pct == null ? s.ticksWave : ""}`} aria-hidden="true">
        {Array.from({ length: 28 }, (_, i) => <i key={i} className={i < filled ? s.tickOn : ""} style={{ animationDelay: `${i * 45}ms` }} />)}
      </span>
      <span className={s.row}>
        <span className={s.stack}><b className={s.accent}>{task.title}</b><small>{task.subtitle}</small></span>
        <span className={`${s.bigValue} ${s.accent}`}>{pct != null ? `${Math.round(pct)}%` : elapsed(task, now)}</span>
      </span>
    </span>
  );
}

/** Extra visual only in the large state. */
function LargeMedia({ task, onPick }: { task: MessengerTask; onPick: (url: string) => void }) {
  const r = task.status === "completed" ? task.result : undefined;
  if (!r) return task.status === "failed" ? null : <div className={s.shimmer} />;
  switch (r.type) {
    case "image": return <img className={s.media} src={r.imageUrl} alt={r.prompt} />;
    case "video": return <video className={s.media} src={r.videoUrl} autoPlay muted loop playsInline />;
    case "flight": return (
      <div className={s.rows}>
        {r.flights.slice(0, 3).map((f) => (
          <div key={f.id} className={s.fare}>
            <span><b>{f.fromTime} → {f.toTime}</b><small>{f.airline} · {f.duration} · {f.stops ? `${f.stops} stop` : "Nonstop"}</small></span>
            <b className={s.accent}>{f.currency} {f.price.toLocaleString()}</b>
          </div>
        ))}
      </div>
    );
    case "research": return <ul className={s.findings}>{r.items[0]?.findings.slice(0, 3).map((x) => <li key={x}>{x}</li>)}</ul>;
    case "email": return <div className={s.rows}><div className={s.fare}><span><b>{r.drafts[0]?.subject}</b><small>{r.drafts[0]?.body}</small></span></div></div>;
    case "esign": return null;
    case "event": return <EventPictures event={r.event} onPick={onPick} />;
  }
}

function LargeActions({ task, pick, done, onOpen }: { task: MessengerTask; pick: string; done: () => void; onOpen: () => void }) {
  const r = task.status === "completed" ? task.result : undefined;
  if (!r) return null;
  if (r.type === "esign") return <button className={`${s.chip} ${s.chipPrimary}`} onClick={onOpen}><FileSignature size={16} strokeWidth={2} />{r.signedAt ? "View document" : "Review & sign"}</button>;
  const toChat = () => {
    if (r.type === "image") actions.sendToChat({ kind: "image", url: r.imageUrl });
    else if (r.type === "video") actions.sendToChat({ kind: "video", url: r.videoUrl, caption: r.title });
    else if (r.type === "event") actions.sendToChat(eventChatItem(r.event, pick));
    else actions.sendToChat({ kind: "card", icon: r.type === "flight" ? "flight" : r.type === "email" ? "mail" : "research", title: task.title, subtitle: task.subtitle, taskId: task.id });
    done();
  };
  return <>
    <button className={`${s.chip} ${s.chipPrimary}`} onClick={toChat}><MessageCircle size={16} strokeWidth={2} />Use in chat</button>
    {r.type === "image" && <a className={s.chip} href={r.imageUrl} target="_blank" rel="noreferrer" onClick={done}><Download size={16} strokeWidth={2} />Save</a>}
    {r.type === "flight" && <button className={s.chip} onClick={() => { done(); actions.navigate("flights"); }}><Plane size={16} strokeWidth={2} />All flights</button>}
  </>;
}

/** Progress ring in the type's accent: real % when known, otherwise a spinning arc. */
function Ring({ task, size }: { task: MessengerTask; size: number }) {
  const pct = isRunning(task) ? task.progress : 100;
  const r = 8, c = 2 * Math.PI * r;
  return (
    <svg className={`${s.ring} ${pct == null ? s.spin : ""}`} style={{ width: size, height: size }} viewBox="0 0 20 20" aria-hidden="true">
      <circle cx="10" cy="10" r={r} className={s.track} />
      <circle cx="10" cy="10" r={r} className={s.bar} strokeDasharray={c} strokeDashoffset={c * (1 - (pct == null ? 0.28 : Math.min(100, pct) / 100))} />
    </svg>
  );
}
