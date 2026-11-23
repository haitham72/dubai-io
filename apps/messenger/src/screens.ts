// Screen registry — owned by the lead session. Every slot is pre-wired here, so a session's work
// shows up the moment its folder is filled in. Sessions never edit this file.
import type { ComponentType } from "react";
import type { ScreenId } from "./types";
import { chatsScreen } from "./chats";
import { aiScreen } from "./ai";
import { flightsScreen } from "./screens/flights";
import { weatherScreen } from "./screens/weather";
import { calendarScreen } from "./screens/calendar";
import { stocksScreen } from "./screens/stocks";
import { filesScreen } from "./screens/files";
import { mailScreen } from "./screens/mail";
import { researchScreen } from "./screens/research";
import { historyScreen } from "./screens/history";
import { aiCleanerScreen } from "./screens/ai-cleaner";

/** The contract every screen folder's index.tsx exports. Omit Sidebar for a full-width screen (e.g. Weather). */
export interface Screen {
  Sidebar?: ComponentType;
  Main: ComponentType;
}

export const screens: Record<ScreenId, Screen> = {
  chats: chatsScreen,
  flights: flightsScreen,
  stocks: stocksScreen,
  weather: weatherScreen,
  mail: mailScreen,
  calendar: calendarScreen,
  files: filesScreen,
  ai: aiScreen,
  research: researchScreen,
  history: historyScreen,
  "ai-cleaner": aiCleanerScreen,
};
