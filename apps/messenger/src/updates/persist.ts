// Messenger Updates survive a reload when the agents service (Redis) runs: finished tasks are saved a second after they
// change and restored on load. Without the service nothing happens (tasks stay in memory, as before).
import { agentsHealth, loadTasks, saveTasks } from "../api";
import { actions, getState, subscribe } from "../store";

let timer = 0;
let lastSaved = "";

void agentsHealth().then(async (h) => {
  if (!h?.ok) return;
  try { actions.restoreTasks(await loadTasks()); } catch { /* keep the in-memory tasks */ }
  subscribe(() => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      const done = getState().tasks.filter((t) => t.status !== "running");
      const key = JSON.stringify(done.map((t) => [t.id, t.status, t.dismissed]));
      if (key === lastSaved) return;
      lastSaved = key;
      void saveTasks(done).catch(() => { lastSaved = ""; });
    }, 1000);
  });
});
