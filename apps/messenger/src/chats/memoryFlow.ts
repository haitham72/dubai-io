// Approval flow for "Save to memory". Framework-free so it is testable: nothing is sent to memory until approve().
import type { MemoryClient, MemoryPreview, SaveResult } from "../apiclient/memory";

export type FlowPhase = "closed" | "loading" | "ready" | "saving" | "done" | "error";
export interface FlowState {
  phase: FlowPhase;
  preview: MemoryPreview | null;
  result: SaveResult | null;
  error: string | null;
}

export function createApprovalFlow(client: MemoryClient, conversationId: string, messageId: string) {
  let state: FlowState = { phase: "closed", preview: null, result: null, error: null };
  const listeners = new Set<() => void>();
  const set = (patch: Partial<FlowState>) => { state = { ...state, ...patch }; listeners.forEach((l) => l()); };

  async function open() {
    set({ phase: "loading", preview: null, result: null, error: null });
    try {
      set({ phase: "ready", preview: await client.preview(conversationId, messageId) });
    } catch (e) {
      set({ phase: "error", error: (e as Error).message });
    }
  }
  function cancel() { set({ phase: "closed", preview: null, result: null, error: null }); } // sends nothing
  async function approve() {
    // Single approval: only from "ready", only when the server said it can be saved, never twice.
    if (state.phase !== "ready" || !state.preview?.can_save_now) return;
    set({ phase: "saving" });
    try {
      const result = await client.save(conversationId, messageId);
      if (result.saved) set({ phase: "done", result });
      else set({ phase: "error", result, error: result.held_back ? "Held back by the server: not saved." : `Not saved (status: ${result.status}).` });
    } catch (e) {
      set({ phase: "error", error: (e as Error).message });
    }
  }
  /** Explicit tap to allow memory in this chat (the server still requires every member's consent). */
  async function allowInThisChat() {
    try { await client.setChatMode(conversationId, "save"); } catch (e) { set({ phase: "error", error: (e as Error).message }); return; }
    await open();
  }
  return {
    get: () => state,
    subscribe: (l: () => void) => { listeners.add(l); return () => { listeners.delete(l); }; },
    open, cancel, approve, allowInThisChat,
  };
}
export type ApprovalFlow = ReturnType<typeof createApprovalFlow>;
