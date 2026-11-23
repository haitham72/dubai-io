// Messenger AI local state: which conversation (or agent result) is open and the messages of each.
// Module-level so Sidebar and Main share it and threads survive leaving the screen.
import { createStore } from "../storeFactory";
import type { AiMessage } from "../types";
import { aiContacts, getDemoMessages } from "./data";

/** `task`: an agent result open in the main area instead of the conversation. */
interface AiState { selected: string; threads: Record<string, AiMessage[]>; thinking: boolean; thinkingThread?: string; task: string | null }

const initial = aiContacts.find((c) => c.id !== "new")?.id ?? "new";
const aiStore = createStore<AiState>({ selected: initial, threads: { [initial]: getDemoMessages(initial).map((m) => ({ ...m })) }, thinking: false, task: null });
const getAi = aiStore.get;
const set = aiStore.set;



export function useAi<T>(select: (s: AiState) => T): T {
  return aiStore.use(select);
}

export const ai = {
  get: getAi,
  select(id: string) {
    const cur = getAi();
    const threads = cur.threads[id] ? cur.threads : { ...cur.threads, [id]: getDemoMessages(id).map((m) => ({ ...m })) };
    set({ selected: id, threads, task: null });
  },
  newChat() {
    const id = `new-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    set({ selected: id, threads: { ...getAi().threads, [id]: [] }, task: null });
  },
  openTask(id: string | null) { set({ task: id }); },
  prepareRegeneration(id: string) {
    if (getAi().thinking) return;
    const cur = getAi();
    const messages = cur.threads[cur.selected] ?? [];
    const index = messages.findIndex((m) => m.id === id && m.role === "assistant");
    if (index < 0) return;
    let userIndex = index - 1;
    while (userIndex >= 0 && messages[userIndex].role !== "user") userIndex--;
    if (userIndex < 0) return;
    const text = messages[userIndex].text;
    set({ threads: { ...cur.threads, [cur.selected]: messages.slice(0, userIndex) } });
    return text;
  },
  push(msg: AiMessage, thread = getAi().selected) {
    set({ threads: { ...getAi().threads, [thread]: [...(getAi().threads[thread] ?? []), msg] } });
  },
  setThinking(thinking: boolean) { set({ thinking, thinkingThread: thinking ? getAi().selected : undefined }); },
};
