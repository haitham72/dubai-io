# Dubai-io Community — P1 audit (what actually exists)

**Status:** planned (revised to D1-D10) — awaiting founder approval. Branch `societal`. Docs only; no code built.
**Method:** four read-only subagent lanes (A code, B design/UX, C trust/safety, D evidence/demo) + lead verification. Every claim carries `file:line` or a URL. Founder decisions D1–D7 override the brief and spec wherever they disagree.

## Governing facts (re-verified, not trusted blindly)

- Community replaces Persocial; nothing is imported from it (D2, `docs/submissions/shared/founder-decisions.md:28`).
- Community is the Facebook-like app and builds **no messenger**. Its Inbox is notifications only (replies, mentions, group activity); "message this person" hands off to the Messenger later (D3, `founder-decisions.md:42`). The parked `chat_*` tables are not extended into a chat product.
- Memory is the rewritten **temporal_note** engine (`apps/memory/` on branch `memory`, package `temporal_memory`). It is not Hindsight or Honcho, and Hindsight's `MEM-01`/AC-1 gates do not apply (D5, `founder-decisions.md:55`). Community reaches memory only through the future `apps/api/app/memory_bridge/`.
- There is **no verified-JWT `user_id`** yet. That is shared B0 work on `contest-shared`; this plan only states needs in `identity-memory-needs.md`.
- Parked modules `apps/api/app/communities.py` and `apps/api/app/social_generation.py` and their tests are **read-only**. New backend goes in `apps/api/app/community/` with `cm_` tables; parked code may be imported, never edited.

## Test evidence (lead's own run)

There is no `.venv` in the societal worktree. Run from `D:\Vscode\dubai-io-societal\apps\api` with the main checkout's interpreter:

```
D:\Vscode\dubai-io\apps\api\.venv\Scripts\python.exe -m pytest -q tests/test_communities.py tests/test_social_generation.py
............................                                             [100%]
28 passed in 11.17s
```

Lane A independently ran the same command: `28 passed in 11.32s` (exit 0). Green means the parked demo behaves as its tests describe — nothing more.

## Lane A — code classification

Legend: **working/tested** = passing test in the two files above; **implemented but unverified** = code exists, those tests do not cover it; **mock/fixture** = seeded demo behaviour; **planned / not found** = absent.

All parked routes are wired into the main app (`apps/api/app/main.py:29`, `:68`) despite the "PARKED 9 Nov" label (`apps/api/CLAUDE.md:33`). No `app.community.server:app` (:8060), `apps/api/app/community/`, `apps/community/`, `apps/api/app/identity/` or `apps/api/app/memory_bridge/` exists yet.

| Area | Classification | Evidence |
|---|---|---|
| `GET /api/communities`, join/leave, `GET /api/feed` (new/top/hot, joined-first), stories, `POST /{id}/posts` (join-gated 409), post read, threaded comments, hide, chats, contacts, calls | working/tested + mock/fixture seed | `communities.py:168,186,197,207,239,275,298,313,341,364,413`; tests `test_communities.py:27,40,47,55,68,87,103,123,141,156` |
| `POST /api/votes` (±1 toggle), `GET /api/me/posts`, `GET /api/community/search` (ML hybrid) | implemented but unverified | `communities.py:630,665`; `ml_api.py:11`; no test references them |
| `social_generation.py` (no routes; `claim()` idempotency, owner-scoped `context()`, `generate()`, `respond()` writing `ai_demo` replies) | working/tested for mocked providers; mock/fixture in production behaviour | `social_generation.py:91,125,205,243,261`; header `:1` (fictional personas, never real members) |
| Recommendations / discovery / profile (`/api/recommendations`, `/api/discovery/places`, `/api/profile/*`, interests) | implemented but unverified for Community | `recommendations.py:373,379,387,393`, `discovery.py:100`, `profile.py:67,77,92,126`. Place-topic ranker and Quest hypothesis profile only — not a social profile or social-graph ranker |
| Actions registry + approvals (`prepare/approve/cancel`, `snapshot_hash`+`revision`, `Idempotency-Key`) | implemented but unverified (reusable infra); no Community capability registered | `actions.py:82,234,313,324,388,399,414` |
| Identity: anonymous cookie session owner; `auth.py` = Google OAuth **connections** only | implemented but unverified; verified JWT **planned / not found** | `actions.py:192,202,388`; `auth.py:65`; "Planned/absent" in `apps/api/CLAUDE.md:54` |
| In-branch memory `mem_*` (owner-scoped CRUD/forget, `provenance: inferred` hypotheses) | implemented but unverified; not the D5 target engine | `memory/schema.py:5`, `memory/api.py:16`, `memory/store.py:163`; `memory/api.py:83` returns hard-coded fixture pings (mock/fixture) |
| Post edit/delete, follows/friends, bookmarks, share, emoji reactions, notifications, moderation/report/block/mute, media upload, private-group roles/pins, people/group search, social profile CRUD | **planned / not found** | No decorators or code found; only a `MEDIA` filename allowlist at `communities.py:54` |

### Tables (all `CREATE TABLE IF NOT EXISTS` in code; no Supabase migration)

Parked DDL `communities.py:25`: `personas:26`, `communities:28`, `community_members:30`, `posts:32`, `comments:35`, `hidden_posts:38`, `votes:39`, `chat_threads:40`, `chat_messages:42`, `chat_reads:45`, `contacts:46`, `call_log:47`, `chat_archived:48`. `social_generation.py:18,23` adds columns and `social_generations`. Reusable neighbours: `recommendation_events/profile_interests/recommendation_runs` (`recommendations.py:105`), `episodes/profile_overrides` (`profile.py:35`), `user_profile/profile_facts` (`user_profile.py:46`), `mem_*` (`memory/schema.py:5`), `actions/sessions/preparations/approvals` (`actions.py:142`).

Seeded personas/communities/posts/comments are `provenance: demo_fixture` (`communities.py:124–138`, fixtures in `fixtures/community/*.json` or fallback `:58–73`); user posts `user_supplied:288`, AI replies `ai_demo` (`social_generation.py:261`). Member counts are `members_base + joined?1:0` (`communities.py:175`) — a fixture number that must render with a visible `Demo data` pill (root `CLAUDE.md` rule 2). Community text is untrusted and never becomes profile facts (`communities.py:5`).

### Spec P0 tables → existing schema

| Spec P0 | Verdict | Parked tables Community may read | New `cm_` tables needed |
|---|---|---|---|
| profiles | Partial — `personas` are fictional demo actors; `user_profile` is a Quest facts doc (no handle/bio/avatar/privacy) | both, read-only | `cm_profiles` |
| communities + memberships | Existing equivalent — but no public/private flag, moderators, pins | `communities`, `community_members` | `cm_` extensions for privacy/roles/pins; never alter parked |
| follows | Missing | — | `cm_follows` |
| posts | Existing — text + image-string only, no edit/delete | `posts` | edit/delete in new layer; `cm_media` link for real uploads |
| comments / reactions | Partial — threaded comments exist; `votes` is ±1 only | `comments`, `votes`, `hidden_posts` | `cm_reactions`, `cm_bookmarks` |
| media | Missing — allowlisted `media/*.jpg` names only | names only | `cm_media` (object storage, signed URLs, quotas) |
| notifications | Missing — chat unread counts are not notifications; D3 Inbox must be this | — | `cm_notifications` |
| moderation events | Missing — `hidden_posts` is per-owner hide; `harsh` is sentiment, "never a moderation verdict" (`apps/api/CLAUDE.md:83`) | hide state | `cm_moderation_events`, `cm_reports` |
| recommendation events | Partial — events exist but topics are places-only (`recommendations.py:20`), two-visit gate `:248` | `recommendation_events` | `cm_recommendation_events` or an adapter feeding the existing ranker social candidates + `Why this?` |

**May read, never alter:** every parked table above (`docs/submissions/CLAUDE.md:49,51`). All new writes go to `cm_` tables.

### What the 28 tests do not cover

`/api/votes`, `/api/me/posts`, chat read receipts, recommendations/discovery/profile/actions/auth/memory endpoints, any `cm_` behaviour, follows/notifications/moderation/media/bookmarks/reactions/edit-delete/private groups, live providers (all mocked), restart persistence, verified-JWT identity (fixtures use anonymous sessions via `/api/session`, `test_communities.py:17`).

**Bottom line:** the parked feed/posts/comments/join/hide/chat work as a tested single-owner demo with fictional AI neighbours. Everything that makes it a multi-user social network — real profiles, follows, notifications, moderation, media, social ranking, verified shared identity — is partial or not found and must be built new.

## Lane B — design authority (summary; detail in gap matrix)

- **"The last four social mockups" (spec conflict c) — ANSWERED (D9, 23 Nov).** No file carried that name; the phrase was prose in the spec (`02_…_PLAN.md:42`). The founder confirmed Lane B's inspected set: **layout/content** from the Higgsfield v3 frames — desktop `l01/l05/l08/l09`, phone `m02/m04/m08/m09` (`design/29-10-2026/INDEX.md:20,24,27,28,11,13,17,18`; `r/dubai` naming stripped, Stories dropped, `m04` = Messenger hand-off) — and **visual style** from `design/20-11-2026/` (canvas `#FFFFFF`/`#FAF8F5`, `INDEX.md:158-165`). Higgsfield is never used inside the product; the frames are references only. The earlier `apps/site` token fallback below is superseded as authority.
- Frozen reference `apps/web` has a working feed (`feed.js:13,27–32,68,124,189`, `social-ui.js:3,25,47`, `community.css:15,45,52,58` "Flat: borders, no shadows") — Reddit-like with stories and AI-persona replies. Community P0 defers Stories (spec `:37`) and never presents seeded personas as real activity.
- Reusable token values (copy values, note source): `apps/site/app/globals.css:4–15,21,56` (`--background:#fbfcfc`, `--foreground:#0b1b21`, `--accent:#0a9cc2`, `--line:#d8e4e9`, `--radius:14px`, `color-scheme: light`, "no shadows" `:1`); patterns `DemoPill`/`Provenance`/`SectionCard` (`apps/site/components/chrome.tsx:107,202`). Do not copy `apps/web/stage.css:21` `--shadow-card` (violates no-shadows).
- Must be original: branding, wordmark, icons, copy, tab iconography, Connected Memory page (no mockup found), group/search/empty/error/moderation surfaces. Strip `r/dubai` naming (phone frame `m08`). Light mode first; no shadows; no Meta/Facebook/Reddit marks.
- Tabs: Feed / Communities / Create / Inbox / Profile (spec `:43`); Discover is a feed lane (Following / Communities / Discover + chronological Following, spec `:23`), not a tab. Post cards: author → context → media → actions; AI subordinate as *Find relevant groups / Explain / Summarize / Draft reply / Why this?* (spec `:44–45`).
- **Gate:** no UI slice is done without founder visual review of a staged preview (`docs/submissions/CLAUDE.md:112`).

## Lane C — trust/safety verdict (summary; full table in gap matrix)

Parked code proves owner isolation and the approval-engine pattern. Private groups, moderation human path, minors handling, spam/fraud controls, and Community AI-publish approval **do not exist** and must be new `cm_` code. Top blockers: (1) private groups + report/block + spam controls absent; (2) minors policy undecided (founder ruling needed); (3) publish must register a new capability reusing the `actions.py` snapshot pattern — parked `social_generation` auto-replies (`ai_demo`) must never become the user-publish path.

## What exists vs what is missing (one view)

- **Exists, tested:** parked demo feed/posts/comments/join/hide/chat with fixture labelling; social-generation reply slots with idempotency and cross-owner non-leakage tests.
- **Exists, unverified:** votes, ML search, place recommendations, Quest profile hypotheses, approval engine, cookie identity, `mem_*` store.
- **Missing:** verified `user_id`, `memory_bridge`, `cm_` social core (profiles/follows/reactions/media/notifications/moderation/private groups), the four community agents as registered capabilities, `apps/community` web app, Connected Memory UI, multi-user evidence.
