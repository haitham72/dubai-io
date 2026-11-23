import { createStore } from '../../storeFactory';
import { actions } from '../../store';
import { getWatchlist, runResearch, type DeepBrief, type ResearchResult } from '../../api';
import { reports, makeReport, seedResults, watchCovers, type Report } from './data';

// The list = your own research (kept in this browser), the weekly watch briefs (agents service) and the hand-written
// demo reports, each labelled. New research runs live (deep research on the agents service, else the server route);
// if it can't finish it says so and offers Try again — it never shows canned findings under your topic.
const SAVED = 'mirsal.research';
const KEEP = 20;

function loadSaved(): Report[] {
  try { return (JSON.parse(localStorage.getItem(SAVED) ?? '[]') as Report[]).filter(r => r.status === 'completed'); } catch { return []; }
}
function save() {
  const mine = getResearch().reports.filter(r => r.id.startsWith('research-') && r.status === 'completed').slice(0, KEEP);
  try { localStorage.setItem(SAVED, JSON.stringify(mine)); } catch { /* storage unavailable */ }
}

interface State { reports: Report[]; selected: string; query: string; formOpen: boolean; toast: string }
const initial = [...loadSaved(), ...reports];
const researchStore = createStore<State>({ reports: initial, selected: initial[0].id, query: '', formOpen: false, toast: '' });
const getResearch = researchStore.get;
const set = researchStore.set;


export function useResearch() { return researchStore.useState(); }
let toastTimer: ReturnType<typeof setTimeout>;
let seedsWoken = false;
const longDate = (d: Date) => d.toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });

/** A weekly watch brief (agents service) as a report in the list. */
function watchReport(id: string, title: string, b: DeepBrief): Report {
  return {
    ...makeReport(`watch-${id}`, title), title, summary: b.summary, findings: b.findings, status: 'completed', demo: b.mode !== 'live',
    sources: b.sources, sourceCount: b.sources.length, sections: b.sections, ranking: b.ranking, verified: `${b.stats.verified}/${b.stats.claims}`,
    category: 'Weekly watch', image: watchCovers[id] ?? makeReport(id, title).image,
    time: new Date(b.createdAt * 1000).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }), date: longDate(new Date(b.createdAt * 1000)),
    stats: [{ value: String(b.stats.searched), label: 'sources searched' }, { value: String(b.stats.read), label: 'pages read' }, { value: `${b.stats.verified}/${b.stats.claims}`, label: 'claims verified' }],
  };
}

/** A finished live (or offline-demo) result as a report. */
function resultReport(base: Report, r: ResearchResult): Report {
  return {
    ...base, title: r.title, summary: r.summary, findings: r.findings, sources: r.sources, sourceCount: r.sources?.length ?? 0,
    sections: r.sections, ranking: r.ranking, verified: r.verified, status: 'completed', startedAt: undefined, demo: r.mode !== 'live',
    time: r.time, date: longDate(new Date()), category: 'Your research',
    stats: [{ value: String(r.findings.length), label: 'key findings' }, { value: String(r.sources?.length ?? 0), label: 'sources reviewed' },
      r.verified ? { value: r.verified, label: 'claims verified' } : { value: r.status?.split('·').pop()?.trim() ?? '—', label: 'research time' }],
  };
}

export function notify(toast: string) { clearTimeout(toastTimer); set({ toast }); toastTimer = setTimeout(() => set({ toast: '' }), 3500); }
export const research = {
  /** Demo seeds start "running" and finish 2–5 s after Research is first shown. Weekly watch briefs load alongside. */
  wakeSeeds() {
    if (seedsWoken) return; seedsWoken = true;
    getWatchlist().then(list => {
      const watch = list.filter(w => w.brief).map(w => watchReport(w.id, w.title, w.brief!));
      if (watch.length) set({ reports: [...getResearch().reports.filter(r => r.id.startsWith('research-')), ...watch, ...getResearch().reports.filter(r => !r.id.startsWith('watch-') && !r.id.startsWith('research-'))] });
    }).catch(() => { /* agents service not running: demo reports only */ });
    for (const [id, result] of Object.entries(seedResults)) {
      const now = Date.now();
      set({ reports: getResearch().reports.map(r => r.id === id && r.status === 'running' ? { ...r, startedAt: now - 3000 } : r) });
      setTimeout(() => set({
        reports: getResearch().reports.map(r => r.id === id ? { ...r, ...result, status: 'completed', startedAt: undefined } : r),
      }), 2000 + Math.random() * 3000);
    }
  },
  select: (selected: string) => set({ selected }), query: (query: string) => set({ query }),
  form: (formOpen: boolean) => set({ formOpen }),
  start(topic: string) {
    const title = topic.trim(); if (!title) return;
    const id = `research-${Math.random().toString(36).slice(2, 10)}`;
    const report = makeReport(id, title);
    set({ reports: [{ ...report, status: 'running', startedAt: Date.now() }, ...getResearch().reports], selected: id, formOpen: false, query: '' });
    const taskId = actions.addTask({ id, type: 'research', title: 'Research running', subtitle: title, status: 'running' });
    runResearch(title)
      .then(result => {
        const done = resultReport(report, result);
        set({ reports: getResearch().reports.map(r => r.id === id ? done : r) });
        save();
        actions.updateTask(taskId, { title: 'Research ready', subtitle: `${done.findings.length} key insights · ${done.title}`, status: 'completed', completedAt: Date.now(), unread: true, result: { type: 'research', items: [done] } });
      })
      .catch((err: unknown) => {
        const error = err instanceof Error && err.message ? err.message : 'The search or the model did not answer';
        set({ reports: getResearch().reports.map(r => r.id === id ? { ...r, status: 'failed', startedAt: undefined, error, findings: [], sources: [], sourceCount: 0 } : r) });
        actions.updateTask(taskId, { title: 'Research didn’t finish', subtitle: title, status: 'failed', error });
      });
  },
  /** Run a failed topic again (replaces the failed entry). */
  retry(id: string) {
    const failed = getResearch().reports.find(r => r.id === id);
    if (!failed) return;
    set({ reports: getResearch().reports.filter(r => r.id !== id) });
    research.start(failed.title);
  },
  /** Remove one of your own reports from this browser. */
  remove(id: string) {
    const rest = getResearch().reports.filter(r => r.id !== id);
    set({ reports: rest, selected: getResearch().selected === id ? rest[0].id : getResearch().selected });
    save();
  },
};
