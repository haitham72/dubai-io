# Docs map — every doc, one line, and what to do with it (9 Nov 2026)

**Paths in §5 are the pre-move locations.** Since 9 Nov the ARCHIVE/MERGE rows live under `docs/archive/` (scheme in `docs/archive/CLAUDE.md`).

Built from four parallel full reads (every line of 74 docs, ~1 MB: 62 tracked repo `.md`, 6 untracked `docs/Researches/*.md`, 6 in the external memory-engine package). Per-doc detail (purpose, identity claim, live content, conflicts) is in the four batch reports; this file is the merged decision view. **Founder decisions recorded 9 Nov** (identity approved; §3 rows 4–8 decided). Round 2 executes on branch `docs-cleanup-2026-11-09`.

## 1. The finding: the core never changed, the shell changed ~8 times

**Identity timeline (merged, chronological):**

| Date | What the app was declared to be | Source |
|---|---|---|
| 9–10 Oct | Visitor companion that "follows through with local merchants"; fixed prices, no bidding ever | `PLAN.md` |
| 13 Oct | Temporal profile is core; cyan look | `PLAN.md`, `ARCHITECTURE.md` §7, `visuals-libraries.md` |
| 19 Oct | Chat-first AI companion for people living in or visiting Dubai; D01–D18 rulings | `redesign.md`, `PLAN.md` §3 |
| 21 Oct | "Not a maps app — Dubai personal assistant"; native Swift authorised | `assistant-context.md`, `ios-swift-plan.md` |
| **22 Oct** | **Pivot: personal assistant for everyday life and work in Dubai; continuity, evidence and exact control; learn from Dots / Grok Bot / Duet; Gates A–F** | `personal-assistant-direction.md`, `assistant-review-decisions.md`, `implementation-plan.md` §0 |
| 23 Oct | "Daily social + assistant app" (community IN) → same day: one React app, temporal_note memory, iOS STOPPED, `apps/web` frozen, gov/payments unlocked behind adapters | `implementation-plan.md` banner, `unified-app-design.md`, `CLAUDE.md` |
| 26 Oct | Journey-first: KHDA, insurance, Mamzar as leading demos | `journeys.md` |
| 29 Oct | Website-first; threads grouped by product domain | `domains.md`, `desktop-full-load.md` |
| 2 Nov | "Grok-style residence companion"; UI bots over a fine ontology; Memory B; contest spine shipped | `cursor-plan.md`, `residence-companion-design.md` |
| 6 Nov | (external research, not adopted) desktop companion + AI browser | `Dubai-io_product evolution.md` |
| 8–9 Nov | Staged memory engine; never-drop weights (§R-ND) | memory-engine package |
| **9 Nov** | **Quest-like personal agent (know you → reveal → people map → daily matched cards) + Grok-like task threads; headless first** | `docs/Researches/CLAUDE.md` |

**Stable core — every batch agrees, unchanged since 22 Oct (rules since 10 Oct):**
- A personal AI agent for people who live and work in Dubai (the visitor framing died 22 Oct).
- **Two pillars were always there:** *memory* (temporal profile 13 Oct → temporal_note 23 Oct → Quest-style 9 Nov) and *task threads that finish things* (Grok/Dots/Duet 22 Oct → residence companion 2 Nov → Grok half 9 Nov). The 9 Nov direction is **memory promoted to the front**, not a new product.
- The LLM proposes; a deterministic, registered action engine executes. Truth in status, provenance on every number, approval before every side effect, `UNKNOWN_STATUS` over invented success, fixed prices / no bidding.
- Memory is visible and correctable; inferences are hypotheses that only re-rank; sensitive traits are never inferred.
- Proactivity comes only from the scheduler/outbox (dedupe, consent, quiet hours 23:00–07:00).
- Imported content (email, web, chats) is untrusted data. No shadows. `apps/web` frozen.

**What churned (the source of the confusion):** the shell (Today sheet → Tasks Home → Home|Chat|Services|Feed → domains → UI bots → Today|Goals|Memory), the audience (visitor → resident), the services emphasis, the community/social track, and native iOS.

## 2. Final identity — APPROVED by the founder, 9 Nov 2026

> **Dubai-io is a personal AI agent for people who live and work in Dubai. It gets to know you first — from the sources you connect (Gmail, Calendar, chats you export) — and shows you what it learned as evidence you can confirm or forget. Then it moves your life forward: each day it brings a few things matched to where you are heading, and when you hand it something, it runs it as a task thread to the end, stopping only at decisions that need you. It never claims what it can't prove, never acts without your tap, and never infers what is sensitive.**

Three pillars: **Know** (memory, reveal, people map) · **Notice** (daily matched cards and feeds) · **Do** (task threads, journeys, services as capabilities). Trust rules cut across all three. UI comes after the headless pipeline works.

## 3. Live contradictions (17 in the canon alone) — resolved by authority unless marked DECIDE

| # | Conflict | Resolution |
|---|---|---|
| 1 | Gov execution "never" (`api-catalog`, `intake.md` step 4, `api-authorization-outreach`, `implementation-plan` §0.8, `domains.md`, `cases.md` C1/C7) vs `CLAUDE.md` rule 4 unlock (23 Oct) | Rule 4 wins; fix wording in docs that stay |
| 2 | Payments/purchasing LATER (`api-catalog`, `cases.md`) vs 23 Oct unlock (`request-backlog`) | Unlock wins (adapters + evidence only) |
| 3 | Native iOS "client"/"un-parked" (README, `ARCHITECTURE` §12, `request-backlog`, `ios-swift-plan`) vs STOPPED 23 Oct | STOPPED wins |
| 4 | Google OAuth "last" (`implementation-plan` §0.4, backlog) vs Gmail-first memory (9 Nov) | **DECIDED 9 Nov:** reversed — Gmail + Calendar first (founder as Google test user) |
| 5 | "Yes to all" batch approval (`journeys.md`, `residence-companion-design` §2, `demo-journeys`) and Auto/Ask/Learn vs rule 6 single approval per side effect | **DECIDED 9 Nov:** rule 6 strict — one tap per side effect; remove "Yes to all" from docs that stay |
| 6 | Memory folders user-visible (9 Nov) vs "user never browses folders" (`cursor-plan`, 2 Nov) | **DECIDED 9 Nov:** visible |
| 7 | Folder/domain sets: 5 domains (`domains.md`) vs 7 UI bots (`cursor-plan`) vs 14-root ontology (`residence-ontology-tree`) vs Quest-style themes | **DECIDED 9 Nov:** visible life themes — Career, Learning, Projects, People & family, Events, Home & money, Travel; the ontology stays the fine tree underneath |
| 8 | Community/social feed track (IN since 23 Oct) vs absent from 9 Nov direction | **DECIDED 9 Nov:** parked — code stays, docs archived, not in the contest build; personalised feeds stay under Notice |
| 9 | Router "Plan 2 next" (`CLAUDE.md`) vs Plans 2–8 parked (`status`, `PLAN`, `handoff`) | Parked wins; rewrite router |
| 10 | Front door: `handoff.md` (`CLAUDE.md`) vs `cursor-plan.md` (`PLAN`, residence plan) vs `status.md` | `status.md` becomes the single state file |
| 11 | Three palettes: cyan `#0A9CC2` vs white + `#357F92` vs Graphite dark | `#357F92` wins (UI later) |
| 12 | `apps/site` "marketing site, DESIGN REJECTED" (README, `apps/site/README`) vs "THE app" | THE app wins; rewrite READMEs |
| 13 | Runtime: Supabase "in use" (`supabase/README`) vs `DATABASE_URL` blank → SQLite (2 Nov) | State SQLite in `status.md` |
| 14 | "Worker/cron stays out" (`PLAN`, `unified-app-design`) vs check-backs/routines (FIN-05..07) and daily cards | Scheduler/outbox jobs are allowed (rule 8); fix wording |
| 15 | §R-ND multiplicative decay with floor vs temporal_note linear decay to 0 vs recommender 90-day expiry | §R-ND wins (founder 9 Nov); open item P4 |
| 16 | `Temporal_profile-Plan.md` §15 WhatsApp via Baileys/Evolution vs manual export only (9 Nov) | Manual export wins; amend §15 |
| 17 | Top-level `.md` limit (4) vs 7 present (`handoff`, `handoff-ios`, `cursor-plan` extra) | Archive the 3 extras |

## 4. Target doc set (what any LLM reads after the cleanup)

**CANON — always read (≈6 docs + 1 new):** `CLAUDE.md` (router + rules 1–10 + gates, ~1 page) · `PLAN.md` (rewritten: identity §2 above + IN/LATER/NEVER + live D-rulings + contest dates) · `ARCHITECTURE.md` (contracts, refreshed) · `README.md` (short front door) · `docs/status.md` (single state file) · `docs/request-backlog.md` (open items only) · **new** `apps/api/app/lab/CLAUDE.md` (the headless pipeline plan, ≤1 page).

**SPEC — read only when working on that piece:** see tier `SPEC` below (memory interfaces, ontology, recommender, news rights, connectors policy, fixtures, task-thread scripts, contest rules, memory-engine package).

**GOV — nested folder rules, stay in place:** `apps/api/CLAUDE.md`, `apps/web/CLAUDE.md` (frozen tree — do not edit), `apps/site/AGENTS.md`, `supabase/*`, `design/**` (founder files — do not move), `docs/services/intake.md`.

**ARCHIVE — `docs/archive/` after the listed content is rescued; git history keeps everything; nothing deleted.**

## 5. Every doc

Tier: **CANON** · **SPEC** · **GOV** · **ARCHIVE** (rescue first where noted) · **MOVE** (other project). Batch = which reader mapped it (A/B/C/D).

### Root
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `CLAUDE.md` | 7 | 23 Oct | CURRENT (router stale) | CANON — rewrite router; keep rules 1–10, gates |
| `PLAN.md` | 29 | 2 Nov | PARTLY | CANON — rewrite around §2 identity; keep IN/LATER/NEVER, D14 (bulk-WhatsApp/AI cold-call hold, UAE Cabinet Res. 56–57/2024), D15, contest dates; archive visitor arc + superseded 22 Oct locks |
| `ARCHITECTURE.md` | 22 | 23 Oct | PARTLY | CANON — drop §12 (iOS), fix §1 shape, renumber dup §11–13; absorb rescues (§6) |
| `README.md` | 2 | 23 Oct | SUPERSEDED | CANON — rewrite (site = THE app, iOS stopped, real ports) |
| `handoff.md` | 42 | 2 Nov | PARTLY | ARCHIVE — rescue top block: founder non-negotiables, founder-supplied-keys list, hosting rec → `status.md`/`PLAN.md` |
| `handoff-ios.md` | 4 | 22 Oct | HISTORICAL | ARCHIVE |
| `cursor-plan.md` | 4 | 2 Nov | CURRENT to 2 Nov | ARCHIVE — rescue residence-companion lock line + UI-bot list → `PLAN.md` history / decision #7 |

### apps/, supabase/, design/
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `apps/api/CLAUDE.md` | 2 | 23 Oct | CURRENT | GOV — add 2 Nov modules (memory, mail, shopping, try-on) + `lab/` |
| `apps/ios/README.md` | 3 | 23 Oct | HISTORICAL | GOV in place (folder is history-only) |
| `apps/site/AGENTS.md` | 1 | 23 Oct | CURRENT | GOV (generated) |
| `apps/site/README.md` | 3 | 23 Oct | PARTLY | GOV — stale banner now; rewrite when UI resumes |
| `apps/site/public/IMAGE_LICENSES.md` | 7 | — | — | GOV |
| `apps/web/CLAUDE.md` | 1 | 23 Oct | CURRENT | GOV — frozen tree, never edit |
| `supabase/CLAUDE.md` · `supabase/README.md` | 1 · 4 | 23/22 Oct | CURRENT · PARTLY | GOV — README: state current runtime (SQLite fallback) |
| `design/CLAUDE.md` · `design/29-10-2026/INDEX.md` · `design/references/claude duet/README.md` · `design/references/v3-higgsfield/README.md` | 3 · 3 · 2 · 1 | 22 Oct–2 Nov | PARTLY / REF | GOV — leave `design/` alone (founder files); later: list missing folders, fold v3 into INDEX |

### docs/ (top, plan/, services/)
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `docs/status.md` | 2 | 2 Nov | CURRENT | CANON — refresh for 9 Nov; single state file |
| `docs/request-backlog.md` | 40 | 2 Nov | PARTLY | CANON — keep only the ~15 open items (batch C list); archive the 21–23 Oct ledger + duplicated block |
| `docs/implementation-plan.md` | 67 | 23 Oct | PARTLY | ARCHIVE — rescue §0 locks, Gate B/D/E/F, REC/SUG-01/EVT-01/ADS-01/CTX-02 contracts, DB-02, REV-01 (§6) |
| `docs/user-app-review-guide.md` | 10 | 22 Oct | HISTORICAL | ARCHIVE — honesty checklist (section B) → tests later |
| `docs/services/cases.md` | 21 | 21 Oct | PARTLY | SPEC — frozen until submission; fix gov wording + broken `redesign.md` link |
| `docs/services/intake.md` | 4 | 19 Oct | PARTLY | GOV — fix step 4 (rule 4) + step 5b (points into frozen `apps/web`) |
| `docs/plan/unified-app-design.md` | 16 | 23 Oct | PARTLY | ARCHIVE — rescue investigation loop, memory-port plan, decisions 1–11, palette numbers → `PLAN`/`ARCHITECTURE`/lab |
| `docs/plan/journeys.md` | 33 | 29 Oct | PARTLY | SPEC — the "Do" pillar's outcomes + sourced research; fix "Yes to all" per decision #5 |
| `docs/plan/dashboard.md` | 11 | 23 Oct | PARTLY | ARCHIVE — founder ops tool (S1/S2 built in `ops.py`); code is the truth |
| `docs/plan/calls-services-panels.md` | 10 | 23 Oct | PARTLY | ARCHIVE — rescue §4 services-expansion rules → `services/intake.md` |
| `docs/plan/domains.md` | 2 | 29 Oct | SUPERSEDED | ARCHIVE — input to decision #7 |
| `docs/plan/ios-upgrade.md` | 7 | 23 Oct | HISTORICAL | ARCHIVE |
| `docs/plan/review-prompt.md` | 2 | 23 Oct | HISTORICAL | ARCHIVE (spent prompt) |
| `docs/plan/website-rebuild.md` | 7 | 23 Oct | SUPERSEDED | ARCHIVE |

### docs/references/
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `assistant-context.md` | 9 | 21 Oct | PARTLY | ARCHIVE — rescue turn-context table, click-vs-statement rule, "Workspace data never feeds ads" → `ARCHITECTURE` |
| `assistant-design-interaction-review-prompt.md` | 10 | 22 Oct | HISTORICAL | ARCHIVE |
| `assistant-design-interaction-review.md` | 45 | 22 Oct | REFERENCE | ARCHIVE — Duet F1–F12 principles stay citable from archive (UI later) |
| `assistant-experience-plan.md` | 26 | 22 Oct | PARTLY | ARCHIVE — rescue RUN-01 worker rules, ATTN-01, decision-card states → `ARCHITECTURE` |
| `assistant-experience-review.md` | 81 | 22 Oct | REFERENCE | ARCHIVE — rescue §9.2–9.5 task state machine, revision write-guard, race/staleness matrix → `ARCHITECTURE` |
| `assistant-plan-review-prompt.md` | 6 | 22 Oct | HISTORICAL | ARCHIVE |
| `assistant-review-decisions.md` | 20 | 22 Oct | PARTLY | ARCHIVE — rescue Gate A–F acceptance, engineering qualifications, Gmail-connector contract (read-only, sender/thread validation, "an email is not proof") → `ARCHITECTURE`/lab |
| `personal-assistant-direction.md` | 19 | 22 Oct | PARTLY | ARCHIVE — rescue PA-03 four memory kinds, PC-01, §7 quality metrics → lab |
| `redesign.md` | 44 | 22 Oct | HISTORICAL | ARCHIVE — provenance of root design PNGs; repoint `design/CLAUDE.md` link |
| `api-catalog.md` | 13 | 21 Oct | PARTLY | SPEC — connectors + the only policy constraints (Places retention, WhatsApp Business templates/opt-in, telemarketing hold); fix gov/payments rows |
| `api-authorization-outreach.md` | 2 | 23 Oct | PARTLY | MERGE → `api-catalog.md` (founder-only provider contact rule) |
| `community-content-sources.md` | 3 | 23 Oct | REFERENCE | ARCHIVE (per decision #8) |
| `community-data-storage-plan.md` | 16 | 23 Oct | HISTORICAL | ARCHIVE (per decision #8) — "AI engagement never trains preferences", SSRF/EXIF rules stay citable |
| `external-review-prompt.md` | 3 | 23 Oct | SUPERSEDED | ARCHIVE |
| `ios-swift-plan.md` | 18 | 23 Oct | PARTLY | ARCHIVE — rescue endpoint inventory + FIN-08 contracts + hosting rec → `apps/api/CLAUDE.md`/`ARCHITECTURE` |
| `ios-web-agent-prompt.md` | 11 | 23 Oct | SUPERSEDED | ARCHIVE (spent prompt) |
| `reading-source-register.md` | 6 | 23 Oct | PARTLY | SPEC — news-card rights (metadata only, admitted publishers) |
| `recommender-plan.md` | 17 | 22 Oct | PARTLY | SPEC — daily-card ranker base (event ledger, decay, "Because…", variety slot) |
| `visuals-libraries.md` | 8 | 19 Oct | REFERENCE | ARCHIVE — repoint `PLAN.md` link |

### docs/superpowers/
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `plans/2026-10-23-unified-app-foundation.md` | 11 | 23 Oct | HISTORICAL (built) | ARCHIVE |
| `plans/2026-10-23-device-switch-and-phone-core.md` | 9 | 23 Oct | PARTLY (parked) | ARCHIVE (UI; recoverable) |
| `plans/2026-10-23-temporal-memory.md` | 8 | 23 Oct | PARTLY | SPEC — exact interfaces: extract, filter_sensitive, consolidate, salience, context_pack + 5 review gates |
| `plans/2026-10-29-desktop-full-load.md` | 2 | 2 Nov | HISTORICAL | ARCHIVE |
| `plans/2026-10-29-domains-website-light.md` | 1 | 29 Oct | SUPERSEDED | ARCHIVE |
| `plans/2026-11-02-residence-companion-mcp.md` | 14 | 2 Nov | PARTLY | ARCHIVE — rescue builder-MCP tool list → lab; open phases C–F → backlog |
| `specs/2026-11-02-residence-companion-design.md` | 12 | 2 Nov | PARTLY | SPEC — behaviour grammar, context-reuse/banned openers, 17-ask dogfood matrix (the "Do" eval) |
| `specs/2026-11-02-residence-ontology-tree.md` | 16 | 2 Nov | CURRENT | SPEC — fine memory tree + "user-stated only" leaves (never-infer list) |
| `specs/2026-11-02-demo-resident.md` | 2 | 2 Nov | PARTLY | SPEC — fixture person; fix: fixture facts are `demo_fixture`, not `user_supplied` |
| `specs/2026-11-02-demo-journeys.md` | 5 | 2 Nov | PARTLY | SPEC — five task-thread scripts with honest terminal states |

### docs/Researches/ (untracked)
| Doc | KB | Last | Batch status | Tier → action |
|---|---|---|---|---|
| `CLAUDE.md` | 19 | 9 Nov | CURRENT | CANON until promoted → then content moves to `PLAN.md` + lab, file archived |
| `contest.md` | 14 | 9 Nov | REFERENCE | SPEC — official rules + dates (note: four categories, not three lanes) |
| `persocial-intake.md` | 14 | 9 Nov | REFERENCE | MOVE → Persocial repo research |
| `Dubai-io_product evolution.md` | 20 | 6 Nov | REFERENCE | ARCHIVE — rescue threat model (read/recommend/act modes, kill switch, audit log) → `ARCHITECTURE` security |
| `Dubai-io iPhone integration.md` · `Dubai-io android integration.md` | 24 · 20 | 6 Nov | REFERENCE | ARCHIVE (no phone connector approved) |
| `quest - info/` | — | 9 Nov | private | Local only — never quoted, never committed (add to `.gitignore`) |

### Memory-engine package (outside the repo: `C:\Users\h.ibrahim\Documents\Claude\Projects\proposals\memory-engine\`)
| Doc | KB | Status | Tier → action |
|---|---|---|---|
| `README.md` | 4 | CURRENT | SPEC — entry point; staged mandate |
| `DECISION-BRIEF.md` | 13 | CURRENT (pending) | SPEC — swap contract §5 (frozen store interface), triggers §6; fix garbled §5.1 provenance list |
| `CONSOLIDATED-PLAN.md` | 15 | PARTLY | SPEC — §R-ND decay rule, checklist C1–C7 |
| `STATE-AND-GAPS.md` | 8 | CURRENT (snapshot) | SPEC — refresh before building |
| `decider-inputs/temporal_note.md` | 13 | REFERENCE | SPEC — salience / confidence formulas, `rrf_search` k=60 |
| `decider-inputs/Temporal_profile-Plan.md` | 18 | PARTLY | SPEC — target shape; amend §15 (no Baileys) |

## 6. Rescue list — content that exists only in a doc proposed for archive

| Destination | What moves there | From |
|---|---|---|
| `PLAN.md` | §2 identity; live D-rulings; founder non-negotiables; contest dates; 23 Oct lock-removal record; "no UI done without founder visual review" gate | `handoff.md` top, `request-backlog.md`, `unified-app-design.md` decisions, `cursor-plan.md` |
| `ARCHITECTURE.md` | Task state machine, revision write-guard, race/staleness matrix; RUN-01 worker rules; ATTN-01; decision-card states; turn-context rules; click-vs-statement; Workspace-data-no-ads; Gmail-connector contract; Gate A–F acceptance; threat model; DB-02 / REV-01 security | `assistant-experience-review.md` §9, `assistant-experience-plan.md`, `assistant-context.md`, `assistant-review-decisions.md`, `implementation-plan.md`, `product evolution.md` |
| `apps/api/CLAUDE.md` | Endpoint inventory; FIN-08 decision-card / brief / task-command contracts; hosting rec (Supabase + FastAPI container + Vercel) | `ios-swift-plan.md`, `handoff.md` |
| `apps/api/app/lab/CLAUDE.md` (new) | Headless build steps 0–6; PA-03 four memory kinds; PC-01 manual-input-first; quality metrics; builder-MCP tool list; investigation loop; links to every SPEC | `Researches/CLAUDE.md`, `personal-assistant-direction.md`, `residence-companion-mcp.md`, `unified-app-design.md` |
| `docs/services/intake.md` | Services-expansion rules (provenance on every entry, adapter or blocker + portal link, licensed charities only) | `calls-services-panels.md` §4 |
| `api-catalog.md` | Founder-only provider contact; keys local only; real data or honest unavailable | `api-authorization-outreach.md` |

## 7. Counts

74 docs · **CANON 7** (incl. new lab guide) · **SPEC 17** (11 repo + 6 memory-engine) · **GOV 13** · **ARCHIVE 35** · **MERGE 1** · **MOVE 1**. Active reading load drops from ~1 MB to roughly 120 KB of canon + specs read on demand.

## 8. After approval (round 2)

A second model pass, prompted from the founder's decisions: rescue §6 content into its destinations, rewrite the CANON docs, fix the contradiction wording in docs that stay, then `git mv` the ARCHIVE set into `docs/archive/` with a one-line `docs/archive/CLAUDE.md` ("Historical. Not authoritative."), tagged first (`docs-before-cleanup-2026-11-09`), on a branch, `apps/web` untouched.
