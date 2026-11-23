// Mirsal AI — agents, their results and the conversation, in one workspace (replaces Mirsal Updates + AI Chat).
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  ArrowUp, Check, ChevronDown, Copy, Globe, Mic, MoreHorizontal,
  Paperclip, Plus, RotateCcw, Share, SquarePen, ThumbsDown, ThumbsUp,
} from "lucide-react";
import { actions, useStore } from "../store";
import { ICON, IconButton, SearchField, SidebarHeader, Spinner } from "../ui";
import type { AiMessage, ScreenId } from "../types";
import { sendUserMessage } from "./runAction";
import { aiContacts, suggestionChips } from "./data";
import { ai, useAi } from "./state";
import { Activity, Fold } from "./Activity";
import { TaskView } from "./TaskView";
import { voice, useVoice, type VoiceStage } from "../voice/state";
import s from "./ai.module.css";

const destinations = new Set<string>(["chats", "flights", "stocks", "weather", "mail", "calendar", "files", "ai", "research", "history"]);
function inlineRender(text: string): React.ReactNode {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\(#[a-z]+\))/g).map((part, i) => {
    if (part.startsWith("**")) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`")) return <code key={i} className={s.mdCode}>{part.slice(1, -1)}</code>;
    const link = part.match(/^\[([^\]]+)\]\(#([a-z]+)\)$/);
    if (link && destinations.has(link[2])) return <button key={i} className={s.mdLink} onClick={() => actions.navigate(link[2] as ScreenId)}>{link[1]}</button>;
    return part;
  });
}
function renderMarkdown(text: string) {
  const out: React.ReactNode[] = [];
  let list: React.ReactNode[] = [];
  let kind: "ul" | "ol" | undefined;
  let start = 1;
  const flush = (key: number) => {
    if (list.length) out.push(kind === "ol" ? <ol key={`list-${key}`} start={start} className={s.mdList}>{list}</ol> : <ul key={`list-${key}`} className={s.mdList}>{list}</ul>);
    list = []; kind = undefined;
  };
  text.split("\n").forEach((line, i) => {
    const item = line.match(/^\s*(?:([-*])\s+|(\d+)\.\s+)(.+)$/);
    if (item) {
      const next = item[2] ? "ol" : "ul";
      if (kind && kind !== next) flush(i);
      if (!kind) { kind = next; start = Number(item[2] ?? 1); }
      list.push(<li key={i}>{inlineRender(item[3])}</li>);
      return;
    }
    flush(i);
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) out.push(<h3 key={i} className={s.mdHeading}>{inlineRender(heading[2])}</h3>);
    else if (line.trim() === "---") out.push(<hr key={i} className={s.mdSep} />);
    else if (!line.trim()) out.push(<div key={i} className={s.mdGap} />);
    else out.push(<div key={i}>{inlineRender(line)}</div>);
  });
  flush(-1);
  return out;
}

function AISidebar() {
  const [q, setQ] = useState("");
  const [chatsOpen, setChatsOpen] = useState(() => window.matchMedia("(max-width: 820px)").matches); // phone: chats only
  const selected = useAi((st) => st.selected);
  const task = useAi((st) => st.task);
  const grouped = aiContacts.filter((c) => c.id !== "new" && c.name.toLowerCase().includes(q.toLowerCase())).reduce<Record<string, typeof aiContacts>>((acc, c) => {
    (acc[c.group ?? "Today"] ??= []).push(c);
    return acc;
  }, {});
  const chatCount = aiContacts.filter((c) => c.id !== "new").length;
  return <div className={s.sidebar}>
    <SidebarHeader title="Mirsal AI"><IconButton icon={SquarePen} label="New chat" onClick={ai.newChat} /></SidebarHeader>
    <div className={s.sidebarScroll}>
      <Activity />
      <section>
        <Fold title="Chats" count={chatCount} open={chatsOpen} onToggle={() => setChatsOpen(!chatsOpen)} />
        {chatsOpen && <>
          <SearchField placeholder="Search chats" value={q} onChange={setQ} />
          {Object.entries(grouped).map(([group, items]) => <section key={group}>
            <h2 className={s.groupLabel}>{group}</h2>
            {items.map((c) => {
              const on = !task && selected === c.id;
              return <button key={c.id} title={c.name} aria-current={on ? "true" : undefined} className={`${s.chatItem} ${on ? s.chatItemActive : ""}`} onClick={() => ai.select(c.id)}>{c.name}</button>;
            })}
          </section>)}
          {!Object.keys(grouped).length && <p className={s.noResults}>No chats found.</p>}
        </>}
      </section>
    </div>
  </div>;
}

/** Preserve live task subscription: progress line → completed inline video. */
function TaskVideo({ m }: { m: AiMessage }) {
  const task = useStore((st) => m.taskId ? st.tasks.find((t) => t.id === m.taskId) : undefined);
  const result = task?.result?.type === "video" ? task.result : undefined;
  if (result) {
    return <video className={s.mdVideo} src={result.videoUrl} title={result.title} controls playsInline preload="metadata" />;
  }
  if (task?.type === "video" && task.status === "running") {
    return <div className={s.thinkingLine}><Spinner />Creating video… {task.progress ?? 0}%</div>;
  }
  if (task?.type === "video" && task.status === "failed") {
    return <div className={s.thinkingLine}>Video failed: {task.error}</div>;
  }
  return null;
}
/** Preserve live task subscription: spinner → completed inline image. */
function TaskImage({ m }: { m: AiMessage }) {
  const task = useStore((st) => m.taskId ? st.tasks.find((t) => t.id === m.taskId) : undefined);
  const url = m.imageUrl ?? (task?.result?.type === "image" ? task.result.imageUrl : undefined);
  if (url) return <img src={url} alt="AI conversation image" className={s.mdImg} />;
  if (task?.status === "running") return <div className={s.thinkingLine}><Spinner />Generating image…</div>;
  if (task?.status === "failed") return <div className={s.thinkingLine}>Image failed: {task.error}</div>;
  return null;
}
function AiTurn({ m, regenerate, busy }: { m: AiMessage; regenerate: () => void; busy: boolean }) {
  const [copied, setCopied] = useState(false);
  const [vote, setVote] = useState<"up" | "down" | null>(null);
  const [more, setMore] = useState(false);
  const [copyError, setCopyError] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();
  useEffect(() => () => clearTimeout(timer.current), []);
  const copy = async () => {
    try { await navigator.clipboard.writeText(m.text); setCopyError(false); setCopied(true); clearTimeout(timer.current); timer.current = setTimeout(() => setCopied(false), 1500); }
    catch { setCopyError(true); }
  };
  return <article className={`${s.turn} ${m.role === "user" ? s.userTurn : s.assistantTurn} ${m.enter ? s.enterTurn : ""}`} aria-label={`${m.role} message`}>
    <TaskImage m={m} />
    <TaskVideo m={m} />
    <div className={m.role === "user" ? s.userBubble : s.assistantText}>{m.role === "assistant" ? renderMarkdown(m.text) : m.text}</div>
    {m.role === "assistant" && !m.pending && <>
      <div className={s.msgActions}>
        <IconButton icon={copied ? Check : Copy} label={copied ? "Copied" : "Copy response"} onClick={() => void copy()} />
        <button className={s.actionBtn} title="Good response" aria-label="Good response" aria-pressed={vote === "up"} onClick={() => setVote(vote === "up" ? null : "up")}><ThumbsUp {...ICON} /></button>
        <button className={s.actionBtn} title="Bad response" aria-label="Bad response" aria-pressed={vote === "down"} onClick={() => setVote(vote === "down" ? null : "down")}><ThumbsDown {...ICON} /></button>
        <button className={s.actionBtn} title="Regenerate response" aria-label="Regenerate response" disabled={busy} onClick={regenerate}><RotateCcw {...ICON} /></button>
        <IconButton icon={MoreHorizontal} label="More response actions" onClick={() => setMore(!more)} />
        {m.status && <span className={s.statusLine}>{m.status}</span>}
      </div>
      {more && <div className={s.responseMore}><button className={s.mdLink} onClick={() => { void copy(); setMore(false); }}>Copy response</button></div>}
      {copyError && <span className={s.statusLine} role="status">Could not copy. Select the text to copy it.</span>}
    </>}
  </article>;
}

const VOICE_LINE: Partial<Record<VoiceStage, string>> = {
  listening: "Listening… tap the mic to send",
  thinking: "Thinking…",
  speaking: "Speaking… tap the mic to stop",
};

/** Composer mic: a tap starts voice mode right away (the browser asks for the microphone inside that tap). */
function MicButton() {
  const stage = useVoice((v) => v.stage);
  const onClick = () => {
    if (stage === "idle" || stage === "error") void voice.start();
    else if (stage === "listening") voice.stop();
    else voice.close();
  };
  const label = stage === "listening" ? "Stop and send" : stage === "thinking" || stage === "speaking" ? "Stop voice" : "Talk to Mirsal";
  return <button className={`${s.micBtn} ${stage === "listening" ? s.micLive : ""}`} aria-label={label} title={label}
    aria-pressed={stage !== "idle" && stage !== "error"} onClick={onClick}><Mic {...ICON} /></button>;
}

function VoiceStatus() {
  const { stage, error, transcript } = useVoice((v) => v);
  if (stage === "error") return <div className={`${s.voiceStatus} ${s.voiceError}`} role="alert">{error}</div>;
  const line = VOICE_LINE[stage];
  if (!line) return null;
  return <div className={s.voiceStatus} role="status">{stage === "thinking" && transcript ? `“${transcript}” · ${line}` : line}</div>;
}

function Main() {
  const taskId = useAi((st) => st.task);
  const task = useStore((st) => taskId ? st.tasks.find((t) => t.id === taskId && !t.dismissed) : undefined);
  return task ? <TaskView task={task} /> : <Conversation />;
}

function Conversation() {
  const selected = useAi((st) => st.selected);
  const messages = useAi((st) => st.threads[st.selected] ?? []);
  const busy = useAi((st) => st.thinking);
  const thinkingHere = useAi((st) => st.thinking && st.thinkingThread === st.selected);
  const [draft, setDraft] = useState("");
  const [notice, setNotice] = useState("");
  const [modelOpen, setModelOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const scroller = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  useEffect(() => { setDraft(""); setNotice(""); setMoreOpen(false); }, [selected]);
  useEffect(() => { scroller.current?.scrollTo({ top: scroller.current.scrollHeight }); }, [selected, messages.length, thinkingHere]);
  useLayoutEffect(() => {
    const el = textarea.current;
    if (el) { el.style.height = "auto"; el.style.height = `${Math.min(el.scrollHeight, 180)}px`; }
  }, [draft, messages.length]);
  const send = useCallback((text: string) => {
    if (!text.trim() || busy) return;
    setDraft(""); void sendUserMessage(text.trim());
  }, [busy]);
  const regenerate = (id: string) => { const text = ai.prepareRegeneration(id); if (text) void sendUserMessage(text); };
  const share = async () => {
    try { await navigator.clipboard.writeText(messages.map((m) => `${m.role === "user" ? "You" : "Mirsal AI"}: ${m.text}${m.imageUrl ? `\n${m.imageUrl}` : ""}`).join("\n\n")); setNotice("Conversation copied for sharing."); }
    catch { setNotice("Could not copy this conversation."); }
  };
  const composer = <div className={s.composerWrap}>
    <div className={s.composer}>
      <textarea ref={textarea} aria-label="Ask anything" placeholder="Ask anything" value={draft} rows={1} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => {
        if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(draft); }
      }} />
      <div className={s.composerTools}>
        <IconButton icon={Plus} label="Add" onClick={() => textarea.current?.focus()} />
        <IconButton icon={Globe} label="Search the web" onClick={() => { setDraft("Search the web for "); textarea.current?.focus(); }} />
        <IconButton icon={Paperclip} label="Attach file" onClick={() => setNotice("File attachments are not available in this demo.")} />
        <div className={s.spacer} />
        <MicButton />
        <button className={s.sendBtn} aria-label="Send message" disabled={!draft.trim() || busy} onClick={() => send(draft)}><ArrowUp {...ICON} /></button>
      </div>
    </div>
    <div className={s.disclaimer}>Mirsal AI can make mistakes. Check important info.</div>
    <VoiceStatus />
    {notice && <div className={s.notice} role="status">{notice}</div>}
  </div>;
  return <div className={s.main}>
    <header className={s.pageHeader}>
      <div className={s.headerControl}>
        <button className={s.modelButton} aria-expanded={modelOpen} onClick={() => setModelOpen(!modelOpen)}>Mirsal AI · GPT-5<ChevronDown {...ICON} /></button>
        {modelOpen && <div className={s.headerPopover}>GPT-5 · Mirsal’s AI assistant</div>}
      </div>
      <div className={s.spacer} />
      <IconButton icon={Share} label="Share conversation" onClick={() => void share()} />
      <div className={s.headerControl}><IconButton icon={MoreHorizontal} label="More conversation actions" onClick={() => setMoreOpen(!moreOpen)} />
        {moreOpen && <div className={`${s.headerPopover} ${s.headerPopoverRight}`}><button onClick={() => { ai.newChat(); setMoreOpen(false); }}>New chat</button><button onClick={() => { void share(); setMoreOpen(false); }}>Copy conversation</button></div>}
      </div>
    </header>
    {messages.length === 0 ? <div className={s.emptyState}>
      <h1 className={s.emptyGreeting}>What can I help with?</h1>
      {composer}
      <div className={s.chipGroup}>{suggestionChips.map((chip) => <button key={chip} className={s.suggestionChip} disabled={busy} onClick={() => send(chip)}>{chip}</button>)}</div>
    </div> : <>
      <div className={s.conversationScroll} ref={scroller}><div className={s.conversation}>
        {messages.map((m) => <AiTurn key={`${selected}-${m.id}`} m={m} busy={busy} regenerate={() => regenerate(m.id)} />)}
        {thinkingHere && <div className={s.thinkingLine} role="status"><Spinner />Thinking…</div>}
      </div></div>
      {composer}
    </>}
  </div>;
}
export const aiScreen = { Sidebar: AISidebar, Main };
