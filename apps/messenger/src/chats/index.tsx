// Chats — the GOLDEN SCREEN (lead session). Geometry reference for every other screen.
import { useCallback, useEffect, useRef, useState } from "react";
import { Lightbox } from "../updates/details/ImageDetail";
import {
  CheckCheck, BellOff, ListFilter, MoreHorizontal, Mic, Paperclip, Phone, Play, Search, Send, Smile,
  SquarePen, Video, Plane, FileText, Mail, Sparkles, Reply, X,
} from "lucide-react";
import { actions, getState, useStore } from "../store";
import { Avatar, Badge, IconButton, ICON, ListRow, SearchField, SidebarHeader, Spinner } from "../ui";
import type { Message, MessengerTask } from "../types";
import { MessengerAiRow } from "../updates";
import { contacts } from "./data";
import { useChat, useChatList } from "./list";
import { MediaPanel } from "./MediaPanel";
import { MessengerMessage } from "./MessengerCards";
import { openResearchCard, ReportDoc } from "./ReportDoc";
import { plainText } from "./skills";
import { StickerMedia } from "./StickerMedia";
import { askMessenger, chatMentions, mentionAt, retryMessenger, useMessengerRequests, type Mention } from "./messenger";
import SaveToMemory from "./SaveToMemory";
import { scheduleContactReply, useContactTyping } from "./autoReply";
import s from "./chats.module.css";

function ChatsSidebar() {
  const activeId = useStore((st) => st.activeChatId);
  const [q, setQ] = useState("");
  const list = useChatList().filter((c) => c.contact.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <>
      <SidebarHeader title="Chats">
        <IconButton icon={SquarePen} label="New chat" />
        <IconButton icon={ListFilter} label="Filter" />
      </SidebarHeader>
      <SearchField placeholder="Search chats, tasks, files..." value={q} onChange={setQ} />
      {/* Messenger AI: agents, results and the assistant open in their own workspace. */}
      <MessengerAiRow />
      <div className={s.list}>
        {list.map((c) => (
          <ListRow
            key={c.id}
            selected={c.id === activeId}
            onClick={() => actions.openChat(c.id)}
            leading={<Avatar src={c.contact.avatar} size={48} online={c.contact.online} />}
            title={c.contact.name}
            subtitle={c.preview}
            trailing={<>
              <span>{c.time}</span>
              {c.unread > 0 ? <Badge>{c.unread}</Badge>
                : c.muted ? <BellOff size={14} /> : <CheckCheck size={14} color="var(--blue)" />}
            </>}
          />
        ))}
      </div>
    </>
  );
}

function mentionText(text: string, people: Mention[]) {
  const known = new Set(people.map(p => p.token.toLowerCase()));
  let offset = 0;
  return text.split(/(@[\p{L}\p{M}\d_-]+)/u).map((part, i) => {
    const start = offset; offset += part.length;
    return known.has(part.toLowerCase()) && (start === 0 || /\s|[([{]/.test(text[start - 1]))
      ? <strong key={i} className={s.mentionText}>{part}</strong> : part;
  });
}
function Bubble({ m, showAvatar, people, onMediaLoad, onReply, focusRequest }: { m: Message; showAvatar: boolean; people: Mention[]; onMediaLoad: () => void; onReply: (m: Message) => void; focusRequest?: number }) {
  const contact = useChat(m.chatId).contact;
  const memoryToken = useStore((st) => (st.mode === "real" && st.auth.status === "signed_in" ? st.auth.sessionToken : null));
  const b = m.body;
  const row = useRef<HTMLDivElement>(null);
  const [preview, setPreview] = useState(false);
  const [highlight, setHighlight] = useState(false);
  const closePreview = useCallback(() => setPreview(false), []);
  useEffect(() => {
    if (!focusRequest) return;
    const frame = requestAnimationFrame(() => {
      row.current?.scrollIntoView({ block: "center" });
      setHighlight(true);
      if (b.kind === "image") setPreview(true);
    });
    const timer = window.setTimeout(() => setHighlight(false), 2600);
    return () => { cancelAnimationFrame(frame); window.clearTimeout(timer); };
  }, [focusRequest]);
  const meta = <span className={s.time}>{m.time}{m.fromMe && <CheckCheck size={14} />}</span>;
  const [report, setReport] = useState<MessengerTask | null>(null);
  const quote = m.replyTo && m.by !== "messenger" && <span className={s.replyQuote}><strong>{m.replyTo.sender}</strong>{m.replyTo.text.slice(0, 120)}</span>;

  let content;
  if (b.kind === "ai" || b.kind === "choices" || b.kind === "plan") {
    content = <MessengerMessage m={m} />;
  } else if (b.kind === "sticker") {
    content = <div className={s.stickerMsg}><StickerMedia url={b.url} onLoad={onMediaLoad} />{meta}</div>;
  } else if (b.kind === "image") {
    content = (
      <div className={s.media}>
        <button className={s.imageOpen} aria-label="Open shared image" onClick={() => setPreview(true)}>
          <img src={b.url} alt={b.caption ?? "Shared image"} onLoad={onMediaLoad} />
        </button>
        {preview && <Lightbox url={b.url} title={b.caption ?? "Shared image"} onClose={closePreview} />}
        {b.caption && <div className={s.caption}>{b.caption}</div>}
        {meta}
      </div>
    );
  } else if (b.kind === "voice") {
    content = (
      <div className={`${s.bubble} ${s.voice}`}>
        <button className={s.play} aria-label="Play voice message"><Play size={14} fill="currentColor" /></button>
        <span className={s.wave}>{Array.from({ length: 34 }, (_, i) => <i key={i} style={{ height: 6 + ((i * 7) % 18) }} />)}</span>
        <span className={s.dur}>0:{String(b.seconds).padStart(2, "0")}</span>
        {meta}
      </div>
    );
  } else if (b.kind === "video") {
    content = (
      <div className={s.media}>
        <video src={b.url} controls playsInline preload="metadata" onLoadedMetadata={onMediaLoad} />
        {b.caption && <div className={s.caption}>{b.caption}</div>}
      </div>
    );
  } else if (b.kind === "card") {
    const I = b.icon === "flight" ? Plane : b.icon === "mail" ? Mail : FileText;
    content = (
      <div className={`${s.bubble} ${s.cardMsg}`}>
        {b.icon === "flight" && <button className={s.flightCardLink} aria-label={`View flights: ${b.title}`} onClick={() => actions.navigate("flights")} />}
        {b.icon === "research" && <button className={s.flightCardLink} aria-label={`Open report: ${b.title}`} onClick={() => openResearchCard(b, setReport)} />}
        {report && <ReportDoc task={report} onClose={() => setReport(null)} />}
        <span className={s.cardIcon}><I {...ICON} /></span>
        <span><strong>{b.title}</strong><br /><span className={s.cardSub}>{b.subtitle}</span></span>
        {meta}
      </div>
    );
  } else {
    content = <div className={s.bubble}>{quote}<span>{mentionText(b.text, people)}</span>{meta}</div>;
  }
  if (m.by === "messenger" && b.kind !== "ai" && b.kind !== "choices" && b.kind !== "plan") content = <MessengerMessage m={m}>{content}</MessengerMessage>;

  // Long-press to reply on touch screens (the hover button is for mouse users).
  const press = useRef(0);
  const touchReply = m.by === "messenger" ? {} : {
    onPointerDown: (e: React.PointerEvent) => { if (e.pointerType !== "mouse") press.current = window.setTimeout(() => onReply(m), 450); },
    onPointerUp: () => window.clearTimeout(press.current),
    onPointerMove: () => window.clearTimeout(press.current),
    onPointerCancel: () => window.clearTimeout(press.current),
  };

  return (
    <div ref={row} className={`${s.msgRow} ${m.fromMe ? s.out : s.in} ${b.kind === "plan" ? s.planRow : ""} ${highlight ? s.messageFocus : ""}`} {...touchReply}>
      {!m.fromMe && <span className={s.avatarCol}>{m.by === "messenger"
        ? <span className={s.messengerTile} aria-label="Messenger"><Sparkles {...ICON} /></span>
        : showAvatar && contact && <Avatar src={contact.avatar} size={32} />}</span>}
      {content}
      {memoryToken && b.kind === "text" && m.by !== "messenger" && <SaveToMemory sessionToken={memoryToken} conversationId={m.chatId} messageId={m.id} />}
      {m.by !== "messenger" && <button className={s.replyBtn} aria-label="Reply" title="Reply" onClick={() => onReply(m)}><Reply size={16} /></button>}
    </div>
  );
}

function Conversation() {
  const activeId = useStore((st) => st.activeChatId);
  const messageFocus = useStore(st => st.messageFocus);
  const messages = useStore((st) => st.messages).filter((m) => m.chatId === activeId);
  const chat = useChat(activeId);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState<Message | null>(null);
  const [caret, setCaret] = useState(0);
  const [mentionIndex, setMentionIndex] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const typingSender = useContactTyping(activeId);
  const isTyping = typingSender !== undefined;
  const typingLabel = typingSender ? `${typingSender} is typing…` : "typing…";
  const requests = useMessengerRequests().filter(r => r.chatId === activeId);
  const people = chatMentions(activeId, messages);
  const mention = dismissed ? null : mentionAt(draft, caret);
  const choices = mention ? people.filter(p => `${p.name} ${p.token}`.toLowerCase().includes(mention.query.toLowerCase())) : [];
  const selectedMention = Math.min(mentionIndex, Math.max(0, choices.length - 1));
  // "@messenger …" anywhere in the message (start, middle, or on a reply).
  const isMessenger = /(?:^|\s)@messenger(?:\b|$)/i.test(draft);
  const requestText = draft.replace(/(?:^|\s)@messenger\b[,:]?/i, ' ').replace(/\s+/g, ' ').trim();
  const scroller = useRef<HTMLDivElement>(null);
  const followLatest = useRef(true);
  const onMediaLoad = () => {
    if (followLatest.current) requestAnimationFrame(() => {
      scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
    });
  };

  useEffect(() => {
    followLatest.current = true;
    scroller.current?.scrollTo({ top: scroller.current.scrollHeight });
  }, [activeId, messages.length, isTyping, requests.map(r => `${r.id}:${r.status}`).join(',')]);
  useEffect(() => { if (messageFocus) followLatest.current = false; }, [messageFocus]);
  useEffect(() => { setDraft(""); setCaret(0); setDismissed(false); setMentionIndex(0); setReplyTo(null); }, [activeId]);
  const [media, setMedia] = useState(false);
  useEffect(() => setMedia(false), [activeId]);
  /** An emoji goes in at the caret; stickers and GIFs send at once (like Telegram). */
  const insertEmoji = (emoji: string) => {
    const at = Math.min(caret, draft.length);
    setDraft(draft.slice(0, at) + emoji + draft.slice(at)); setCaret(at + emoji.length);
    requestAnimationFrame(() => { input.current?.focus(); input.current?.setSelectionRange(at + emoji.length, at + emoji.length); });
  };
  const startReply = (m: Message) => { setReplyTo(m); requestAnimationFrame(() => input.current?.focus()); };
  const quoteOf = (m: Message) => ({ id: m.id, sender: m.fromMe ? "You" : chat.contact.name, text: plainText(m) });

  const insertMention = (person: Mention) => {
    if (!mention) return;
    const trailing = draft.slice(mention.end).match(/^[\p{L}\p{M}\d_-]*/u)?.[0].length ?? 0;
    const prefix = draft.slice(0, mention.start) + person.token + ' ';
    setDraft(prefix + draft.slice(mention.end + trailing)); setCaret(prefix.length); setDismissed(true);
    requestAnimationFrame(() => { input.current?.focus(); input.current?.setSelectionRange(prefix.length, prefix.length); });
  };

  const send = () => {
    if (!draft.trim() || (isMessenger && !requestText)) return;
    const text = draft.trim();
    const quoted = replyTo ? quoteOf(replyTo) : undefined;
    const id = actions.sendToChat({ kind: "text", text }, activeId, quoted);
    if (isMessenger) askMessenger(activeId, requestText, id, quoted);
    else if (getState().mode === "demo") scheduleContactReply(activeId, chat.contact.name, text);
    setDraft(""); setCaret(0); setDismissed(true); setReplyTo(null);
  };

  return (
    <>
      <header className={s.header}>
        <Avatar src={chat.contact.avatar} size={44} online={chat.contact.online} />
        <div>
          <div className={s.name}>{chat.contact.name}</div>
          <div className={s.status}>{isTyping ? typingLabel : chat.contact.online ? "Online" : "Last seen recently"}</div>
        </div>
        <div className={s.headerActions}>
          <IconButton icon={Phone} label="Voice call" />
          <IconButton icon={Video} label="Video call" />
          <IconButton icon={Search} label="Search in chat" />
          <IconButton icon={MoreHorizontal} label="More" />
        </div>
      </header>
      <div className={s.messages} ref={scroller} onScroll={e => {
        const el = e.currentTarget;
        if (el.scrollHeight - el.clientHeight - el.scrollTop < 96) followLatest.current = true;
      }} onWheel={e => { if (e.deltaY < 0) followLatest.current = false; }}
        onTouchMove={() => { followLatest.current = false; }}
        onPointerDown={e => { if (e.target === e.currentTarget) followLatest.current = false; }}>
        {messages.map((m, i) => (
          <Bubble key={m.id} m={m} people={people} onMediaLoad={onMediaLoad} onReply={startReply} focusRequest={messageFocus?.id === m.id ? messageFocus.request : undefined} showAvatar={!m.fromMe && messages[i + 1]?.fromMe !== false} />
        ))}
        {requests.map(r => <div key={`${r.chatId}-${r.taskId ?? r.id}`} className={s.messengerLine} role="status">
          <Sparkles {...ICON} /><span>{r.label}</span>
          {r.status === 'failed' ? <><span>·</span><button onClick={() => void retryMessenger(r.id)}>Retry</button></> : r.status !== 'ready' && <Spinner />}
        </div>)}
        {isTyping && <div className={`${s.msgRow} ${s.in}`} role="status" aria-label={typingLabel}>
          <span className={s.avatarCol}><Avatar src={chat.contact.avatar} size={32} /></span>
          <div className={`${s.bubble} ${s.typingBubble}`} aria-hidden="true"><i /><i /><i /></div>
        </div>}
      </div>
      <footer className={`${s.composer} ${isMessenger ? s.messengerComposer : ''}`}>
        {replyTo && <div className={s.replyBar}>
          <Reply size={16} /><span><strong>Replying to {replyTo.fromMe ? "yourself" : chat.contact.name}</strong>{plainText(replyTo).slice(0, 120)}</span>
          <button aria-label="Cancel reply" onClick={() => setReplyTo(null)}><X size={16} /></button>
        </div>}
        {mention && <div id={`mentions-${activeId}`} className={s.mentionPopover} role="listbox" aria-label="Mention a person or Messenger">
          <div className={s.mentionHeading}>Mention in this chat</div>
          {choices.length ? choices.map((person, i) => <button key={person.token} id={`mention-${activeId}-${i}`} role="option" aria-selected={i === selectedMention} className={`${s.mentionOption} ${i === selectedMention ? s.mentionSelected : ''}`} onMouseDown={e => e.preventDefault()} onClick={() => insertMention(person)}>
            {person.face ? <Avatar src={person.face} size={32} /> : <span className={s.messengerTile}><Sparkles {...ICON} /></span>}
            <span><strong>{person.name}</strong><small>{person.token}</small></span>
          </button>) : <div className={s.mentionEmpty}>No matching people.</div>}
        </div>}
        <IconButton icon={Paperclip} label="Attach" />
        <input ref={input} className={s.input} placeholder={isMessenger ? "Ask Messenger: is this true · create sticker of this · create image about this · setup plan for this…" : replyTo ? "Reply… (add @messenger is this true to fact-check it)" : "Type a message..."} value={draft}
          aria-label="Message" role="combobox" aria-autocomplete="list" aria-expanded={!!mention} aria-controls={mention ? `mentions-${activeId}` : undefined} aria-activedescendant={mention && choices.length ? `mention-${activeId}-${selectedMention}` : undefined}
          onChange={e => { setDraft(e.target.value); setCaret(e.target.selectionStart ?? e.target.value.length); setDismissed(false); setMentionIndex(0); }}
          onSelect={e => setCaret(e.currentTarget.selectionStart ?? draft.length)} onBlur={() => setDismissed(true)}
          onKeyDown={e => {
            if (e.nativeEvent.isComposing) return;
            if (mention && e.key === "Escape") { e.preventDefault(); e.stopPropagation(); setDismissed(true); return; }
            if (mention && choices.length && (e.key === "ArrowUp" || e.key === "ArrowDown")) { e.preventDefault(); setMentionIndex(i => (i + (e.key === "ArrowDown" ? 1 : -1) + choices.length) % choices.length); return; }
            if (mention && choices.length && (e.key === "Enter" || e.key === "Tab")) { e.preventDefault(); insertMention(choices[selectedMention]); return; }
            if (e.key === "Enter") { e.preventDefault(); send(); }
          }} />
        <span data-media-toggle className={media ? s.mediaOn : undefined}><IconButton icon={Smile} label="Emoji, stickers and GIFs" onClick={() => setMedia(v => !v)} /></span>
        {media && <MediaPanel chatId={activeId} onClose={() => setMedia(false)} onEmoji={insertEmoji}
          onSticker={(url, pack) => actions.sendToChat({ kind: "sticker", url, pack }, activeId)}
          onGif={g => { actions.sendToChat({ kind: "image", url: g.url }, activeId); setMedia(false); }} />}
        <IconButton icon={Mic} label="Voice message" />
        <button className={s.send} aria-label="Send" disabled={!draft.trim() || (isMessenger && !requestText)} onClick={send}><Send {...ICON} size={18} /></button>
      </footer>
    </>
  );
}

export const chatsScreen = { Sidebar: ChatsSidebar, Main: Conversation };
