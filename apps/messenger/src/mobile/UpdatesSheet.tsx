// Messenger Updates on the phone: one sheet. List of tasks → tap → the same detail cards as desktop.
import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, X } from "lucide-react";
import { actions, useStore } from "../store";
import { ICON } from "../ui";
import { TaskIcon, TaskStatus } from "../updates/common";
import { Detail } from "../updates/details/Detail";
import { ORB } from "./parts";
import { Sheet } from "./Sheet";
import s from "./mobile.module.css";

const segments = ["All", "Running", "Done"] as const;

export function UpdatesSheet({ initialId, onClose }: { initialId?: string; onClose: () => void }) {
  const all = useStore((st) => st.tasks);
  const tasks = useMemo(() => all.filter((t) => !t.dismissed), [all]);
  const [selectedId, setSelectedId] = useState<string | undefined>(initialId);
  const [segment, setSegment] = useState<(typeof segments)[number]>("All");
  const [lightbox, setLightbox] = useState(false);
  const [now, setNow] = useState(Date.now());
  const [toast, setToast] = useState<{ text: string; until: number } | null>(null);
  const selected = tasks.find((t) => t.id === selectedId);
  const running = tasks.filter((t) => t.status === "running" || t.status === "queued").length;

  useEffect(() => { actions.markTasksRead(); }, []);
  useEffect(() => { const id = window.setInterval(() => setNow(Date.now()), 1000); return () => window.clearInterval(id); }, []);

  const shown = tasks.filter((t) => segment === "All" || (segment === "Done" ? t.status === "completed" : t.status !== "completed"));
  const notify = (text: string) => setToast({ text, until: Date.now() + 3000 });

  return (
    <Sheet label="Messenger Updates" onClose={onClose}>
      <div className={s.sheetHead}>
        {selected
          ? <button className={s.sheetBack} onClick={() => { setSelectedId(undefined); setLightbox(false); }}><ChevronLeft {...ICON} />Updates</button>
          : <><img className={s.sheetOrb} src={ORB} alt="" /><h2 className={s.sheetTitle}>Messenger Updates<small>{tasks.length} updates{running ? ` · ${running} running` : ""}</small></h2></>}
        <button className={`${s.gbtn} ${s.gbtnSmall}`} aria-label="Close" onClick={onClose}><X {...ICON} size={18} /></button>
      </div>

      {selected ? (
        <div className={s.detail}>
          <h3 className={s.detailTitle}>{selected.title}</h3>
          <p className={s.detailSub}>{selected.subtitle}</p>
          <Detail task={selected} now={now} lightbox={lightbox} onLightbox={setLightbox} notify={notify} />
        </div>
      ) : (
        <>
          <div className={s.seg} role="tablist">
            {segments.map((x) => <button key={x} role="tab" aria-selected={x === segment} className={x === segment ? s.segOn : ""} onClick={() => setSegment(x)}>{x}</button>)}
          </div>
          <div className={s.taskList}>
            {shown.map((t) => (
              <button key={t.id} className={s.task} onClick={() => setSelectedId(t.id)}>
                {t.result?.type === "image"
                  ? <img className={s.taskThumb} src={t.result.imageUrl} alt="" />
                  : <TaskIcon type={t.type} />}
                <span className={s.taskText}><b>{t.title}</b><span>{t.subtitle}</span></span>
                <span className={s.taskStatus}><TaskStatus task={t} now={now} /></span>
              </button>
            ))}
            {!shown.length && <p className={s.empty}>Nothing here yet.</p>}
          </div>
        </>
      )}
      {toast && toast.until > now && <div className={s.toast} role="status">{toast.text}</div>}
    </Sheet>
  );
}
