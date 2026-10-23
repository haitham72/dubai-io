# Website rebuild brief — DRAFT, for the other LLM after founder sign-off (23 Oct 2026)

Status: plan only. This brief is handed to a separate LLM after the founder signs it off. That LLM works only in `apps/site/**`; it does not touch `apps/api`, `apps/web`, `apps/ios`, or `supabase`. Source log: `docs/request-backlog.md` ("Website redo").

## 1. Verdict and bar

Founder verdict on the shipped `apps/site`: absolute trash — static marketing bands, no onboarding funnel, no signup→first-win journey, no SaaS-grade polish. It stays in the tree only as a route/API-integration reference.

Rebuild bar: Apple.com-grade marketing craft (confident typography, generous space, large real image bands, restrained motion) fused with state-of-the-art SaaS onboarding (Linear/Stripe-grade motion and typography, guided setup, try-before-signup). Light/dark + reduced motion kept. No UI kit, no shadows.

## 2. Routes and sections

- `/` — hero showing the product in action (real app imagery, not abstract bands); benefit sections; social proof; pricing skeleton (ties to the SaaS licensing idea — skeleton only, no checkout); FAQ; footer.
- `/demo` — try-before-signup interactive moment against the real API (read-only operations only).
- `/signup` → `/setup` → `/first-win` → `/dashboard` — the onboarding funnel (§3).
- Signed-in web views reuse backend contracts; no invented backend behavior (see §5).

## 3. Onboarding funnel (the core deliverable)

signup → guided setup (areas, household, services) → first win (first task created + first decision surfaced) → dashboard. Requirements:

- Progress indicator, skips at every step, teaching empty states (never blank screens).
- Each funnel step emits a step event for drop-off measurement (event contract agreed with the backend owner before instrumenting; events carry step name + surface + session ref, no free text).
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

## 6. Acceptance gates (all must pass)

1. `npm run build` green; no new lint/type errors.
2. Funnel walkthrough passes end-to-end against the real API (signup → setup → first win → dashboard), with skips and failure states demonstrated.
3. Funnel step events observable for drop-off measurement.
4. Reduced-motion + light/dark pass at desktop and both phone widths.
5. **Founder visual review of a staged preview** — build-green is not design-accepted. Deliverable for review: staged preview URL + full-page screenshots of every route. This gate exists because the last pass failed it.

## 7. Handoff rules

- Work only in `apps/site/**`. Questions about backend behavior go to the founder, not to invented endpoints.
- Report: routes built, funnel walkthrough evidence, screenshots, and a NOT-VERIFIED list.
- Do not touch `apps/api`, `apps/web`, `apps/ios`, `supabase`, or any `*.md` outside `apps/site/` without being asked.
