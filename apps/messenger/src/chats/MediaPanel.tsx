// Telegram-style media panel over the composer: Emoji · Stickers · GIFs. Floats above the composer (the chat never
// resizes). Stickers come from the sticker packs (agents service, else public/stickers); "+ New pack" asks Mirsal Builder
// for three options to swipe. GIFs come from GIPHY through the agents service — without a key the tab says so, no fakes.
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, Apple, Cat, Clock, Flag, Heart, Lightbulb, Loader2, Plane, Plus, Search, Smile, Sparkles, Users, X,
} from "lucide-react";
import { generateStickerOptions, listStickerPacks, searchGifs, type BuilderOption, type Gif } from "../api";
import { ICON } from "../ui";
import { emojiCategories, type EmojiItem } from "./data";
import { chatContext } from "./skills";
import { StickerMedia } from "./StickerMedia";
import s from "./media.module.css";

type Tab = "emoji" | "stickers" | "gifs";
interface Pack { id: string; title: string; urls: string[]; mine?: boolean }

const RECENT_EMOJI = "mirsal.recentEmoji";
const RECENT_STICKERS = "mirsal.recentStickers";
const MY_PACKS = "mirsal.myPacks";
const read = <T,>(key: string, fallback: T): T => { try { return JSON.parse(localStorage.getItem(key) ?? "") as T; } catch { return fallback; } };
const write = (key: string, value: unknown) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ } };
const remember = (key: string, value: string, max: number) => write(key, [value, ...read<string[]>(key, []).filter((v) => v !== value)].slice(0, max));

const CATEGORY_ICON: Record<string, typeof Smile> = {
  Smileys: Smile, People: Users, Animals: Cat, Food: Apple, Travel: Plane, Activities: Activity, Objects: Lightbulb, Symbols: Heart, Flags: Flag,
};

export function MediaPanel({ chatId, onEmoji, onSticker, onGif, onClose }: {
  chatId: string; onEmoji: (e: string) => void; onSticker: (url: string, pack: string) => void; onGif: (gif: Gif) => void; onClose: () => void;
}) {
  const [tab, setTab] = useState<Tab>("emoji");
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); onClose(); } };
    const away = (e: PointerEvent) => {
      const t = e.target as Element;
      if (!panel.current?.contains(t) && !t.closest("[data-media-toggle]")) onClose();
    };
    window.addEventListener("keydown", key, true);
    window.addEventListener("pointerdown", away, true);
    return () => { window.removeEventListener("keydown", key, true); window.removeEventListener("pointerdown", away, true); };
  }, [onClose]);

  return <div ref={panel} className={s.panel} role="dialog" aria-label="Emoji, stickers and GIFs">
    <div className={s.tabs} role="tablist">
      {(["emoji", "stickers", "gifs"] as const).map((t) => <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? s.tabOn : ""}
        onClick={() => setTab(t)}>{t === "emoji" ? "Emoji" : t === "stickers" ? "Stickers" : "GIFs"}</button>)}
      <button className={s.close} aria-label="Close" onClick={onClose}><X {...ICON} size={18} /></button>
    </div>
    {tab === "emoji" && <EmojiTab onPick={(e) => { remember(RECENT_EMOJI, e, 24); onEmoji(e); }} />}
    {tab === "stickers" && <StickersTab chatId={chatId} onPick={(url, pack) => { remember(RECENT_STICKERS, url, 15); onSticker(url, pack); }} />}
    {tab === "gifs" && <GifsTab onPick={onGif} />}
  </div>;
}

/* ---------------- Emoji ---------------- */
function EmojiTab({ onPick }: { onPick: (e: string) => void }) {
  const [query, setQuery] = useState("");
  const [active, setActive] = useState("Recent");
  const body = useRef<HTMLDivElement>(null);
  const recent = read<string[]>(RECENT_EMOJI, []);
  const q = query.trim().toLowerCase();
  const found = useMemo(() => q ? emojiCategories.flatMap((c) => c.items).filter((i) => i.words.includes(q) || i.e === q) : [], [q]);
  const sections = q ? [{ name: "Results", items: found }]
    : [...(recent.length ? [{ name: "Recent", items: recent.map((e) => ({ e, words: "" })) }] : []), ...emojiCategories];
  const jump = (name: string) => {
    setActive(name);
    body.current?.querySelector(`[data-section="${name}"]`)?.scrollIntoView({ block: "start", behavior: "smooth" });
  };
  const onScroll = () => {
    const top = body.current?.scrollTop ?? 0;
    const heads = [...(body.current?.querySelectorAll<HTMLElement>("[data-section]") ?? [])];
    const cur = heads.filter((h) => h.offsetTop - 8 <= top).pop();
    if (cur) setActive(cur.dataset.section!);
  };
  return <>
    <label className={s.search}><Search {...ICON} size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search emoji" aria-label="Search emoji" /></label>
    <div className={s.body} ref={body} onScroll={onScroll}>
      {sections.map((sec) => <section key={sec.name} data-section={sec.name}>
        <h3>{sec.name}</h3>
        <div className={s.emojiGrid}>{sec.items.map((i: EmojiItem) => <button key={sec.name + i.e} title={i.words} aria-label={i.words || i.e} onClick={() => onPick(i.e)}>{i.e}</button>)}</div>
        {!sec.items.length && <p className={s.empty}>No emoji match “{query}”.</p>}
      </section>)}
    </div>
    {!q && <nav className={s.strip} aria-label="Emoji categories">
      {recent.length > 0 && <button aria-label="Recent" className={active === "Recent" ? s.stripOn : ""} onClick={() => jump("Recent")}><Clock {...ICON} size={18} /></button>}
      {emojiCategories.map((c) => { const I = CATEGORY_ICON[c.name] ?? Smile; return <button key={c.name} aria-label={c.name} className={active === c.name ? s.stripOn : ""} onClick={() => jump(c.name)}><I {...ICON} size={18} /></button>; })}
    </nav>}
  </>;
}

/* ---------------- Stickers ---------------- */
function StickersTab({ chatId, onPick }: { chatId: string; onPick: (url: string, pack: string) => void }) {
  const [packs, setPacks] = useState<Pack[] | null>(null);
  const [active, setActive] = useState("recent");
  const [builder, setBuilder] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const recent = read<string[]>(RECENT_STICKERS, []);
  const press = useRefTimer();
  useEffect(() => {
    let live = true;
    listStickerPacks().then((list) => { if (live) setPacks([...read<Pack[]>(MY_PACKS, []).map((p) => ({ ...p, mine: true })), ...list]); })
      .catch(() => { if (live) setPacks(read<Pack[]>(MY_PACKS, []).map((p) => ({ ...p, mine: true }))); });
    return () => { live = false; };
  }, [builder]);
  if (builder) return <Builder chatId={chatId} onDone={(kept) => { setBuilder(false); if (kept) setActive(kept); }} />;
  if (!packs) return <div className={s.loading}><Loader2 {...ICON} className={s.spin} />Loading stickers…</div>;
  const shown = active === "recent" ? { id: "recent", title: "Recent", urls: recent } : packs.find((p) => p.id === active) ?? packs[0];
  return <>
    <div className={s.body}>
      <h3>{shown?.title}{packs.find((p) => p.id === shown?.id)?.mine && <em className={s.mine}>My pack</em>}</h3>
      <div className={s.stickerGrid}>
        {shown?.urls.map((url) => <button key={url} aria-label="Send sticker"
          onClick={() => { if (!press.fired()) onPick(url, shown.id); }}
          onPointerDown={() => press.start(() => setPreview(url))} onPointerUp={press.clear} onPointerLeave={press.clear}>
          <StickerMedia url={url} />
        </button>)}
        {active !== "recent" && <button className={s.newPack} onClick={() => setBuilder(true)}><Plus {...ICON} />New pack</button>}
      </div>
      {active === "recent" && !recent.length && <p className={s.empty}>Stickers you send show up here.</p>}
    </div>
    <nav className={s.strip} aria-label="Sticker packs">
      <button aria-label="Recent stickers" className={active === "recent" ? s.stripOn : ""} onClick={() => setActive("recent")}><Clock {...ICON} size={18} /></button>
      {packs.map((p) => <button key={p.id} aria-label={p.title} title={p.title} className={`${s.cover} ${active === p.id ? s.stripOn : ""}`} onClick={() => setActive(p.id)}>{p.urls[0] && <StickerMedia url={p.urls[0]} />}</button>)}
      <button aria-label="New pack with Mirsal" onClick={() => setBuilder(true)}><Sparkles {...ICON} size={18} /></button>
    </nav>
    {preview && <button className={s.preview} aria-label="Close preview" onClick={() => setPreview(null)}><StickerMedia url={preview} /></button>}
  </>;
}
/** Long-press (400 ms) previews a sticker large; the tap that ends it doesn't also send. */
function useRefTimer() {
  const t = useRef(0); const did = useRef(false);
  return {
    start(fn: () => void) { did.current = false; t.current = window.setTimeout(() => { did.current = true; fn(); }, 400); },
    clear() { window.clearTimeout(t.current); },
    fired() { const f = did.current; did.current = false; return f; },
  };
}

/** Mirsal Builder: three generated packs to swipe; "Keep this pack" saves it to My packs (this browser). */
function Builder({ chatId, onDone }: { chatId: string; onDone: (kept?: string) => void }) {
  const [opts, setOpts] = useState<{ mode: string; options: BuilderOption[] } | null>(null);
  const [error, setError] = useState(false);
  const [index, setIndex] = useState(0);
  const track = useRef<HTMLDivElement>(null);
  useEffect(() => {
    generateStickerOptions("new sticker pack for this chat", chatContext(chatId).lines).then(setOpts).catch(() => setError(true));
  }, [chatId]);
  const keep = () => {
    const o = opts!.options[index];
    const id = `mine-${o.id}-${Date.now().toString(36)}`;
    write(MY_PACKS, [{ id, title: o.title, urls: o.stickers.map((x) => x.url) }, ...read<Pack[]>(MY_PACKS, [])].slice(0, 12));
    onDone(id);
  };
  return <div className={s.body}>
    <h3><Sparkles {...ICON} size={16} />New pack from Mirsal Builder{opts?.mode === "demo" && <em className={s.mine}>Demo</em>}</h3>
    {error ? <p className={s.empty}>Mirsal Builder runs on the agents service (npm run agents). <button className={s.link} onClick={() => onDone()}>Back</button></p>
      : !opts ? <div className={s.loading}><Loader2 {...ICON} className={s.spin} />Designing three packs…</div>
      : <>
        <div className={s.options} ref={track} onScroll={(e) => setIndex(Math.round(e.currentTarget.scrollLeft / e.currentTarget.clientWidth))}>
          {opts.options.map((o) => <div key={o.id} className={s.option}>
            <strong>{o.title}</strong>
            <div className={s.optionGrid}>{o.stickers.slice(0, 8).map((x) => <span key={x.url}><StickerMedia url={x.url} /></span>)}</div>
          </div>)}
        </div>
        <div className={s.dots}>{opts.options.map((o, i) => <button key={o.id} aria-label={`Option ${i + 1}`} className={i === index ? s.dotOn : ""}
          onClick={() => track.current?.scrollTo({ left: i * track.current.clientWidth, behavior: "smooth" })} />)}</div>
        <div className={s.builderActions}><button className={s.link} onClick={() => onDone()}>Cancel</button><button className={s.keep} onClick={keep}>Keep this pack</button></div>
      </>}
  </div>;
}

/* ---------------- GIFs ---------------- */
function GifsTab({ onPick }: { onPick: (gif: Gif) => void }) {
  const [query, setQuery] = useState("");
  const [res, setRes] = useState<{ mode: "giphy" | "off"; gifs: Gif[] } | null>(null);
  useEffect(() => {
    let live = true;
    const t = window.setTimeout(() => searchGifs(query.trim()).then((r) => { if (live) setRes(r); }), query ? 350 : 0);
    return () => { live = false; window.clearTimeout(t); };
  }, [query]);
  if (res?.mode === "off") return <div className={s.offline}><strong>GIFs aren't connected yet</strong><span>Add a GIPHY key to the agents service to search GIFs here.</span></div>;
  const cols: Gif[][] = [[], []];
  const heights = [0, 0];
  for (const g of res?.gifs ?? []) { const c = heights[0] <= heights[1] ? 0 : 1; cols[c].push(g); heights[c] += g.height / g.width; }
  return <>
    <label className={s.search}><Search {...ICON} size={16} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search GIPHY" aria-label="Search GIFs" /></label>
    <div className={s.body}>
      <h3>{query.trim() ? `Results for “${query.trim()}”` : "Trending"}</h3>
      {!res ? <div className={s.loading}><Loader2 {...ICON} className={s.spin} />Loading GIFs…</div>
        : <div className={s.masonry}>{cols.map((col, i) => <div key={i}>{col.map((g) => <button key={g.id} aria-label={`Send GIF: ${g.title}`} onClick={() => onPick(g)}>
          <img src={g.preview} alt={g.title} loading="lazy" style={{ aspectRatio: `${g.width} / ${g.height}` }} />
        </button>)}</div>)}</div>}
      {res && !res.gifs.length && <p className={s.empty}>No GIFs for “{query}”.</p>}
      <p className={s.credit}>Powered by GIPHY</p>
    </div>
  </>;
}
