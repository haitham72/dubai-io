# Mirsal — Submission 3: Best Business AI Agent

**Planning baseline:** 23 November 2026 · **Revised:** 23 November 2026 using actual public GitHub repository  
**Product type:** WhatsApp-style messaging app with original visual design and integrated agentic AI  
**Test audience:** Founder, mother, sister, and friends (voluntary private beta)  
**Business-category demo:** Real collaboration/coordination in a small team, powered by chat-to-action AI  
**Source of truth for pre-existing implementation:** [`haitham72/Mirsal-redesign`](https://github.com/haitham72/Mirsal-redesign), branch `master` (inspected 23 Nov 2026). Repository is accessible and contains a working *visual/agent POC*. It is **not** a real multi-user messenger. Code and asset ownership for contest reuse remain to be verified; public visibility alone does not establish IP rights.

## 0. Existing repository: verified code/design baseline

**Do not redesign or rebuild what already exists.** The GitHub repository contains substantial presentation/agent work. This classification is from code and documentation inspected via GitHub (not from running the app or its tests):

| Feature | Repository evidence | Status / limitations |
|---|---|---|
| Desktop and phone UI | `Mirsal-redesign.md`, `src/screens.ts`, `src/mobile/`, `src/chats/`, `src/updates/` | Designed and implemented as clickable layouts. Desktop has three zones; phone has iOS-style tabs, stories, Dynamic Island and voice island. Not a native app. |
| Chat experience | `src/chats/data.ts`, `src/store.ts` | Seeded contacts, conversations and media; messages held in client app state. **No confirmed cross-user send/receive, auth or server-side durable chat transport.** |
| AI voice / in-app actions | `agents/mirsal_agents/engine.py`, `agents/README.md` | Documented 14 actions with safe-recipient routing, meeting drafts and action traces. Offline evaluations reported 113 dev / 32 holdout passing, but current live cloud/audio and browser interaction unverified. |
| Chat skills and planning | `agents/mirsal_agents/skills/`, `ARCHITECTURE.md` | Fact check with sources, image choices, sticker pick/generation hook, trip/meeting planners, optional connector contracts; some actions use fixtures. |
| Sticker experience | `src/chats/MediaPanel.tsx`, `agents/mirsal_agents/sticker_builder.py`, `ARCHITECTURE.md` | Picker, demo packs, `.webm` playback, Mirsal Builder Library and MCP adapter; **live new-pack generator dependent on separate Builder service/configuration**. |
| Images and video | `api/images.ts`, `api/videos.ts`, `README.md` (API docs) | Demo fallback by default; actual provider calls require Higgs credentials, endpoint and paid settings. No verified end-to-end delivery between two users. |
| Workspace modules | `src/screens.ts`, `src/screens/*` | AI chat, flights, stocks, weather, mail, calendar, files, research, history, image cleaner; real/mocked features vary. Preserve modular workspace design. |
| AI memory | `agents/mirsal_agents/routes/memory.py`, `agents/mirsal_agents/store.py` | Simple agent facts/tasks in Redis or process memory. **Not Hindsight, not the seven-folder Markdown export, not common Quest/Community memory.** |
| Connectors | `ARCHITECTURE.md` | Gmail OAuth prepared; Diwan, Nadi and Mirsal Builder MCP contracts; weather/finance/research APIs. Configured/working vs fixture must be tested individually; no blanket live claim. |
| Test evidence | `README.md`, `agents/README.md` | Repo documentation reports 169 offline passes + 1 Redis skip and 10 additional cleaner tests. **Not rerun during this review.** |

**Existing visual authority:** [`Mirsal-redesign.md`](https://github.com/haitham72/Mirsal-redesign/blob/master/Mirsal-redesign.md) and the repo's `Slides/output_grid/` and `screens/` references, with 15 approved reference selections. Use them before changing layouts. The visual spec requires compact progressive-disclosure states (collapsed -> preview -> detail -> workspace), glass primarily on overlays, and **no chat reflow/cropping when the Mirsal Updates tray opens**.

**Reviewed foundation:** React 18 + TypeScript + Vite, Vercel `api/` functions, Python FastAPI agents + Redis, some PostgreSQL/pgvector for *photo search only*. Do not mistake that photo database for durable message storage or Dubai-io shared memory. Current repo default branch is `master`.

**Links:** [repo](https://github.com/haitham72/Mirsal-redesign) · [README](https://github.com/haitham72/Mirsal-redesign/blob/master/README.md) · [ARCHITECTURE](https://github.com/haitham72/Mirsal-redesign/blob/master/ARCHITECTURE.md) · [chat store](https://github.com/haitham72/Mirsal-redesign/blob/master/src/store.ts) · [seeded messages](https://github.com/haitham72/Mirsal-redesign/blob/master/src/chats/data.ts).

---

## 1. Product and pitch

**Product target:** Convert the existing Mirsal visual/agent prototype into a familiar, fast and reliable **real** messenger with 1:1/group messaging, rich media, custom AI stickers and images, consented AI recall, contextual agents, and selected utility workspaces. The essential experience is messaging—not an AI dashboard or just another chatbot. Preserve the working design and agent modules; validate rather than presume their live readiness.

**Personal beta:** The founder uses the app naturally with family and friends to validate onboarding, reliability, chat quality, media and creative tools. These are test relationships, **not business-user claims**.

**Business-contest pitch:** “An AI-powered communication workspace that turns messy group conversations into verified decisions, tasks, searchable knowledge and coordinated actions—without requiring users to leave chat.” A WhatsApp-like experience remains the primary UI. Demonstrate the business advantage with a separate opt-in project/team group.

**Submission caveat:** A family chat app with AI stickers is not, by itself, a strong *Business AI Agent* case. The judging narrative should demonstrate an actual work outcome: fewer missed action items, faster handoffs, source-backed summaries, and an approved task being created/completed.

**IP and permissions — blocker before external submission:** This idea/design has been discussed in connection with an app built at the founder's office. Determine who owns the implemented design, code, graphics, brand, and any extensions. Do **not** submit or reuse employer/client-owned assets or private chats without written authorization. If ownership is uncertain, develop a clean-room, independently owned MVP with original branding and assets. Contest entry rights require separate verification.

## 2. Core chat experience

### P0 — Convert the seeded chat POC into a usable messenger
- **Current gap:** `src/chats/data.ts` supplies demo contacts/messages and `src/store.ts` starts from `seedMessages`; these are not user accounts and cannot demonstrate actual communication across phones. Build the real transport/identity path separately, then replace seed data in authenticated production mode (retain explicit demo mode).
- One shared Dubai-io identity with Quest and Community (verified `user_id`), but independent app UI and session.
- Private 1:1 chats and small group chats; contacts/invites; owner- and membership-checked access; list/search chats.
- Text messages, edit/delete semantics, delivery/read states, typing indicator, presence where desired, attachments (photo, file), voice notes, emoji and sticker sending.
- Reconnect, pagination, offline queue/drafts, retry/idempotency, notification preferences and basic block/report controls.
- Media storage with signed access, content validation, upload limits, and deletion paths.
- Simple voice/video calling can be investigated as a P1 feature; do not pretend a call works if only the UI exists.

### P1 — “AI-powered everything” as contextual utilities
**Existing hooks to reuse before building new ones:** `@mirsal` chat skills (`factcheck`, `stickers`, `image_ideas`, `planner`), research pipeline, 14-action voice engine, image/video APIs, Mirsal Builder adapter, and the Updates tray. Validate live providers, permissions and actual message integration; avoid parallel implementations.
- **Contextual AI chat assistant:** An opt-in participant/panel accessible through a call/chat toggle, slash command or action menu; no automatic silent entry into private groups.
- **Summarize unread:** concise catch-up summary with linked message references and explicit scope (“this conversation, last 30 messages”).
- **Conversation search:** semantic retrieval with dates, senders, topic filters, and click-through to exact messages.
- **Smart reply and drafting:** optional suggested replies, translation, tone, spellcheck and rewrite; user taps Send.
- **Voice notes:** speech-to-text, optional translation and summary; treat transcription as unverified and show the original.
- **Memory-assisted recall:** “What laptop did I mention last week?” with source attribution and chat-scoped access; no unconsented cross-chat leakage.
- **Calendar/task extraction:** recognize *proposed* dates, decisions and follow-ups; create tasks/reminders only after user approval; don't treat a joke or third-party statement as an obligation.
- **AI images and stickers:** prompt-to-image, photo-to-sticker, text-to-sticker, variations, background removal, transparent export, sticker packs, saved media. Use licensed generation providers/models, permissioned uploads, safety checks, clear model failures, rate limits and spending caps.

### Business-specific agent features — P1 mandatory for contest
1. **Decision Keeper:** Find candidate decisions in an approved team chat; show who said what and when; ask a person to confirm before making them official.
2. **Action Tracker:** Extract candidate tasks, assignee and due date with quoted evidence; human confirms; create a durable workspace task and track its state.
3. **Project Brief Agent:** Generate a cited “What changed since yesterday?” brief across explicitly selected work groups and approved files.
4. **Knowledge Assistant:** Answer “What did we agree about Feature X?” using only accessible team chat and explicitly connected workspace docs, with direct source links.
5. **Approval Cards:** Propose an external action (e.g. send a project update or create a calendar event) and request a per-action approval; log effect, destination and evidence. No invisible sending.

## 3. UX and design

- **Primary design source:** the actual repo `Mirsal-redesign.md`, `Slides/output_grid/` and `screens/` (15 selected references), subject to verified reuse rights. Preserve the approved three-zone desktop architecture: narrow global rail, contextual sidebar and main workspace; and the iPhone layout with four tabs, stories, floating voice island and Dynamic Island-like activities.
- Preserve **Mirsal Updates** as compact stateful trays/cards; do not let them compress, crop or resize ongoing chat.
- Treat the visual prototype as a strong asset; do not replace it with a generic WhatsApp skin or recreate its components without first reviewing them.
- Familiar WhatsApp-like navigation, but original Mirsal visual language, icons, naming, layout and motion. Avoid copying protected app assets or claiming affiliation.
- **Proposed call/chat toggle (feature not confirmed built):** Chat screen top-right **Call** opens Caller view; the top-right becomes **Chat** to return. This is an additional interaction requirement, not evidence that the current demo has working calls.
- Caller view shortcuts: **Call / Contacts / Keypad / Favorites**, plus favorite contact shortcuts.
- Primary experiences: Chats, Conversation, Call, AI Actions, Sticker/Image Creation, Shared Tasks/Decisions, Profile & Privacy.
- Keep AI visually secondary until requested: chips, compact action menus and explainable cards inside the conversation. Ordinary chat performance and readability must remain excellent.
- On iOS, prioritize responsive touch targets and on-device notification consent; use web/PWA as the quickest initial testing surface, then assess native constraints. Desktop Electron may reuse the same API; don't assume the office desktop app is reusable without rights.

## 4. Shared memory architecture

**Critical distinction:** Mirsal stores actual *messages* in its own chat service; the central Dubai-io memory service stores carefully selected, source-linked *memories*. They are not the same database objects or permissions.

**One account:** Verified `user_id` is shared across Quest (Grok-like companion), Community (Facebook-like social) and Mirsal (messenger). No separate “Mirsal user profile” facts bank; messenger-specific settings can exist.

**Memory ingestion:** After explicit opt-in, the pipeline derives facts and candidate memories from the user's own messages, selected threads, attachments, and conversations. Messages from other people remain third-party content, not automatic confirmed facts about the account owner. For groups, don't send group content to a model or shared long-term memory without a transparent group policy and appropriate participant consent.

**Memory stages:** Raw source -> typed event -> cheap deterministic extraction -> model-derived candidate -> source/actor/time/scope attribution -> sensitive filters -> user-confirmed or appropriately labeled inferred memory -> Hindsight/PG. Periodic consolidation/supersession maintains temporal history. No LLM may directly mutate authoritative state or send a message.

**Cross-app usage:**
- Quest can use permitted Mirsal memories to help *the account owner*, never to expose private correspondence to third parties.
- Community can read only explicitly consented *general interest features*, never private chat text or social inferences about private contacts.
- Mirsal may use authorized Gmail, YouTube, Outlook, Chrome activity and WhatsApp exports **only through the shared connector/memory layer**, subject to provider/OS capability, OAuth permissions, per-source scopes and user review—not by covertly reading another app.

**Sources and reality checks:**
- Gmail: official Gmail OAuth, read-only scopes first; existing pipeline requires live configuration and acceptance testing.
- Outlook: Microsoft Graph with proper OAuth and permissions, or manual export until connector is verified.
- YouTube: authorized playlists/likes/uploads via supported API, historical watch activity via user-provided Google Takeout; no claim of blanket live watch-history API.
- Chrome: user-authorized browser extension, supported browser history integration or user-exported files; no secret collection of private conversations from third-party websites.
- WhatsApp: user-provided `Export chat` files only, per existing Dubai-io rules. Do not enable unofficial linked-device or message-scraping interfaces.
- Cross-source entity resolution needs explicit identity proof/confirmation; the same name is not sufficient.

**Memory viewer:** Provide seven category folders with chronological dated events, evidence and corrections: People, Career & Craft, Projects, Learning, Home & Money, Events, Travel. Markdown/Obsidian tree is an export/view from PostgreSQL; it does not become the writable source of truth.

## 5. Privacy, identity and chat trust

- Per-conversation AI participation and memory controls: **Off / Session Only / Save Approved Memories**. Default to private, no hidden ingestion.
- Distinguish sender visibility, group membership, memory owner, and data shared with external AI providers.
- Do not label the system **end-to-end encrypted** unless the full protocol has been implemented and independently assessed. E2EE chat and cloud AI require explicit design choices about local decryption and consent; don't weaken a claimed E2EE model silently.
- Enforce tenant/user access server-side, ideally RLS; log actions and corrections; revoke AI access and delete derived memories when source consent is withdrawn (subject to disclosed retention obligations).
- No automatic mailing, publishing, sending, joining groups, or sharing work documents. One meaningful explicit approval per external side effect, with the exact recipient/payload and an idempotency key.
- All testers opt in; minors or third parties are not silently profiled. Use synthetic fixtures for examples where consent cannot be obtained.

## 6. Technical boundaries and suggested components

- **Existing client (confirmed):** `haitham72/Mirsal-redesign`, React 18 + TypeScript + Vite web/PWA presentation code. **It is not an Electron project**. Reuse its `src/screens.ts`, `src/chats/`, `src/mobile/`, `src/updates/`, `src/voice/`, `src/ui/` components subject to ownership review. Preserve the current desktop/phone responsive interface; do not force a new framework.
- **Current API/agents:** Vercel `api/*.ts` functions + standalone Python FastAPI agents (with Redis), including chat skills, connector contracts, voice and research. Keep these APIs where useful; add a **separate authenticated real-time messaging transport** (Supabase Realtime/Postgres with RLS, or a justified WebSocket service). Do not confuse `/agents/voice` streaming with chat message transport.
- **Database:** the existing repo uses PostgreSQL/pgvector for its **photo metadata/search**, not for person-to-person chats. Add permissioned Postgres tables for users, contact requests, memberships, messages, delivery/read receipts, attachments metadata, tasks, approvals and audit. Object storage for media; enforce verified owner/member access and RLS.
- **AI:** reuse/extensibly adapt the **existing** Python agent engine (`agents/mirsal_agents/`) and TS image/video APIs. Wire `@mirsal` skills and approval flows to **authorized real messages** instead of seeded examples, with bounded context, provider gates and safe execution. For long-term memory, bridge/reconcile the current simple Redis/in-process store with **Quest's Hindsight `MemoryBackend` + `ScopeGuard`**, not another permanent facts bank.
- **Provenance:** source IDs, conversation/message IDs, author, timestamps, retrieval scope, trust tier, validity and confirmation history.
- **Operating costs:** quotas, size limits, on-demand generation, local Qwen extraction where appropriate, bounded context, and monitored image/voice inference spending. Keep no-Gemini restriction from the current project plan.

## 7. Live test design

**Stage 1 — family/friends beta (personal usability):**
- Invite the founder plus a small number of consenting relatives/friends. Test onboarding, account recovery, 1:1/group messaging, attachments, voice notes, stickers, and normal conversation.
- Turn AI and memory on selectively by user/thread. Verify users understand precisely which content can be recalled later.
- Test a natural example: a friend proposes a day to meet; AI suggests a reminder **for the user** and awaits confirmation. Do not create a third party's reminder without their consent.
- Test deletion/forget, accidental upload handling, reconnects, and one account logging into multiple devices.

**Stage 2 — business-category pilot (agentic value):**
- Create a permissioned, independent *test project group* with consenting participants and a real or realistic coordination task.
- Exchange messages about a feature request, ownership, deadlines and a design decision.
- Trigger **Summarize → Decision Keeper → Draft task → Approval → Task created → Evidence-backed progress report**.
- Demonstrate team-member-specific visibility and a denied access case.
- Record reproducible before/after measures, e.g. minutes needed to locate the decision, proportion of extracted actions validated by users, and number of necessary approvals. Report observations, not invented improvement percentages.

## 8. Acceptance criteria

- [ ] Two **real authenticated** users can reliably send, receive, edit/delete and retrieve messages across different devices; reload/restart preserves state; seeded `src/chats/data.ts` messages are never misrepresented as this test passing.
- [ ] A third user cannot query a private chat, attachment or its embeddings/memory.
- [ ] Real-time status, idempotent sends, offline retry and media permissions are tested.
- [ ] Summary and Q&A cite exact messages and never read beyond the caller's permitted scope.
- [ ] Existing Mirsal Builder/image APIs are exercised with real provider availability (or distinctly labeled fixture mode); AI images and stickers are generated, saved, transferred and displayed **between two accounts** end-to-end, with failure and quota reporting.
- [ ] AI cannot publish/send/create tasks or calendar entries without human confirmation of the exact effect.
- [ ] The existing `/agents/memory/*` simple Redis/in-process store is not mistaken for Hindsight; memory-derived facts persist in the shared service with source, time, actor, scope and correction/forget behavior across all three apps.
- [ ] Cross-source imports are only demonstrated where connector permissions/data are actually available; simulated data is labeled.
- [ ] Contest business demo produces a persistent, reviewable task and evidence-backed project summary.
- [ ] Written rights/approval for any office-origin code/design/assets used in submission, or proof of independently authored alternative.

## 9. Implementation order

**A. GitHub repo audit + IP rights** -> start with `haitham72/Mirsal-redesign` on `master` and inventory `src/`, `api/`, `agents/`, design screenshots and permissions. Preserve approved visuals and working modules, clarify rights before contest deployment. Classify docs-only tests vs personally rerun tests.  
**B. Real chat core / live beta** -> replace seeded data in authenticated mode with shared Supabase Auth identity, member-checked private/group chats, persistent messages, delivery receipts, real-time transport, attachments and reconnects; maintain isolated demo mode.  
**C. Connect existing creative/voice agents to real chats** -> reuse sticker picker/Builder hook, image/video endpoints, voice engine and contextual `@mirsal` skills. Verify paid connector settings and completion; persist/transfer generated assets between actual users.  
**D. Scoped memory** -> bridge the prototype's Redis/in-process facts/tasks to the established Quest Hindsight/PG API. Opt-in source-linked memory, explicit cross-app scopes, reversible ingestion, seven-theme Markdown export.  
**E. Business agent** -> action/decision extraction, approvals, task creation and audit.  
**F. Cross-product verification / contest package** -> multi-account tests, demo recording, privacy walkthrough, metrics and independent rights check.

**Guardrail:** Do not turn Mirsal into a Slack replica; retain the personal messenger UX and approved three-zone design while proving a business agent can coordinate work through chat. Treat repo documentation's reported tests as historical until rerun. No assumption that the public repo proves ownership or contest eligibility.
