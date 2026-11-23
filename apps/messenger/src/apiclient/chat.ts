// AI chat + contact auto-replies (OpenAI, small model on the server).
import type { AiMessage, FlightQuery } from "../types";
import { json } from "./http";

/* ---------- AI chat (OpenAI on the server) ----------
   The server decides the intent. `action` tells the frontend what to start. */
export interface AiReply {
  text: string;
  action?:
    | { type: "image"; prompt: string }
    | { type: "video"; prompt: string }
    | { type: "flight"; query: FlightQuery }
    | { type: "weather"; city: string }
    | { type: "research"; topic: string };
}

/** Where the chat model lives. Without it, a request like "open my last chat" gets the stock "I can't access
 *  external chat programs" — but in Mirsal the chats, mail and calendar are this app, and voice/@mirsal act on them. */
const MIRSAL_CONTEXT =
  "You are inside the Mirsal app itself: the person's chats, mail, calendar, research reports and Mirsal Updates are " +
  "in this app, not an external program. Mirsal acts on them through voice commands (mic button) and @mirsal in a " +
  "chat: open a chat or 'my last chat', read messages aloud, send or reply to a message, write an email, check " +
  "notifications, plan a trip, research a topic, fact-check with '@mirsal is this true'. If the person asks for one " +
  "of those here, never say you can't access a chat app: say briefly which words to use (for example 'say: open my " +
  "chat with Arif'), or answer what you can. Never claim you already did an action in the app.";

export async function askAi(history: Pick<AiMessage, "role" | "text">[]): Promise<AiReply> {
  return json<AiReply>(await fetch("/api/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: [{ role: "system", text: MIRSAL_CONTEXT }, ...history] }),
  }));
}

/* ---------- contact auto-replies (OpenAI, small model on the server) ----------
   The server role-plays the contact (or a group member) from the recent chat history. */
export interface ContactReply { text: string; sender?: string } // sender = group member's first name

export async function getContactReply(
  chatId: string, contactName: string, isGroup: boolean,
  history: { fromMe: boolean; text: string }[],
): Promise<ContactReply> {
  return json<ContactReply>(await fetch("/api/reply", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chatId, contactName, isGroup, history }),
  }));
}
