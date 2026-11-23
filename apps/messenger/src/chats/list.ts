// The chat list: chats created this session (groups from an @messenger plan) above the seeded ones.
import { useStore } from "../store";
import type { Chat } from "../types";
import { chats } from "./data";

export function useChatList(): Chat[] {
  const extra = useStore((st) => st.extraChats);
  return extra.length ? [...extra, ...chats] : chats;
}

export function useChat(id: string): Chat {
  const list = useChatList();
  return list.find((c) => c.id === id) ?? list[0];
}
