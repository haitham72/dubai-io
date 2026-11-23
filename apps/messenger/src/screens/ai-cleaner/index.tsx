import { useEffect, useRef, useState } from 'react';
import { AlertCircle, Check, Download, Eraser, ImagePlus, RotateCcw, Send, Share2, ShieldCheck } from 'lucide-react';
import { Badge, Button, Card, ICON, PageHeader, Segmented, Spinner } from '../../ui';
import { cleaner, resultUrl, useCleaner, CLEAN_MODES } from './state';
import { FALLBACK_STAGES, visibleStages } from '../../api';
import s from './ai-cleaner.module.css';

function Stages({ stages, stage, note, done }: { stages: string[]; stage: string; note: string; done: boolean }) {
  const rows = visibleStages(stages, stage || 'Checking image');
  const currentIdx = done ? rows.length : Math.max(0, rows.indexOf(stage));
  return <ol className={s.stages}>
    {rows.map((row, i) => (
      <li key={row} className={i < currentIdx || done ? s.stageDone : i === currentIdx ? s.stageActive : s.stagePending}>
        <span className={s.stageDot}>{i < currentIdx || done ? <Check size={12} strokeWidth={2.5} /> : i === currentIdx ? <Spinner /> : null}</span>
        <span><strong>{row}</strong>{i === currentIdx && !done && note !== row && <small>{note}</small>}</span>
      </li>
    ))}
  </ol>;
}

function Compare({ before, after }: { before: string; after: string }) {
  const [pos, setPos] = useState(50);
  return <div>
    <div className={s.compare}>
      <img src={after} alt="Cleaned result" draggable={false} />
      <div className={s.compareBefore} style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}>
        <img src={before} alt="Original" draggable={false} />
      </div>
      <div className={s.compareHandle} style={{ left: `${pos}%` }} aria-hidden />
      <span className={`${s.compareTag} ${s.tagBefore}`}>Before</span>
      <span className={`${s.compareTag} ${s.tagAfter}`}>After</span>
    </div>
    <input className={s.compareRange} type="range" min={0} max={100} value={pos} aria-label="Before-after position"
      onChange={e => setPos(Number(e.target.value))} />
  </div>;
}

function Main() {
  const st = useCleaner();
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  useEffect(() => { cleaner.loadChatImages(); cleaner.loadCapabilities(); }, []);
  const running = st.status === 'running';
  const out = resultUrl();
  const quality = st.job?.quality;
  const pick = (f: File | undefined) => { if (f) cleaner.setFile(f); };
  return <>
    <PageHeader title="Clean AI Detection" subtitle="Remove AI fingerprints from an image" />
    <div className={s.workspace}>
      <Card className={s.card}>
        <div className={s.uploadRow}>
          <div className={`${s.dropzone} ${drag ? s.dragging : ''}`}
            onDragOver={e => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={e => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]); }}>
            {st.previewUrl
              ? <img src={st.previewUrl} alt="Original to clean" />
              : <div className={s.dropHint}><ImagePlus {...ICON} /><div><strong>Drop an image here</strong><span>or choose a file · JPEG, PNG, WebP · up to 50 MB</span></div></div>}
            <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden
              onChange={e => { pick(e.target.files?.[0]); e.target.value = ''; }} />
          </div>
          <div className={s.controls}>
            <div className={s.controlRow}>
              <Button icon={ImagePlus} onClick={() => inputRef.current?.click()}>Choose image</Button>
              {st.fileName && <span className={s.fileName}>{st.fileName}</span>}
            </div>
            <Segmented options={CLEAN_MODES} value={st.mode} onChange={cleaner.setMode} />
            <Button variant="primary" icon={Eraser} style={!st.previewUrl || running ? { opacity: 0.5 } : undefined} onClick={() => { if (st.previewUrl && !running) cleaner.start(); }}>
              {running ? 'Cleaning…' : 'Clean image'}
            </Button>
            {st.demo && <Badge tone="muted">Demo</Badge>}
          </div>
        </div>
        {!!st.chatImages.length && !running && <div className={s.chatStrip}>
          <span>From chats</span>
          {st.chatImages.map(c => (
            <button key={c.id} onClick={() => cleaner.useChatImage(c.url)} aria-label="Use image from chat">
              <img src={c.url} alt="" loading="lazy" />
            </button>
          ))}
        </div>}
      </Card>

      {(running || st.job) && <Card className={s.card}>
        <Stages stages={st.job?.stages ?? FALLBACK_STAGES} stage={st.job?.stage ?? 'Checking image'} note={st.job?.note ?? ''} done={st.status === 'done'} />
      </Card>}

      {st.status === 'failed' && <Card className={s.card}><div className={s.error}>
        <AlertCircle {...ICON} /><div><h2>This image didn’t finish</h2><p>{st.error}. Nothing was made up in its place.</p>
          <div className={s.errorActions}><Button variant="primary" icon={RotateCcw} onClick={() => cleaner.retry()}>Try again</Button>
            <Button icon={ImagePlus} onClick={() => cleaner.reset()}>New image</Button></div></div>
      </div></Card>}

      {st.status === 'done' && out && <Card className={s.card}>
        <div className={s.resultHead}><h2>Result {st.demo && <Badge tone="muted">Demo</Badge>}</h2>
          <div className={s.resultActions}>
            <a className={s.download} href={out} download={st.demo ? st.fileName : undefined}><Download size={16} strokeWidth={2} />Download</a>
            <Button icon={Send} onClick={() => cleaner.share()}>Share to chat</Button>
            <Button icon={Share2} onClick={() => cleaner.reset()}>New image</Button>
          </div>
        </div>
        <Compare before={st.previewUrl} after={out} />
        {!!quality && (quality.psnr_db !== undefined || quality.signals_before !== undefined) && (
          <p className={s.quality}>
            {quality.psnr_db !== undefined && <>Fidelity PSNR {String(quality.psnr_db)}{typeof quality.psnr_db === 'number' ? ' dB' : ''}</>}
            {quality.mean_absolute_difference !== undefined && <> · mean pixel difference {quality.mean_absolute_difference}/255</>}
            {quality.signals_before !== undefined && <> · metadata signals {quality.signals_before} → {quality.signals_after}</>}
            {st.demo && <> · demo numbers, not measured</>}
          </p>
        )}
        <p className={s.limits}>No local scanner can guarantee whether Instagram will label this image as AI-generated.</p>
        {st.verifyAvailable && !st.demo && <div className={s.verify}>
          <div className={s.verifyHead}>
            <Button icon={ShieldCheck} style={st.verifying ? { opacity: 0.5 } : undefined}
              onClick={() => { if (!st.verifying) cleaner.verify(); }}>
              {st.verifying ? 'Verifying…' : st.verify ? 'Verify again' : 'Verify with OpenAI'}
            </Button>
            <small>Sends this image to OpenAI for analysis — only on tap, never automatically.</small>
          </div>
          {st.verifyError && <p className={s.verifyError}>{st.verifyError}</p>}
          {st.verify && <ul className={s.verifyRows}>
            <li><span>OpenAI C2PA</span><strong>{st.verify.results.c2pa.replace('_', ' ')}</strong></li>
            <li><span>OpenAI SynthID</span><strong>{st.verify.results.synthid.replace('_', ' ')}</strong></li>
            <li><span>Overall</span><strong>{st.verify.overall === 'no_supported_openai_signal_detected' ? 'No supported OpenAI provenance signal detected' : st.verify.overall}</strong></li>
          </ul>}
        </div>}
      </Card>}
    </div>
    {st.toast && <div className={s.toast} role="status">{st.toast}</div>}
  </>;
}
export const aiCleanerScreen = { Main };
