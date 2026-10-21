# Request backlog — 21 Oct 2026

Execution ledger for the founder's requests; scope remains in `PLAN.md`. Requirements, implementation and verification are separate states. A partial result is not completion.

## Working rule

Finish the active task before taking the next. New messages refine the active task or enter this backlog; questions get an answer without replacing the task. Reorder only when the founder explicitly changes priorities or the agent explains a logical reordering in the same session and updates this ledger. Preserve unresolved requests across handoffs. The founder explicitly lifted the native iOS hold on 21 Oct.

**Active order, founder instruction:** detailed docs/status → commit/push current `redesign` → create `ios-swift` → implement and verify the first native slice. The table below retains earlier requests; its unfinished backend/features are not silently completed or discarded. Native plan: [ios-swift-plan.md](references/ios-swift-plan.md).

## Current sequence

| Order | Request | State / next result |
|---|---|---|
| 1 | Maps: separate 2D/3D; replace two category rows with drill-down; cyan selections | Implemented and browser checked. Pets opens pet options; Back restores categories. Loading/failure/late responses preserve the selected map mode. Screenshot: `output/playwright/maps-single-row-cyan.png`. Physical phone review remains. |
| 2 | Moderate recommender, own temporal profiler, LangGraph short/long memory, PostgreSQL profiling tables | Written plan: [recommender-plan.md](references/recommender-plan.md). Planning deliverable complete; recommender implementation remains queued. Supabase is the target platform; local development is viable with a working runtime. |
| 3 | Reviewer assessment of code and UI before founder review | Assessment delivered in [review findings](review-findings-2026-10-21.md), with priorities, code evidence, visual gaps and validation limits. Fixes and physical iPhone validation remain tracked; the app is not declared optimal or production ready. |
| 4 | Existing API problems; remaining API access/registration/company requirements; live demo versus TBD | [API catalog](references/api-catalog.md) updated with access tiers, provider-specific gates, explicit unknowns and demo recommendation. Configured APIs were live checked earlier. Careem MCP and Uber approval paths correct the older “no API” labels. Applications/access grants and unselected providers' exact terms remain external work. |
| 5 | PostgreSQL failure; Supabase local/hosted integration | Diagnosis/options documented in [backend-options.md](references/backend-options.md). Original database remains unrecovered; no volume reset. Migration/auth implementation not started. Preserve data, map owners/roles, then validate local and hosted paths. |
| 6 | Implement moderate recommender after its plan and app review | Queued. Build on existing profile facts and episodes; immediate session adaptation, server ranking and visible hypotheses. No recommender code or migrations have been applied. |
| 7 | Context-aware Dubai assistant across places/services/products/plans; museum-card follow-up example | Requirements/proposal in [assistant-context.md](references/assistant-context.md); structured focus and itinerary implementation pending. The product is a personal assistant, with Maps as one surface. |
| 8 | Sponsored food results; birthday/school/occasion suggestions; nearby festivals and artist events | Captured in [service cases](services/cases.md), C9/C13/C15. Requirements only. Preserve labeling, dates/sources, user controls, provider access and existing scope decisions before implementation. |
| 9 | Open third-party websites in an in-app browser, like Instagram/X | Detailed native browser policy in [iOS plan](references/ios-swift-plan.md). Safari sheet in the first native slice; native authentication and custom browser are distinct later integrations. Web/PWA framing limits remain. |
| Active | Convert to native Swift iOS | **Start authorized**, superseding the earlier hold. Founder has a Mac and iPhone 13 Pro Max. Snapshot/push baseline, create `ios-swift`, then first native slice. This workspace has no Swift/Xcode; actual macOS build results must be reported separately. |

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
