# Dubai-io Community — log

## 23 Nov 2026 — Build waves 1+2 (Muse, D11 approved; adults only 18+)

**Preconditions met:** roadmap status `approved — 23 Nov 2026 (founder, D11)`. Gate S has **not** passed — no `identity/` or `memory_bridge/` in this tree, so CM-B5/CM-B8 were not started. Under-18 slices not built (D11). Baseline on the untouched tree: 409 passed + same 3 pre-existing failures (connectors scoping, 2 tryon — unrelated, no Community files).
**Wave 1 (CM-B2/B3/B4, commit `71b72a7`):** `apps/api/app/community/` (`__init__`, `store`, `routes`, `server`) + 3 test files + demo seed. Adults-only gate, private groups (invite→moderator-approve, owner-reversible log), notifications-only Inbox. Lead re-ran: 48 passed.
**Wave 2 — 4 parallel lanes, lead re-ran every gate:** CM-B6 `media.py` + `test_community_media.py` (+fixture): signed HMAC URLs, quotas. CM-B7 `moderation.py` + `test_community_moderation.py`: flags never hide, human keep/remove/restore + appeal, fail-closed sensitive + spam flagged-not-banned. CM-B9 `agents.py` + `test_community_agents.py` + `test_community_publish.py`: local-interest Discovery with `why_this`, Answer draft→approve-exact-revision (`community.answer.publish`)→post, Organizer proposals with zero outbound (D14), replay-once approvals (D15), allowlisted publishers. CM-B10 `apps/community/` Next.js preview: Feed/Communities/Create/Inbox/Profile, `DemoPill`, Inbox has no composer.
**Lead evidence:** community+parked suites 79 passed in one run; whole API suite 460 passed + the same 3 pre-existing failures (no regressions); `npm test` 9 passed + `npm run build` green (re-run). `app.community.server:app` serves 67 OpenAPI paths incl. all plugin routers. Note: this FastAPI version lists plugin routes under `_IncludedRouter` — route counts undercount; OpenAPI paths are the true check.
**Open:** CM-B10 is STAGED, not done — needs the founder's visual review of a staged preview. CM-B5/B8 wait for Gate S. CM-B11/CM-B12 next.

## 23 Nov 2026 — P1 revision to D1-D10 (Muse)

**Founder answers applied (D9/D10 on `contest-shared`):** Q1 visual authority = layout/content from Higgsfield v3 frames `l01/l05/l08/l09` + `m02/m04/m08/m09`, style from `design/20-11-2026/`, no Higgsfield inside the product. Q2 = **all ages with an age gate** (P1's adults-only recommendation superseded), with D9's under-18 protections re-planned into CM-B3/CM-B7/CM-B8 and a new pre-CM-B3 slice CM-B2C. Q3/Q4 = P1 recommendations accepted. Q5 = tunnel from the founder's PC, ≥ 5 consenting adults (D10), plus separate Supabase staging (`apps/community/supabase/`) and `FakeTemporalMemoryClient` naming. All docs' status lines now read `planned (revised to D1-D10) — awaiting founder approval`; Q1–Q5 marked answered in `open-questions.md`.

**Lane E (new, read-only): UAE child digital-safety sourcing.** Fetched official sources (u.ae, uaelegislation.gov.ae) for the Child Digital Safety Law (Decree-Law 26/2025), Cabinet Resolution 106/2026, Wadeema (3/2016), PDPL (45/2021) and reporting channels; full requirement map + proposed under-13 policy in `child-safety.md`. **Top finding: stop-and-ask.** Under-15s may not hold personal social-media accounts and parental consent cannot override it; self-declaration is not sufficient age verification. The lead independently re-fetched the u.ae Children's digital safety page and confirmed the under-15/under-13 wording. Adopted reading (flagged in `open-questions.md` as new blocking item **N1**, under D9's own "stop and ask" clause): the 18 Dec demo gates to verified 18+ adult testers — already D9/D10's tester ruling — and under-18 admission is deferred pending the founder's confirmations and legal advice on platform classification. No under-18 slice of CM-B3/CM-B7/CM-B8 may start until N1 is answered.

**Scope note:** the founder's D9/D10 answers were recorded in these Community docs (decision + what changed + blocked slices). `docs/request-backlog.md` was **not** edited: `docs/submissions/CLAUDE.md` forbids editing it from this branch.

## 23 Nov 2026 — P1 (Muse)

**What I checked**
- Branch verified: `git branch --show-current` → `societal` in `D:\Vscode\dubai-io-societal`. Read in order: `docs/submissions/shared/founder-decisions.md` (D1–D7, overrides the brief), root `CLAUDE.md`, `docs/submissions/CLAUDE.md`, the founder spec `02_DUBAI_IO_COMMUNITY_PLAN.md`, the ingest prompt (tasks A–F, Community only), the Messenger spec §4–5, `PLAN.md` §1–§5/§7, `ARCHITECTURE.md` §7/§9, `apps/api/CLAUDE.md`.
- Four read-only subagent lanes (A code audit, B design/UX, C trust/safety red-team, D societal evidence/demo/pitch), each given the §2 read-only list verbatim and "do not edit any file; do not switch branches; do not touch `apps/web`". Working tree stayed clean throughout (`git status` empty until the lead wrote these docs).
- Lead's own test run (no `.venv` in this worktree; main checkout's interpreter, from `apps/api`): `D:\Vscode\dubai-io\apps\api\.venv\Scripts\python.exe -m pytest -q tests/test_communities.py tests/test_social_generation.py` → **28 passed in 11.17s**. Lane A independently: 28 passed in 11.32s.
- Temporal_note checked on `origin/memory` (`apps/memory/README.md`, `src/temporal_memory/models.py` contract: `Owner`, `Record` with forget `generation` fence, `Fact` requiring `evidence`, provenance set). Neither `apps/api/app/identity/` nor `apps/api/app/memory_bridge/` exists here. Lead re-fetched the CDA 8th Social Survey (Government of Dubai Media Office) and confirmed "someone to rely on … 84%".

**What changed** (docs only, all under `docs/submissions/community/`)
- `audit.md` — what exists: parked demo working/tested (28 green), unverified neighbours, missing multi-user core; P0-table mapping with read-vs-`cm_` split.
- `IMPLEMENTATION_GAP_MATRIX.md` — every spec feature: evidence · reuse · missing · S/M/L · dependency · acceptance test, incl. Lane C's 13 proposed `test_community_*.py` files.
- `DELIVERY_ROADMAP.md` — slices CM-B1…CM-B12 in spec §8 order; B0-dependent slices marked **[waits: B0]**; packaging slices CM-B11/CM-B12 for Fri 18 Dec 2026. Status: `planned — awaiting founder approval (23 Nov 2026, Muse)`.
- `identity-memory-needs.md` — interest-feature reads only, scoped writes (saves, joins, own public posts), consent toggles, Forget. Aligned in shape with the Messenger's needs file so P2 can fold both into one contract.
- `demo-script.md`, `sources.md` — scenes A–D in ≤ 4:00 with `Demo data`/`Demo trigger` marks; official Dubai figures with URLs/as-of (two derived figures labelled derived; statistics-PDF fetch failure recorded); 3 outcome metrics; 10-slide deck outline.
- `open-questions.md` — 5 blocking questions (mockup identification, minors, private-group model, Scene C allowlist, packaging surface), each with recommendation, blocked slice, deadline.

**Top risks**
1. Identity and memory do not exist yet — Scenes B/D and slices CM-B5/CM-B8 wait on B0 Gate S; the plan never pretends the cookie owner is a verified `user_id`.
2. "Last four social mockups" is unconfirmed prose; Lane B's Higgsfield-v3 identification needs the founder's word (Q1) or UI fidelity is guesswork.
3. Minors, private groups, and moderation are undecided/absent, not small gaps (Q2/Q3; Lane C blockers).
4. Population series break (register-based recount) can silently corrupt a pitch chart if old/new figures are mixed; `sources.md` flags it.
5. Parked `social_generation` auto-replies (`ai_demo`) sit one import away from the publish path — CM-B9 must register its own capability and never reuse that path.

**Next:** founder gate (answer Q1–Q5, set roadmap status to `approved — <date>`), then P2 Part B folds `identity-memory-needs.md` into the shared contract. No build starts before that.
