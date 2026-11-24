// Desktop only: Messenger runs as an app window on a macOS-style desktop (wallpaper, menu bar, Dock), so the demo reads as
// "a Mac running the Messenger app", not a website. Traffic lights: red closes, yellow minimizes to the Dock, green zooms to
// fill the screen (and enters browser fullscreen). The Dock holds Messenger and each of its workspaces (our own icons in the
// macOS style — no Apple artwork); clicking one opens/restores the window on that screen.
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import {
  BatteryFull, Calendar, CandlestickChart, CloudSun, FileSearch, Folder, History, Mail, MessageCircle, Plane, Search, Sparkles, Wifi, type LucideIcon,
} from "lucide-react";
import { actions, useStore } from "../store";
import type { ScreenId } from "../types";
import s from "./mac.module.css";

const DOCK: { id: ScreenId; label: string; icon: LucideIcon; tone: string }[] = [
  { id: "ai", label: "Messenger AI", icon: Sparkles, tone: s.tViolet },
  { id: "files", label: "Files", icon: Folder, tone: s.tAmber },
  { id: "flights", label: "Flights", icon: Plane, tone: s.tBlue },
  { id: "weather", label: "Weather", icon: CloudSun, tone: s.tSky },
  { id: "calendar", label: "Calendar", icon: Calendar, tone: s.tRed },
  { id: "stocks", label: "Stocks", icon: CandlestickChart, tone: s.tGraphite },
  { id: "mail", label: "Mail", icon: Mail, tone: s.tBlue },
  { id: "research", label: "Research", icon: FileSearch, tone: s.tTeal },
  { id: "history", label: "History", icon: History, tone: s.tGrey },
];

type WindowState = "normal" | "zoomed" | "minimized" | "closed";
const MENUS = ["File", "Edit", "View", "Window", "Help"];

/* Resizable + movable window. The window lives in an absolute {x,y,w,h} frame inside the
 * stage: default 1440×900 (16:10) centred with a margin, max = stage. The minimum follows the stage so
 * the window never overflows it on any screen: 1100×680 on a big screen, ~740×600 on a tablet-sized one,
 * never more than the stage itself. Below the shell's design size (APP_W×APP_H) the app inside is scaled
 * down to fit, like a zoomed-out Mac window — the layout is never cropped. Zoomed overrides to full screen;
 * restoring returns to the last frame. Persisted to localStorage. */
const DEF_W = 1440, DEF_H = 900, MARGIN = 16, APP_W = 1100, APP_H = 680;
const FRAME_KEY = "messenger:mac-frame";
interface Frame { x: number; y: number; w: number; h: number }

function minSize(sw: number, sh: number) {
  const w = sw >= 1100 ? 1100 : sw >= 820 ? Math.min(740, Math.floor(sw * 0.92)) : sw;
  const h = sh >= 680 ? 680 : Math.min(600, sh);
  return { w: Math.max(0, Math.floor(w)), h: Math.max(0, Math.floor(h)) };
}
/** `dock` = the stage's bottom padding (the Dock's area). A big screen centres the 1440×900 window as
 *  before; a smaller one fits the window above the Dock instead of letting the Dock cover its bottom. */
function defaultFrame(sw: number, sh: number, dock = 0): Frame {
  const w = Math.min(DEF_W, Math.max(0, sw - MARGIN * 2));
  const x = Math.max(0, (sw - w) / 2);
  if (sh - dock >= DEF_H + MARGIN * 2) return { x, y: (sh - DEF_H) / 2, w, h: DEF_H };
  const h = Math.max(0, sh - dock - MARGIN * 2);
  return { x, y: MARGIN, w, h };
}
const clampFrame = (f: Frame, sw: number, sh: number): Frame => {
  const min = minSize(sw, sh);
  const w = Math.min(Math.max(f.w, min.w), sw);
  const h = Math.min(Math.max(f.h, min.h), sh);
  return { w, h, x: Math.min(Math.max(f.x, 0), Math.max(0, sw - w)), y: Math.min(Math.max(f.y, 0), Math.max(0, sh - h)) };
};

type Dir = "n" | "s" | "e" | "w" | "ne" | "nw" | "se" | "sw";
const HANDLES: Dir[] = ["n", "s", "e", "w", "ne", "nw", "se", "sw"];

/* Desktop wallpapers (chosen in the Dock; .desktop carries data-wallpaper → tokens.css) */
const WALLPAPERS = [
  { id: "aurora", label: "Aurora", token: "--wp-aurora" },
  { id: "desert", label: "Desert", token: "--wp-desert" },
  { id: "ocean", label: "Ocean", token: "--wp-ocean" },
  { id: "mono", label: "Mono", token: "--wp-mono" },
] as const;

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => { const id = window.setInterval(() => setNow(new Date()), 15_000); return () => window.clearInterval(id); }, []);
  return <span>{now.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" })}&nbsp;&nbsp;{now.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })}</span>;
}

/** The window's content area: below APP_W×APP_H the shell renders at its design size and is zoomed down to fit. */
function FitContent({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ w: number; h: number } | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setBox({ w: el.clientWidth, h: el.clientHeight }); // measured before the first paint: no full-size flash
    const ro = new ResizeObserver(([e]) => setBox({ w: e.contentRect.width, h: e.contentRect.height }));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const scale = box ? Math.min(1, box.w / APP_W, box.h / APP_H) : 1;
  return <div ref={ref} className={s.content}>
    <div className={s.fit} style={box && scale < 1 ? { zoom: scale, width: box.w / scale, height: box.h / scale } : undefined}>{children}</div>
  </div>;
}

export function MacDesktop({ children }: { children: ReactNode }) {
  const [win, setWin] = useState<WindowState>("normal");
  const [frame, setFrame] = useState<Frame | null>(null);
  const [interacting, setInteracting] = useState(false);
  const stageRef = useRef<HTMLElement>(null);
  const drag = useRef<{ mode: "move" | Dir; startX: number; startY: number; base: Frame } | null>(null);
  // The frame the user chose (last drag/resize, persisted); null = follow the default for the current screen.
  // The shown frame is always this one fitted to the stage, so shrinking the screen and growing it back
  // returns to the same window instead of leaving it squeezed.
  const chosen = useRef<Frame | null>(null);

  // Fit the frame to the stage on mount and whenever the stage changes size (browser resize, rotation,
  // fullscreen, devtools). Observing the stage itself is reliable; the window "resize" event can lag.
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    try {
      const raw = localStorage.getItem(FRAME_KEY);
      if (raw) chosen.current = JSON.parse(raw) as Frame;
    } catch { /* corrupted value: use the default */ }
    const fit = () => {
      const r = stage.getBoundingClientRect();
      setFrame(chosen.current
        ? clampFrame(chosen.current, r.width, r.height)
        : defaultFrame(r.width, r.height, parseFloat(getComputedStyle(stage).paddingBottom) || 0));
    };
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(stage);
    return () => ro.disconnect();
  }, []);

  // Leaving browser fullscreen with Esc also un-zooms the window.
  useEffect(() => {
    const onChange = () => { if (!document.fullscreenElement) setWin((w) => (w === "zoomed" ? "normal" : w)); };
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  // Pointer drag shared by title-bar moves and edge/corner resizes.
  useEffect(() => {
    if (!interacting) return;
    const onMove = (e: PointerEvent) => {
      const d = drag.current, stage = stageRef.current;
      if (!d || !stage) return;
      const r = stage.getBoundingClientRect();
      const dx = e.clientX - d.startX, dy = e.clientY - d.startY;
      const b = d.base;
      let f: Frame;
      if (d.mode === "move") {
        f = { ...b, x: b.x + dx, y: b.y + dy };
      } else {
        const m = d.mode;
        const left = m.includes("w") ? b.x + dx : b.x;
        const top = m.includes("n") ? b.y + dy : b.y;
        const w = m.includes("w") ? b.w - dx : m.includes("e") ? b.w + dx : b.w;
        const h = m.includes("n") ? b.h - dy : m.includes("s") ? b.h + dy : b.h;
        f = { x: left, y: top, w, h };
      }
      setFrame(clampFrame(f, r.width, r.height));
    };
    const onUp = () => {
      drag.current = null;
      setInteracting(false);
      setFrame((f) => {
        if (f) { chosen.current = f; try { localStorage.setItem(FRAME_KEY, JSON.stringify(f)); } catch { /* private mode */ } }
        return f;
      });
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    return () => { window.removeEventListener("pointermove", onMove); window.removeEventListener("pointerup", onUp); };
  }, [interacting]);

  const begin = (mode: "move" | Dir) => (e: React.PointerEvent) => {
    if (e.button !== 0 || win !== "normal" || !frame) return;
    if (mode === "move" && (e.target as HTMLElement).closest("button")) return; // not on traffic lights
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    drag.current = { mode, startX: e.clientX, startY: e.clientY, base: frame };
    setInteracting(true);
  };

  const zoom = () => {
    if (win === "zoomed") { setWin("normal"); if (document.fullscreenElement) void document.exitFullscreen().catch(() => {}); return; }
    setWin("zoomed");
    void document.documentElement.requestFullscreen?.().catch(() => { /* not allowed: the window still fills the screen */ });
  };
  const open = () => setWin((w) => (w === "zoomed" ? w : "normal"));
  const screen = useStore((st) => st.screen);
  const wallpaper = useStore((st) => st.wallpaper);
  const go = (id: ScreenId) => { actions.navigate(id); open(); };
  const free = win === "normal" && frame !== null;

  return (
    <div className={s.desktop} data-wallpaper={wallpaper}>
      <header className={s.menubar}>
        <span className={s.menuApp}>Messenger</span>
        {MENUS.map((m) => <span key={m} className={s.menuItem}>{m}</span>)}
        <span className={s.menuRight}>
          <BatteryFull size={18} strokeWidth={1.75} /><Wifi size={16} strokeWidth={2} /><Search size={15} strokeWidth={2} /><Clock />
        </span>
      </header>

      <main className={s.stage} ref={stageRef}>
        {win !== "closed" && frame && (
          <section
            className={`${s.window} ${free ? s.free : ""} ${win === "zoomed" ? s.zoomed : ""} ${win === "minimized" ? s.minimized : ""} ${interacting ? s.interacting : ""}`}
            style={free ? { left: frame.x, top: frame.y, width: frame.w, height: frame.h } : undefined}
            aria-label="Messenger window"
          >
            <div className={s.titlebar} onDoubleClick={zoom} onPointerDown={begin("move")}>
              <span className={s.lights}>
                <button className={s.red} aria-label="Close" onClick={() => setWin("closed")}><i>×</i></button>
                <button className={s.yellow} aria-label="Minimize" onClick={() => setWin("minimized")}><i>−</i></button>
                <button className={s.green} aria-label={win === "zoomed" ? "Exit full screen" : "Enter full screen"} onClick={zoom}><i>{win === "zoomed" ? "↙" : "↗"}</i></button>
              </span>
              <span className={s.title}>Messenger</span>
            </div>
            <FitContent>{children}</FitContent>
            {free && HANDLES.map((d) => (
              <span key={d} className={`${s.handle} ${s[`h_${d}`]}`} onPointerDown={begin(d)} />
            ))}
          </section>
        )}
      </main>

      {/* Windows-style desktop icons, left side: iOS tiles that open each screen */}
      {win !== "zoomed" && (
        <div className={s.deskIcons} aria-label="Desktop shortcuts">
          <button className={s.deskIcon} onClick={() => go("chats")}>
            <span className={`${s.dockIcon} ${s.tBlue}`}><MessageCircle size={26} strokeWidth={1.8} /></span>
            <span>Messenger</span>
          </button>
          {DOCK.map(({ id, label, icon: I, tone }) => (
            <button key={id} className={s.deskIcon} onClick={() => go(id)}>
              <span className={`${s.dockIcon} ${tone}`}><I size={26} strokeWidth={1.8} /></span>
              <span>{label}</span>
            </button>
          ))}
        </div>
      )}

      <nav className={`${s.dock} ${win === "zoomed" ? s.dockHidden : ""}`} aria-label="Dock">
        <button className={s.dockApp} aria-label="Messenger" onClick={() => go("chats")}>
          <span className={`${s.dockIcon} ${s.tBlue}`}><MessageCircle size={26} strokeWidth={1.8} /></span>
          <span className={s.dockLabel}>Messenger</span>
          {win !== "closed" && <i className={s.running} />}
        </button>
        <span className={s.dockDivider} aria-hidden="true" />
        {WALLPAPERS.map((w) => (
          <button
            key={w.id}
            className={`${s.dockApp} ${s.wpApp}`}
            aria-label={`${w.label} wallpaper`}
            aria-pressed={wallpaper === w.id}
            title={`${w.label} wallpaper`}
            onClick={() => actions.setWallpaper(w.id)}
          >
            <span className={s.wpSwatch} style={{ background: `var(${w.token})` }} />
            <span className={s.dockLabel}>{w.label}</span>
            {wallpaper === w.id && <i className={s.running} />}
          </button>
        ))}
      </nav>
    </div>
  );
}
