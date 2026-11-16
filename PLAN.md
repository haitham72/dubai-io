# Dubai-io — Plan

**Updated:** 16 Nov 2026 · **Owner:** Haitham · State: [docs/status.md](docs/status.md) · Open requests: [docs/request-backlog.md](docs/request-backlog.md) · Active build: `apps/api/app/lab/CLAUDE.md`

The single plan: identity, founder decisions, scope locks, live rulings, contest facts, demo arc, pitch guardrails. Done work lives in git history; the previous version of this file is `git show main:PLAN.md`.

## 1. Identity (approved by the founder, 9 Nov 2026)

> **Dubai-io is a personal AI agent for people who live and work in Dubai. It gets to know you first — from the sources you connect (Gmail, Calendar, chats you export) — and shows you what it learned as evidence you can confirm or forget. Then it moves your life forward: each day it brings a few things matched to where you are heading, and when you hand it something, it runs it as a task thread to the end, stopping only at decisions that need you. It never claims what it can't prove, never acts without your tap, and never infers what is sensitive.**

**Three pillars:** **Know** (memory, reveal, people map) · **Notice** (daily matched cards and feeds) · **Do** (task threads, journeys, services as capabilities). The trust rules (`CLAUDE.md` 1–10) cut across all three. UI comes after the headless pipeline works.

**References:** Quest (new.quest) is the closest reference for Know and Notice — its experience, not its access methods (a cloud phone linked to the user's WhatsApp, residential proxies, unconfirmed inference of sensitive facts). Grok Bot is the reference for task threads.

**What it is not:** not a visitor or tourist app (visitor framing retired 22 Oct) · not a DubaiNow clone · not a services-only or shop app (services are capabilities inside Do) · not a social network (community parked 9 Nov; Persocial is a separate project).

## 2. Founder decisions log (newest first)

Only decisions still in force. Superseded ones stay in git history.

**16 Nov 2026 — memory design** (research, schema and numbers: `docs/Researches/memory-research-2026-11.md`)

Decided (founder, 16 Nov):
- **One memory service on Postgres (Supabase), every table keyed by `user_id`**, merging Mem0 (links between memories), Graphiti (a dated end for a fact), Hindsight (a verdict per new fact against the closest memories), the Quest tree (sections, topic and person files, profile) and the temporal_note engine. **The md tree is an export, not the store.** This settles the open Stage-2 engine pick of 8–9 Nov: no single engine is adopted.
- **About ten tables:** `sources, source_records, chunks, topics, memories, entities, links, followups, profile, alias_suggestions`. The main ones are `memories` (the full temporal capture) and `profile` (personality rows).
- **Topics:** a fixed list of main sections (10–15) with dynamic subtopics that agents can split, merge, add or remove; the seven life themes of 9 Nov stay the user-visible folders.
- **A correction never overwrites:** the old memory gets an end date and a pointer to the new one. Every memory keeps the message range it came from, so "forget everything from this chat" removes everything built from it.
- **End goals added:** (1) profile screens modelled on Quest's "What I noticed about you", "signature moves" and "Your People", with Confirm / Edit / Not true / Forget on every item; (2) a daily recommender under Notice: shared searches per topic, matched to each user's confirmed topics, pushed with a "Because…" reason, response feedback updates the weights. Cross-user signals stay aggregate-only with a visible opt-out (8–9 Nov); no user's memory is ever shown to or searched by another.
- **Queries the product needs:** by subject across years ("select flights"), by topic or person with counts, by date; the agent answers from these and may correct memory through the same write path.

Proposed, not yet approved:
- **Extraction:** chunks sized to the model and cut where the conversation changes (a day or a pause is not a boundary); one memory per fact with its time; the sensitive check runs on messages before extraction, not as one flag per chunk; follow-up questions resolved later by a second pass that may answer only from cited memories.
- **GraphRAG and a graph database: parked.** The `links` table keeps the door open; start only when a set of real questions fails on hybrid search plus links.
- **Sources:** YouTube history and Instagram analytics were requested; neither is in the IN list (activity data would be counted, not narrated). Gmail + Calendar and exported chats remain the IN sources.
- **Order of work** (one active item, no re-ranking until #1 is done): 1 a thin end-to-end slice on real data in Postgres · 2 the verdict step with end dates · 3 a minimal UI (progress bar, tree, ask box, Confirm / Forget) · 4 email · 5 one daily push for the real user from confirmed topics · 6 forget by source, demo data, pitch. The internal target stays Fri 18 Dec (§5).

**Open — positioning wording.** On 16 Nov the founder described the app as an "AI companion for Dubai visitors". §1 and the 22 Oct ruling say it is **not** a visitor or tourist app. Neither is edited here; settle it by editing §1.

**9 Nov 2026**
- Identity and pillars as §1.
- **Gmail + Calendar connectors first**, with the founder as a Google test user. Reverses "Google OAuth last" (21 Oct).
- **Rule 6 strict:** one explicit tap per side effect; no "Yes to all" batch approval. Auto / Ask / Learn modes stay rule-compliant: sends and shares always need a tap.
- **Memory folders are user-visible life themes:** Career · Learning · Projects · People & family · Events · Home & money · Travel. The residence ontology stays the fine tree underneath (`docs/superpowers/specs/2026-11-02-residence-ontology-tree.md`). Supersedes the 2 Nov UI-bot list and "user never browses folders".
- **WhatsApp only from manually exported chats** (WhatsApp's own Export chat). No linked device, Baileys or Evolution API, no automation of a personal account.
- **Community/social track parked:** code stays, not in the contest build. Personalised feeds stay under Notice.
- **UI work paused** while a headless pipeline is built in `apps/api/app/lab/` (guide: `apps/api/app/lab/CLAUDE.md`).
- **Persocial** is a separate, deprioritised project with its own repo. Never build its features into Dubai-io, or the reverse.

**8–9 Nov 2026 — memory engine** (package outside the repo: `%USERPROFILE%\Documents\Claude\Projects\proposals\memory-engine\`)
- **Staged engine:** the deterministic temporal_note port is the early layer; Mem0 or Graphiti takes over per user once there is enough captured history. The Stage-2 pick and its trigger are open.
- **Never-drop rule (§R-ND):** no idea is deleted by age; unrefreshed items lose 20–50% of their weight; a refresh resets the clock. App-layer, applies to every engine.
- **Cross-user learning:** aggregate-only, with a visible opt-out; per-user stores stay isolated; no cross-user retrieval.

**2 Nov 2026** (from docs/archive/root/cursor-plan.md) — residence-companion lock, still valid: not DEWA Jarvis, not a shop, not a DubaiNow clone; Services = a feature (cards → detail → approve → honest proof); "Because…" chips stay rare; the temporal_note *engine* (cloud-slim), never the founder's personal vault. Taxi / UAE Pass demos: no fake Paid / Filed. The UI-bot list (Lifestyle · Career · Social · Household · Money · Travel · Me) is superseded by the 9 Nov life themes.

**23 Oct 2026**
- **One React codebase** (`apps/site`) → website, desktop (Tauri/Electron), iOS/Android (Capacitor), with one central design system: a design change is one edit that echoes everywhere. Screens are ported from the original mobile app, as close as possible to it. Light mode first; dark = Graphite after. Wrapping the original as the phone app was declined.
- **`apps/web` frozen** at tag `mobile-pwa-baseline-2026-10-23`: the reference, never "classic"; embedded at `/?devices` with an Original ⇄ New toggle; retired only after parity and explicit founder approval.
- **Native iOS (Swift) STOPPED.**
- **Lock removal:** government/civic transactions, bill top-ups/payments, in-app donations and third-party purchasing are unlocked — only through a real registered adapter with per-action approval and verified provider evidence (rule 4). Without an adapter: show the blocker and an "Open official portal" link, keep the draft. Still locked: the DubaiNow look, fake statuses, invented facts, bidding.
- Dubai-io is the product; Mirsal-redesign is visual craft only. Behaviour target: Grok Bot + ChatGPT Dots + Claude Duet. Memory is modelled on temporal_note — copy the engine freely; the founder's personal data is never imported. Vault control dropped.
- **Cases that must survive:** DXB airport guide and lost item in a taxi.
- **Look:** white `#FFFFFF` / `#F6F7F8` + accent `#357F92`; soft haze only behind the home greeting/composer and onboarding; dark = Graphite `#141618` / `#1B1E21` / `#202428`, accent `#6FA9B8`. Quality bar: Feed is the benchmark screen; Services gets an uplift to Feed's level when ported.
- Unified-app decisions 1–11 (`docs/archive/plan/unified-app-design.md` §5) govern the UI when it resumes, except the Assistant ⇄ Community switch (community parked) and "worker/cron stays out": scheduler/outbox jobs are allowed under rule 8.
- **Real APIs, real users:** keys in local `.env` only, never committed; each newly keyed path shows real data or its honest unavailable state; a staging API and data set before any real user; fixtures never presented as real.

**22 Oct 2026**
- Visitor-companion identity rejected: Dubai-io is for everyday life and work in Dubai. Learn from Dots, Grok Bot and Duet.
- Adaptive suggestions evolve with recent activity and repeated, separated visits; never a constant feed or a permanent label inferred from one visit. Explicit current intent wins; influence is explained and the user can correct or pause learning (`docs/references/recommender-plan.md`).

**21 Oct 2026** — Supabase (PostgreSQL + pgvector, backend-only `dubaiio` schema) is the selected backend; SQLite stays the test/offline fallback.

**19 Oct 2026** — No shadows; chat looks like ChatGPT/Claude (plain AI text, tinted user box, white rounded action boxes). One order path through the server engine. Lost item (C6) = prefilled report + official handoff + honest "not recovered". No new service cases before submission. Live D-rulings: §4.

**13 Oct 2026** — Temporal profile is core: visible hypotheses with Confirm / Not true / Forget (`ARCHITECTURE.md` §7).

**10 Oct 2026** — No bidding, quotes or negotiation, ever. Fixed published prices; every service row opens its own sandboxed modal mini-app.

## 3. Scope

### IN (contest build)

- **The Know / Notice / Do pipeline**, headless first in `apps/api/app/lab/`: Gmail + Calendar connectors and chat-export import → consolidation into the life themes → reveal → people map → daily matched cards.
- **Task threads** that run a hand-off to an honest terminal state (draft, Waiting, Blocked or `UNKNOWN_STATUS` — never an unproven success), including the two surviving cases.
- **The shipped contest spine** (2 Nov; list in `docs/status.md`): live Google Places, Google Shopping AE with try-on, memory lite with "Because…" chips, Maps + Dashboard.
- Held until after submission: merchant onboarding from a price-list photo; new service cases (`docs/services/cases.md` is frozen).

### LATER

Civic RAG with citations · background geofencing · ticket wallet · media memory · Arabic RTL UI · live AR try-on · affiliate marketplace feeds. A broader audience does not automatically activate these features. (Unlocked 23 Oct by founder: resident bills + Salik/DEWA displays, payments and third-party purchasing, government transactions — each ships only behind a real adapter with verified evidence; no fake sends.)

Also out of the contest build for now: **community/social track** (parked 9 Nov; code stays) · **UI work** (paused 9 Nov until the headless pipeline works; when it resumes, no UI track is done without founder visual review of a staged preview) · native iOS (STOPPED 23 Oct).

### NEVER

Fake "Confirmed/Booked/Paid" · invented positions, belts, queues or prices shown as real · copying the official DubaiNow look · bidding / quote / price negotiation in any form.

## 4. Live D-rulings (19 Oct)

| # | Decision | Ruling |
|---|---|---|
| D14 | Merchant growth | Inbound opt-in; **AI cold-calling / bulk WhatsApp on HOLD** (UAE Cabinet Res. 56–57/2024; counsel sign-off required) |
| D15 | "Do the rest" autonomy | One explicit approval per side effect |

The other D-rows (D01–D13, D16–D18) are history: `git show main:PLAN.md`, §3.

## 5. Contest facts

Source: `docs/Researches/contest.md` (official page, last updated 15 Oct 2026). Archive a dated screenshot of the rules before submission.

- **Create AI Agents Championship** (Dubai Chambers). Four categories: Societal, Personal, Business, Youth (lead under 21). Our entry: **Best Personal AI Agent** — agents that "help people live better every day". Each category winner gets a USD 150,000 grant; one of them is also named Dubai AI Agent of the Year.
- **Timeline:** registration opened 7 Oct 2026 · build phase Nov–Dec 2026 · **January 2027: registration closes; submit the agent prototype + pitch deck + demo video** (day not stated) · January: 24 semi-finalists and the Tech Accelerator · March 2027: semi-final pitch day, 12 finalists · **Grand Final: first week of May 2027**.
- **Internal target: Fri 18 Dec 2026** — deck, demo video, hosting or tunnel, small user test.
- **Rules:** individual or team (max 6) · an original solution, not copied or taken from an existing repository · idea, prototype or early-MVP stage, not fully commercialised · must protect personal, confidential and organisational data and prevent leakage · English only · free to enter. **Finalists must present a fully functional, working agent live** — not an MVP.
- No published rubric; IP terms not stated (portal checked 19 Oct).
- **Service cases frozen until submission.** Try for one real merchant willing to answer on video before the May final (fallback: the labelled sandbox merchant). Hosting + domain by submission (fallback: local + tunnel).

## 6. Demo arc (9 Nov)

Connect Google (Gmail + Calendar) and import exported chats → the reveal → confirm two items → the people map → the next morning's matched card. Plus one task thread run to an honest terminal state.

Stage rules still apply: a trigger the user did not cause (such as fast-forwarding to the morning card) is labelled `Demo trigger` (rule 8); fixture data shows `Demo data` (rule 2).

The earlier visitor arc (late-night DXB arrival → laundry deadline → taxi-memory payoff) and its jury answers are in git history: `git show main:PLAN.md`, §3.

## 7. Pitch guardrails

- Say "it coordinates and follows through with your permission". Never "we replace Google/Careem/DubaiNow", and never claim a live government or partner integration that has no registered adapter and provider evidence.
- The on-stage difference from Quest (from docs/archive/Researches/CLAUDE-2026-11-09-quest-direction.md, 9 Nov): nothing about the user is hidden; no sensitive inference; forget by source ("Forget everything from this chat"); daily cards only from confirmed interests; approval before every side effect.
- Strongest evidence beat: 104,000+ items lost in Dubai taxis in 2025, including ~3,000 passports (official data, 9 Oct research). Claims from forums or unverified research are pitched as "reported", never as measured pain.
