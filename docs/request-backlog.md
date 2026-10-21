# Request backlog — 21 Oct 2026

Execution ledger for the founder's requests; scope remains in `PLAN.md`. Requirements, implementation and verification are separate states. A partial result is not completion.

## Working rule

Finish the active task before taking the next. New messages refine the active task or enter this backlog; questions get an answer without replacing the task. Reorder only when the founder explicitly changes priorities or the agent explains a logical reordering in the same session and updates this ledger. Preserve unresolved requests across handoffs. The founder explicitly lifted the native iOS hold on 21 Oct.

**Active order, latest founder instruction:** finish recommender controls/coverage -> assistant context/draft plans -> events/occasion suggestions -> sponsored food discovery -> remaining review fixes. Local Supabase has reached its verified checkpoint. Native features are parked for Mac testing; Google OAuth is last for the single tester. **Primary detailed plan:** [implementation-plan.md](implementation-plan.md), under root PLAN.md. Next task REC-03. Current runtime: root handoff.md.

## Current sequence

| Order | Request | Implementation and next result |
|---|---|---|
| Done, phone review pending | Maps modes/category navigation/cyan | Explicit 2D/3D and one-row drill-down are browser checked. Pet-specific query and captured async metadata fixes are implemented. Physical phone framing remains. |
| Done, local checkpoint | PostgreSQL/Supabase | Dedicated local Supabase is healthy; versioned private schema, owner checks, access denial and SQLite review-record import verified. API port 8000 now uses it. Original Postgres recovery, hosted deployment and production Auth remain DB-02/03. |
| ACTIVE | Own temporal profiler, moderate recommender, PostgreSQL tables and LangGraph short/long memory | REC-01 event/projection/ranking slice, two memory scopes and visible Confirm/Not true/Forget/Resume are implemented. Home category adaptation and live-map observations work. REC-02 is verified complete: explicit Edit, visible evidence/scopes, aggregate caps, transactional facts, cache invalidation and timeline labels. REC-03 eligibility/wider surfaces is next; REC-04 measurements remain. Legacy six hypotheses coexist; no fixture training. |
| Next | Context-aware Dubai assistant; selected museum fact and itinerary example | CTX-01 whole-place focus, removable chat chip, bounded history and owner checkpoint forgetting are implemented. CTX-02 fragments/server resolution/availability guard and PLAN-01 draft itinerary revisions/diffs remain. |
| Then | Birthday/school/occasion suggestions and nearby festivals/artist events | SUG-01/EVT-01 are detailed pending tasks. Confirmed dates, source/organizer verification, explicit uncertainty and notification consent are required. No live event feed is claimed. |
| Then | Sponsored restaurants personalized in a food thread | ADS-01 pending. Current observations are organic-only; no advertiser inventory, ad targeting or campaigns are implemented. Keep labels, organic alternatives and eligible evidence separate. |
| Follow-up | Code/UI reviewer assessment before founder checks | Assessment delivered; memory forgetting and map query/metadata issues fixed in this checkpoint. Proxy quotas, merchant throttling/roles, visual parity and physical-device checks remain REV-01/02. Not declared optimal or production ready. |
| Answer delivered, external work pending | Existing API access problems; open APIs/registration/company gates; demo versus TBD | API catalog preserves live configured discovery, provider-specific approval/affiliate gates, Careem MCP/Uber corrections and honest sandbox/handoffs. Grants/applications/real adapters are not implied or submitted. |
| Native slice done, wider parity parked | In-app browser like Instagram/X | Safari sheet exists on ios-swift; web arbitrary iframe limitations remain. Native OAuth, mini-app bridge and full order parity remain separate. |
| PARKED | Swift iOS conversion | ios-swift first slice and handoff pushed. Seven package tests + unsigned Simulator build passed at cfb65a4 (run 39585052919). Founder will test on Mac/iPhone 13 Pro Max. Guide/recovery/order/Auth/SSE/APNs parity remains; no forced Windows toolchain. |
| LAST | Google OAuth / account identity | Explicitly deferred by founder. Single tester retains existing cookie session; Google API keys keep working independently. No shared public tester override. |

The queue lists implementation requests separately from completed planning. Items requiring external credentials or a scope decision remain visible rather than being treated as completed.

## Completed answers and preserved work

| Request | Result |
|---|---|
| Were earlier iOS/Swift/UI repositories and skills preserved? | Located ShipSwift and Libraries.dev references in `docs/references/visuals-libraries.md` and native direction in `PLAN.md`; installed Swift/iOS and ShipSwift skills were located globally. |
| What were the failures? | Search permission/missing-path warnings were distinguished from app failures; the Postgres crash/runtime issue is documented separately. |
| Apple TV style browse dock that collapses to chat | Implemented and browser checked: one composer in chat, browse dock hidden/inert, Back restores browsing/draft. Physical iPhone keyboard validation remains. |
| Gorgeous onboarding, Wi-Fi and gradients | Preserved and browser checked. Start at `/#demo.wifi`; `#maps`/`#services` bypass onboarding deliberately. |
| Astra medium plan review | Completed for the earlier backend/navigation plan. It does not count as a review of the later recommender plan. |
| Google sign-in information and personalization | Answered: basic identity, separately authorized profile/Calendar/Gmail access; no Google Ads interest-profile export. Data Portability offers broader imports only for eligible regions/accounts; UAE is not currently listed. Workspace data cannot be used for advertising. |
| Does local Supabase break Google OAuth/services? | Answered in backend options: supported local callback/configuration; outbound APIs remain available; phone testing and incoming webhooks require reachable endpoints. Local Windows stack depends on a container runtime. |

## Reordering record

- 21 Oct: consolidated the drifting requests. Finish Maps, then the recommender plan, then full code/UI review and API/demo assessment. Supabase decisions refine the backend/recommender plan; they do not replace the queue. Native iOS explicitly held by the founder.
- 21 Oct, later founder instruction: document full plan/status, commit/push/sync current work, create `ios-swift`, start native iOS. This explicitly lifts the native hold and moves that work ahead of pending Supabase/recommender implementation. Other requests remain tracked above.

- 21 Oct, latest founder instruction: park substantial remaining iOS work with `handoff-ios.md`; resume Supabase, recommender and all pending requests. Test on the founder's Mac without forcing a Windows toolchain. Google OAuth is explicitly last; preserve the single-tester cookie session and owner isolation.

- 21 Oct, plan-continuity instruction: the plan is more important than the handoff. PLAN.md is authoritative; docs/implementation-plan.md now records nested tasks, dependencies, exact implemented scope, acceptance gates and the then-active task REC-02 (completed in the checkpoint below). Code comparison establishes progress; do not treat plan prose as completed implementation.

- 21 Oct, REC-02 completed without a scope diversion: 109 tests passed on each database (11 live skipped), five cache tests and eight browser checks passed. Local temporal-v2 projections were backed up/reconciled; API restarted. Next active task is REC-03. Commit/push/sync is explicitly requested; keep the rest of the nested plan pending.
