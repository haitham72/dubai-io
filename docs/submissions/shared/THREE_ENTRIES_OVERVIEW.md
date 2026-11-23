# Three Entries Overview — Dubai Chambers Contest Portfolio

**Date:** 2026-11-23
**Status:** `draft — awaiting Community needs (P2 Part B)`
**Branch:** `contest-shared` (referencing `origin/main` @ `f016856`, `origin/memory` @ `fc2e24a` [latest `apps/memory` commit `602c8c3`], `origin/desktop` @ `d07ee53`, `origin/ios` @ `3b12997`, `societal` @ `cccf09f`, `business` @ `fc18129`)
**Memory baseline note:** `origin/memory` (`fc2e24a`) is the newest `temporal_note` (`apps/memory/`, package `temporal_memory`) branch on `origin` and is used as the memory contract reference until the other PC's `main` is pushed.

---

## 1. Portfolio Summary

All three Dubai Chambers *Create AI Agents Championship* entries share **one verified `user_id`** (`apps/api/app/identity/`) and **one authorised long-term memory engine** (`apps/memory/`, package `temporal_memory`, reached exclusively via `apps/api/app/memory_bridge/`), governed by `docs/submissions/shared/founder-decisions.md` (D1–D7) and `docs/submissions/CLAUDE.md`. Multiple entries are permitted (`docs/Researches/contest.md`). Internal milestone target: **Fri 18 Dec 2026**; official submission: **Jan 2027** (English).

| # | Track | Entry | Reference Shape | Branch & Runtime Ports | Core Boundary (D1–D7) |
|---|---|---|---|---|---|
| 1 | **Best Personal AI Agent** | **Quest / Dubai-io** | ChatGPT-like personal memory companion | `main` (and PC2 `main`: `origin/memory`, `origin/desktop`, `origin/ios`) · API `:8030`, `temporal_memory` `:8040` | Owns Know / Notice / Do personal assistant, Vault, Morning Brief, connectors |
| 2 | **Best Societal AI Agent** | **Dubai-io Community** | Facebook-like social network | `societal` · `apps/community/` + `app.community.server:app` (`:8060`) | Replaces Persocial (D2); **owns NO P2P messaging** (D3 — Inbox is notifications only + deep-link handoff to Messenger); reads consented *interest features* only |
| 3 | **Best Business AI Agent** | **Messenger** *(working name; O2 pending)* | WhatsApp-like AI messenger | `business` · `apps/messenger/` + `app.messenger.server:app` (`:8070`) | Rebranded from founder-authored redesign features (`github.com/haitham72/Mirsal-redesign`, 19 Nov AI workspace `6b45ba4`, D1/D4); **owns ALL P2P messaging** (1:1, groups, media, stickers) + chat-to-action business agents; Builder excluded (D6); founder static packs + local bg-removal stickers only (D7) |

---

## 2. Entry 1 — Quest / Dubai-io (Best Personal AI Agent)

- **Identity & Track Fit:** Personal AI agent for people who live and work in Dubai (`PLAN.md` §1). Built around three pillars: **Know** (temporal memory & sovereign vault), **Notice** (deterministic proactive cards & Morning Brief), and **Do** (task threads & approved external actions).
- **Differentiator:** Temporal entity-subject graph with explicit provenance (`"You told me"` vs `"I noticed …"` with two-visit qualification), fail-closed Rule 9 sensitive-category guard (`apps/api/app/lab/sensitive.py` & `temporal_memory/privacy/sensitive.py`), generation-fenced Forget-by-source (`privacy/forget.py`), and deterministic `ActionEngine` approvals (`apps/api/app/actions.py`).
- **Agentic Workflow:**
  1. Ingest consented personal sources (chat turns, Gmail, Calendar, manual WhatsApp `.txt` exports, Google Takeout, IDE/browser sessions) via `apps/api/app/lab/` and `temporal_memory`.
  2. Extract time-anchored facts and candidate hypotheses (`status="hypothesis"`), surfaced only with `Confirm / Edit / Not true / Forget`.
  3. Propose external side effects through registered `actions.CAPABILITIES` requiring one explicit user tap per action (Rule 6 / D15) and authoritative provider evidence before `Confirmed`/`Booked`/`Paid` (Rule 1).
- **Dependencies:**
  - Reconciliation of PC2 `main` (`origin/memory`, `origin/desktop`, `origin/ios`) with `origin/main` (founder merge).
  - Upstream `temporal_memory` HTTP contract additions `CR-TM-1..4` and security fixes (`api/vault.py:55-58`, `privacy/forget.py:147`).
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

- **Identity & Track Fit:** Facebook-like social network for Dubai residents and communities (`docs/submissions/shared/founder-inputs/02_DUBAI_IO_COMMUNITY_PLAN.md`, `founder-decisions.md` D2–D3): Feed (`Following`, `Communities`, `Discover`), profiles, posts/media, threaded comments, reactions, public/private groups, search, notifications Inbox, and moderation. Replaces Persocial (D2).
- **Differentiator:** Measurable societal outcomes (helping newcomers find reliable local groups, verified public resources, and community events) with **strictly least-privilege AI**: Feed ranking reads *consented interest features only* (`InterestFeature` DTO) with a visible `Why this?` explanation — never raw Quest chats, email bodies, Messenger text, sensitive categories, or family details.
- **Agentic Workflow (`02_DUBAI_IO_COMMUNITY_PLAN.md` §2):**
  1. **Discovery Agent:** Matches users to groups/discussions/events via consented `InterestFeature` signals + public community activity with `Why this?` explanation.
  2. **Community Answer Agent:** Retrieves verifiable public sources (with URL, `as_of`, `provenance`) and drafts cited answers; human approves exact revision/destination via registered `actions.CAPABILITIES` before publishing (Rule 6 / D15, zero official emblems per Rule 5).
  3. **Group Organizer Agent:** Summarizes authorized group discussions and proposes events/checklists — never autonomously posts or sends invitations.
  4. **Moderation Copilot:** Flags spam/fraud/abuse/duplication with evidence for human moderators; never silently bans.
  - **D3 Messaging Boundary:** Zero P2P messaging or DMs in Community. Inbox holds notifications only; "Message this person" deep-links to Messenger after Gate S.
- **Dependencies:**
  - Community P1 plan (`societal:docs/submissions/community/`) landing from Muse → folded into P2 Part B (`SHARED_MEMORY_CROSS_APP_CONTRACT.md`).
  - Founder Gate approval of `shared-slices.md` + Community `open-questions.md`.
  - Gate S (`CS-B1`..`CS-B5`) for multi-user verified identity, `InterestFeature` reads, Community→Quest attributed writes, and Forget propagation (core non-memory social UI slices may start after Founder Gate per `docs/submissions/CLAUDE.md:62`).
  - Hosting/staging Postgres RLS apply procedure for `apps/community/supabase/` SQL.
- **Demo Criteria (`02_DUBAI_IO_COMMUNITY_PLAN.md` §6–7, adjusted for D1/D3/D5):**
  - **Scene A:** New resident selects public interests → Discovery Agent recommends Dubai groups with `Why this?` → user joins and comments.
  - **Scene B:** Same verified `user_id` signs in from Quest, enables `allow_interest_export_to_community` → Community feed improves using permitted Quest interest without any private chat/mail/sensitive payload leaking into social API responses.
  - **Scene C:** Community Answer Agent retrieves cited public sources, drafts answer, and publishes only after explicit approval tap.
  - **Scene D:** Saving a discussion writes source-linked memory → Quest recalls within scope → Forget/revoke propagates immediately. Seeded feed items carry `Demo data` badges.
- **What is Real vs Fixture Today:**
  - **Real / working today:**
    - `societal` (`cccf09f`) holds planning briefs only (`docs/submissions/community/briefs/1-plan.md`, `2-build.md`).
    - On `main` (read-only reference only, **never modified**), parked `apps/api/app/communities.py:168-680` (mounted `main.py:68`) and `social_generation.py` provide single-owner SQLite CRUD under anonymous `dubaiio_lab_session` (`communities.py:146-148`).
  - **Fixture / unverified / absent today:**
    - All seeded personas, communities, stories, posts, comments, calls, and chats in `communities.py:3-7,58-79,124-141,386-394,558` are single-owner `demo_fixture` (`provenance: demo_fixture`). Parked `chat_*` tables are frozen and never extended (D3).
    - **Absent:** `apps/community/`, `apps/api/app/community/` (`cm_*` tables, `:8060` server), verified multi-user profiles/follows/groups/moderation, notifications-only Inbox + Messenger handoff, all 4 AI agents, registered `actions.CAPABILITIES`, and `memory_bridge` interest-only integration.

---

## 4. Entry 3 — Messenger (Best Business AI Agent; Working Name, O2 Pending)

- **Identity & Track Fit:** WhatsApp-like AI messenger built by rebranding founder-authored features from `github.com/haitham72/Mirsal-redesign` (current 19 Nov **AI workspace** design `6b45ba4`, D1/D4) into a real multi-user messenger (`1:1`, small groups, media, founder-made static sticker packs + local image background-removal stickers per D7) with chat-to-action business agents (`business:docs/submissions/messenger/DELIVERY_ROADMAP.md`, `demo-script.md`). Owns **all** P2P messaging across the portfolio (D3).
- **Differentiator:** Turns messy team group chats into cited decisions, tracked tasks, and explicitly approved external actions — without leaving chat or leaking private correspondence across threads or apps.
- **Agentic Workflow (`business:docs/submissions/messenger/demo-script.md` & `03_MIRSAL_AI_MESSENGER_PLAN.md` §2):**
  1. **Decision Keeper:** Extracts candidate decisions in consented work groups with exact quoted message attribution; requires human confirmation to make official.
  2. **Action Tracker:** Extracts candidate tasks, assignee, and due date with quoted message links (`mgmsg:<id>`); user approves exact `workspace.task.create` payload via `ActionEngine` (registered into `actions.CAPABILITIES`, D15).
  3. **Project Brief Agent & Knowledge Assistant:** Produces cited "What changed since yesterday?" briefs and Q&A strictly scoped to `messenger:<conversation_id>` (plus opt-in private owner recall when enabled).
  4. **Consent & Sticker Guardrails:** Per-conversation AI mode (`Off / Session only / Save approved memories`, default `Off`), dual group consent checks, zero AI image/sticker generation (D7), zero Builder service code/data/MCP (D6), zero unauthorized E2EE claims.
- **Dependencies:**
  - Execution of Messenger **P1b revisions** (`business:docs/submissions/messenger/briefs/1b-revise.md`) to apply D1–D7 across `business:docs/submissions/messenger/*`.
  - **Founder Gate:** Confirm M0 keep/exclude/rebuild file list before `git subtree add --prefix=apps/messenger <repo> master --squash` + immediate rebrand commit; pick new product name (**O2**); confirm organizer prototype-reuse check (`PLAN.md:174`); confirm staging Postgres RLS apply procedure for `apps/messenger/supabase/`.
  - **Gate S (`CS-B1`..`CS-B5`):** Unblocks `MG-B2` (real B0-authenticated FastAPI WebSocket on `:8070`), `MG-B4` (chat-scoped `memory_bridge` + Forget), and `MG-B5` (`ActionEngine` approvals under verified `user_id`). (M0 rebrand snapshot and static sticker packs / local bg-removal may proceed after Founder Gate M0 approval per `docs/submissions/CLAUDE.md:62`.)
- **Demo Criteria (`business:docs/submissions/messenger/demo-script.md`):**
  - Stage 1 (private beta usability): real two-user 1:1 and group messaging over WebSocket, attachments, static sticker packs + local background-removal user sticker, conversation `Off/Session/Save` toggle, and two separate Forget controls ("Forget memories from this chat" vs "Delete chat").
  - Stage 2 (business pitch): consented project group → Decision Keeper → Action Tracker → explicit approval tap on `workspace.task.create` → cited Project Brief + denied cross-chat/third-user access check. Seeded threads carry `Demo data` badges.
- **What is Real vs Fixture Today:**
  - **Real / working today:**
    - `business` (`fc18129`) holds P1 planning docs only (9 docs, pre-P1b); `apps/messenger/` and `apps/api/app/messenger/` contain zero code yet.
    - In the read-only redesign POC (`haitham72/Mirsal-redesign` @ `6b45ba4`, inspected in `business:docs/submissions/messenger/audit.md:11-40,76-99`): offline Python agent suite **200 passed, 1 skipped** (Redis at `tests/test_store.py:20`), voice routing eval **113/113 dev + 32/32 holdout** (rules-based fake decider, `audit.md:33-35`), retired `server/` suite **40 passed** with mocked providers (`audit.md:36`), TypeScript `typecheck` passed (`audit.md:37`), and React 18/Vite UI screens including the 19 Nov AI workspace exist on disk (`audit.md:78`).
  - **Fixture / unverified / absent today:**
    - **Chat is 100% client-side fixture:** `src/store.ts:106` seeds `seedMessages` from `src/chats/data.ts`; sending appends to browser state only; **no server chat tables, no multi-user transport, no RLS, no E2EE** (`audit.md:56,79,94-97`).
    - **Auth is demo-only:** `DEMO_KEY` cookie (`middleware.ts:1-2`) + untrusted override header (`audit.md:62,95`).
    - **Memory is scratch KV:** Redis/in-memory `facts:`, `tasks:`, `thread:` (`audit.md:58,85`, `identity-memory-needs.md:62-68`) — NOT `temporal_note`.
    - **Business & sticker gaps:** `workspace.task.create` is not yet registered in `actions.CAPABILITIES` (`actions.py:82-103`, `demo-script.md:9`); media generation defaults to fake and AI generation/Builder MCP are excluded by D6/D7 (`audit.md:83,86,106`); Vite production build and live browser runtime unverified (`audit.md:40`).
