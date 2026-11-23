import { useEffect, useRef, useState } from 'react';
import { AlertCircle, ArrowRight, BookOpen, Check, ChevronRight, Clock, Download, FileText, Globe, Plus, RotateCcw, Send, Share2, Sparkles, Trash2, X } from 'lucide-react';
import { Button, Card, ICON, IconButton, ImageCard, SearchField, SidebarHeader, Spinner } from '../../ui';
import { actions } from '../../store';
import type { Report } from './data';
import { notify, research, useResearch } from './state';
import s from './research.module.css';

function elapsed(startedAt?: number) { const secs = Math.max(0, Math.floor((Date.now() - (startedAt ?? Date.now())) / 1000)); return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`; }
function useClock(active: boolean) { const [, tick] = useState(0); useEffect(() => { if (!active) return; const timer = setInterval(() => tick(n => n + 1), 1000); return () => clearInterval(timer); }, [active]); }
function ReportRow({ report, selected }: { report: Report; selected: boolean }) {
  return <button className={`${s.reportRow} ${selected ? s.selected : ''}`} onClick={() => research.select(report.id)} aria-label={`Open ${report.title}`}>
    <span className={`${s.documentIcon} ${report.status === 'failed' ? s.failedIcon : ''}`}>{report.status === 'running' ? <Spinner /> : report.status === 'failed' ? <AlertCircle {...ICON} /> : <FileText {...ICON} />}</span><span><strong>{report.title}</strong><small>{report.status === 'running' ? `Researching · ${elapsed(report.startedAt)}` : report.status === 'failed' ? 'Didn’t finish · open to try again' : `${report.findings.length} insights · ${report.time}`}{report.demo && <em className={s.demoTag}>Demo</em>}</small></span><ChevronRight {...ICON} />
  </button>;
}
function Sidebar() {
  const st = useResearch(); useClock(true);
  const filtered = st.reports.filter(r => `${r.title} ${r.category}`.toLowerCase().includes(st.query.toLowerCase()));
  return <>
    <SidebarHeader title="Research"><IconButton icon={Plus} label="Start new research" onClick={() => research.form(true)} /></SidebarHeader>
    <div className={s.newResearch}><Button variant="primary" icon={Plus} onClick={() => research.form(true)}>New research</Button></div>
    <SearchField placeholder="Search your reports…" value={st.query} onChange={research.query} />
    <div className={s.reportList}>{(['running', 'completed'] as const).map(status => { const group = filtered.filter(r => status === 'running' ? r.status === 'running' : r.status !== 'running'); return <section key={status}><div className={s.listHeading}><h2>{status === 'running' ? 'Running' : 'Completed'}</h2><span>{group.length}</span></div>{group.map(r => <ReportRow key={r.id} report={r} selected={r.id === st.selected} />)}{!group.length && <p className={s.emptyGroup}>{status === 'running' ? 'No matching research in progress.' : 'No matching completed reports.'}</p>}</section>; })}</div>
    <div className={s.sidebarNote}><Sparkles {...ICON} /><div><strong>Your knowledge, organized</strong><span>Clear findings. Useful next steps.</span></div></div>
  </>;
}
function NewResearch() {
  const [topic, setTopic] = useState('');
  return <form className={s.newForm} onSubmit={e => { e.preventDefault(); research.start(topic); }}>
    <div><span className={s.newIcon}><Sparkles {...ICON} /></span><div><h2>What would you like to explore?</h2><p>A focused question makes a useful report.</p></div><button type="button" className={s.closeForm} aria-label="Close new research" onClick={() => research.form(false)}><X {...ICON} /></button></div>
    <label htmlFor="research-topic">Research topic</label><input id="research-topic" autoFocus value={topic} onChange={e => setTopic(e.target.value)} placeholder="e.g. Arabic AI tools for a small support team" maxLength={160} required />
    <footer><span>Searches the web live · deep research takes about 30–60 seconds</span><button className={s.start} type="submit" disabled={!topic.trim()}><Sparkles {...ICON} />Start research</button></footer>
  </form>;
}
function Main() {
  const st = useResearch(); const report = st.reports.find(r => r.id === st.selected) ?? st.reports[0];
  useEffect(() => research.wakeSeeds(), []);
  useClock(report.status === 'running');
  const running = report.status === 'running';
  const workspace = useRef<HTMLDivElement>(null);
  useEffect(() => { workspace.current?.scrollTo({ top: 0 }); }, [st.selected, st.formOpen]);
  return <>
    <header className={s.header}><div className={s.headerTitle}><BookOpen {...ICON} /><div><strong>Research workspace</strong><span>{running ? 'In progress' : 'Your reports and insights'}</span></div></div><div className={s.headerActions}><Button icon={Share2} onClick={() => notify('Report link copied · demo')}>Share</Button><Button icon={Download} onClick={() => notify('PDF export prepared · demo')}>Export PDF</Button><Button variant="primary" icon={Send} onClick={() => running ? notify('This report is still running. Use in chat when it’s ready.') : actions.sendToChat({ kind: 'card', icon: 'research', title: report.title, subtitle: `${report.findings.length} key insights · ${report.category}`, taskId: report.id })}>Use in chat</Button></div></header>
    <div className={s.workspace} ref={workspace}>
      {st.formOpen && <NewResearch />}
      <article className={s.document}>
        <div className={s.documentMeta}><span>{report.category}{report.demo && <em className={s.demoTag}>Demo</em>}</span><span>{running ? <><Spinner />Researching · {elapsed(report.startedAt)}</> : report.status === 'failed' ? <><AlertCircle {...ICON} />Didn’t finish</> : <><Check {...ICON} />Research complete</>}</span></div>
        <div className={s.hero}><ImageCard src={report.image!} title={report.title} subtitle="Mirsal Research" ratio={3.6} onClick={() => notify('Report cover preview opened · demo')} /></div>
        <div className={s.documentHeading}><span className={s.eyebrow}>RESEARCH BRIEF</span><h1>{report.title}</h1><div><span><Clock {...ICON} />{report.date}</span><span>{report.reading}</span><span>{report.sourceCount} sources</span></div></div>
        {report.status === 'failed' ? <Card className={s.runningCard}><AlertCircle {...ICON} /><div><h2>This research didn’t finish</h2><p>{report.error}. Nothing was made up in its place.</p><div className={s.failedActions}><Button variant="primary" icon={RotateCcw} onClick={() => research.retry(report.id)}>Try again</Button><Button icon={Trash2} onClick={() => research.remove(report.id)}>Remove</Button></div></div></Card> : running ? <Card className={s.runningCard}><Spinner /><div><h2>Connecting the dots</h2><p>{report.summary}</p><small>Researching · {elapsed(report.startedAt)} · {report.id.startsWith('research-') ? 'Your report will be ready shortly.' : 'Demo research in progress.'}</small></div></Card> : <>
          <section className={s.summary}><h2>Executive summary</h2><p>{report.summary}</p></section>
          <section className={s.findings}><div className={s.sectionTitle}><h2>Key findings</h2><span>{report.findings.length} insights</span></div><ol>{report.findings.map((finding, i) => <li key={finding}><span>{i + 1}</span><p>{finding}</p></li>)}</ol></section>
          {!!report.ranking?.length && <section className={s.findings}><div className={s.sectionTitle}><h2>Ranking</h2><span>{report.ranking.length} picks</span></div><ol>{report.ranking.map((r, i) => <li key={r.name}><span>{i + 1}</span><p><strong>{r.name}</strong>{r.price && r.price !== '—' ? ` · ${r.price}` : ''} — {r.why}</p></li>)}</ol></section>}
          {report.sections?.map(sec => <section key={sec.heading} className={s.summary}><h2>{sec.heading}</h2><p>{sec.body}</p></section>)}
          <section className={s.numbers}><h2>By the numbers</h2><div>{report.stats.map(stat => <Card key={stat.label} className={s.stat}><strong>{stat.value}</strong><span>{stat.label}</span></Card>)}</div></section>
          <section className={s.sources}><div className={s.sectionTitle}><h2>Sources & further reading</h2><span>{report.sources?.length} references</span></div>{report.sources?.map(source => <button key={source.url ?? source.domain} onClick={() => source.url ? window.open(source.url, '_blank', 'noopener') : notify(`${source.title} · source preview opened`)}><span className={s.sourceInitial}>{source.domain[0].toUpperCase()}</span><span><strong>{source.title}</strong><small>{source.domain}</small></span><Globe {...ICON} /><ArrowRight {...ICON} /></button>)}</section>
          <div className={s.documentFooter}><span><Sparkles {...ICON} />{report.demo ? 'Demo report · not live research' : report.verified ? `Prepared by Mirsal · ${report.verified} claims checked against their sources` : 'Prepared by Mirsal · live web research'}</span>{report.id.startsWith('research-') && <button onClick={() => research.remove(report.id)}><Trash2 {...ICON} />Remove</button>}<button onClick={() => research.form(true)}>Explore another topic<ArrowRight {...ICON} /></button></div>
        </>}
      </article>
    </div>
    {st.toast && <div className={s.toast} role="status">{st.toast}</div>}
  </>;
}
export const researchScreen = { Sidebar, Main };
