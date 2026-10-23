# CLAUDE.md — Dubai-io (contest build)

Personal assistant for everyday life and work in Dubai. Contest entry (Best Personal AI Agent). Repo: `github.com/haitham72/dubai-io` (private).

## Orient — read only what your task needs

| Task | Read |
|---|---|
| **Start of any session (23 Oct onward)** | `handoff.md` top section, then `docs/plan/unified-app-design.md` |
| Current plans (unified app) | `docs/superpowers/plans/` (Plan 2 next; roadmap table at its bottom) |
| Current branches, state, next work | `docs/status.md` |
| Backend/API work | `apps/api/CLAUDE.md` |
| Unified app (website + desktop + mobile, React) | `apps/site` + `docs/plan/unified-app-design.md` |
| Classic mobile demo (FROZEN) | `apps/web/CLAUDE.md` — read-only, tag `mobile-pwa-baseline-2026-10-23` |
| DB/migrations | `supabase/CLAUDE.md` |
| Scope locks (IN / LATER / NEVER), demo arc | `PLAN.md` |
| Architecture, contracts, state machine | `ARCHITECTURE.md` |
| Run-book, runtime notes | `handoff.md` |
| Ordered requests, backlog | `docs/request-backlog.md` |
| Design frames | `design/CLAUDE.md` first |

Do not read every doc up front. Nested `CLAUDE.md` files govern their folder; the rules below always apply. Done work lives in git history; this file stays a router.

## Non-negotiable rules

1. **Truth in status.** Never show `Confirmed`, `Booked`, `Paid`, `Filed`, `Verified` or `Delivered` without an authoritative event: a merchant action in the inbox or a verified adapter response. LLM text never changes status. Use `UNKNOWN_STATUS` before you would invent a success.
2. **Every number has provenance.** Prices, balances, ratings, dates and counts carry `provenance` (`official | provider_confirmed | merchant_submitted | user_supplied | inferred | estimate | demo_fixture`) and `as_of`. Fixture data renders a visible `Demo data` pill.
3. **No invented positions or facts.** The arrival guide never claims an indoor position, belt, gate or queue time the user didn't confirm. Map pins mark only user-confirmed places. Prices and times are labelled estimates.
4. **Government/civic execution (unlocked 23 Oct, founder).** Salik, DEWA, RTA, Tasjeel, fines, police reporting and donations may execute only through a real registered adapter with explicit per-action approval and verified provider evidence — rule 1 still applies (no authoritative event, no success status). When no adapter exists, show the blocker and keep the draft; never a fake Send. No wait times unless measured.
5. **No official branding.** No DubaiNow layout, government emblems or ministry logos; never recreate the deleted DubaiNow-clone montage.
6. **Approval before side effects.** Sharing data with a merchant and sending a fixed-price order each need an explicit user tap on an approval card that lists exactly which fields get shared. Single approval only — there is no second quote approval because quotes do not exist.
7. **Only registered actions execute.** A card action's `id` must match a capability ID in the registry. The agent fills in *data*. It never writes executable payloads, HTML, SQL or URLs to call.
8. **Proactive = deterministic.** Reminders and triggers come from the scheduler/outbox, not from LLM polling. Every one is deduplicated (`dedupe_key`), consented, respects quiet hours, and is stored as a normal chat message. A trigger the user did not cause is labelled `Demo trigger` on stage. The PWA does **not** do background geofencing.
9. **Memory is user-given or visibly inferred.** Facts the user states are `user_supplied` and shown as "You told me". Inferences are only **hypotheses** (`provenance: inferred`, confidence, evidence, valid time), each listed under "I noticed" with Confirm / Edit / Not true / Forget. An unconfirmed hypothesis may re-rank options only, with a visible "Because…" chip. It never pre-fills a field, appears on an approval card, triggers a proactive message or sets a status. Nothing about the user is stored where they can't see it. Health, religion, ethnicity, nationality-as-trait, gender, sexuality and politics are never inferred. See `ARCHITECTURE.md` §7.
10. **Widget sandbox:** provider HTML runs only from the separate widget origin, inside `<iframe sandbox="allow-scripts">`, with `connect-src 'none'`. It reaches the host only through the allowlisted `postMessage` bridge. See `ARCHITECTURE.md` §5.

**Service execution:** prepare from confirmed facts → approval of the exact side effect → a registered adapter → provider evidence. When no adapter exists, show the blocker and keep the draft; never a fake Send. **UI:** no shadows; plain AI text, tinted user box, white rounded action boxes.

## Frozen mobile demo (founder, 23 Oct)

`apps/web` must not be modified, diluted or retired without explicit founder approval. Check before every merge: `git diff --quiet mobile-pwa-baseline-2026-10-23 HEAD -- apps/web`. Subagent briefs must forbid touching it.

## Gates

- If a request needs something `PLAN.md` lists as **LATER** or **NEVER**, stop and ask. Don't build a "small version" of it.
- New service idea, shop or reference image: follow `docs/services/intake.md`; file under `docs/services/<shops|service>/<category>/`; never write a case into `PLAN.md`; stop if it touches a NEVER item.
- Never add top-level `*.md` beyond the four canon files. Add agent guidance as nested `<dir>/CLAUDE.md` instead.

## Repo layout

```
apps/api/   FastAPI + LangGraph backend, tests/
apps/site/  THE app: one React codebase → website, desktop app (Tauri/Electron), iOS/Android (Capacitor)
apps/web/   Classic mobile demo PWA — FROZEN (tag mobile-pwa-baseline-2026-10-23), embedded at /?devices
apps/ios/   Native SwiftUI client — STOPPED 23 Oct (history only)
supabase/   Migrations, local project config
docs/       Backlog, plans, references, services/
design/     Screen references
```

## Working conventions

- Keep founder requests and execution order in `docs/request-backlog.md`. Finish the active item before moving on; new messages refine or queue, they don't auto-replace the task. Log any reordering in-session.
- Every workflow ships with fixtures plus a happy-path and a failure-path test.
- Verify before claiming: run the touched area's tests (see folder guides). A partial slice is never "done".
- Validate generated content by assertion (counts, schema, loader, tests) — never re-read bulk output back into context.
- Never rotate, edit or expose credentials/keys without an explicit ask. Keys stay server-side.
