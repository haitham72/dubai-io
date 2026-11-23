import { useEffect, useRef, useState } from 'react';
import { Archive, ArrowRight, Bell, CalendarPlus, ChevronLeft, ChevronRight, Download, FileText, FolderInput, Globe, Mail, MapPin, MoreHorizontal, Paperclip, Phone, Plane, Reply, ReplyAll, Send, Sparkles, SquarePen, Star, Tag, Trash2, UserRound, X } from 'lucide-react';
import { actions, useStore } from '../../store';
import { Avatar, Backdrop, Button, Card, ICON, IconButton, SearchField, SidebarHeader, Spinner } from '../../ui';
import { categories, folders, type Email } from './data';
import { mail, notify, selectedEmail, useMail, visibleEmails } from './state';
import s from './mail.module.css';

function SenderMark({ email, large = false }: { email: Email; large?: boolean }) {
  return email.face ? <Avatar src={email.face} size={large ? 44 : 40} /> : <span className={`${s.brand} ${s[email.tone]} ${large ? s.largeBrand : ''}`}>{email.initials}</span>;
}
function Sidebar() {
  const st = useMail(); const drafts = useStore(x => x.mailDrafts); const items = visibleEmails(st, drafts);
  const count = (f: typeof folders[number]) => f === 'Drafts' ? drafts.length : f === 'Inbox' ? st.emails.filter(e => !e.folder && e.unread).length : st.emails.filter(e => e.folder === f).length;
  return <>
    <SidebarHeader title="Mail"><IconButton icon={SquarePen} label="Compose email" onClick={() => mail.compose({ to: '', subject: '', body: '' })} /><IconButton icon={Star} label="Filter starred emails" onClick={mail.starredOnly} /></SidebarHeader>
    <SearchField placeholder="Search in mail…" value={st.query} onChange={mail.query} />
    <div className={s.folders} role="tablist" aria-label="Mail folders">{folders.map(f => <button key={f} role="tab" aria-selected={f === st.folder} className={f === st.folder ? s.activeFolder : ''} onClick={() => mail.folder(f)}>{f}{count(f) > 0 && <b>{count(f)}</b>}</button>)}</div>
    {st.folder === 'Inbox' && <div className={s.categories}>{categories.map(c => <button key={c} aria-pressed={c === st.category} className={c === st.category ? s.activeCategory : ''} onClick={() => mail.category(c)}>{c}</button>)}</div>}
    <div className={s.inboxMeta}><span>{st.starredOnly ? 'Starred messages' : st.folder}</span><span>{items.length} messages</span></div>
    <div className={s.list}>{items.map(e => <div key={e.id} className={`${s.emailRow} ${e.id === st.selected ? s.selected : ''}`}>
      <button className={s.selectEmail} onClick={() => mail.select(e.id)} aria-label={`Read ${e.subject}`}>
        <span className={`${s.unread} ${e.unread ? s.unreadVisible : ''}`} /><SenderMark email={e} />
        <span className={s.rowText}><strong>{e.draftId ? <><em className={s.draftTag}>Draft</em>{e.sender}</> : e.folder === 'Sent' ? `To: ${e.sender}` : e.sender}</strong><span className={e.unread ? s.unreadSubject : ''}>{e.subject}</span><small>{e.preview}</small></span>
        <span className={s.rowTime}>{e.time}</span>
      </button>
      <div className={s.rowTools}>{e.attachments.length > 0 && <Paperclip {...ICON} aria-label="Has attachments" />}<button onClick={() => mail.star(e.id)} aria-label={`${e.starred ? 'Unstar' : 'Star'} ${e.subject}`} aria-pressed={e.starred}><Star {...ICON} className={e.starred ? s.starred : ''} /></button></div>
    </div>)}{!items.length && <div className={s.empty}><Mail {...ICON} /><strong>{st.folder === 'Inbox' ? 'No messages found' : `Nothing in ${st.folder}`}</strong><span>{st.folder === 'Inbox' ? 'Try another category or search.' : st.folder === 'Drafts' ? 'Unsent emails you or Mirsal save appear here.' : 'Emails appear here as you use Mail.'}</span></div>}</div>
  </>;
}
function Compose({ initial }: { initial: { to: string; subject: string; body: string; draftId?: string } }) {
  const [to, setTo] = useState(initial.to); const [subject, setSubject] = useState(initial.subject); const [body, setBody] = useState(initial.body);
  return <Backdrop backdrop={s.composeBackdrop} onClose={() => mail.compose(null)}><form className={s.compose} role="dialog" aria-modal="true" aria-label="Compose email" onClick={e => e.stopPropagation()} onSubmit={e => { e.preventDefault(); void mail.send(to, subject, body, initial.draftId); mail.compose(null); }}>
    <header><strong>{initial.draftId ? 'Draft' : 'New message'}</strong><button type="button" className={s.composeIcon} aria-label="Close compose" onClick={() => mail.compose(null)}><X {...ICON} /></button></header>
    <label>To<input autoFocus type="email" required value={to} onChange={e => setTo(e.target.value)} placeholder="name@example.com" /></label>
    <label>Subject<input required value={subject} onChange={e => setSubject(e.target.value)} placeholder="Subject" /></label>
    <textarea required aria-label="Email message" value={body} onChange={e => setBody(e.target.value)} placeholder="Write your message…" />
    <footer><button className={s.send} type="submit"><Send {...ICON} />Send</button><button type="button" className={s.composeIcon} aria-label="Attach to email" onClick={() => notify('Attachment picker opened · demo')}><Paperclip {...ICON} /></button><button type="button" className={s.saveDraft} onClick={() => { mail.saveDraft({ to, subject, body, draftId: initial.draftId }); mail.compose(null); }}>Save draft</button><span>Demo inbox</span></footer>
  </form></Backdrop>;
}
function Main() {
  const st = useMail(); const drafts = useStore(x => x.mailDrafts);
  const items = visibleEmails(st, drafts); const e = selectedEmail(st, drafts);
  const composeReq = useStore(x => x.mailCompose);
  useEffect(() => { if (composeReq) { mail.compose(composeReq); actions.composeMail(null); } }, [composeReq]);
  const editDraft = (d: Email) => mail.compose({ to: d.address, subject: d.subject === '(no subject)' ? '' : d.subject, body: d.paragraphs.join('\n\n'), draftId: d.draftId });
  const summary = e && st.summaries[e.id];
  const reader = useRef<HTMLElement>(null);
  useEffect(() => { void mail.loadLive(); }, []);
  useEffect(() => { reader.current?.scrollTo({ top: 0 }); }, [st.selected]);
  const action = (text: string) => notify(text);
  const reply = (mode: 'Reply' | 'Reply all' | 'Forward') => { if (e) mail.compose({ to: mode === 'Forward' ? '' : e.address, subject: `${mode === 'Forward' ? 'Fwd' : 'Re'}: ${e.subject}`, body: mode === 'Forward' ? `Forwarded message from ${e.sender}:

${e.paragraphs.join('\n\n')}` : '' }); };
  const next = (direction: number) => { const index = items.findIndex(item => item.id === e?.id); const target = items[index + direction]; if (target) mail.select(target.id); else notify('You’re at the end of this inbox view'); };
  return <>
    <header className={s.toolbar}>
      <div className={s.actions}>
        <button disabled={!e} onClick={() => e && mail.remove(e.id, 'Archived')}><Archive {...ICON} />Archive</button>
        <button disabled={!e} onClick={() => e && mail.remove(e.id, 'Deleted')}><Trash2 {...ICON} />Delete</button>
        <button disabled={!e} onClick={() => action('Move to folder · demo chooser opened')}><FolderInput {...ICON} />Move</button>
        <button disabled={!e} onClick={() => action('Label added: Personal')}><Tag {...ICON} />Label</button>
        <button disabled={!e} onClick={() => action('Snoozed until tomorrow at 9 AM')}><Bell {...ICON} />Snooze</button>
        <IconButton icon={MoreHorizontal} label="More mail actions" onClick={() => action('More actions: mark unread, print, block sender · demo')} />
      </div>
      <div className={s.readerNavigation}><IconButton icon={ChevronLeft} label="Previous email" onClick={() => next(-1)} /><IconButton icon={ChevronRight} label="Next email" onClick={() => next(1)} /></div>
      <button className={s.summarize} disabled={!e || summary === 'working'} onClick={() => e && mail.summary(e.id)}>{summary === 'working' ? <Spinner /> : <Sparkles {...ICON} />}{summary === 'working' ? 'Summarizing…' : 'Summarize with Mirsal AI'}</button>
    </header>
    {e ? <div className={s.workspace}>
      <article className={s.reader} ref={reader}>
        <div className={s.senderHeader}><SenderMark email={e} large /><div><strong>{e.sender}</strong><span>&lt;{e.address}&gt;</span><small>to me · {e.date}</small></div><span className={s.sentTime}>{e.time}</span><span className={e.starred ? s.starred : undefined}><IconButton icon={Star} label="Toggle selected email star" onClick={() => mail.star(e.id)} /></span><IconButton icon={Reply} label="Reply to sender" onClick={() => reply('Reply')} /></div>
        <div className={s.subject}><h1>{e.subject}</h1><span>{st.folder}</span></div>
        {e.draftId && <div className={s.draftBar}><span>{e.draftBy === 'mirsal' ? 'Mirsal drafted this from your trip plan. ' : ''}Not sent — nothing leaves until you press Send.</span><Button variant="primary" icon={Send} onClick={() => editDraft(e)}>Review &amp; send</Button></div>}
        {e.flight ? <>
          <div className={s.flightHero}><img src={e.hero} alt="Aircraft above the clouds" /><div className={s.heroCopy}><span>Emirates · booking EK429H</span><h2>Your journey<br />is confirmed</h2></div></div>
          <div className={s.route}><div><strong>Dubai (DXB)</strong><span>Thu, 15 Oct 2026</span><b>10:30</b></div><div className={s.routeMiddle}><span>EK007 · 7h 25m</span><div /><Plane {...ICON} /><small>Non-stop</small></div><div><strong>London (LHR)</strong><span>Thu, 15 Oct 2026</span><b>14:55</b></div></div>
          <div className={s.bookingTiles}><div><UserRound {...ICON} /><span>Passenger<strong>Haitham · 1 adult</strong></span></div><div><Plane {...ICON} /><span>Class<strong>Economy</strong></span></div><div><FileText {...ICON} /><span>Booking reference<strong>EK429H</strong></span></div><button onClick={() => action('Booking details opened · demo')}>Manage booking<ArrowRight {...ICON} /></button></div>
        </> : e.hero && <img className={s.emailPhoto} src={e.hero} alt={e.subject} />}
        <div className={s.body}>{e.paragraphs.map((p, i) => <p key={i}>{p}</p>)}</div>
        {e.flight && <section className={s.itinerary}><div className={s.sectionHeading}><h2>Your itinerary</h2><button onClick={() => action('Full itinerary opened · demo')}>View full itinerary</button></div><Card className={s.itineraryCard}><span className={`${s.brand} ${s.red}`}>EK</span><div><strong>EK007 · Dubai → London</strong><span>Terminal 3 · Thu, 15 Oct 2026 · 10:30–14:55</span></div><div><strong>7h 25m</strong><span>Boeing 777-300ER · Economy</span></div></Card></section>}
        <div className={s.replyActions}><Button icon={Reply} onClick={() => reply('Reply')}>Reply</Button><Button icon={ReplyAll} onClick={() => reply('Reply all')}>Reply all</Button><Button icon={ArrowRight} onClick={() => reply('Forward')}>Forward</Button></div>
      </article>
      <aside className={s.context} aria-label="Email context">
        <Card className={s.contextCard}><div className={s.contextSender}><SenderMark email={e} /><strong>{e.sender}</strong><button aria-pressed={!!st.following[e.sender]} onClick={() => mail.follow(e.sender)}>{st.following[e.sender] ? 'Following' : '+ Follow'}</button></div><h2>About</h2><p>{e.flight ? 'Global airline based in Dubai' : `${e.sender} · ${e.category}`}</p><button className={s.contextLink} onClick={() => action(`${e.website} · website preview opened`)}><Globe {...ICON} />{e.website}</button><button className={s.contextLink} onClick={() => action(`Call ${e.phone} · demo`)}><Phone {...ICON} />{e.phone}</button><div className={s.contextLink}><MapPin {...ICON} />{e.location}</div></Card>
        <Card className={s.contextCard}><div className={s.sectionHeading}><h2>Attachments</h2><button onClick={() => action(e.attachments.length ? 'All attachments saved · demo' : 'This message has no attachments')}>Save all</button></div>{e.attachments.length ? e.attachments.map(a => <button key={a.name} className={s.attachment} onClick={() => action(`${a.name} · preview opened`)}><span className={s.pdf}><FileText {...ICON} /></span><span><strong>{a.name}</strong><small>{a.size} · PDF</small></span><Download {...ICON} /></button>) : <p>No attachments in this message.</p>}</Card>
        <Card className={`${s.contextCard} ${s.summaryCard}`}><h2><Sparkles {...ICON} />Mirsal AI</h2>{summary === 'ready' ? <p>{e.summary}</p> : summary === 'working' ? <p className={s.working}><Spinner />Summarizing this message…</p> : <><p>A quick overview, without leaving your inbox.</p><button className={s.contextLink} onClick={() => mail.summary(e.id)}>Summarize this email<ArrowRight {...ICON} /></button></>}</Card>
        <Card className={s.contextCard}><h2>Quick actions</h2>{(e.flight ? [[CalendarPlus, 'Add to Calendar'], [Plane, 'Track Flight'], [Globe, 'View Booking'], [MapPin, 'Find Hotels in London']] : [[CalendarPlus, 'Create a reminder'], [Mail, 'Contact sender'], [Archive, 'Save for later']]).map(([Icon, label]) => { const I = Icon as typeof Plane; return <button key={String(label)} className={s.quickAction} onClick={() => action(`${label} · demo action ready`)}><I {...ICON} />{String(label)}<ChevronRight {...ICON} /></button>; })}</Card>
      </aside>
    </div> : <div className={s.empty}><Mail {...ICON} /><h1>No message selected</h1><p>Choose another category or compose a message.</p><Button icon={SquarePen} onClick={() => mail.compose({ to: '', subject: '', body: '' })}>Compose email</Button></div>}
    {st.compose && <Compose key={`${st.compose.to}:${st.compose.subject}`} initial={st.compose} />}
    {st.toast && <div className={s.toast} role="status">{st.toast}</div>}
  </>;
}
export const mailScreen = { Sidebar, Main };
