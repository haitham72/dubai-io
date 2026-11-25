# CLAUDE.md — Dubai-io (contest build)

This monorepo contains Dubai-io (Personal), Community (Societal) and Messenger (Business): one entry per Dubai Chambers award track (Best Personal / Societal / Business AI Agent). Dubai-io is a personal AI agent for people who live and work in Dubai (identity: `PLAN.md` §1; contest strategy `PLAN.md` §2). See `PLAN.md` for scope and `ARCHITECTURE.md` for product and service boundaries. Repo: `github.com/haitham72/dubai-io` (private).

## Orient — read only what your task needs

- **Canon, in order:** this file → `PLAN.md` (identity, founder decisions, IN / LATER / NEVER, contest facts, demo arc) → `ARCHITECTURE.md` (contracts, state machine, memory §7) → `docs/status.md` (current state, run commands, keys). Open founder requests: `docs/request-backlog.md`.
- **Active build (17 Nov):** the headless Know / Notice / Do pipeline — guide `apps/api/app/lab/CLAUDE.md`.
- **Specs on demand:** `docs/docs-map.md` §4–5 says which spec to read for which piece.
- **Nested folder guides:** `apps/api/CLAUDE.md`, `apps/site/AGENTS.md`, `apps/web/CLAUDE.md` (frozen tree), `supabase/CLAUDE.md`, `design/CLAUDE.md` (read before any design frame), `docs/CLAUDE.md`, `docs/connectors/README.md`, `docs/services/intake.md`.
- **`docs/archive/` is historical** — don't read it unless the founder asks. Old versions of rewritten docs: `git show main:<path>`.

Do not read every doc up front. Nested `CLAUDE.md` files govern their folder; the rules below always apply. Done work lives in git history; this file stays a router.

## Non-negotiable rules

Founder instructions override anything below; sensitive categories (rule 9) are never inferred from third-party/ambient text and are stored only when the user explicitly states them or opts in.

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | inferred | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **Government/civic execution (unlocked 23 Oct, founder).** Salik, DEWA, RTA, Tasjeel, fines, police reporting and donations may execute only through a real registered adapter with explicit per-action approval and verified provider evidence — rule 1 still applies (no authoritative event, no success status). When no adapter exists, show the blocker and keep the draft; never a fake Send. No wait times unless measured.
5. **No official branding.** No DubaiNow layout, government emblems or ministry logos; never recreate the deleted DubaiNow-clone montage.
6. **Approval before side effects.** Sharing data with a merchant and sending a fixed-price order each need an explicit user tap on an approval card that lists exactly which fields get shared. Single approval only — there is no second quote approval because quotes do not exist.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given or visibly inferred.** Facts the user states are `user_supplied` and shown as "You told me". Inferences are only **hypotheses** (`provenance: inferred`, confidence, evidence, valid time), each listed under **"I noticed"** with Confirm / Edit / Not true / Lower, and require **two-visit qualification** (observed across at least two separated sessions/visits) before they personalise or re-rank anything. An unconfirmed hypothesis may re-rank options only, with a visible "Because…" chip. It never pre-fills a field, appears on an approval card, triggers a proactive message or sets a status. Nothing about the user is stored where they can't see it. **Family, faith/religion, and health** (along with ethnicity, nationality-as-trait, gender, sexuality, politics, and third parties' private matters) are **never displayed as plain facts** and **never inferred** (`apps/api/app/lab/sensitive.py` two-layer fail-closed filter) — they require explicit user confirmation before any card or profile surface may use them. Per D19 (25 Nov), item/source controls **Lower** weights to floor `0.01` (below the `0.10` active surface threshold, hiding them from unsolicited Chat and cards while keeping them visible in Memory Vault) rather than deleting; lowered items remain **100% callable** whenever the user explicitly triggers or queries them, and that explicit call adds back to their weight (clearing `lowered_at`). Account-level **"Delete my data"** removes data from external queries and Redis immediately while keeping an isolated de-identified backup for training as disclosed in FAQs. See `ARCHITECTURE.md` §7.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md` §5.

**Service execution:** prepare from confirmed facts → approval of the exact side effect → a registered adapter → provider evidence. When no adapter exists, show the blocker and keep the draft; never a fake Send. **UI:** no shadows; plain AI text, tinted user box, white rounded action boxes.

## Original mobile app and the UI (founder, 23 Oct; paused 9 Nov)

**Founder priorities (23 Oct; superseded for delivery, 24 Nov):** one central design system so a design change is **one edit that echoes everywhere**; every screen is ported from the original mobile app, as close as possible to it. Current delivery: Dubai-io uses `apps/mobile` (iPhone via Expo Go, website via Expo web) and `apps/desktop` (Electron); `apps/site` is paused. Finish the E0–E4 real-data round (`apps/memory/upgrade/prompts/`) before design polish.
**Light mode first**; dark (Graphite) comes after light is polished.

`apps/web` is the original mobile app — the reference, never labelled classic, old, legacy or stale. It must not be modified, diluted or retired without explicit founder approval. Check before every merge: `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`. Subagent briefs must forbid touching it.

**UI work paused 9 Nov** (design polish now follows the E0–E4 real-data round).

## Gates

- **NEVER remove, move, or delete Quest reference files:** `docs/plan/Memory/_archive/quest-memory-export/`, `docs/plan/Memory/_archive/quest-memory-export.zip`, `docs/plan/Memory/_archive/quest-tree-mechanics.md`, `docs/plan/Memory/_archive/hindsight-kb-export/`, and **`design/references/quest/`** (`cards.jpeg`, `connectors.jpeg`, `full memory md files.jpeg`, `people.jpeg`, `user summary.jpeg`) are permanent founder benchmarks and must **never** be deleted, moved out, or cleaned up by any agent.
- If a request needs something `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Don't build a "small version" of it.
- New service idea, shop or reference image: follow `docs/services/intake.md`; file under `docs/services/<shops|service>/<category>/`; never write a case into `PLAN.md`; stop if it touches a NEVER item.
- Never add top-level `*.md` beyond the four canon files: `CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `README.md`. Add agent guidance as nested `<dir>/CLAUDE.md` instead.

## Repo layout

```
apps/api/          FastAPI + LangGraph backend, tests/
apps/api/app/lab/  Headless Know / Notice / Do pipeline (extraction skills: chat, email, ide_session)
apps/mobile/       Dubai-io client: iPhone via Expo Go + website via Expo web
apps/desktop/      Dubai-io Electron desktop client
apps/memory/       temporal_note memory engine (guide apps/memory/CLAUDE.md; tracker apps/memory/upgrade/)
apps/community/    Community (Societal entry); mobile/ + desktop/ shells
apps/messenger/    Messenger (Business entry); mobile/ + desktop/ shells
apps/api/app/identity, apps/api/app/memory_bridge   shared per-user layer (all three products)
apps/site/         Paused Next.js client (UI paused 9 Nov)
apps/web/          Original mobile app PWA — FROZEN, the reference (tag mobile-pwa-baseline-2026-10-23), embedded at /?devices
apps/ios/          Native SwiftUI client — STOPPED 23 Oct (history only; iPhone is now apps/mobile in Expo Go)
scripts/           Local ingestion pipelines (Gmail 50k tokens, YouTube 4-feed, local browser history, dev sessions, two-tower)
supabase/          Migrations, local project config
docs/              Status, backlog, specs, services/
docs/archive/      Historical docs — not authoritative
design/            Screen references (founder files), locked Quest references (`design/references/quest/`), interactive demo mockups (`design/demo/`)
```

## Working conventions

- Keep founder requests and execution order in `docs/request-backlog.md`. Finish the active item before moving on; new messages refine or queue, they don't auto-replace the task. Log any reordering in-session.
- Every workflow ships with fixtures plus a happy-path and a failure-path test.
- Verify before claiming: run the touched area's tests (see folder guides). A partial slice is never "done".
- Validate generated content by assertion (counts, schema, loader, tests) — never re-read bulk output back into context.
- Never rotate, edit or expose credentials/keys without an explicit ask. Keys stay server-side.

## Contest submissions (all three products on `main`; decision D16, 24 Nov 2026)

All three products and the shared per-user layer live on `main`: Dubai-io (Personal), Community (Societal) and Messenger (Business). They share one verified `user_id` and one memory service (temporal_note).

| Track | Entry | Folder |
|---|---|---|
| Shared: identity, memory bridge, cross-app contract | — | `docs/submissions/shared/` |
| Best Personal AI Agent | Dubai-io | `apps/mobile`, `apps/desktop`, `apps/api`, `apps/memory` |
| Best Societal AI Agent | Dubai-io Community | `apps/community`, `docs/submissions/community/` |
| Best Business AI Agent | Messenger | `apps/messenger`, `docs/submissions/messenger/` |

Start every feature branch from `main`. The integrator verifies the applicable gates and merges finished branches into `main` (D16). Available agents: Gemini, Codex (half volume), Devin; Muse is unavailable. Read `docs/submissions/README.md` and `docs/submissions/CLAUDE.md` first: entry guides, owned vs read-only paths, gates, and the Messenger's IP and naming gate. Founder answers: `docs/submissions/shared/founder-decisions.md`. Rules 1–10 apply to every entry.
