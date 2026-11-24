import React from "react";
import { useChatList, useChat } from "../../src/chats/list";
import type { Chat } from "../../src/types";

export { actions, getState, subscribe } from "../../src/store";
export { img, avatar } from "../../src/ui";
export { ORB } from "../../src/mobile/parts";
export {
  ChatApiError,
  ChatCoreSocket,
  resolveApiBase,
  resolveWsUrl,
  signInSupabasePassword,
  openIdentitySession,
  getIdentityMe,
  issueWsTicket,
  listConversations,
  createConversation,
  fetchMessages,
  sendMessageRest,
  editMessageRest,
  deleteMessageRest,
  sendReceiptRest,
} from "../../src/api";

export function readChatListSnapshot(): { list: Chat[]; activeFallback: Chat } {
  const internals = (
    React as unknown as {
      __SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED?: {
        ReactCurrentDispatcher: { current: unknown };
      };
    }
  ).__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED;
  const prev = internals?.ReactCurrentDispatcher.current;
  if (internals) {
    internals.ReactCurrentDispatcher.current = {
      useSyncExternalStore: <T>(_sub: unknown, getSnap: () => T) => getSnap(),
    };
  }
  try {
    return { list: useChatList(), activeFallback: useChat("") };
  } finally {
    if (internals) internals.ReactCurrentDispatcher.current = prev;
  }
}
