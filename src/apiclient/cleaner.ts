// AI Image Cleaner (agents service; demo fallback when it is off).
// P3 will add the single shared job runner here for the screen + the chat skill.
import { AGENTS } from "./agents";
import { json } from "./http";

export type CleanMode = "resize" | "sdxl" | "resize_then_sdxl";
export interface CleanJob {
  id: string; mode: CleanMode; stage: string; note: string; percent?: number;
  done: boolean; error?: string; result?: boolean;
  /** Ordered static stages for this job's mode (server-owned); absent in demo payloads. */
  stages?: string[];
  quality?: { psnr_db?: number | string; mean_absolute_difference?: number; signals_before?: number; signals_after?: number };
}

export const CLEAN_MODE_LABEL: Record<CleanMode, string> = { resize: "Resize", sdxl: "SDXL", resize_then_sdxl: "Resize + SDXL" };

/** Demo/offline checklist order (mirrors the full server order incl. a faces line). */
export const FALLBACK_STAGES = ["Checking image", "Resizing image", "Cleaning AI traces", "Preserving faces", "Presenting result"];

/** Checklist rows from the server order; the live faces wording slots in before
 *  "Presenting result". Unknown strings never break the list. */
export function visibleStages(order: string[], current: string): string[] {
  if (!current) return [...order];
  if (order.includes(current)) return [...order];
  const out = [...order];
  const i = out.indexOf("Presenting result");
  out.splice(i < 0 ? out.length : i, 0, current);
  return out.filter((s, j) => out.indexOf(s) === j);
}

export interface CleanRun {
  onStage?: (job: CleanJob) => void;
  pollMs?: number;
  maxPolls?: number;
}
/** Start a job and poll it to completion (missed polls are skipped). Throws on timeout. */
export async function runCleanJob(file: File, mode: CleanMode, run: CleanRun = {}): Promise<{ jobId: string; job: CleanJob }> {
  const { job_id: jobId } = await startCleanJob(file, mode);
  const pollMs = run.pollMs ?? 1000;
  const maxPolls = run.maxPolls ?? 600;
  for (let i = 0; i < maxPolls; i++) {
    await new Promise((r) => setTimeout(r, pollMs));
    let job: CleanJob;
    try {
      job = await getCleanJob(jobId);
    } catch { continue; }
    run.onStage?.(job);
    if (job.done) return { jobId, job };
  }
  throw new Error("timeout");
}
export interface CleanerCapabilities { modes: CleanMode[]; engine: string; verify_openai: boolean }

export async function startCleanJob(file: File, mode: CleanMode): Promise<{ job_id: string }> {
  const form = new FormData();
  form.append("image", file, file.name);
  form.append("mode", mode);
  return json<{ job_id: string }>(await fetch(`${AGENTS}/ai-cleaner/jobs`, { method: "POST", body: form }));
}

export async function getCleanJob(id: string): Promise<CleanJob> {
  return json<CleanJob>(await fetch(`${AGENTS}/ai-cleaner/jobs/${encodeURIComponent(id)}`));
}

export function cleanFileUrl(id: string): string {
  return `${AGENTS}/ai-cleaner/jobs/${encodeURIComponent(id)}/file`;
}

export interface OpenAiVerify {
  provider: string; status: string;
  results: { c2pa: string; synthid: string }; overall: string;
}

/** Official OpenAI provenance check. Exists server-side only when a key is configured. */
export async function verifyCleanImage(file: File): Promise<OpenAiVerify> {
  const form = new FormData();
  form.append("image", file, file.name);
  return json<OpenAiVerify>(await fetch(`${AGENTS}/ai-cleaner/verify`, { method: "POST", body: form }));
}

export async function getCleanerCapabilities(): Promise<CleanerCapabilities | null> {
  try {
    const res = await fetch(`${AGENTS}/ai-cleaner/capabilities`);
    if (!res.ok) return null;
    return res.json() as Promise<CleanerCapabilities>;
  } catch { return null; }
}
