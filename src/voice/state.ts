// Mirsal voice mode: listen → transcribe (OpenAI) → Mirsal AI (same chat + actions) → speak the answer (OpenAI TTS).
// With the agents service running (commands.ts), speech becomes commands: streamed while the person speaks when live
// speech-to-text is on, otherwise the transcript below is sent to it. Anything that isn't a command goes to the chat.
// The phone shell shows it in the Dynamic Island, Siri-style; `level` (0–1) drives the orb's pulse.
//
// iOS details that matter:
// - The microphone stream is kept for the whole page session (tracks are only disabled between requests), so
//   Safari asks for permission once. iOS still ends the stream if Safari goes to the background; then it asks again.
// - Safari's MediaRecorder writes one MP4 at stop; timeslice chunks can produce a file the transcriber rejects.
// - Audio may only start from a tap. The tap that opens voice mode resumes one AudioContext, and the spoken answer
//   is played through that context later (decoded buffer), which iOS allows even after the network round trip.
import { createStore } from "../storeFactory";
import { speak, transcribe } from "../api";
import { sendUserMessage } from "../ai/runAction";
import { ai } from "../ai/state";
import { CommandStream, commandMode, type Outcome } from "./commands";

export type VoiceStage = "idle" | "listening" | "thinking" | "speaking" | "error";
interface VoiceState { stage: VoiceStage; transcript: string; reply: string; level: number; error?: string }

const voiceStore = createStore<VoiceState>({ stage: "idle", transcript: "", reply: "", level: 0 });
const getVoice = voiceStore.get;
const set = voiceStore.set;



export function useVoice<T>(select: (s: VoiceState) => T): T {
  return voiceStore.use(select);
}

const SILENCE_MS = 1500;          // stop after this much quiet once speech was heard
const MAX_MS = 15000;             // hard stop for one request
// Voice-activity hysteresis: idle-mic hiss sits near 0.06 after the meter's ×4 gain, so a single
// hot frame must not count as speech (it re-armed the silence timer forever on noisy inputs).
const SPEECH_START = 0.12;        // level that counts as speech, 3 frames running
const SPEECH_END = 0.06;          // level that counts as quiet

let audioCtx: AudioContext | null = null;
let stream: MediaStream | null = null;
let micSource: MediaStreamAudioSourceNode | null = null;
let recorder: MediaRecorder | null = null;
let raf = 0;
let playing: AudioBufferSourceNode | null = null;
let run = 0; // cancels stale async steps
let live: { stream: CommandStream; node: AudioWorkletNode; sink: GainNode } | null = null; // streaming capture

/* 24 kHz mono PCM16 frames for live speech-to-text. Each output sample is the average of the input samples it covers
   (a box low-pass): plain sample-dropping folds everything above 12 kHz back into the speech band and blurs consonants. */
const PCM_WORKLET = `class P extends AudioWorkletProcessor{constructor(){super();this.r=sampleRate/24000;this.a=0;this.s=0;this.n=0;this.b=[]}
process(i){const c=i[0]&&i[0][0];if(!c)return true;for(let k=0;k<c.length;k++){this.s+=c[k];this.n+=1;this.a+=1;if(this.a>=this.r){this.a-=this.r;
const v=Math.max(-1,Math.min(1,this.s/this.n));this.s=0;this.n=0;this.b.push(v<0?v*32768:v*32767)}}if(this.b.length>=2400){const o=new Int16Array(this.b);
this.b=[];this.port.postMessage(o.buffer,[o.buffer])}return true}}registerProcessor("mirsal-pcm24k",P);`;
let workletReady: Promise<void> | null = null;

/** Feed `level` from an audio node (mic or the spoken reply). Returns a stop function. */
function meter(source: AudioNode, onFrame?: (level: number) => void, output = false) {
  const analyser = audioCtx!.createAnalyser();
  analyser.fftSize = 512;
  source.connect(analyser);
  if (output) analyser.connect(audioCtx!.destination);
  const data = new Uint8Array(analyser.fftSize);
  const tick = () => {
    analyser.getByteTimeDomainData(data);
    let sum = 0;
    for (const v of data) sum += ((v - 128) / 128) ** 2;
    const level = Math.min(1, Math.sqrt(sum / data.length) * 4);
    set({ level: getVoice().level * 0.6 + level * 0.4 });
    onFrame?.(level);
    raf = requestAnimationFrame(tick);
  };
  tick();
  return () => { cancelAnimationFrame(raf); try { source.disconnect(analyser); } catch { /* already */ } };
}

/** A kept stream iOS has silenced (muted after an interruption) or ended is useless: drop it and ask again. */
const usable = (st: MediaStream | null) => !!st && st.getAudioTracks().some((t) => t.readyState === "live" && !t.muted);
function dropMic() { stream?.getTracks().forEach((t) => t.stop()); stream = null; micSource = null; }

const getMic = () => navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });

async function micStream(): Promise<MediaStream> {
  let st = stream;
  if (!st || !usable(st)) {
    dropMic();
    try { st = await getMic(); }
    catch (err) {
      // With the site already set to Allow, iOS can still refuse the first call after Safari resumes. Retry once.
      if (!(err instanceof DOMException && err.name === "NotAllowedError")) throw err;
      await new Promise((r) => setTimeout(r, 350));
      st = await getMic();
    }
    stream = st;
  }
  st.getAudioTracks().forEach((t) => { t.enabled = true; });
  micSource ??= audioCtx!.createMediaStreamSource(st);
  return st;
}
/** Between requests the mic stays granted but silent (never stopped — stopping means a new permission prompt). */
function muteMic() { stream?.getAudioTracks().forEach((t) => { t.enabled = false; }); }

// iOS silences a kept mic stream once Safari is backgrounded; start fresh on return instead of reusing a dead one.
if (typeof document !== "undefined") {
  document.addEventListener("visibilitychange", () => { if (document.hidden && getVoice().stage === "idle") dropMic(); });
}

/** Short, human error with the reason attached so a failure on the phone can be diagnosed. */
const why = (err: unknown) => {
  const m = err instanceof Error ? err.message : String(err);
  return m.length > 60 ? m.slice(0, 60) + "…" : m;
};

/** Markdown reply → something pleasant to say out loud (first paragraph, no links/markup). */
function spoken(text: string) {
  const plain = text.replace(/\[([^\]]+)\]\([^)]+\)/g, "").replace(/[*_`#>]/g, "").replace(/^\s*[-•]\s+/gm, "").trim();
  return plain.split(/\n\s*\n/)[0].slice(0, 400);
}

function failAndClose(id: number, error: string) {
  if (id !== run) return;
  set({ stage: "error", error, level: 0 });
  window.setTimeout(() => id === run && voice.close(), 3000);
}

async function answer(id: number, blob: Blob) {
  set({ stage: "thinking", level: 0 });
  let text: string;
  try { text = (await transcribe(blob)).trim(); } catch (err) { return failAndClose(id, `Couldn't transcribe (${why(err)})`); }
  if (id !== run) return;
  if (!text) return failAndClose(id, "I didn't catch that.");
  set({ transcript: text });

  if ((await commandMode()) === "text") {
    const stream = await CommandStream.open(false, () => {});
    if (stream && id === run) {
      stream.text(text);
      const outcome = await stream.end();
      if (id !== run) return;
      if (!outcome.chat) return finishCommand(id, outcome);
    }
  }
  await chatAnswer(id, text);
}

/** A decided command: show what happened and say it; a question is spoken and Mirsal listens again for the answer. */
async function finishCommand(id: number, outcome: Outcome) {
  if (outcome.chat) return chatAnswer(id, outcome.chat);
  const reply = outcome.reply || "Done";
  set({ stage: "speaking", reply, level: 0 });
  const done = () => voice.close();
  if (!outcome.ask) return await say(id, reply, done, done);
  const listenAgain = () => { voice.close(); void voice.start(); };
  await say(id, reply, listenAgain, listenAgain); // a dead speaker must not eat the answer either
}

async function chatAnswer(id: number, text: string) {
  set({ stage: "thinking" });
  await sendUserMessage(text); // never throws: errors become an assistant message
  if (id !== run) return;
  const thread = ai.get().threads[ai.get().selected] ?? [];
  const last = [...thread].reverse().find((m) => m.role === "assistant");
  const reply = last ? spoken(last.text) : "";
  set({ reply });
  if (!reply) return void voice.close();

  // Show the answer even if speech fails.
  set({ stage: "speaking" });
  await say(id, reply, () => window.setTimeout(() => id === run && voice.close(), 1600));
}

/** Speak `text` through the unlocked AudioContext; `then` runs when playback ends, `onFail` if it can't. */
async function say(id: number, text: string, then: () => void, onFail?: () => void) {
  try {
    const audio = await speak(text);
    if (id !== run) return;
    const buffer = await audioCtx!.decodeAudioData(await audio.arrayBuffer());
    if (id !== run) return;
    const source = audioCtx!.createBufferSource();
    source.buffer = buffer;
    const stop = meter(source, undefined, true);
    playing = source;
    source.onended = () => { stop(); playing = null; set({ level: 0 }); if (id === run) then(); };
    source.start();
  } catch {
    if (id !== run) return;
    if (onFail) onFail();
    else window.setTimeout(() => id === run && voice.close(), 5000); // reply stays on screen to read
  }
}

export const voice = {
  /** Start listening — call from a tap (iOS needs the gesture for the mic and for audio). */
  async start() {
    if (getVoice().stage !== "idle" && getVoice().stage !== "error") return;
    const id = ++run;
    set({ stage: "listening", transcript: "", reply: "", level: 0, error: undefined });
    try {
      audioCtx ??= new AudioContext();
      void audioCtx.resume(); // unlock audio inside the tap (don't await before getUserMedia)
      const s = await micStream();
      if (id !== run) return;
      if ((await commandMode()) === "stream" && await startStreaming(id)) return;
      const chunks: Blob[] = [];
      const rec = new MediaRecorder(s);
      recorder = rec;
      rec.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
      let stopMeter = () => {};
      rec.onstop = () => {
        stopMeter();
        muteMic();
        if (id !== run) return;
        const blob = new Blob(chunks, { type: rec.mimeType || chunks[0]?.type || "audio/mp4" });
        if (!blob.size) return failAndClose(id, "I didn't catch that.");
        void answer(id, blob);
      };
      rec.start(); // one blob at stop (Safari's chunked MP4s can be unreadable)
      const began = Date.now();
      let heard = 0, quietSince = 0, hot = 0;
      stopMeter = meter(micSource!, (level) => {
        const now = Date.now();
        hot = level > SPEECH_START ? hot + 1 : 0;
        if (hot >= 3) { heard = now; quietSince = 0; }
        else if (heard && !quietSince && level < SPEECH_END) quietSince = now;
        if ((heard && quietSince && now - quietSince > SILENCE_MS) || now - began > MAX_MS) voice.stop();
      });
    } catch (err) {
      const denied = err instanceof DOMException && (err.name === "NotAllowedError" || err.name === "SecurityError");
      failAndClose(id, denied
        ? "Mirsal couldn't reach the microphone — tap again. If it repeats: Settings › Apps › Safari › Microphone › Allow."
        : `The microphone isn't available (${why(err)})`);
    }
  },
  /** Stop listening and send what was said. */
  stop() {
    if (live) return void stopStreaming(run);
    if (recorder?.state === "recording") recorder.stop();
  },
  /** Dismiss voice mode (stops recording and speech; the mic stays granted but muted for the next request). */
  close() {
    run++;
    if (live) { live.stream.close(); teardownStreaming(); }
    if (recorder?.state === "recording") { recorder.onstop = null; recorder.stop(); }
    muteMic();
    recorder = null;
    cancelAnimationFrame(raf);
    try { playing?.stop(); } catch { /* not started */ }
    playing = null;
    set({ stage: "idle", level: 0 });
  },
};

/* ---------------- live streaming (agents service with live speech-to-text) ---------------- */
async function startStreaming(id: number): Promise<boolean> {
  try {
    workletReady ??= audioCtx!.audioWorklet.addModule(URL.createObjectURL(new Blob([PCM_WORKLET], { type: "application/javascript" })));
    await workletReady;
    holdingReply = false;
    let heardText = false; // any transcript yet — 30 s of live audio with zero words means dead STT, stop
    const stream = await CommandStream.open(true, (text) => {
      if (id !== run) return;
      if (text.trim()) heardText = true;
      set({ transcript: text });
    }, () => { if (id === run) holdingReply = true; });
    if (!stream || id !== run) { stream?.close(); return false; }
    const node = new AudioWorkletNode(audioCtx!, "mirsal-pcm24k");
    const sink = audioCtx!.createGain();
    sink.gain.value = 0; // the node must reach the destination to run; silent
    node.port.onmessage = (m) => stream.audio(m.data as ArrayBuffer);
    micSource!.connect(node);
    node.connect(sink).connect(audioCtx!.destination);
    live = { stream, node, sink };
    const began = Date.now();
    let heard = 0, quietSince = 0, hot = 0;
    const stopMeter = meter(micSource!, (level) => {
      const now = Date.now();
      hot = level > SPEECH_START ? hot + 1 : 0;
      if (hot >= 3) { heard = now; quietSince = 0; }
      else if (heard && !quietSince && level < SPEECH_END) quietSince = now;
      // Streaming acts on its own while the person speaks, so end of speech can be quicker than the batch path —
      // unless a reply is being dictated into an opened chat, which gets a longer window. A transcript that ends
      // mid-thought ("open Sara Ali and…") gets the same hold: the sentence isn't over, the pause is thinking.
      const holding = holdingReply;
      const trailing = CONTINUES.test(getVoice().transcript);
      const quietLimit = holding || trailing ? HOLD_SILENCE_MS : STREAM_SILENCE_MS;
      const maxMs = heard ? STREAM_MAX_MS : MAX_MS;
      if ((heard && quietSince && now - quietSince > quietLimit) || now - began > maxMs
        || (!heardText && now - began > NO_TRANSCRIPT_MS)) void stopStreaming(id);
    });
    stopLiveMeter = stopMeter;
    return true;
  } catch {
    return false; // fall back to the batch recorder
  }
}

// Quiet that ends a streamed turn: a natural pause is ~1 s, so 1.5 s. In-app actions can still run
// before this, while the person is speaking.
const STREAM_SILENCE_MS = 1500;
// 30 s of live audio without a single transcribed word means the speech service is dead (it errored or
// never streamed): stop and let the turn resolve instead of recording until the 2-minute cap.
const NO_TRANSCRIPT_MS = 30000;
// The live transcript ends mid-thought: a conjunction or an unfinished send/reply head. The speaker paused
// to think, not finished — hold the turn for the rest instead of ending on "open Sara Ali and".
const CONTINUES = /\b(and( then)?|but|tell (him|her|them)( that)?|reply( (with|saying|that))?|send( (it|that|this))?|(saying|with|that))\s*[.…]*$/i;
// The service signals dictation separately from acts, including standalone sends and replies that start
// after a chat already opened. Dictation gets 4 s of quiet; active speech can last up to two minutes.
const HOLD_SILENCE_MS = 4000;
const STREAM_MAX_MS = 120000;
let holdingReply = false;
let stopLiveMeter: () => void = () => {};

function teardownStreaming() {
  stopLiveMeter();
  holdingReply = false;
  if (!live) return;
  try { micSource?.disconnect(live.node); live.node.disconnect(); live.sink.disconnect(); } catch { /* already */ }
  live = null;
  muteMic();
}

async function stopStreaming(id: number) {
  if (!live || id !== run) return;
  const { stream } = live;
  teardownStreaming();
  set({ stage: "thinking", level: 0 });
  const outcome = await stream.end();
  if (id === run) await finishCommand(id, outcome);
}
