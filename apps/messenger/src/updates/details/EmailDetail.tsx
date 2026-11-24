import { useState } from "react";
import { actions } from "../../store";
import type { TaskResult } from "../../types";
import { DetailActions, share, type Notify } from "./Detail";
import s from "../updates.module.css";

export function EmailDetail({ result, notify, link, sendCard }: {
  result: Extract<TaskResult, { type: "email" }>; notify: Notify; link: string;
  sendCard: (icon: "mail", title: string, subtitle: string) => void;
}) {
  const [id, setId] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("draft") ?? result.drafts[0]?.id);
  const draft = result.drafts.find(d => d.id === id) ?? result.drafts[0];
  if (!draft) return <p className={s.empty}>No email drafts are available.</p>;
  return <div className={s.splitDetail}>
    <div className={s.resultList} aria-label="Email drafts">{result.drafts.map(entry => <button key={entry.id}
      className={`${s.resultItem} ${entry.id === draft.id ? s.selectedItem : ""}`} aria-pressed={entry.id === draft.id} onClick={() => setId(entry.id)}>
      <strong>{entry.to}</strong><small>{entry.time}</small><span>{entry.subject}</span>
    </button>)}</div>
    <article className={s.document}><dl className={s.emailFields}><dt>To</dt><dd>{draft.to}</dd><dt>Subject</dt><dd>{draft.subject}</dd></dl>
      <div className={s.emailBody}>{draft.body}</div>
      <DetailActions openLabel="Open draft" onOpen={() => actions.navigate("mail")}
        onShare={() => { void share(`${link}&draft=${encodeURIComponent(draft.id)}`, notify); }} onChat={() => sendCard("mail", draft.subject, `Draft to ${draft.to}`)} />
    </article>
  </div>;
}
