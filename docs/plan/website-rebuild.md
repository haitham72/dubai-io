# Website rebuild brief — DRAFT, for the other LLM after founder sign-off (23 Oct 2026)

Status: plan only. This brief is handed to a separate LLM after the founder signs it off. That LLM works only in `apps/site/**`; it does not touch `apps/api`, `apps/web`, `apps/ios`, or `supabase`. Source log: `docs/request-backlog.md` ("Website redo").

## 1. Verdict and bar

Founder verdict on the shipped `apps/site`: absolute trash — static marketing bands, no onboarding funnel, no signup→first-win journey, no SaaS-grade polish. It stays in the tree only as a route/API-integration reference.

Rebuild bar: Apple.com-grade marketing craft (confident typography, generous space, large real image bands, restrained motion) fused with state-of-the-art SaaS onboarding (Linear/Stripe-grade motion and typography, guided setup, try-before-signup). Light/dark + reduced motion kept. No UI kit, no shadows.

## 2. Routes and sections

- `/` — hero showing the product in action (real app imagery, not abstract bands); benefit sections; social proof; pricing skeleton (ties to the SaaS licensing idea — skeleton only, no checkout); FAQ; footer.
- `/demo` — try-before-signup interactive moment against the real API (read-only operations only).
- `/signup` → `/setup` → `/first-win` → `/dashboard` — the onboarding funnel (§3).
- `/dashboard` is a handoff page, not an end-user dashboard: it confirms the first task and links into the PWA Home on the API origin (`/`). The site builds no Home/task overview of its own (`docs/plan/dashboard.md` §1 keeps end-user scope A out; that plan's dashboard is a founder ops tool, not this route).
- Signed-in web views reuse backend contracts; no invented backend behavior (see §5).

## 3. Onboarding funnel (the core deliverable)

signup → guided setup → first win (first task created) → dashboard handoff. Each step uses only the endpoint mapped below (verified on `main` 23 Oct 2026). A step marked GAP is not built by the site: it renders as a skippable step with an honest "Coming soon" state until the founder adds the contract.

| Step | Endpoint | Status |
|---|---|---|
| signup | `GET /api/session` (`apps/api/app/actions.py:388`): sets the `dubaiio_lab_session` cookie, returns `{user_id, mode: "anonymous_lab_session"}` | Exists. Anonymous session only; real accounts (Supabase Auth) are not built. Copy must not say "account created". |
| setup: area | `PUT /api/session/memory/area` (`apps/api/app/main.py:140`, body `{value}`, max 80 chars); stored as a "You told me" fact | Exists |
| setup: household | none (`FactKey` in `apps/api/app/luna/schema.py:25` has no household key) | GAP (founder open item) |
| setup: services | none (`/api/profile/interests` controls inferred interests; it does not record what the user states) | GAP (founder open item) |
| first win | `POST /api/tasks` (`apps/api/app/tasks.py:413`) | Exists |
| first decision surfaced | none (service Decisions are still pending per `PLAN.md`) | Cut from the funnel; the PWA handles it after handoff |
| dashboard | link to the PWA Home (§2) | No endpoint needed |

Requirements:

- Progress indicator, skips at every step, teaching empty states (never blank screens).
- Each funnel step emits a step event to `POST /api/ops/events` (contract owned by `docs/plan/dashboard.md` §5.4/§6; events carry step name + surface + session ref, no free text). The site does not instrument events until that endpoint is on `main` (see §6 gate 3).
- Failure at any step shows the honest state with retry; never a dead end or a fake success.

## 4. Design tokens and constraints

- Cyan accent; existing light/dark tokens; no shadows; restrained motion with reduced-motion instant fallbacks.
- Real, openly licensed imagery with attribution recorded; no placeholders presented as product, people, or venues.
- Responsive: desktop-first marketing, clean 390/428 rendering, no horizontal scroll.

## 5. Contracts (hard rules for the other LLM)

- The FastAPI backend is the ONLY backend. Every dynamic datum comes from a real endpoint with exact shapes (revisions, idempotency keys, provenance); client contract details live in `docs/references/ios-swift-plan.md` ("Web contracts").
- Never invent backend behavior, mock a success status, or present fixture/demo data without the Demo label.
- Status words (`Confirmed`, `Booked`, `Paid`, etc.) only from authoritative provider evidence, via the backend.
- Keys server-side only; nothing secret in client code or `.env` committed files.
- Call the API same-origin: add a Next.js rewrite `/api/:path*` → the Dubai-io API origin and default `API_BASE` to `""`. The API has no CORS middleware, so browser calls from `:3000` to another port fail, and the old default `http://localhost:8000` is taken by another app on the founder's Mac (verified 23 Oct).

## 6. Acceptance gates (all must pass)

1. `npm run build` green; no new lint/type errors.
2. Funnel walkthrough passes end-to-end against the real API using only the §3 endpoint map (signup → area → first task → PWA handoff), with GAP steps shown as honest skippable states, plus skips and failure states demonstrated.
3. Funnel step events observable for drop-off measurement. Blocked until `POST /api/ops/events` lands on `main` (`docs/plan/dashboard.md` §9 S4, or a standalone ingest slice the founder orders first). If it has not landed, the site still ships with this gate marked BLOCKED, not faked.
4. Reduced-motion + light/dark pass at desktop and both phone widths.
5. **Founder visual review of a staged preview** — build-green is not design-accepted. Deliverable for review: staged preview URL + full-page screenshots of every route. This gate exists because the last pass failed it.

## 7. Handoff rules

- Work only in `apps/site/**`. Questions about backend behavior go to the founder, not to invented endpoints. Any step not in the §3 map is a GAP to report, not a contract to improvise.
- Report: routes built, funnel walkthrough evidence, screenshots, and a NOT-VERIFIED list.
- Do not touch `apps/api`, `apps/web`, `apps/ios`, `supabase`, or any `*.md` outside `apps/site/` without being asked.

## 8. Open questions for sign-off

1. ~~Setup GAPs (§3)~~ Decided 23 Oct: the backend adds household + stated-services contracts before the rebuild starts; the two GAP rows become real steps once those land.
2. Event ingest order: land `POST /api/ops/events` as a standalone slice before the site rebuild starts, or let gate 3 stay BLOCKED until dashboard S4?
