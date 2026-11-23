import { useState } from "react";
import { actions } from "../../store";
import type { TaskResult } from "../../types";
import { DetailActions, share, type Notify } from "./Detail";
import s from "../updates.module.css";

export function ResearchDetail({ result, notify, link, sendCard }: {
  result: Extract<TaskResult, { type: "research" }>; notify: Notify; link: string;
  sendCard: (icon: "research", title: string, subtitle: string) => void;
}) {
  const [id, setId] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("item") ?? result.items[0]?.id);
  const item = result.items.find(item => item.id === id) ?? result.items[0];
  if (!item) return <p className={s.empty}>No research items are available.</p>;
  return <div className={s.splitDetail}>
    <div className={s.resultList} aria-label="Research reports">{result.items.map(entry => <button key={entry.id}
      className={`${s.resultItem} ${entry.id === item.id ? s.selectedItem : ""}`} aria-pressed={entry.id === item.id} onClick={() => setId(entry.id)}>
      <strong>{entry.title}</strong><small>{entry.time}</small><span>{entry.summary}</span>
    </button>)}</div>
    <article className={s.document}><div className={s.documentTitle}><h3>{item.title}</h3><small>{item.time}</small></div>
      <p>{item.summary}</p><ol className={s.findings}>{item.findings.map((finding, i) => <li key={i}>{finding}</li>)}</ol>
      {item.sources?.length ? <p className={s.sourceList}>Sources: {item.sources.map(source => `${source.title} (${source.domain})`).join(" · ")}</p> : null}
      <DetailActions openLabel="Open full report" onOpen={() => actions.navigate("research")}
        onShare={() => { void share(`${link}&item=${encodeURIComponent(item.id)}`, notify); }} onChat={() => sendCard("research", item.title, item.summary)} />
    </article>
  </div>;
}
