// A research brief opened from a chat card, shown as a document page (PDF style) over the app — the chat never resizes.
// Opening it marks the linked Mirsal Updates notification as seen.
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { ArrowUpRight, BookOpen, ExternalLink, X } from "lucide-react";
import { actions, getState } from "../store";
import type { MessageBody, MirsalTask, ResearchItem } from "../types";
import { Button, ICON, IconButton } from "../ui";
import s from "./report.module.css";

type Card = Extract<MessageBody, { kind: "card" }>;
type Brief = ResearchItem & { mode?: "live" | "demo" };

/** The research task a chat card points at: its own `taskId`, else the finished research task with the same title. */
export function researchTaskFor(card: Card): MirsalTask | undefined {
  const tasks = getState().tasks.filter((t) => t.result?.type === "research" && t.status === "completed");
  return tasks.find((t) => t.id === card.taskId)
    ?? tasks.find((t) => t.result?.type === "research" && t.result.items.some((i) => i.title === card.title || card.subtitle.includes(i.title)));
}

/** Open a research card: the brief as a document if Mirsal has it, else the Research screen. */
export function openResearchCard(card: Card, open: (task: MirsalTask) => void) {
  const task = researchTaskFor(card);
  if (!task) return actions.navigate("research");
  if (task.unread) actions.updateTask(task.id, { unread: false }); // seen
  open(task);
}

export function ReportDoc({ task, onClose }: { task: MirsalTask; onClose: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  const brief = (task.result?.type === "research" ? task.result.items[0] : undefined) as Brief | undefined;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    dialog.current?.querySelector<HTMLButtonElement>("button")?.focus();
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") { e.preventDefault(); e.stopImmediatePropagation(); onClose(); } };
    window.addEventListener("keydown", key, true);
    return () => { window.removeEventListener("keydown", key, true); previous?.focus(); };
  }, [onClose]);

  if (!brief) return null;
  const date = new Date(task.completedAt ?? Date.now()).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const sources = brief.sources ?? [];

  return createPortal(<div className={s.backdrop} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
    <div className={s.viewer} ref={dialog} role="dialog" aria-modal="true" aria-label={`Research brief: ${brief.title}`}>
      <header className={s.toolbar}>
        <span className={s.fileIcon}><BookOpen {...ICON} /></span>
        <span className={s.fileName}><strong>{brief.title}</strong><small>Research brief · {date}</small></span>
        <Button icon={ArrowUpRight} onClick={() => { onClose(); actions.navigate("research"); }}>Open in Research</Button>
        <IconButton icon={X} label="Close report" onClick={onClose} />
      </header>

      <div className={s.canvas}>
        <article className={s.page}>
          <div className={s.pageHead}>
            <span className={s.brand}>MIRSAL RESEARCH</span>
            <span>{date}{brief.mode === "demo" && <em className={s.demo}>Demo</em>}</span>
          </div>
          <h1>{brief.title}</h1>
          <p className={s.meta}>
            {brief.findings.length} key findings · {sources.length} sources{brief.verified ? ` · ${brief.verified} claims checked against their sources` : ""}
          </p>

          <h2>Executive summary</h2>
          <p>{brief.summary}</p>

          <h2>Key findings</h2>
          <ol className={s.findings}>{brief.findings.map((f) => <li key={f}>{f}</li>)}</ol>

          {!!brief.ranking?.length && <>
            <h2>Ranking</h2>
            <ol className={s.findings}>{brief.ranking.map((r) => <li key={r.name}><strong>{r.name}</strong>{r.price && r.price !== "—" ? ` · ${r.price}` : ""} — {r.why}</li>)}</ol>
          </>}

          {brief.sections?.map((sec) => <section key={sec.heading}><h2>{sec.heading}</h2><p>{sec.body}</p></section>)}

          {!!sources.length && <>
            <h2>Sources</h2>
            <ol className={s.sources}>{sources.map((src, i) => <li key={src.url ?? `${src.domain}-${i}`}>
              {src.url ? <a href={src.url} target="_blank" rel="noopener noreferrer">{src.title || src.domain}<ExternalLink size={12} strokeWidth={2} /></a> : <span>{src.title}</span>}
              <small>{src.domain}</small>
            </li>)}</ol>
          </>}

          <footer className={s.pageFoot}><span>Prepared by Mirsal{brief.mode === "demo" ? " · demo brief, not live research" : ""}</span><span>1</span></footer>
        </article>
      </div>
    </div>
  </div>, document.body);
}
