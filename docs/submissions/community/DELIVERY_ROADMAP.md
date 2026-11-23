# Dubai-io Community — Delivery roadmap

**Status:** planned — awaiting founder approval (23 Nov 2026, Muse)

Build slices `CM-B1…CM-B12` in the spec's §8 order (A audit → B social core → C memory integration → D agentic demo → E polish). Owned files only: `apps/community/**`, `apps/api/app/community/**`, `apps/api/tests/test_community_*.py`, `apps/api/tests/fixtures/community/**`, `docs/submissions/community/**`. Parked `communities.py`/`social_generation.py` may be imported, never edited. Lane branches `cm/<slice-id>` from latest `societal`; lead merges after re-running gates. Slices marked **[waits: B0]** must not start until Gate S passes and `contest-shared` is merged into `societal` (check `docs/submissions/shared/log.md`). Every slice ships synthetic fixtures plus a happy-path and a failure-path test.

Baseline before CM-B1 (build brief §0): run the whole API suite once and record the pass count in `log.md`. P1 baseline for the parked pair, lead run 23 Nov 2026: `28 passed in 11.17s` (main-checkout interpreter; no `.venv` in this worktree).

## A — Audit (done in P1)

| Slice | Goal / owned files | Depends on | Tests (happy / failure) | Demo beat unlocked |
|---|---|---|---|---|
| CM-B1 Audit pack (this plan) | `docs/submissions/community/{audit,IMPLEMENTATION_GAP_MATRIX,DELIVERY_ROADMAP,identity-memory-needs,demo-script,sources,open-questions,log}.md` | — | Docs assertion: every claim has `file:line`/URL / founder gate rejects uncited claims | None — enables founder approval |

## B — Social core

| Slice | Goal / owned files | Depends on | Tests (happy / failure) | Demo beat |
|---|---|---|---|---|
| CM-B2 Social core API: profiles, follows, posts with edit/delete, comments, reactions, bookmarks | `apps/api/app/community/**` (`cm_profiles, cm_follows, cm_reactions, cm_bookmarks`), `apps/api/tests/test_community_core_*.py`, fixtures | CM-B1 approval; **not** B0 (cookie owner locally, verified owner swapped in at CM-B5) | H: create/edit/delete own post, threaded reply, reaction toggle after restart / F: non-owner edit 404, cross-post parent rejected | Scene A join + comment persistence |
| CM-B3 Groups: public/private, invite/approval join, moderators, pins, group search | `apps/api/app/community/**` (`cm_` group extensions), `test_community_private_groups.py` | CM-B2; founder answers Q2/Q3 | H: member reads/posts, moderator pins / F: non-member list/read/search/vote 404, invite-less join 403/404 | Scene A relevant-group join |
| CM-B4 Notifications + Inbox (notifications only, D3) | `apps/api/app/community/**` (`cm_notifications`), `test_community_notifications_*.py` | CM-B2 | H: reply/mention creates one deduped notification / F: duplicate event deduped; Inbox exposes no composer, fabricates no messaging | Inbox beat in Scenes A/C |
| CM-B5 Identity hookup **[waits: B0]** | `apps/api/app/community/**` owner resolution via `apps/api/app/identity/` only; `test_community_identity_*.py` | **B0 Gate S** | H: same verified `user_id` in Quest + Community / F: unverified/expired token 401, display-name merge refused | Scene B same-`user_id` badge |
| CM-B6 Media: object storage, signed URLs, quotas | `apps/api/app/community/**` (`cm_media`), `test_community_media_*.py` | CM-B2 | H: owner upload → signed read after restart / F: other user denied, expired URL fails, quota error honest | Post attachments in Scene A |
| CM-B7 Moderation + safety core: reports, block/mute, flag queue, human resolve/appeal, spam controls, sensitive gate wiring | `apps/api/app/community/**` (`cm_reports, cm_moderation_events`), Lane C test files (`test_community_moderation.py`, `…_spam_fraud.py`, `…_sensitive_gate.py`, `…_minors_third_party.py`, `…_isolation.py`) | CM-B2; Q2 minors ruling | H: report queues, human keep/remove/restore / F: model `harsh` flag never auto-hides/bans; sensitive variants store nothing | Trust beat behind Scene C |

## C — Memory integration

| Slice | Goal / owned files | Depends on | Tests (happy / failure) | Demo beat |
|---|---|---|---|---|
| CM-B8 Memory bridge integration: consented interest reads, scoped writes (saved discussions, joined groups, authored public posts with provenance), consent toggles, Forget | `apps/api/app/community/**` via `apps/api/app/memory_bridge/` only (never a new facts table); `test_community_memory_*.py`, `…_cross_app_leakage.py`, `…_forget_propagation.py`, `…_hypothesis_limits.py` | **B0 Gate S**; P2 contract | H: Quest interest (consented) re-ranks with `Why this?`; save → scoped Quest recall; Forget removes both / F: raw-text canaries absent from payloads; second user sees nothing; forgotten signal cannot resurrect | Scenes B + D |

## D — Agentic demo

| Slice | Goal / owned files | Depends on | Tests (happy / failure) | Demo beat |
|---|---|---|---|---|
| CM-B9 Agents: Discovery (`Why this?`), Community Answer (citations → approve exact revision+destination → post, registered capability), Group Organizer (proposals only), Moderation Copilot UI hooks | `apps/api/app/community/**` agents + capability registration at import; `test_community_publish_approval.py`, `…_d14_no_bulk_outreach.py`, `…_d15_one_approval_per_effect.py` | CM-B3, CM-B7, CM-B8 for cross-app Discovery (local-interest Discovery may start at CM-B3) | H: approved revision posts with citations / F: edited/switched destination 409 + zero posts; bulk invite 400 + empty outbox; two posts need two approvals | Scenes A (`Why this?`) + C |
| CM-B10 Web app: `apps/community` iPhone-first PWA (Feed/Communities/Create/Inbox/Profile + Discover lane + Connected Memory settings), token values copied from `apps/site/app/globals.css` noting source, light mode, no shadows | `apps/community/**` | CM-B2–B4 APIs; Q1 mockup confirmation; founder visual review per staged preview (blocking) | `npm test && npm run build` green / founder rejects preview → slice not done | All scenes on device |

## E — Polish / packaging

| Slice | Goal / owned files | Depends on | Tests (happy / failure) | Demo beat |
|---|---|---|---|---|
| CM-B11 Demo hardening: scenes A–D end-to-end ×3 without manual fix, restart continuity, two-user isolation suite green | `docs/submissions/community/**` runbook + test evidence in `log.md` | CM-B5, CM-B8–B10 | H: 3 clean runs / F: any manual fix or stale-cache resurrection restarts the count | Full ≤ 4-min demo |
| CM-B12 Packaging: 10-slide deck (English, stands alone), ≤ 4-min video, hosting or tunnel, multi-user test write-up | `docs/submissions/community/**` (+ deck/video assets under same folder) | CM-B11; internal target **Fri 18 Dec 2026** | Multi-user test (n ≥ 5) written up in `log.md`; citation URLs re-fetched 200 / any `Demo data`/`Demo trigger` unlabelled on stage blocks release | Submission, Jan 2027 |

## Gates for every merge (lead re-runs; a subagent report is not evidence)

1. `cd apps/api && .venv/Scripts/python -m pytest -q tests` (whole suite; on this PC use the main checkout's `.venv` interpreter until this worktree has one).
2. `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web && echo "apps/web untouched"`.
3. Own-commit scope: `git diff --name-only HEAD~1 HEAD` touches only `docs/submissions/community/**` (this P1 commit) — for build slices, only the slice's owned paths plus inherited `contest-shared` paths.
4. The entry app: `cd apps/community && npm test && npm run build` (from CM-B10).
5. Once `origin/pc2-main` exists: `git merge-tree --write-tree HEAD origin/pc2-main` must be clean; conflicts outside own paths stop and go to the founder.

No UI slice is done without founder visual review of a staged preview. Seeded posts are `Demo data`; triggers the user did not cause are `Demo trigger`. Never commit to or push `main`.
