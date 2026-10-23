# Unified dashboard plan — DRAFT, awaiting founder sign-off (23 Oct 2026)

Status: plan only. Do not implement until the founder signs off, starting with the scope decision in §1.

## 1. Scope decision (sign-off item #1)

Three candidate scopes were identified; the founder has not picked one. Recommendation: **B**.

| Scope | Audience | What it is |
|---|---|---|
| A. End-user Home | Daily user | Task/decision/briefing overview inside the product |
| **B. Founder ops (recommended)** | Founder only | Health, queues, content, funnel for running the daily-driver phase |
| C. Dev mobile-preview | Developer/LLM | Live client preview + contract/endpoint exerciser |

Recommended: build **B with an embedded mobile side view** (live PWA preview at phone sizes). Rationale: the journey from here is real APIs + real users + the founder daily-driving the app — the missing tool is an ops view (is the backend healthy? are jobs running? what is the funnel doing?), not another end-user surface. The mobile side view covers most of C's value (see §6). A stays out; end-user Home already exists in the PWA.

If the founder picks A or C instead, §§4–6 swap panels but the API/acceptance/slice structure below still applies.

## 2. Goals / non-goals

Goals: one screen answering "is everything working and what are users doing" — backend/infra health, Celery/ML job state, community/Reddit content + reports, website funnel events, client build/version status, and a live mobile side view. Founder-only, honest states (unknown shown as unknown, never green-by-default).

Non-goals: end-user features; moderation *actions* beyond queue visibility in v1 (hide/remove stay API-gated later); multi-user auth; hosted multi-tenant analytics; any direct database access from the dashboard (all reads go through the FastAPI backend, the ONLY backend).

## 3. Users and access

- v1: localhost-only, no login. A visible banner states it is a founder tool showing real usage data.
- Hosted later (explicit later slice): founder auth required before any hosted deploy; never a public URL.
- Privacy: no PII beyond what the backend already stores; the dashboard adds no new user-data collection except funnel step events (§5.4), which carry no free-text user content.

## 4. Layout

- Desktop-first grid (min 1280px): left column health + infra, center ML/jobs + content, right funnel + clients; mobile side view docked right (toggleable, 390/428 widths).
- Mobile side view is part of the dashboard, not a separate page: same session, same backend.
- Reduced-motion: instant swaps, no animated charts. Light/dark follows the existing tokens (cyan accent, no shadows).

## 5. Panels (each: purpose, source, cadence, states)

### 5.1 Backend & infra health

- Purpose: is the API, DB, broker and worker alive.
- Source: new `GET /api/ops/health` (aggregate: API uptime, SQLite/Postgres write probe, Redis ping on project port, RabbitMQ reachability, Celery worker heartbeat, last migration id). All fields carry `as_of`; unreachable dependency renders `UNKNOWN`, never fake green.
- Cadence: 15s poll, manual refresh; poll stops when tab hidden.
- States: ok / degraded (named dependency) / unknown; each dependency row names what was probed and when.

### 5.2 ML pipeline & jobs

- Purpose: Celery/RabbitMQ/Redis state, sentiment/toxicity classification counts, RAG query volume and fallback rate.
- Source: new `GET /api/ops/ml` (queue depths, active/failed jobs with safe failure categories, per-class counts over 24h/7d, hybrid-vs-keyword-fallback ratio for RAG search). Failed jobs link to job id + category, never to raw payloads with user text.
- Cadence: 15s poll.
- States: empty (no jobs yet) with "run a classification to populate" hint; honest `unavailable` when broker/worker unreachable.

### 5.3 Community/Reddit content & moderation

- Purpose: volume and safety of posts/comments/votes; report queue visibility.
- Source: new `GET /api/ops/content` (counts by community/state, votes cast, reports open/resolved, toxicity-flagged items pending review). Counts are recomputable from the DB, never invented.
- Cadence: 30s poll.
- States: empty communities show zero honestly; v1 has no action buttons (view + link to item only).

### 5.4 Funnel & usage events

- Purpose: website onboarding funnel (visit → signup → setup → first win → dashboard) drop-off, plus PWA/iOS feature usage counts.
- Source: new `POST /api/ops/events` (ingest: step name, surface, session ref, timestamp; no free text) + `GET /api/ops/funnel` (step counts, conversion between consecutive steps). Site instruments its funnel steps; PWA/iOS add counters later.
- Cadence: 60s poll.
- States: pre-instrumentation shows "no events yet" per step, not zeros presented as measured.

### 5.5 Client / release status

- Purpose: which client builds are current and against which backend contract.
- Source: static manifest committed in-repo (client, expected route set, contract version) + `GET /api/ops/health` backend version; the dashboard compares and flags drift. No auto-discovery that could silently pass.
- Cadence: on load + manual refresh.
- States: match / drift (named route or shape) / unknown.

### 5.6 Mobile side view

- Purpose: watch the real PWA while ops data updates beside it.
- Behavior: embedded live preview of the PWA at 390x844 and 428x926 (toggle), route switcher for the main surfaces (Home/Chat/Services/Feed), same backend session. v1 interactive (it is the real client); a read-only lock toggle is a later slice if the founder wants click-safety.
- Failure: if the PWA route fails to load, the panel shows the HTTP status, not a spinner forever.

## 6. API additions (all new, all read-only except ingest)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/ops/health` | GET | §5.1 aggregate |
| `/api/ops/ml` | GET | §5.2 aggregate |
| `/api/ops/content` | GET | §5.3 aggregate |
| `/api/ops/funnel` | GET | §5.4 aggregates |
| `/api/ops/events` | POST | §5.4 ingest (dedupe key, no free text) |

Rules: read-only endpoints take no side-effect params; every number carries provenance + `as_of`; failures return honest 503 with the named dependency, never empty-200 masquerading as healthy.

## 7. Frontend home (sign-off item #2)

Recommended: new `apps/dash/` static page served by the API (same origin, no new server, no new backend). Alternative: a route inside `apps/web` — rejected as default because the prototype must stay a clean mobile reference; a desktop ops grid inside it muddies that role. Either way: plain HTML/CSS/ES modules, existing tokens, no framework, no shadows.

## 8. Acceptance gates

- All five aggregates render with real data on localhost; each dependency failure renders its honest degraded/unknown state (verified by stopping Redis/worker and screenshotting).
- Poll cadences respected; hidden tab stops polling (verified in devtools).
- Reduced-motion + light/dark pass; 1280px layout with no horizontal scroll; side view toggles both phone widths.
- Backend: happy-path + failure-path tests per new endpoint (broker down, worker silent, empty tables); existing 227/11 suite stays green.
- No new top-level `*.md`; dashboard docs live here.

## 9. Slices (in order, each reviewed separately)

- S1: `/api/ops/health` + health panel + page shell. Gate: kill Redis, see honest degraded.
- S2: `/api/ops/ml` + jobs panel. Gate: failed job shows id + safe category.
- S3: `/api/ops/content` + content panel. Gate: counts match direct DB counts.
- S4: events ingest + funnel panel. Gate: site funnel steps appear end-to-end.
- S5: client status + mobile side view + polish. Gate: drift flag fires on a deliberate route rename in a scratch branch (reverted after).

## 10. Open questions for sign-off

1. Scope A/B/C (§1)?
2. Frontend home: `apps/dash/` vs prototype route (§7)?
3. Mobile side view interactive in v1, or read-only locked?
4. Funnel ingest from the PWA/iOS in v1, or site-only?
