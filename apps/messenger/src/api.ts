// API client — barrel. Screens call these; never fetch() from a component.
// Server endpoints live in api/*.ts (Vercel functions; the Vite dev server runs the same files). Weather calls Open-Meteo directly (no key).
// Domain modules live in src/apiclient/ (http.ts holds the shared helper and is NOT re-exported).
export { searchFlights } from "./apiclient/flights";
export type { ImageJob } from "./apiclient/media";
export { startImage, getImageJob } from "./apiclient/media";
export type { VideoStart, VideoJob } from "./apiclient/media";
export { startVideo, getVideoJob } from "./apiclient/media";
export type { Quote } from "./apiclient/stocks";
export { getQuotes } from "./apiclient/stocks";
export type { ResearchResult } from "./apiclient/research";
export { runResearch } from "./apiclient/research";
export type { AiReply, ContactReply } from "./apiclient/chat";
export { askAi, getContactReply } from "./apiclient/chat";
export { transcribe, speak } from "./apiclient/voice";
export { weatherLabel, peekWeather, getWeather } from "./apiclient/weather";
export type { PhotoHit, PhotoSearch, PhotoList } from "./apiclient/photos";
export { searchPhotos, listPhotos } from "./apiclient/photos";
export type { AgentsHealth, DeepBrief, WatchTopic, GmailMessage, ChatContextLine, StickerPack, BuilderOption, Gif } from "./apiclient/agents";
export {
  agentsHealth, openVoiceStream, deepResearch, briefToItem, getWatchlist,
  getMailbox, getMailMessage, sendMail, loadTasks, saveTasks, serverHealth,
  getDiwanEvents, moreFromEventPicture, generateStickerOptions, listStickerPacks,
  bundledStickerPacks, searchGifs,
} from "./apiclient/agents";
export type { FactCheck, ImageIdeas, CommandWireEvent, LookAnswer } from "./apiclient/messenger";
export { messengerFactCheck, messengerImageIdeas, messengerStickers, messengerPlan, messengerCommand, messengerLook, photoForCheck } from "./apiclient/messenger";
export type {
  AgeBand,
  SocketConnectionState,
  SupabaseUser,
  SupabaseSignInResult,
  IdentitySession,
  IdentityMe,
  WsTicket,
  ChatMessageRow,
  ConversationRow,
  ClientOptions,
  OpenIdentitySessionOptions,
  WsTicketOptions,
  WebSocketLike,
  WebSocketFactory,
  WebSocketConstructor,
  ChatCoreSocketOptions,
} from "./apiclient/chatCore";
export {
  ChatApiError,
  resolveApiBase,
  resolveWsUrl,
  resolveSupabaseConfig,
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
  ChatCoreSocket,
} from "./apiclient/chatCore";
