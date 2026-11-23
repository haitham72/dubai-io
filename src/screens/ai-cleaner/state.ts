import { createStore } from '../../storeFactory';
import { actions, getState } from '../../store';
import { CLEAN_MODE_LABEL, FALLBACK_STAGES, cleanFileUrl, getCleanerCapabilities, runCleanJob, verifyCleanImage, visibleStages, type CleanJob, type CleanMode, type OpenAiVerify } from '../../api';

// Canonical stage checklist. The API owns the strings; this only orders them for display.
// Anything unrecognized renders as its own trailing row, verbatim.
export const CLEAN_MODES: { value: CleanMode; label: string }[] = [
  { value: 'resize', label: 'Resize' },
  { value: 'sdxl', label: 'SDXL' },
  { value: 'resize_then_sdxl', label: 'Resize + SDXL' },
];







export interface ChatImage { id: string; url: string }

interface State {
  fileName: string; previewUrl: string; mode: CleanMode;
  job: CleanJob | null; status: 'idle' | 'running' | 'done' | 'failed';
  error: string; demo: boolean; chatImages: ChatImage[]; toast: string;
  verifyAvailable: boolean; verify: OpenAiVerify | null; verifying: boolean; verifyError: string;
}
let pendingFile: File | null = null;

let demoTimers: ReturnType<typeof setTimeout>[] = [];
const cleanerStore = createStore<State>({
  fileName: '', previewUrl: '', mode: 'resize_then_sdxl',
  job: null, status: 'idle', error: '', demo: false, chatImages: [], toast: '',
  verifyAvailable: false, verify: null, verifying: false, verifyError: '',
});
const getCleaner = cleanerStore.get;
const set = cleanerStore.set;


export function useCleaner() { return cleanerStore.useState(); }
let toastTimer: ReturnType<typeof setTimeout>;
export function notify(toast: string) { clearTimeout(toastTimer); set({ toast }); toastTimer = setTimeout(() => set({ toast: '' }), 3500); }
function stopTimers() { demoTimers.forEach(clearTimeout); demoTimers = []; }

const taskTitle = (mode: CleanMode) => `Cleaning AI traces (${CLEAN_MODE_LABEL[mode]})`;

export const cleaner = {
  setMode: (mode: CleanMode) => { if (getCleaner().status !== 'running') set({ mode }); },
  setFile(file: File) {
    if (!/\.(jpe?g|png|webp)$/i.test(file.name)) { notify('Use a JPEG, PNG or WebP image.'); return; }
    if (file.size > 50 * 1024 * 1024) { notify('That image is over the 50 MB limit.'); return; }
    if (getCleaner().previewUrl.startsWith('blob:')) URL.revokeObjectURL(getCleaner().previewUrl);
    pendingFile = file;
    set({ fileName: file.name, previewUrl: URL.createObjectURL(file), job: null, status: 'idle', error: '', demo: false, verify: null, verifyError: '' });
  },
  loadChatImages() {
    try {
      const st = getState();
      const imgs = st.messages.filter(m => m.body.kind === 'image').slice(-8).reverse()
        .map(m => ({ id: m.id, url: (m.body as { url: string }).url }));
      set({ chatImages: imgs });
    } catch { /* store unreadable */ }
  },
  async useChatImage(url: string) {
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const ext = (blob.type.split('/')[1] || 'jpg').replace('jpeg', 'jpg');
      cleaner.setFile(new File([blob], `chat-image.${ext}`, { type: blob.type || 'image/jpeg' }));
    } catch { notify('Couldn’t fetch that image — download it and upload instead.'); }
  },
  reset() { stopTimers(); pendingFile = null; set({ fileName: '', previewUrl: '', job: null, status: 'idle', error: '', demo: false, verify: null, verifyError: '' }); },
  async loadCapabilities() {
    try {
      const caps = await getCleanerCapabilities();
      if (caps) set({ verifyAvailable: caps.verify_openai });
    } catch { /* service off: no verify button */ }
  },
  /** Opt-in per tap: sends the cleaned result (or the original in demo) to OpenAI. */
  async verify() {
    if (getCleaner().verifying || getCleaner().status !== 'done') return;
    set({ verifying: true, verifyError: '', verify: null });
    try {
      const url = resultUrl();
      const res = await fetch(url);
      if (!res.ok) throw new Error('fetch');
      const blob = await res.blob();
      const out = await verifyCleanImage(new File([blob], 'verify.jpg', { type: blob.type || 'image/jpeg' }));
      set({ verify: out });
    } catch {
      set({ verifyError: 'Verification didn’t go through — try again.' });
    } finally {
      set({ verifying: false });
    }
  },
  retry() { cleaner.start(); },
  start() {
    if (!pendingFile || getCleaner().status === 'running') return;
    stopTimers();
    const file = pendingFile, mode = getCleaner().mode;
    const taskId = actions.addTask({ type: 'image', title: taskTitle(mode), subtitle: file.name, status: 'running' });
    set({ status: 'running', error: '', demo: false, job: null });
    runCleanJob(file, mode, { onStage: (job) => set({ job }) }).then(({ jobId: job_id, job }) => {
      stopTimers();
      if (job.error) {
        set({ status: 'failed', error: job.error });
        actions.updateTask(taskId, { title: 'Cleaning didn’t finish', subtitle: file.name, status: 'failed', error: job.error });
      } else {
        set({ status: 'done' });
        actions.updateTask(taskId, {
          title: 'Image cleaned', subtitle: `${file.name} · ${CLEAN_MODE_LABEL[mode]}`, status: 'completed',
          completedAt: Date.now(), unread: true, result: { type: 'image', imageUrl: cleanFileUrl(job_id), prompt: file.name },
        });
      }
    }).catch(() => {
      // Agents service not running: clearly labelled demo run, original shown as the result.
      set({ demo: true });
      const stages = visibleStages(FALLBACK_STAGES, '');
      stages.forEach((stage, i) => {
        demoTimers.push(setTimeout(() => {
          set({ job: { id: 'demo', mode, stage, note: stage, done: false } });
          if (i === stages.length - 1) {
            demoTimers.push(setTimeout(() => {
              set({ job: { id: 'demo', mode, stage, note: stage, done: true, result: true }, status: 'done' });
              actions.updateTask(taskId, { title: 'Image cleaned', subtitle: `${file.name} · demo`, status: 'completed', completedAt: Date.now(), unread: true, result: { type: 'image', imageUrl: getCleaner().previewUrl, prompt: file.name } });
            }, 900));
          }
        }, 900 * (i + 1)));
      });
    });
  },
  share() {
    const cur = getCleaner();
    const url = cur.demo || !cur.job || cur.job.id === 'demo' ? cur.previewUrl : cleanFileUrl(cur.job.id);
    if (!url) return;
    actions.sendToChat({ kind: 'image', url, caption: `Cleaned · ${CLEAN_MODE_LABEL[getCleaner().mode]}${getCleaner().demo ? ' · demo' : ''}` });
    notify('Sent to the open chat.');
  },
};

export function resultUrl(): string {
  if (getCleaner().status !== 'done') return '';
  const cur = getCleaner();
  return cur.demo || !cur.job || cur.job.id === 'demo' ? cur.previewUrl : cleanFileUrl(cur.job.id);
}
