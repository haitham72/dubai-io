// A Diwan event's pictures as a swipe carousel: the current post centred and as tall as the space allows, neighbours
// peeking in dimmed; each keeps its own ratio (posts 4:5, stories 9:16). The picture showing is the one "Use in chat" shares.
// Every picture has a heart (favourites, this browser only). A picture Diwan holds more versions of offers
// "Generate more": a spinner while Mirsal asks Diwan, then the versions nest under that picture (a count on the picture
// and a strip below it). Picking a version makes it that picture's main image; the original stays in the strip.
import { useCallback, useEffect, useRef, useState } from "react";
import { Lightbox } from "./ImageDetail";
import { ChevronLeft, ChevronRight, Heart, Layers, Loader2, Sparkles } from "lucide-react";
import { moreFromEventPicture } from "../../api";
import type { DiwanEvent } from "../../types";
import { ICON } from "../../ui";
import s from "../updates.module.css";

type Status = "idle" | "loading" | "done" | "error";
interface Slot { base: string; shown: string; versions: string[]; status: Status; open: boolean; source?: string }

const FAVS = "mirsal.eventFavourites";
const MIN_SPIN_MS = 700; // the demo answers instantly; keep the spinner long enough to read
const name = (url: string) => url.split("?")[0].split("/").pop() ?? url;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function readFavs(): Set<string> {
  try { return new Set(JSON.parse(localStorage.getItem(FAVS) ?? "[]") as string[]); } catch { return new Set(); }
}

export function EventPictures({ event, onPick, className = "" }: { event: DiwanEvent; onPick: (url: string) => void; className?: string }) {
  const [slots, setSlots] = useState<Slot[]>(() => event.images.map((url) => ({ base: url, shown: url, versions: [], status: "idle", open: false })));
  const [index, setIndex] = useState(0);
  const [preview, setPreview] = useState("");
  const closePreview = useCallback(() => setPreview(""), []);
  const [favs, setFavs] = useState(readFavs);
  const track = useRef<HTMLDivElement>(null);

  const current = slots[index];
  useEffect(() => { if (current) onPick(current.shown); }, [current?.shown]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!slots.length) return null;

  const patch = (i: number, p: Partial<Slot>) => setSlots((list) => list.map((sl, j) => (j === i ? { ...sl, ...p } : sl)));

  // Slides keep their own width (posts are wider than stories), so positions come from each slide's centre.
  const centre = (el: HTMLElement) => el.offsetLeft + el.offsetWidth / 2;
  function go(i: number, smooth = true) {
    const el = track.current;
    const to = Math.max(0, Math.min(slots.length - 1, i));
    const slide = el?.children[to] as HTMLElement | undefined;
    if (!el || !slide) return;
    el.scrollTo({ left: centre(slide) - el.clientWidth / 2, behavior: smooth ? "smooth" : "auto" });
    setIndex(to);
  }
  const onScroll = () => {
    const el = track.current;
    if (!el) return;
    const mid = el.scrollLeft + el.clientWidth / 2;
    let best = 0;
    [...el.children].forEach((c, i) => { if (Math.abs(centre(c as HTMLElement) - mid) < Math.abs(centre(el.children[best] as HTMLElement) - mid)) best = i; });
    setIndex(best);
  };

  function toggleFav(url: string) {
    setFavs((prev) => {
      const next = new Set(prev);
      if (!next.delete(url)) next.add(url);
      try { localStorage.setItem(FAVS, JSON.stringify([...next])); } catch { /* storage unavailable */ }
      return next;
    });
  }

  async function generateMore(i: number) {
    const slot = slots[i];
    if (slot.status === "loading") return;
    patch(i, { status: "loading" });
    try {
      const [res] = await Promise.all([moreFromEventPicture(event.id, name(slot.base)), sleep(MIN_SPIN_MS)]);
      patch(i, { status: "done", versions: res.images.map((im) => im.url), source: res.source, open: res.images.length > 0 });
    } catch {
      patch(i, { status: "error" });
    }
  }

  const canMore = (sl: Slot) => (event.more ?? []).includes(sl.base);

  return <div className={`${s.carousel} ${className}`}>
    {preview && <Lightbox url={preview} title={event.title} onClose={closePreview} />}
    <div className={s.carouselStage}>
      <div ref={track} className={s.carouselTrack} onScroll={onScroll} tabIndex={0} aria-roledescription="carousel"
        aria-label={`${event.title} pictures`}
        onKeyDown={(k) => { if (k.key === "ArrowLeft") go(index - 1); if (k.key === "ArrowRight") go(index + 1); }}>
        {slots.map((sl, i) => {
          const on = i === index;
          const fav = favs.has(sl.shown);
          return <div key={sl.base} className={`${s.carouselSlide} ${on ? s.slideOn : ""}`} aria-roledescription="slide"
            aria-label={`Picture ${i + 1} of ${slots.length}${sl.shown !== sl.base ? ", a version" : ""}`} onClick={on ? undefined : () => go(i)}>
            <button type="button" className={s.pictureOpen} aria-label={`Open picture ${i + 1}`} onClick={() => {
              if (on) setPreview(sl.shown); else go(i);
            }}>
              <img src={sl.shown} alt={event.title} onLoad={i === 0 ? () => { if (index === 0) go(0, false); } : undefined}
                className={sl.status === "loading" ? s.picBusy : undefined} />
            </button>
            {sl.status === "loading" && <span className={s.picSpinner} role="status"><Loader2 {...ICON} size={26} className={s.spin} />Asking Diwan…</span>}
            {on && sl.status !== "loading" && <div className={s.picTools}>
              <button type="button" className={`${s.picTool} ${fav ? s.picFav : ""}`} aria-pressed={fav}
                aria-label={fav ? "Remove from favourites" : "Add to favourites"} onClick={() => toggleFav(sl.shown)}>
                <Heart {...ICON} size={18} fill={fav ? "currentColor" : "none"} />
              </button>
              {sl.versions.length > 0
                ? <button type="button" className={`${s.picTool} ${sl.open ? s.picToolOn : ""}`} aria-expanded={sl.open}
                    aria-label={`${sl.versions.length} versions`} onClick={() => patch(i, { open: !sl.open })}>
                    <Layers {...ICON} size={18} /><b>{sl.versions.length}</b>
                  </button>
                : canMore(sl) && <button type="button" className={s.picTool} onClick={() => generateMore(i)}>
                    <Sparkles {...ICON} size={18} />{sl.status === "error" ? "Try again" : sl.status === "done" ? "No more yet" : "Generate more"}
                  </button>}
            </div>}
          </div>;
        })}
      </div>
      {slots.length > 1 && <>
        <button type="button" className={`${s.carouselArrow} ${s.carouselPrev}`} aria-label="Previous picture" disabled={index === 0}
          onClick={() => go(index - 1)}><ChevronLeft {...ICON} /></button>
        <button type="button" className={`${s.carouselArrow} ${s.carouselNext}`} aria-label="Next picture" disabled={index === slots.length - 1}
          onClick={() => go(index + 1)}><ChevronRight {...ICON} /></button>
      </>}
    </div>

    {current?.open && current.versions.length > 0 && <div className={s.versions} role="radiogroup" aria-label="Versions of this picture">
      <span className={s.versionsLabel}>{current.versions.length} versions · {current.source}</span>
      {[current.base, ...current.versions].map((url, v) => <button key={url} type="button" role="radio" aria-checked={url === current.shown}
        className={url === current.shown ? s.versionOn : undefined} onClick={() => patch(index, { shown: url })}>
        <img src={url} alt={v ? `Version ${v}` : "Original"} />
        <small>{v ? v : "Original"}</small>
        {favs.has(url) && <Heart {...ICON} size={12} fill="currentColor" className={s.versionFav} />}
      </button>)}
    </div>}

    {slots.length > 1 && <div className={s.carouselDots}>
      {slots.map((sl, i) => <button key={sl.base} type="button" aria-label={`Show picture ${i + 1}`} aria-current={i === index}
        className={i === index ? s.dotOn : undefined} onClick={() => go(i)} />)}
    </div>}
  </div>;
}

/** What "Use in chat" sends for an event: the picture showing, with a caption, or a text line when there is none. */
export const eventChatItem = (e: DiwanEvent, url?: string) => {
  const image = url || e.images[0];
  return image ? { kind: "image" as const, url: image, caption: `${e.title} · ${e.when}` } : { kind: "text" as const, text: `${e.title} · ${e.when}` };
};
