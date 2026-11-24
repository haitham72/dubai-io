// The chat list: real conversations in real mode, or demo-labelled seeded chats in demo mode.
import { useStore } from "../store";
import type { Chat } from "../types";
import { chats } from "./data";

export function useChatList(): Chat[] {
  const mode = useStore((st) => st.mode);
  const extra = useStore((st) => st.extraChats);
  const conversations = useStore((st) => st.conversations);

  if (mode === "real") {
    return extra.length ? [...extra, ...conversations] : conversations;
  }

  const demoChats = chats.map((c) => ({
    ...c,
    preview: c.preview.startsWith("Demo data") ? c.preview : `Demo data · ${c.preview}`,
  }));
  return extra.length ? [...extra, ...demoChats] : demoChats;
}

export function useChat(id: string): Chat {
  const mode = useStore((st) => st.mode);
  const list = useChatList();
  return (
    list.find((c) => c.id === id) ??
    list[0] ?? {
      id: id || "",
      contact: { id: "", name: mode === "demo" ? "Demo" : "Chats", avatar: "" },
      preview: "",
      time: "",
      unread: 0,
    }
  );
}
