// E-sign flow (demo of UAE PASS signing). The document asks for a typed signature; on iPhone the
// Dynamic Island shows the UAE PASS confirm sheet (Apple-Pay style), on desktop it signs directly.
import { createStore } from "../storeFactory";
import { actions, getState } from "../store";

/** Only these typed names are accepted as Haitham's signature. */
const SIGNERS = ["haitham mohamed", "هيثم محمد"];
export const normalizeName = (v: string) => v.trim().replace(/\s+/g, " ").toLowerCase();
export const isValidSignature = (v: string) => SIGNERS.includes(normalizeName(v));
export const isArabic = (v: string) => /[؀-ۿ]/.test(v);

export type Stage = "idle" | "confirm" | "scanning" | "done";
interface EsignState { stage: Stage; taskId?: string; signature?: string }

const esignStore = createStore<EsignState>({ stage: "idle" });
const getEsign = esignStore.get;
const set = esignStore.set;
let islandPresent = false;



export function useEsign<T>(select: (s: EsignState) => T): T {
  return esignStore.use(select);
}

/** The phone shell's Dynamic Island registers itself so signing confirms there. */
export function setIslandPresent(v: boolean) { islandPresent = v; }

function sign(taskId: string, signature: string) {
  const task = getState().tasks.find((t) => t.id === taskId);
  if (task?.result?.type !== "esign") return;
  actions.updateTask(taskId, {
    title: "Contract signed", subtitle: "e& yearly renewal · signed with UAE PASS", unread: true, completedAt: Date.now(),
    result: { ...task.result, signature: signature.trim(), signedAt: Date.now() },
  });
}

export const esign = {
  /** "Sign with UAE PASS" pressed with a valid typed signature. */
  request(taskId: string, signature: string) {
    if (!isValidSignature(signature)) return;
    if (!islandPresent) { set({ stage: "scanning", taskId, signature }); window.setTimeout(() => { sign(taskId, signature); set({ stage: "idle" }); }, 900); return; }
    set({ stage: "confirm", taskId, signature });
  },
  /** Confirm in the island: Face ID scan, then signed. */
  confirm() {
    const { taskId, signature } = getEsign();
    if (!taskId || !signature || getEsign().stage !== "confirm") return;
    set({ stage: "scanning" });
    window.setTimeout(() => {
      sign(taskId, signature);
      set({ stage: "done" });
      window.setTimeout(() => set({ stage: "idle", taskId: undefined, signature: undefined }), 2600);
    }, 1500);
  },
  cancel() { set({ stage: "idle", taskId: undefined, signature: undefined }); },
};
