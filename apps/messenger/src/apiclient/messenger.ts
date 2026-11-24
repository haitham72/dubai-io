// @messenger in a chat (agents service; callers fall back when it is off).
import type { AiSource, TripPlan, Verdict } from "../types";
import { post, type ChatContextLine, type StickerPack } from "./agents";

export interface FactCheck { claim: string; verdict: Verdict; answer: string; sources: AiSource[]; mode: "live" | "demo" | "offline"; status?: string; fallback?: boolean; photos?: number }
/** "@messenger is this true", optionally about photos (the service looks at them with a vision model). */
export async function messengerFactCheck(target: string, context: ChatContextLine[], images: string[] = []) {
  return post<FactCheck>("/messenger/factcheck", { target, context, images: await Promise.all(images.slice(0, 3).map(photoForCheck)) });
}

/** A chat photo in a form the service accepts: app pictures as their path, web pictures as their URL, anything local
 *  (blob:/data:) downscaled to a 1024 px JPEG data URL so uploads stay small. */
export async function photoForCheck(url: string): Promise<string> {
  const u = new URL(url, location.href);
  if (u.origin === location.origin && !u.pathname.startsWith("/agents/")) return u.pathname;
  if (u.protocol === "https:") return u.href;
  const blob = await (await fetch(url)).blob();
  const bitmap = await createImageBitmap(blob);
  const k = Math.min(1, 1024 / Math.max(bitmap.width, bitmap.height));
  const canvas = Object.assign(document.createElement("canvas"), { width: Math.round(bitmap.width * k), height: Math.round(bitmap.height * k) });
  canvas.getContext("2d")!.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", 0.85);
}

export interface ImageIdeas { subject: string; ideas: { title: string; prompt: string }[]; mode: string }
export const messengerImageIdeas = (request: string, context: ChatContextLine[]) => post<ImageIdeas>("/messenger/image-ideas", { request, context });

export const messengerStickers = (context: ChatContextLine[], exclude = "") => post<StickerPack>("/messenger/stickers", { context, exclude });

/** `request` is the @messenger message itself ("plan egypt on 2 january"): its destination, date and length win over the chat.
 *  `members` carries an existing card's resolved participants across date changes (even empty): the planner
 *  keeps exactly these people instead of re-deriving them, so nobody is asked twice. */
export const messengerPlan = (context: ChatContextLine[], contacts: { id: string; name: string }[], chatPartner?: string, request = "", members?: string[]) =>
  post<TripPlan>("/messenger/plan", { context, contacts, chatPartner, request: request.slice(0, 500), ...(members !== undefined ? { members } : {}) });

export interface CommandWireEvent {
  type: "act" | "undo" | "confirm" | "ask" | "cancel" | "chat"; id?: string; action?: string;
  args?: Record<string, string>; label?: string; awaiting?: string; undoMs?: number;
}
/** "@messenger open/read/reply …": decided by the same intent engine as voice (one turn, most-recent chat first). */
export const messengerCommand = (text: string, contacts: { id: string; name: string }[]) =>
  post<{ events: CommandWireEvent[] }>("/messenger/command", { text: text.slice(0, 500), contacts });

export interface LookAnswer { answer: string; mode: "live" | "demo" | "offline"; photos: number; status: string; fallback?: boolean }
/** "What is he doing in the image?": the vision model answers from the photo itself (not the caption). */
export const messengerLook = (image: string, question: string, context: ChatContextLine[]) =>
  post<LookAnswer>("/messenger/look", { target: question.slice(0, 500), context, images: [image] });
