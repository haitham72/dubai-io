# Muse handoff — three branches (23 Oct 2026)

## Resumed three-track authorization — 23 Oct 2026

Founder resumed option B: finalize `redesign-community`, integrate into `main`, then build `dubai-io-web` and `ios-swift` from that baseline. The pause note below is superseded.

## Latest scope correction — 23 Oct 2026

Stay on `redesign-community` and finish current branch edits only. **Do not merge into main or start web/iOS branches.** Earlier three-track execution authorization is paused by the founder. Plan the durable Reddit-like community database and Storage buckets in `docs/references/community-data-storage-plan.md`; implementation of that full target is not claimed. Recommender remains partial (REC-03C/REC-04 and PostgreSQL adoption pending).


## Execution update — 23 Oct 2026

The founder has now assigned implementation directly to the current agent/team. Finalize and verify `redesign-community`, integrate into `main`, then build the web and iOS branches from that baseline, preserving prior iOS source. Luna writes the rich fixture population; the backend orchestrates live NaraRouter Agnes replies from stable persona identities and conversation history. Target ten respondents to a new post, a couple of related personas to a comment, and the assigned relationship persona in direct chat. This supersedes the fixture-only reply model and Muse-only handoff below. Never represent generated demo personas as real people.


Paste this entire document into Muse at the repository root. This is the current founder instruction and supersedes older two-branch, branch-switching and native-paused instructions. Requirements below are work to do, not claims of completion.

You are **Muse**, the long-horizon implementation agent for Dubai-io. Complete three tracks, with small verified commits and a separate worktree per branch. Preserve the existing backend and the approved prototype. Do not stop after a cosmetic mockup.

## Read first

Read `CLAUDE.md`, `PLAN.md`, `ARCHITECTURE.md`, `handoff.md`, `docs/request-backlog.md`, `docs/references/ios-swift-plan.md`, and `design/CLAUDE.md`. Inspect the existing app and relevant reference frames before changing it. This founder feedback takes precedence over historical scope/branch instructions; all remaining product safeguards still apply.

## Branch ownership

| Branch | Worktree | Scope |
|---|---|---|
| `redesign-community` | Existing checkout if already checked out there; otherwise `../dubai-io-rc` | Minimal targeted prototype fixes and fixture enrichment listed below. Preserve the excellent Feed design. No broad refactors, architecture rewrites or unrelated restyling. |
| `dubai-io-web` | `../dubai-io-web` | Apple.com-inspired website in `apps/site/**`, full application depth, using the same backend. |
| `ios-swift` | `../dubai-io-ios` | Native SwiftUI app in `apps/ios/**`, plus `handoff-ios.md`, using the same backend. |

Inspect `git status`, `git worktree list`, local/remote branches and running servers first. Reuse existing worktrees; never check out the same branch twice or switch branches in the founder's main folder. Coordinate ownership before touching files another agent is editing. Create missing branches/worktrees from the current verified `redesign-community` baseline. Never reset or discard existing work. Merge verified community changes into the web/iOS branches at safe checkpoints, without overwriting their client files.

Web/iOS must not edit `apps/web/**`, `apps/api/**` or `supabase/**`. Record missing API contracts under "Native/site requests" in `docs/request-backlog.md`; implement only narrowly required shared changes on `redesign-community`, with regression checks. Preserve existing data and backend contracts.

## Track 1 — minimal prototype improvements

### Feed

- The Feed is excellent: preserve its current design and behavior.
- Replies must be Facebook-style nested threads with actual parent/reply relationships, readable indentation and expand/collapse. Twitter-style @mention text is not a substitute for nesting.
- Make every story thumbnail a true circle: equal width/height, no flex shrink, consistent crop and ring. Align circles and labels evenly; verify long names and mobile sizes.

### Chat and calls

- Remove the confusing caller icon beside the user profile icon.
- Implement the founder's exact requested Calls hierarchy: **Calls** heading, **Search**, then **Calls | Contacts | Keypad | Favorites**. Verify the current WhatsApp reference if available, while keeping these explicit labels/order. Every tab must work; search, contact details, favorite toggles and keypad actions must have meaningful behavior. Preserve honest device-dialer handoff; never imply a call connected without evidence.
- Delegate fixture enrichment to a small agent at low-to-medium effort. Create **10–15 distinct chat personas**, real licensed photo thumbnails and substantial believable chat histories, including replies, follow-ups and varied conversations rather than repeated filler.
- Actually use the configured NaraRouter API for fixture generation: read `NARAROUTER_API_KEY` privately from `apps/api/.env`; read the endpoint and model list from local `opencode.json` without logging its credentials. The configured Agnes default is `agnes-2.5-flash` (provider-qualified config ID `nararouter/agnes-2.5-flash`). Do not send the nickname `agnes` as an invented model ID.
- When a role/model is not annotated or the selected model is unavailable, select a compatible fallback from that local model list. Record the model used and generation/validation outcome without request headers or secrets. If credentials/network/provider fail, report the actual blocker; do not claim fixtures were model-generated. Keep fixture generation separate from the live assistant model configuration.

### Communities

- Joining in Feed must carry through to **Chat › Communities**, including opening the same community and its threads, refresh persistence, leaving, and duplicate-join handling. Preserve user scoping.
- Build **10–15 Dubai communities** with **about 100 distinct users across them**, each with a coherent persona and real licensed thumbnail. The chat personas may be a subset of this shared population; keep IDs and identity consistent.
- Populate substantial, varied posts and deep multi-user nested conversations: questions, answers, disagreements, clarifications, follow-ups and resolutions. Include several threads at least three reply levels deep. Do not inflate counts with duplicate filler or orphaned replies.
- Topics: used-item sales, hiring/job-search difficulties, rent, moving, neighborhoods, transport, food, weekend plans and resident questions about Dubai. Research r/dubai and r/UAE for topic inspiration if useful. Write original fictional interactions; do not copy Reddit users, photos or personal stories into personas. Treat legal/visa/employment claims as demo discussion, not authoritative guidance.
- Validate unique IDs, valid authors/parents, same-thread parents, acyclic reply trees, chronological messages, population counts, and join-to-chat journeys. Make seed loading repeatable without overwriting user content; preserve the existing fixed-date policy.

### Home news

Match the requested Google News card composition: a large image spanning the card width, then the title, then a subtitle underneath. Replace the small-thumbnail horizontal row layout. Keep source attribution, publication date and real article links. Handle unavailable images cleanly without fake news or placeholder imagery.

### Services

Show **exactly three complete thumbnails per row** at the supported phone widths, with consistent gutters and crops. No clipped 1.5-tile carousel. Add relevant tiles where necessary, preserving working service actions and readable labels.

## Imagery across all tracks

Use real, openly licensed or explicitly reuse-permitted photographs for people, food, Dubai locations and items wherever possible. No placeholder services, repeated generic avatars, broken image URLs or invented photo provenance. Check each asset's actual reuse terms; a search result or image host alone does not establish permission. Keep a source/creator/license/attribution manifest and prefer stable downloaded assets when permitted. Fictional demo identities must not imply the pictured person actually authored posts or endorses the app. Preserve visible Demo data labels.

## Track 2 — Apple.com-inspired website

Build `apps/site` with Next.js App Router and TypeScript, using the existing API, Supabase identity/storage contracts and Python backend. Apple.com is a visual reference: confident typography, generous space, large real image bands, restrained motion, cyan accent, light/dark support and reduced-motion support. No UI kit or shadows.

Create a coherent design system, then complete Home, Privacy and Demo pages and the signed-in `/app`. Full depth means functional Home/tasks/decisions/news, Feed/stories/nested communities, Chat/Calls/Contacts, Services/mini-apps, profile and on-demand Maps; meaningful routes, loading/empty/error states and working back navigation. Avoid dead-end feature cards. Preserve backend approval, evidence and ownership rules. Do not build a separate backend or replace the prototype.

Use `NEXT_PUBLIC_API_BASE` and only an appropriately restricted `NEXT_PUBLIC_MAPS_KEY`; all private keys stay server-side. Vercel is the target host; do not treat a local build as a deployment.

## Track 3 — native Swift iOS

Build the SwiftUI app on `ios-swift` for the target in `docs/references/ios-swift-plan.md` (iOS 26+, Xcode 26.3; founder device iPhone 13 Pro Max). Inspect the installed toolchain and existing project first. Extend the typed API client and models, then shell → Home → Feed/stories/nested communities → Chat/Calls/Contacts → Services/mini-app host → on-demand Maps → notifications. Apply the founder's corrected layouts and richer fixtures consistently.

Retain native in-app browsing, the approved onboarding, sandboxed mini-app bridge, explicit approvals and the same backend. Verify with package/contract tests, Xcode build, Previews and Simulator as available. Report physical-device checks separately; do not claim device verification without running them.

## Configuration check before generation or launch

Inspect `apps/api/.env` by key presence and parse validity only. Never print, commit or copy credentials into browser/Swift code, fixtures or reports. Both `.env` and `opencode.json` are ignored local files; new worktrees do not automatically receive them. Configure private per-worktree environments intentionally without committing secrets or disrupting the existing server.

Local static audit on 23 Oct (not a live provider test): `NARAROUTER_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_PLACES_KEY`, `NEWSDATA_API_KEY`, `TVLY_API_KEY`, `SERPAPI_KEY` and `FINNHUB_API_KEY` are populated. NaraRouter credentials match the local model config; there are no duplicate `.env` keys. `LUNA_MODEL`, `DATABASE_URL`, `DATABASE_SCHEMA` and `GOOGLE_MAPS_BROWSER_KEY` are absent/empty. The code supplies a default model and SQLite fallback; do not describe Supabase as active based on this file. Process environment can override file defaults. Check actual runtime configuration privately before changing it. A separate restricted browser Maps key remains needed for public hosting. Recheck this audit when executing.

## Verification and delivery

- Run focused existing tests for touched behavior and add meaningful regression coverage for nesting, membership persistence and fixture validity.
- Inspect the prototype at **390×844 and 428×926**, normal and reduced motion. Verify circular stories, aligned labels, full-width news images, exactly three Services tiles, all Calls tabs, nested replies and Feed join → Chat community → thread → refresh.
- Verify photo loading/crops, keyboard access, readable text and no overflow. Test empty/error states as well as seeded happy paths.
- Build/test the website and Swift client with their actual toolchains. Keep backend, live-provider, Simulator, device and deployment verification distinct.
- Preserve approval-before-send/share, provenance, Demo labels, honest status, no payments/government execution, and untrusted community content rules.
- Report per branch: changed files and behavior, commit hash, test/build results, screenshots or artifact paths, fixture/persona counts, model actually used, image manifest, and remaining blockers. Push verified slices to the intended branches; do not claim another track is complete because one branch passes.
