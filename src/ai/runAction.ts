// Turns an AI reply's `action` into real work + Mirsal tasks. Exported so Chats can reuse it later.
import { actions, getState } from "../store";
import { askAi, getImageJob, getVideoJob, getWeather, runResearch, searchFlights, startImage, startVideo, type AiReply } from "../api";
import type { AiMessage, MirsalTask } from "../types";
import { MOCK_VIDEO_MS, MOCK_VIDEO_TICK_MS, pickMockVideo } from "../videos";
import { cabinLabel, flightDate } from "../screens/flights/format";
import { ai } from "./state";

type Action = NonNullable<AiReply["action"]>;
const uid = () => Math.random().toString(36).slice(2, 10);

/** Poll a server image job until done; retries update the original Mirsal task id. */
async function pollImage(jobId: string, prompt: string, taskId = jobId) {
  for (let i = 0; i < 90; i++) {
    await new Promise((r) => setTimeout(r, 2000));
    try {
      const job = await getImageJob(jobId);
      if (job.status === "completed" && job.imageUrl) {
        actions.updateTask(taskId, {
          title: "Image ready", subtitle: prompt, status: "completed", completedAt: Date.now(),
          unread: true, result: { type: "image", imageUrl: job.imageUrl, prompt },
        });
        return;
      }
      if (job.status === "failed") {
        actions.updateTask(taskId, { title: "Image failed", status: "failed", error: job.error ?? "Image generation failed" });
        return;
      }
    } catch { /* transient: keep polling */ }
  }
  actions.updateTask(taskId, { title: "Image failed", status: "failed", error: "Timed out" });
}

/** Fake video generation: ease-out progress ticks, then a ready-made clip. Never Higgs. */
async function mockVideo(taskId: string, prompt: string) {
  const video = pickMockVideo();
  const started = Date.now();
  for (;;) {
    await new Promise((r) => setTimeout(r, MOCK_VIDEO_TICK_MS));
    const t = Math.min(1, (Date.now() - started) / MOCK_VIDEO_MS);
    if (t >= 1) {
      actions.updateTask(taskId, {
        title: "Video done", subtitle: video.title, status: "completed", completedAt: Date.now(),
        unread: true, progress: 100,
        result: { type: "video", videoUrl: video.url, prompt, title: video.title },
      });
      return;
    }
    actions.updateTask(taskId, { progress: Math.round(100 * (1 - Math.pow(1 - t, 2))) });
  }
}

/** Kling 3.0 through the server when it's configured; otherwise the bundled demo clips. */
async function liveOrMockVideo(taskId: string, prompt: string) {
  let start;
  try { start = await startVideo(prompt); } catch { start = { mode: "mock" as const }; }
  if ("mode" in start) return mockVideo(taskId, prompt);
  const began = Date.now();
  for (let i = 0; i < 120; i++) {
    await new Promise((r) => setTimeout(r, 4000));
    // Kling 5s usually takes 1-3 minutes: elapsed-based progress, held below 100 until it's really done
    actions.updateTask(taskId, { progress: Math.min(95, Math.round(((Date.now() - began) / 150_000) * 100)) });
    let job;
    try { job = await getVideoJob(start.id); } catch { continue; /* transient: keep polling */ }
    if (job.status === "completed" && job.videoUrl) {
      actions.updateTask(taskId, {
        title: "Video done", subtitle: prompt, status: "completed", completedAt: Date.now(), unread: true, progress: 100,
        result: { type: "video", videoUrl: job.videoUrl, prompt, title: prompt },
      });
      return;
    }
    if (job.status === "failed") throw new Error(job.error ?? "Video generation failed");
  }
  throw new Error("Timed out");
}

/** Start/poll image jobs while retaining an existing task id on retry. */
async function imageTask(prompt: string, existingId?: string) {
  const job = await startImage(prompt);
  const taskId = existingId ?? job.id;
  if (!existingId) actions.addTask({ id: taskId, type: "image", title: "Generating image", subtitle: prompt, status: "running" });
  void pollImage(job.id, prompt, taskId);
  return taskId;
}
function videoTask(prompt: string, existingId?: string) {
  const taskId = existingId ?? uid();
  if (!existingId) actions.addTask({ id: taskId, type: "video", title: "Creating video", subtitle: prompt, status: "running", progress: 0 });
  void liveOrMockVideo(taskId, prompt).catch(err => {
    actions.updateTask(taskId, { title: "Video failed", status: "failed", error: err instanceof Error ? err.message : String(err) });
  });
  return taskId;
}

/** "Prompt your edits" in Mirsal Studio — images only: Nano Banana 2 edits the original image with the instruction
 *  (real Higgsfield on the dev server via the CLI, or via the API when keys are set). The edit lands as a new task. */
export async function editImage(task: MirsalTask, instruction: string): Promise<{ taskId: string; fake: boolean }> {
  const r = task.result;
  if (r?.type !== "image") throw new Error("Only images can be edited.");
  const job = await startImage(instruction.trim(), r.imageUrl);
  const label = `${r.prompt} · ${instruction.trim()}`;
  actions.addTask({ id: job.id, type: "image", title: "Editing image", subtitle: instruction.trim(), status: "running" });
  void pollImage(job.id, label, job.id);
  return { taskId: job.id, fake: !!job.fake };
}

/** Retry only failed generation tasks. The original task id keeps inline replies linked. */
export async function retryTask(task: MirsalTask): Promise<boolean> {
  const current = getState().tasks.find(t => t.id === task.id);
  if (!current || current.status !== "failed" || (current.type !== "image" && current.type !== "video")) return false;
  const prompt = (current.result?.type === current.type ? current.result.prompt : current.subtitle).trim();
  if (!prompt) throw new Error("This task has no prompt to retry.");
  // Claim the retry synchronously so a second click cannot start a duplicate paid image job.
  actions.updateTask(current.id, {
    status: "running", title: current.type === "image" ? "Generating image" : "Creating video", subtitle: prompt,
    startedAt: Date.now(), completedAt: undefined, error: undefined, result: undefined,
    progress: current.type === "video" ? 0 : undefined, unread: true,
  });
  try {
    if (current.type === "image") await imageTask(prompt, current.id);
    else videoTask(prompt, current.id);
    return true;
  } catch (err) {
    actions.updateTask(current.id, { status: "failed", title: current.type === "image" ? "Image failed" : "Video failed", error: err instanceof Error ? err.message : String(err) });
    throw err;
  }
}

/** Run an action; returns the assistant message to show. */
export async function runAction(action: Action, serverText: string): Promise<AiMessage> {
  if (action.type === "image") {
    const taskId = await imageTask(action.prompt);
    return { id: uid(), role: "assistant", text: serverText, taskId };
  }

  if (action.type === "flight") {
    const flights = await searchFlights(action.query);
    if (!flights.length) return { id: uid(), role: "assistant", text: "No flights found for that route and date." };
    const cheapest = flights.reduce((a, b) => (a.price <= b.price ? a : b));
    actions.addTask({
      type: "flight", title: "Flight found", status: "completed", completedAt: Date.now(),
      subtitle: `${flights.length} flights to ${action.query.to} from ${cheapest.currency} ${cheapest.price.toLocaleString()}`,
      result: { type: "flight", query: action.query, flights },
    });
    const top3 = flights.slice(0, 3).map((f) =>
      `- **${f.airline} ${f.flightNo}** · ${f.fromTime} → ${f.toTime} · ${f.duration} · ${f.stops ? `${f.stops} stop` : "Non-stop"} · ${cabinLabel(f.cabin)} · ${f.currency} ${f.price.toLocaleString()}`,
    ).join("\n");
    return {
      id: uid(), role: "assistant",
      text: `I found **${flights.length} flights** from ${action.query.from} to ${action.query.to} on ${flightDate(flights[0].date)}:\n\n${top3}\n\n[View all flights](#flights)`,
    };
  }

  if (action.type === "research") {
    const taskId = actions.addTask({ type: "research", title: "Researching", subtitle: action.topic, status: "running" });
    try {
      const brief = await runResearch(action.topic);
      actions.updateTask(taskId, {
        title: "Research ready", subtitle: `${brief.findings.length} key insights · ${brief.title}`, status: "completed",
        completedAt: Date.now(), unread: true, result: { type: "research", items: [brief] },
      });
      return {
        id: uid(), role: "assistant", status: brief.status,
        text: `**${brief.title}**\n\n${brief.summary}\n\n${brief.findings.map((f) => `- ${f}`).join("\n")}\n\n[Open Research](#research)`,
      };
    } catch (err) {
      actions.updateTask(taskId, { title: "Research failed", status: "failed", error: err instanceof Error ? err.message : String(err) });
      return { id: uid(), role: "assistant", text: "I couldn't finish that research right now — please try again." };
    }
  }

  if (action.type === "video") {
    const taskId = videoTask(action.prompt);
    return { id: uid(), role: "assistant", text: serverText, taskId };
  }

  const w = await getWeather(action.city);
  const today = w.daily[0];
  return {
    id: uid(), role: "assistant",
    text: `**${w.location}, ${w.country}** · ${w.tempC}°C, ${w.condition}\nFeels like ${w.feelsLikeC}°C · H ${today?.maxC ?? "–"}° / L ${today?.minC ?? "–"}° · Humidity ${w.humidity}% · Wind ${w.windKmh} km/h\n\n[Open Weather](#weather)`,
  };
}

/** Send a user message in the open thread and append the assistant's reply. */
export async function sendUserMessage(text: string) {
  const thread = ai.get().selected;
  const history = [...(ai.get().threads[thread] ?? []), { id: uid(), role: "user" as const, text }];
  ai.push(history[history.length - 1], thread);
  ai.setThinking(true);
  const started = Date.now();
  try {
    const reply = await askAi(history.map(({ role, text }) => ({ role, text })));
    const msg = reply.action ? await runAction(reply.action, reply.text) : { id: uid(), role: "assistant" as const, text: reply.text };
    ai.push({ ...msg, status: `Reasoned for ${Math.max(1, Math.round((Date.now() - started) / 1000))}s` }, thread);
  } catch (err) {
    const e = err instanceof Error ? err.message : String(err);
    const offline = /503|Failed to fetch|NetworkError|ECONNREFUSED|500/.test(e);
    ai.push({
      id: uid(), role: "assistant",
      text: offline
        ? "Mirsal AI is unavailable right now — check `OPENAI_API_KEY` in `.env` (or the Vercel project settings)."
        : `Sorry, something went wrong: ${e}`,
    }, thread);
  } finally {
    ai.setThinking(false);
  }
}
