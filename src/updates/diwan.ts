// Diwan events become Mirsal notifications: on load, today's / yesterday's / this week's UAE events (agents service).
// Without the service nothing is added.
import { getDiwanEvents } from "../api";
import { actions, getState } from "../store";

void getDiwanEvents().then(({ events }) => {
  for (const e of events) {
    const id = `diwan-${e.id}`;
    if (getState().tasks.some((t) => t.id === id)) continue;
    actions.addTask({
      id, type: "event", status: "completed", completedAt: Date.now(),
      title: `${e.when} · ${e.title}`, subtitle: e.summary || e.source, result: { type: "event", event: e },
    });
  }
}).catch(() => { /* agents service off */ });
