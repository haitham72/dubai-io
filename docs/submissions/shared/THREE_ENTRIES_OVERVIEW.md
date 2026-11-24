# Three Entries Overview — Dubai Chambers Contest Portfolio

**Date:** 2026-11-23
**Status:** `ready for founder approval`
**Branch:** `contest-shared` (referencing `origin/main` @ `f016856`, `origin/memory` @ `fc2e24a` [latest `apps/memory` commit `602c8c3`], `origin/desktop` @ `d07ee53`, `origin/ios` @ `3b12997`, `societal` @ `317de4d`, `business` @ `4f7c675`)
**Memory baseline note:** `origin/memory` (`fc2e24a`) is the newest `temporal_note` (`apps/memory/`, package `temporal_memory`) branch on `origin` and is used as the memory contract reference until the other PC's `main` is pushed.

---

## 1. Portfolio Summary

All three Dubai Chambers *Create AI Agents Championship* entries share **one verified `user_id`** (`apps/api/app/identity/`) and **one authorised long-term memory engine** (`apps/memory/`, package `temporal_memory`, reached exclusively via `apps/api/app/memory_bridge/`), governed by `docs/submissions/shared/founder-decisions.md` (D1–D10) and `docs/submissions/CLAUDE.md`. Multiple entries are permitted (`docs/Researches/contest.md`). Internal milestone target: **Fri 18 Dec 2026** (via secure tunnel from the founder's PC, separate staging Supabase project, test with `>= 5` consenting adults per entry, D10); official submission: **Jan 2027** (English).

| # | Track | Entry | Reference Shape | Branch & Runtime Ports | Core Boundary (D1–D10) |
|---|---|---|---|---|---|
| 1 | **Best Personal AI Agent** | **Quest / Dubai-io** | ChatGPT-like personal memory companion | `main` + branches `memory`, `desktop`, `ios` · API `:8030`, `temporal_memory` `:8040` | Owns Know / Notice / Do personal assistant, Vault, Morning Brief, connectors; `handoff-temporal-note.md` covers `CR-TM-1..4` + 2 fixes (D10) |
| 2 | **Best Societal AI Agent** | **Dubai-io Community** | Facebook-like social network | `societal` (`317de4d`) · `apps/community/` + `app.community.server:app` (`:8060`) | Replaces Persocial (D2); **owns NO P2P messaging** (D3 — Inbox is notifications only + Messenger hand-off); **all ages with self-declared age gate** (under-18: zero cross-app personalisation, zero memory writes, D9); `v3-higgsfield` layout + `design/20-11-2026/` visual style (D9) |
| 3 | **Best Business AI Agent** | **Messenger** *(working name; O2 pending)* | WhatsApp-like AI messenger | `business` (`4f7c675`, M0 imported; `MG-B2` active) · `apps/messenger/` + `app.messenger.server:app` (`:8070`) | Rebranded from founder-authored redesign features (`github.com/haitham72/Mirsal-redesign`, 19 Nov AI workspace `6b45ba4`, D1/D4/D8); **owns ALL P2P messaging** + chat-to-action business agents; Builder/Higgsfield/Diwan/Nadi/watermark-cleaner dropped (D6–D8); founder packs + U²-Net any-subject cut-out stickers (D7/D8) |

---

## 2. Entry 1 — Quest / Dubai-io (Best Personal AI Agent)

- **Identity & Track Fit:** Personal AI agent for people who live and work in Dubai (`PLAN.md` §1). Built around three pillars: **Know** (temporal memory & sovereign vault), **Notice** (deterministic proactive cards & Morning Brief), and **Do** (task threads & approved external actions).
- **Differentiator:** Temporal entity-subject graph with explicit provenance (`"You told me"` vs `"I noticed …"` with two-visit qualification), fail-closed Rule 9 sensitive-category guard (`apps/api/app/lab/sensitive.py` & `temporal_memory/privacy/sensitive.py`), generation-fenced Forget-by-source (`privacy/forget.py`), and deterministic `ActionEngine` approvals (`apps/api/app/actions.py`).
- **Agentic Workflow:**
  1. Ingest consented personal sources (chat turns, Gmail, Calendar, manual WhatsApp `.txt` exports, Google Takeout, IDE/browser sessions) via `apps/api/app/lab/` and `temporal_memory`.
  2. Extract time-anchored facts and candidate hypotheses (`status="hypothesis"`), surfaced only with `Confirm / Edit / Not true / Forget`.
  3. Propose external side effects through registered `actions.CAPABILITIES` requiring one explicit user tap per action (Rule 6 / D15) and authoritative provider evidence before `Confirmed`/`Booked`/`Paid` (Rule 1).
- **Dependencies:**
  - Merging `memory`, `desktop` and `ios` into `main` (Entry 1 only; `societal` and `business` are never merged into `main`, D15).
  - Upstream `temporal_memory` hand-off (`docs/submissions/shared/handoff-temporal-note.md`: `CR-TM-1..4` + `vault.py:55-58` & `forget.py:147` fixes, D10).
  - Gate S (`apps/api/app/identity/` + `apps/api/app/memory_bridge/`) to replace hardcoded `"karim"` / anonymous cookie sessions with verified `user_id` and `owner-device` tokens.
  - Founder OAuth credentials (`GOOGLE_OAUTH_CLIENT_ID`, etc.) for live Gmail/Calendar connectors (`docs/status.md:43`).
- **Demo Criteria (`PLAN.md`, `ARCHITECTURE.md` §16):**
  - Surviving cases: DXB airport guide and lost item in a taxi (`PLAN.md:133`).
  - Live Google Places + Google Shopping AE with try-on, Memory "You told me" + "Because…" chips, task threads reaching honest terminal states (`draft`, `WAITING_USER`, `BLOCKED`, `UNKNOWN_STATUS`), and cross-app recall of consented memories from Community/Messenger after Gate S.
- **What is Real vs Fixture Today:**
  - **Real / working today:**
    - FastAPI + LangGraph pipeline (`apps/api/app/main.py:58-74,131`, `luna/`).
    - Deterministic `ActionEngine` (`apps/api/app/actions.py:222-360`) with snapshot hash, revision guard, and idempotency; manual tasks & projects (`tasks.py`, `projects.py`, SQLite-verified, `ARCHITECTURE.md:238-246,340`).
    - Live Google Places, Google Shopping AE (SerpAPI), Maps/weather (`apps/api/app/main.py:190-322`, `docs/status.md:28-31`).
    - Headless `apps/api/app/lab/` pipeline + two-layer fail-closed `sensitive.py` + S0–S5 eval (**154 passed** offline in CI across lab/memory/connector suites, `docs/status.md:15,19`).
    - Rewritten `temporal_note` engine on `origin/memory:apps/memory/src/temporal_memory/` (`models.py`, `api/app.py`, `api/vault.py`, `mcp/server.py`, `privacy/forget.py`, `live/context.py`).
    - Frozen reference PWA `apps/web/` untouched at `mobile-pwa-baseline-2026-10-23`.
  - **Fixture / unverified / absent today:**
    - **No verified cross-app `user_id`:** `apps/api/app/actions.py:386-393` uses anonymous cookie `dubaiio_lab_session` (`mode: anonymous_lab_session`); `apps/api/app/auth.py:65-120` binds Google OAuth connection grants to that cookie. Neither `origin/desktop` (`d07ee53`) nor `origin/ios` (`3b12997`) has user JWT auth — both default to client-editable `"karim"` (`origin/desktop:apps/desktop/electron/main/index.ts:43,55-61`; `origin/ios:apps/mobile/src/features/connect/connectApi.ts:7,27-38,62-70`).
    - `apps/api/app/identity/` and `apps/api/app/memory_bridge/` do not exist yet (built in B0).
    - Runtime DB defaults to local SQLite (`docs/status.md:37`); Postgres hosting/migrations unverified.
    - `laundry..maid.request` & `recovery.rta` are `BLOCKED` (`actions.py:82-92`); `order.request` uses sandbox `demo_fixture` merchants (`ARCHITECTURE.md:34`); `apps/api/app/connectors/` is mock-tested only (`docs/status.md:24`); `DEMO_MAIL=1` fixture mode (`docs/status.md:33`); `apps/site` UI paused 9 Nov (`CLAUDE.md:39`).

---

## 3. Entry 2 — Dubai-io Community (Best Societal AI Agent)

- **Identity & Track Fit:** Facebook-like social network for Dubai residents and communities (`societal` @ `317de4d`, `founder-decisions.md` D2–D3, D9): Feed (`Following`, `Communities`, `Discover`), profiles, posts/media, threaded comments, reactions, public/invisible-private groups, search, notifications Inbox, and moderation. Replaces Persocial (D2). Visual layout from `design/references/v3-higgsfield/` (`l01,l05,l08,l09`, `m02,m04,m08,m09`; `r/dubai` & Stories stripped) styled to `design/20-11-2026/` (D9).
- **Differentiator:** Measurable societal outcomes (helping newcomers find reliable local groups, verified public resources, and community events) with **strictly least-privilege AI & child safety**: Feed ranking reads *consented interest features only* (`InterestFeature` DTO) with a visible `Why this?` explanation — never raw chats, mail, Messenger text, sensitive categories, or family details — and under-18 accounts receive zero cross-app personalisation and zero memory writes (D9).
- **Agentic Workflow (`societal:docs/submissions/community/DELIVERY_ROADMAP.md` & `demo-script.md`):**
  1. **Discovery Agent:** Matches adult users to groups/discussions/events via consented `InterestFeature` signals + public community activity with `Why this?` explanation.
  2. **Community Answer Agent:** Retrieves allowlisted official public information pages (URL, publisher, `as_of`, `provenance`, no integration claim, plus a non-civic fallback, D9) and drafts cited answers; human approves exact revision/destination via registered `actions.CAPABILITIES` before publishing (Rule 6 / D15, zero official emblems per Rule 5).
  3. **Group Organizer Agent:** Summarizes authorized group discussions and proposes events/checklists — never autonomously posts or sends invitations (D14).
  4. **Moderation Copilot:** Flags spam/fraud/abuse/duplication with evidence for human moderators (with priority on reports involving minor-protected accounts, D9); never silently bans.
  - **D3 Messaging Boundary:** Zero P2P messaging or DMs in Community. Inbox holds notifications only; "Message this person" (`m04` chat hand-off) deep-links to Messenger after Gate S.
- **Dependencies:**
  - Founder Gate approval of `SHARED_MEMORY_CROSS_APP_CONTRACT.md` & `shared-slices.md` (`societal` P1 plan is ready @ `317de4d`; Community lead updates Q1–Q5 & sources UAE official child-safety/under-13 policy before `CM-B3`, D9).
  - Gate S (`CS-B1`..`CS-B5`) for multi-user verified identity (`CM-B5`), `InterestFeature` reads + Community→Quest attributed writes + Forget propagation (`CM-B8`), and cross-app Discovery (`CM-B9`). Core non-memory social slices (`CM-B2`..`B4`, `CM-B6`..`B7`) may start after Founder Gate (`DELIVERY_ROADMAP.md:137-142`).
  - Staging Supabase project + `apps/community/supabase/` Auth/RLS apply script + secure tunnel from founder's PC for `>= 5` adult tester demo by 18 Dec (D10).
- **Demo Criteria (`societal:docs/submissions/community/demo-script.md`, ≤ 4 min):**
  - **Scene A:** New resident selects public interests → Discovery Agent recommends Dubai groups with `Why this?` → user joins and comments.
  - **Scene B:** Same verified adult `user_id` signs in from Quest, enables *Cross-app interest-only personalisation* → Community feed re-ranks using permitted Quest interest without importing raw chat/mail/sensitive payloads.
  - **Scene C:** Community Answer Agent retrieves allowlisted public sources, drafts answer, user edits and taps **Approve exact revision + destination** → published post shows citations.
  - **Scene D:** Saving a discussion writes `"saved from Community, topic only"` → Quest recalls within scope → tapping **Forget** removes derived memory from both apps while keeping social posts intact. Seeded posts carry `Demo data` badges; fast-forwards carry `Demo trigger`.
- **What is Real vs Fixture Today:**
  - **Real / working today:**
    - `societal` (`317de4d`) holds the completed P1 plan pack (`10` docs under `docs/submissions/community/`).
    - Muse verified **28 passed in 11.17s** on the parked demo pair (`apps/api/tests/test_communities.py`, `test_social_generation.py`, `societal:audit.md:17-22`).
    - On `main` (read-only reference only, **never modified**), parked `apps/api/app/communities.py:168-680` (mounted `main.py:68`) and `social_generation.py` provide single-owner SQLite CRUD under anonymous `dubaiio_lab_session` (`communities.py:146-148`).
  - **Fixture / unverified / absent today:**
    - All seeded personas, communities, stories, posts, comments, calls, and chats in `communities.py:3-7,58-79,124-141,386-394,558` are single-owner `demo_fixture`. Parked `chat_*` tables are frozen and never extended (D3).
    - **Absent:** `apps/community/`, `apps/api/app/community/` (`cm_*` tables, `:8060` server), verified multi-user profiles/follows/private groups/moderation, self-declared `age_band` + under-18/under-13 guards, notifications-only Inbox + Messenger hand-off, all 4 AI agents as registered capabilities, and `memory_bridge` integration.

---

## 4. Entry 3 — Messenger (Best Business AI Agent; Working Name, O2 Pending)

- **Identity & Track Fit:** WhatsApp-like AI messenger built by rebranding founder-authored features from `github.com/haitham72/Mirsal-redesign` (current 19 Nov **AI workspace** design `6b45ba4`, D1/D4/D8) into a real multi-user messenger (`1:1`, small groups, media, founder-made static sticker packs + local U²-Net any-subject background-removal stickers per D7/D8) with chat-to-action business agents (`business:docs/submissions/messenger/DELIVERY_ROADMAP.md`, `demo-script.md`). Owns **all** P2P messaging across the portfolio (D3).
- **Differentiator:** Turns messy team group chats into cited decisions, tracked tasks, and explicitly approved external actions — without leaving chat or leaking private correspondence across threads or apps.
- **Agentic Workflow (`business:docs/submissions/messenger/demo-script.md` & `DELIVERY_ROADMAP.md`):**
  1. **Decision Keeper:** Extracts candidate decisions in consented work groups with exact quoted message attribution; requires human confirmation to make official.
  2. **Action Tracker:** Extracts candidate tasks, assignee, and due date with quoted message links (`mgmsg:<id>`); user approves exact `workspace.task.create` payload via `ActionEngine` (registered into `actions.CAPABILITIES` at import time, D15).
  3. **Project Brief Agent & Knowledge Assistant:** Produces cited "What changed since yesterday?" briefs and Q&A strictly scoped to `messenger:<conversation_id>` (plus opt-in private owner recall when enabled).
  4. **Consent & Sticker Guardrails:** Per-conversation AI mode (`Off / Session only / Save approved memories`, default `Off`), dual group consent checks, zero AI image/video/sticker generation (D7/D8), zero Builder service code/data/MCP (D6), Diwan/Nadi/watermark-cleaner dropped (D8), zero unauthorized E2EE claims.
- **Dependencies:**
  - **`MG-B1` & `MG-B2` approved now (D8):** `--squash` snapshot imported (`e7638e4` / `4f7c675`); `MG-B2` rebrand + exclusions active in `D:\Vscode\dubai-io-business`.
  - **Founder Gate (before `MG-B3`..`B9`):** Approve contract/slices; pick new product name (**O2** before `MG-B8`); founder writes to `createaiagents@dubaichamber.com` on prototype reuse (D10).
  - **Gate S (`CS-B1`..`CS-B5`):** Unblocks `MG-B3` (live two-user FastAPI WebSocket on `:8070` bound to B0 `user_id` + WS tickets), `MG-B5` (chat-scoped `memory_bridge` + Forget), `MG-B6` (`ActionEngine` approvals under verified `user_id`), and `MG-B7` (E2E).
  - Staging Supabase project + `apps/messenger/supabase/` Auth/RLS apply script + secure tunnel from founder's PC for `>= 5` adult tester demo by 18 Dec (D10).
- **Demo Criteria (`business:docs/submissions/messenger/demo-script.md`):**
  - Stage 1 (private usability): real two-user 1:1 and group messaging over WebSocket, attachments, founder static packs + U²-Net local cut-out sticker, conversation `Off/Session/Save` toggle, and two separate Forget controls ("Forget memories from this chat" vs "Delete chat").
  - Stage 2 (business pitch): consented project group → Decision Keeper → Action Tracker → explicit approval tap on `workspace.task.create` → cited Project Brief + denied cross-chat/third-user access check. Seeded threads carry `Demo data` badges; operator triggers carry `Demo trigger`.
- **What is Real vs Fixture Today:**
  - **Real / working today:**
    - `business` (`4f7c675`) has revised P1b docs (`2523d3d`), confirmed M0 (`faeaff7` / D8), and imported the `--squash` snapshot under `apps/messenger/` (`e7638e4` / `4f7c675`); `MG-B2` rebrand/drop edits are underway in `D:\Vscode\dubai-io-business`.
    - In the read-only redesign POC (`haitham72/Mirsal-redesign` @ `6b45ba4`, `business:docs/submissions/messenger/audit.md`): offline Python agent suite **200 passed, 1 skipped** (Redis), voice routing eval **113/113 dev + 32/32 holdout** (rules-based fake decider), retired `server/` suite **40 passed** with mocked providers, TypeScript `typecheck` passed, and React 18/Vite UI screens including the 19 Nov AI workspace exist on disk.
  - **Fixture / unverified / absent today:**
    - **Chat is 100% client-side fixture:** `src/store.ts:106` seeds `seedMessages` from `src/chats/data.ts`; sending appends to browser state only; **no server chat tables (`mg_*`), no multi-user WebSocket transport, no RLS, no E2EE**.
    - **Auth is demo-only:** `DEMO_KEY` cookie + untrusted override header (`x-messenger-user` after rebrand, not a verified Dubai-io user).
    - **Memory is scratch KV:** Redis/in-memory KV — NOT `temporal_note`.
    - **Business & sticker gaps:** `apps/api/app/messenger/` (`:8070` server, `workspace.task.create` capability registration, `memory_client.py`) and local U²-Net cut-out / founder packs (`apps/messenger/public/packs/`) are not yet built; Vite production build and live browser runtime unverified.
