// Opening a video from Messenger Updates lands it in AI Chat's shared "Videos" thread.
// First open: a welcome line and an entrance animation. Later opens: "Here is your video."
import { actions } from "../store";
import type { MessengerTask } from "../types";
import { isVideoOpened, markVideoOpened } from "../videos";
import { ai } from "./state";

export const VIDEOS_THREAD = "videos";

export function openVideoInAi(task: MessengerTask) {
  if (task.result?.type !== "video") return;
  const { videoUrl, title } = task.result;
  const isNew = !isVideoOpened(videoUrl);
  markVideoOpened(videoUrl);
  actions.updateTask(task.id, { unread: false, ...(task.title === "New video" ? { title: "Your video" } : {}) });
  ai.select(VIDEOS_THREAD);
  ai.push({
    id: Math.random().toString(36).slice(2, 10), role: "assistant", taskId: task.id, enter: isNew,
    text: isNew ? `Welcome! 🎬 Your new video **${title}** just arrived. Press play to take a look.` : "Here is your video.",
  }, VIDEOS_THREAD);
  actions.navigate("ai");
}
