# Dubai-io Community — Founder questions

**Status:** planned (revised to D1-D10) — awaiting founder approval

Q1–Q5 were answered by the founder on 23 Nov 2026 in D9/D10 (`docs/submissions/shared/founder-decisions.md`, on `contest-shared`, merged into `societal` with this revision). They are recorded here as answered; nothing below blocks CM-B3/CM-B7/CM-B9/CM-B11 any more, except the under-13 sourcing duty in Answered Q2, which must complete **before CM-B3**.

## Already answered before P1 — not re-asked

- **Persocial:** Community replaces Persocial; nothing to import (D2).
- **Inbox boundary:** notifications only; Community builds no messenger; "message this person" hands off to the Messenger once shared identity exists; parked `chat_*` tables are not extended (D3).
- **Memory engine:** temporal_note via `memory_bridge/`; Hindsight/Honcho and their AC-1/MEM-01 gates do not apply (D5).

## Answered 23 Nov (D9/D10)

### Q1 — Visual authority — ANSWERED (D9)

**Layout and content:** the Higgsfield v3 Community frames in `design/references/v3-higgsfield/` — desktop `l01`, `l05`, `l08`, `l09`; phone `m02`, `m04`, `m08`, `m09`. Strip `r/dubai`-style naming; drop the Stories rail; `m04`'s private chat is a hand-off to the Messenger (D3).
**Visual style:** `design/20-11-2026/` (warm luxury white canvas `#FFFFFF`/`#FAF8F5`, `design/20-11-2026/INDEX.md:158-165`), the look the founder has moved the iOS app to, so Community reads as part of the Dubai-io family.
**Boundary:** Higgsfield is never used inside any product — the frames are design references only; no Higgsfield API, CLI, or generated asset ships in the app.
This supersedes the P1 assumption that token values come from `apps/site/app/globals.css`; those values remain a fallback note in `audit.md`, not the authority.

### Q2 — Ages — ANSWERED (D9): all ages, with an age gate (not adults-only)

- Age band is **self-declared at sign-up and never inferred**.
- **Under-18 protections by default:** no cross-app personalisation, no memory writes, private-by-default profiles, not discoverable or searchable by adults outside shared groups, moderation priority on reports involving them.
- **Duty before CM-B3:** source the UAE's official child digital-safety and child-data requirements (parental consent, any minimum age) and propose the under-13 policy — see Lane E findings in `child-safety.md`. If a requirement cannot be met by 18 Dec, stop and ask.
- Multi-user testers are consenting adults (also D10).
The P1 recommendation of adults-only launch is **superseded**.

### Q3 — Private groups — ANSWERED (D9, P1 recommendation accepted)

Private groups are invisible to non-members. Members invite; a moderator approves. One owner, named moderators (pin, remove); every moderator action is logged and reversible by the owner. Planned in CM-B3/CM-B7.

### Q4 — Scene C topic — ANSWERED (D9, P1 recommendation accepted)

One official public-information topic, answered only from that authority's own public pages (allowlisted publishers), with no claim of any integration. A non-civic fallback topic is rehearsed too.

### Q5 — Packaging surface — ANSWERED (D10)

Demo and tests by 18 Dec run through a **secure tunnel from the founder's PC** (no spend), used for the videos and for a test with **≥ 5 consenting adults** per entry. Accounts: a separate Supabase **staging** project (sign-up disabled, test users only); its Auth/RLS SQL is applied by a script from `apps/community/supabase/`; `supabase/migrations/` stays frozen. Memory builds use a clearly named `FakeTemporalMemoryClient` until the temporal_note hand-off lands.

## New blocking item from Lane E (D9's stop-and-ask clause, triggered)

### N1 — Under-18 admission cannot be built as D9 describes, on official evidence fetched 23 Nov

Lane E (`child-safety.md`) found, and the lead corroborated on u.ae: under-15s may not hold personal social-media accounts (Cabinet Resolution No. 106 of 2026; parental consent cannot override), and self-declared age is not sufficient verification. That conflicts directly with "all ages, self-declared" for any under-18 account.
**Planner's adopted reading (flagged, not silent):** the 18 Dec demo gates to verified 18+ consenting adult testers only — exactly D9/D10's tester ruling — and D9's under-18 protections are planned in full for a post-demo launch. Under-15 accounts, the 15–<16 restricted tier, and compliant age verification are deferred.
**Asks of the founder:** (1) confirm the adults-only demo gate; (2) decide whether to take UAE legal advice on whether Community is a Resolution 106 "social media platform" per surface; (3) confirm the all-ages ambition is post-demo, pending an approved verification method. **Blocks:** any under-18 slice of CM-B3/CM-B7/CM-B8. Adult slices are not blocked. **Deadline:** before CM-B3.

## Still open (non-blocking; defaults proceed)
- Group size caps, reaction set (beyond the parked ±1 vote), bookmark/share mechanics: builder's choice within the gap matrix; revisit after the multi-user test.
- Whether Discover also becomes a search destination later: spec says feed lane; keep it a lane for P1.
- Member-count display while seeded: always `Demo data` pill; real counts only from `cm_` membership rows.
- Final product branding beyond "Dubai-io Community": working name stands; no Meta-like marks either way.
- D10 recommended founder action (not a planner question): ask the organisers in writing (createaiagents@dubaichamber.com) whether a founder's own earlier prototype may be reused in an entry.
