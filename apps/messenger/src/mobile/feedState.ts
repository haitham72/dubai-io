// Opens the full-screen media feed from anywhere on the phone (story cards, Updates) without prop drilling.
// Likes are a per-session demo affordance.
import { createStore } from "../storeFactory";

interface FeedState { openAt: string | null; liked: Record<string, boolean> }
const feedStore = createStore<FeedState>({ openAt: null, liked: {} });
const getFeed = feedStore.get;
const set = feedStore.set;



export function useFeed<T>(select: (s: FeedState) => T): T {
  return feedStore.use(select);
}

export const feed = {
  open(taskId: string) { set({ openAt: taskId }); },
  close() { set({ openAt: null }); },
  toggleLike(taskId: string) { const cur = getFeed(); set({ liked: { ...cur.liked, [taskId]: !cur.liked[taskId] } }); },
};
