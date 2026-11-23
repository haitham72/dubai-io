# Mirsal Architecture & Cheat Sheet

A concise, high-yield guide covering **100% of the working application**: architecture, complete folder map, key runtime engines, and the exact protocol when backend teams ask you to update fields or endpoints.

---

## 1. 30-Second Architecture Overview

```
                         [ React 18 + TypeScript (Vite) ]
               Dual Shell: Mac Desktop (1920x1080) / iPhone (<=820px)
                                      │
                                      ▼
                        Global Store (`src/store.ts`)
                                      │
                                      ▼
                         API Barrel (`src/api.ts`)
                                      │
                      API Clients (`src/apiclient/*.ts`)
                                ┌─────┴─────┐
                                │           │
                                ▼           ▼
           [ Serverless Node / Vercel ]    [ Python AI Agents Service ]
                    (`api/*.ts`)                  (`agents/` :8787)
           • Chat completions / Replies     • Real-time Voice WebSocket
           • Flight search / Stocks         • AI Image Cleaner job runner
           • Photo search & index           • Deep research & fact check
```

- **Resilient Fallback Design:** Every client in `src/apiclient/` contains fallback seed data. Even if backend endpoints or Python agents are offline, the frontend demo operates without crashing.
- **Strict Client Barrel:** UI components never call `fetch()` directly; they always import typed functions from `src/api.ts`.

---

## 2. Complete Map of the Working App (Where Everything Lives)

### Core Shell & Application Wiring
| Path | What Happens Here |
|---|---|
| [`src/App.tsx`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/App.tsx) | **Main Root:** Checks viewport; renders `MacDesktop` or `MobileApp`. Mounts screen, sidebar, modals, command cards, and quick cards. |
| [`src/screens.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens.ts) | **Screen Registry:** Central dictionary mapping route IDs to their component (`Sidebar` + `Main`). |
| [`src/types.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/types.ts) | **Single Type Authority:** Shared contracts for Chat, Messages, Trip Plans, Flights, Cleaner, Tasks. |
| [`src/store.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/store.ts) | **Global Reactive Store:** Screen state, active chat, messages, Mirsal tasks, email drafts, calendar events, theme & wallpaper. |
| [`src/shell/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/shell) | **Desktop Frame:** macOS window chrome (traffic lights, titlebar, dock, blur backdrop, navigation rail `Nav.tsx`). |
| [`src/mobile/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/mobile) | **Mobile Subsystem:** iPhone 17 Pro Max shell, `DynamicIsland.tsx` live activities, bottom `Sheet.tsx`, stories feed, and touch gestures. |

### Working Features & Screen Modules
| Feature / Screen | Path | Responsibilities & Details |
|---|---|---|
| **Chats & AI Assistant** | [`src/chats/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/chats) & [`src/ai/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/ai) | Messaging threads, voice notes, stickers, quoted replies, `@mirsal` assistant tags, interactive `TripPlan` cards. |
| **Voice Command Engine** | [`src/voice/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/voice) | Real-time speech/command orchestrator (`CommandCard.tsx`, `state.ts`). Connects via WebSocket to parse commands into UI actions. |
| **Updates & Tasks Tray** | [`src/updates/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/updates) | "Mirsal Updates" notification tray (`Tray.tsx`, `Collapsed.tsx`). Manages background agent tasks, Diwan events, and status cards. |
| **Quick Action Overlays** | [`src/quick/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/quick) | Flyout cards (`QuickCards.tsx`) that display flight search results or email drafts floating over any active screen. |
| **AI Cleaner & Detection**| [`src/screens/ai-cleaner/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/ai-cleaner) | Uploads images to clean AI artifacts (Resize, SDXL, Resize+SDXL). Polls progress checklist and outputs PSNR quality scores. |
| **Flights Workspace** | [`src/screens/flights/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/flights) | Airport autocompletion, route search, departure/return dates, interactive flight result cards. |
| **Mail & Compose** | [`src/screens/mail/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/mail) | Mail inbox, draft generator (e.g. vacation requests drafted by `@mirsal` trip planner), and compose view. |
| **Calendar** | [`src/screens/calendar/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/calendar) | Schedule planner, month view, event booking automatically wired from chat trip plans. |
| **Stocks & Market** | [`src/screens/stocks/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/stocks) | Real-time watchlist, market cards, percentage gainers/losers. |
| **Weather** | [`src/screens/weather/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/weather) | Direct Open-Meteo live integration with local forecast, hourly temps, and rain probabilities. |
| **Files & Documents** | [`src/screens/files/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/files) | Cloud file browser, photos search index, and document preview. |
| **E-Sign** | [`src/esign/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/esign) | Document signing canvas and verification state. |
| **Research & History** | [`src/screens/research/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/research) & [`src/screens/history/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/screens/history) | Deep research synthesis briefs, source link citations, and agent execution history. |
| **Profile & Settings** | [`src/profile/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/profile) | User modal, security preferences, theme toggler (Light / Dark / System), and desktop wallpapers. |

### API & Backends
| Layer | Path | What Lives Here |
|---|---|---|
| **Frontend API Barrel** | [`src/api.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/api.ts) | Public facade exporting all fetchers. Screens import from here only. |
| **Frontend Fetchers** | [`src/apiclient/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/apiclient) | Individual client fetchers (`cleaner.ts`, `agents.ts`, `chat.ts`, `flights.ts`, `photos.ts`, `weather.ts`, `stocks.ts`). |
| **Node Serverless API** | [`api/`](file:///g:/Haitham/VsCode/Mirsal-redesign/api) | Vercel serverless endpoints: `chat.ts`, `flights.ts`, `photos.ts`, `reply.ts`, `images.ts`, `videos.ts`. |
| **Python Agents Service**| [`agents/`](file:///g:/Haitham/VsCode/Mirsal-redesign/agents) | FastAPI backend on `:8787` (`run.py`, `mirsal_agents/`): Voice STT/TTS WebSocket, cleaner engine, fact checking, research. |

---

## 3. "Backend says: update this field or export" (The 4-Step Chain)

Whenever backend teams say: *"We changed a field in the response"* or *"We added a new export endpoint"*:

```
Step 1: src/types.ts               → Add/update the interface or property
Step 2: src/apiclient/<module>.ts  → Update request payload or response parser
Step 3: src/api.ts                 → Re-export the new function/type (if new)
Step 4: src/screens/<feature>/     → Update where JSX renders it
```

### Quick Scenarios:

1. **Backend renamed/added a field in a payload:**
   - Go to [`src/types.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/types.ts) (or module interface in `src/apiclient/`).
   - Rename/add the field on the interface.
   - Update the UI component rendering it in `src/screens/<feature>/`.
   - Run `npm run typecheck` — TypeScript will highlight any missed references.

2. **Backend added a new API endpoint:**
   - Create or update the fetcher function in [`src/apiclient/<module>.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/apiclient).
   - Re-export it from [`src/api.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/api.ts).
   - Import and call it inside the component: `import { yourFunction } from "../../api"`.

3. **Backend changed Chat / AI Plan format:**
   - Check `MessageBody`, `TripPlan`, or `PlanStep` in [`src/types.ts`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/types.ts).
   - Update message rendering in [`src/chats/`](file:///g:/Haitham/VsCode/Mirsal-redesign/src/chats).

---

## 4. Key Working Systems to Highlight in Your Interview

1. **Voice & Assistant Engine (`src/voice/` + `agents/`):**
   - Live duplex WebSocket (`openVoiceStream`) to Python agents service.
   - Translates spoken commands directly into UI state changes (e.g. booking flights, drafting emails, displaying task cards).
2. **AI Image Cleaner Pipeline (`src/screens/ai-cleaner/`):**
   - Multi-stage asynchronous job runner (`runCleanJob`).
   - Supports 3 modes (`resize`, `sdxl`, `resize_then_sdxl`), polls status, protects human faces, and displays final PSNR image quality metrics.
3. **Adaptive Dual-Shell Architecture:**
   - Single codebase automatically adapts between a 1920×1080 macOS glassmorphism desktop experience and an iPhone 17 Pro Max UI with Dynamic Island (`≤820px` or `?device`).
4. **Instant Verification:**
   - Run `npm run typecheck` to verify complete type harmony across frontend components and backend contracts.
