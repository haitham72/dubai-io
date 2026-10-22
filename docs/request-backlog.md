# Request backlog — 22 Oct 2026

Execution ledger for the founder's requests; scope remains in `PLAN.md`. Requirements, implementation and verification are separate states. A partial result is not completion.

## Working rule

Finish the active task before taking the next. New messages refine the active task or enter this backlog; questions get an answer without replacing the task. Reorder only when the founder explicitly changes priorities or the agent explains a logical reordering in the same session and updates this ledger. Preserve unresolved requests across handoffs. The founder explicitly lifted the native iOS hold on 21 Oct.

**Active order, latest founder instruction:** change the visitor-first product framing; learn from OpenAI Dots, Grok Bot and Claude Duet and propose mature features for everyday life/work in Dubai. Research and proposal: [personal-assistant-direction.md](references/personal-assistant-direction.md). Pilot audience/features remain proposals where not explicitly selected; earlier implementation tasks are preserved below, not silently cancelled. `6470ad4` is committed/pushed on `redesign`. Native remains parked; single-tester Google OAuth remains last. A/B PostgreSQL verification/reconciliation is still gated by the 22 Oct write stall. Runtime: root handoff.md.

## Current sequence

| Order | Request | Implementation and next result |
|---|---|---|
| ACTIVE planning | Mature personal assistant for everyday life/work in Dubai; learn from Dots/Grok Bot/Duet | Visitor-first persona explicitly superseded. Official sources reviewed; proposed responsibility/task model, Today/decision view, inspectable context, routines, communications/calendar, plans/local follow-through and optional channels recorded with dependencies/acceptance gates. First pilot audience asked; new features not implemented or automatically selected. |
| Done, phone review pending | Maps modes/category navigation/cyan | Explicit 2D/3D and one-row drill-down are browser checked. Pet-specific query and captured async metadata fixes are implemented. Physical phone framing remains. |
| Baseline verified; current write issue | PostgreSQL/Supabase | The 21 Oct private schema, owner/access checks and SQLite import were verified. On 22 Oct reads worked but new test-schema writes stalled (`WALWrite`/locks) and Docker returned HTTP 500. No volume reset, source-data replacement or v3 deployment is claimed. Original Postgres recovery and hosted/Auth work remain DB-02/03. |
| Preserved dependency | Own temporal profiler, moderate recommender, PostgreSQL tables and LangGraph short/long memory | REC-01/02 implemented. REC-03A/B add separated-visit qualification, signed influence, trusted live places, radius/open-now constraints, stable order/variety/reasons and seven-day item hiding. 128 SQLite tests and seven controlled browser scenarios passed; PostgreSQL gate remains. REC-03C service/product eligibility/completions and REC-04 measurement/lifecycle remain pending under the revised product. Legacy six hypotheses coexist; no fixture training. |
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

- 22 Oct: founder clarified suggestions must adapt over time. Expanded the temporal behavior contract and nested REC-03/SUG/EVT gates before implementation. REC-03A/B now have SQLite/browser verification; exact natural-language constraints, service/product adapters and broader relevance evaluation remain explicit. One separate live Google field-mask request succeeded. Local database write stalls prevented PostgreSQL verification; the old database and `.env` were preserved.
- 22 Oct, branch clarification/finalization: one repository/working folder, currently `redesign`; `ios-swift` is unchanged. Founder requested commit/finalization and explicitly said not to start iOS. Finish the current checkpoint and sync its documents; do not infer a native merge or a completed wider roadmap.
- 22 Oct, checkpoint finalized: `6470ad4` was committed/pushed to `redesign`; source and upstream were synchronized. No iOS branch change or Supabase deployment was claimed.
- 22 Oct, explicit change of plans: founder rejected the visitor-companion identity and requested learning from Dots, Grok Bot and Duet. This authorizes product replanning ahead of the previous execution queue. PLAN.md/CLAUDE.md now distinguish confirmed audience broadening from proposed features. No application code, connector permissions or native work were changed for this research task.
