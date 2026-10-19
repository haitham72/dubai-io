# Handoff: Dubai-io local build, 13 Oct 2026

Branch: redesign. Changes are local/uncommitted; private Artifacts have not been republished. Read CLAUDE.md → PLAN.md → ARCHITECTURE.md, then routed case/reference files.

## Implemented locally

- Cyan Services hero, area choices, short suggestions and grouped categories. Provider cards have one native whole-card Open action, keyboard Enter/Space and sorting support. The temporary provider-pages.js rendering wrapper leaves offers.js/miniapps untouched for the other LLM.
- Slower onboarding and shared C1 reflection 0.55 × 0.70 = 0.385. Founder quote: "cards flying up in onbording should be smoother and slower, now they are super fast". Reveal/exit timers, keyboard exit guard, input-owned transition, reduced motion and replay checks pass locally.
- chat.js calls Luna on the API origin; luna-client.js validates the actual contract, serializes turns, shows source/model/latency and falls back once after 15 s/unavailability. Late/reset results cannot dispatch another flow. Luna display text cannot claim execution/prices. User/thread checkpoint keys are scoped; the browser client bootstraps a private local cookie session.
- session-state.js stores same-browser plain-text history and structured reports, not HTML or tokens. Reports reopen after refresh. Your saved details supports scoped view/edit/forget through the API. Existing backend FactStore JSON remains the told-fact store; full checkpoint forgetting/server transcript replay remain pending.
- actions.py implements eight preparation capabilities, typed user-supplied fields, private anonymous sessions, SQLite persistence, payload-bound preparation retries, snapshot/revision/terms-bound approval, duplicate/concurrent dispatch protection, provider evidence gating and UNKNOWN_STATUS for ambiguous outcomes/restart. Unsent drafts can be discarded; dispatched cancellation requires a provider adapter.
- service-workflow.js provides shared request preparation/review, per-provider edits and Me → Saved requests. Runtime provider adapters are all absent, so requests stay draft/blocked with no fake Send. Taxi Continue uses this flow; the rejected “Official guidance / Your report stays here” page is removed. Copy is an optional manual alternative, not required completion.
- oauth.py/auth.py prepare Google browser start/callback with state+PKCE, verified userinfo, encrypted server-side grants, scope checks, serialized refresh and revocation. Connect remains disabled because credentials are missing. This is a connection to the local browser session, not completed production/cross-device account login.
- Retired chromatic HTML/palette/map/CSS branches removed. Cyan reflection remains.

## Configuration needed next

For Google web OAuth, set these in apps/api/.env, then restart the API:
- GOOGLE_OAUTH_CLIENT_ID
- GOOGLE_OAUTH_CLIENT_SECRET (server only)
- GOOGLE_OAUTH_REDIRECT_URI (exact registered URI ending /api/auth/google/callback)

Optional OAUTH_TOKEN_KEY supplies the encryption key. The local lab creates ignored data/oauth.key if configured without one; production needs a managed key/session deployment. HTTP localhost callbacks are supported; a phone/public callback needs the approved HTTPS origin. Places/Routes API keys are separate from OAuth. Identity scopes do not authorize Gmail/Calendar or merchant website sessions.

No real OAuth/provider/model calls were made in these checks. Mock credentials/grants only exist in temporary test stores; no real Connected or submitted status is claimed.

## Verification

- Offline API suite: 40 tests (Luna validation/scoping, action safety/durability/private sessions/memory, OAuth exchange/refresh/revocation). 11 paid golden cases remain deselected.
- JS: 7 Luna-client + 8 recovery-state tests; existing profile suite 92 checks.
- Chromium 390 × 844: WebGL active; slower intro exit/input, whole provider cards, shared request saving/missing-field editing, same-browser chat/report refresh and no required copy/no fake Send pass. Saved-details edit/forget and Connected-account disconnect were checked with mocked responses in a fresh browser context; real unconfigured Google stays disabled. Whole provider cards reach shared preparation, and discarded drafts remain discarded. Luna browser responses were mocked; the action API/store were real local code.
- Screenshots under ignored output/playwright/: services-after.png, intro-after.png, c1-reflection-after.png, cleaning-full-cards.png, shared-request-prepared.png. Earlier official/provider-preview screenshots describe rejected flows, not current acceptance.
- Syntax/diff checks pass. Local API is running on 8000 from the verified project venv. No permanent firewall settings changed.

## Remaining

1. Supply OAuth configuration and verify real Google consent/return/refresh/revocation on the approved origin.
2. Connect a supported live provider adapter and approval/evidence path. OAuth alone does not provide merchant or RTA integration access. Government execution remains disabled pending a narrow validated capability.
3. Step 03 branch 0a85715 reviewed: **edit before merge**, still unmerged. Original sandbox messages throw SecurityError at bridge.js:256; session validation is absent. Diagnostic-only browser probes also found dismissed approvals stuck and old dispatch cleanup closing newer sheets. Fix approval ownership, idempotency/error cleanup, strict entry/payload checks, confirmed area and unapproved pharmacy prices. Detailed local report/paste prompt: output/playwright/bridge-review-report.md and bridge-followup.txt.
4. Remaining reference parity: guide/chat/approval-events/map detail/merchant screens and laundry deadline arc. C6 remains rebuild until real agentic recovery integration and phone approval.
5. Production React + separate widget hosting, Postgres/roles/server transcript replay, SSE/outbox, persistent profiler, cross-device auth and live Google Maps. The lab's SQLite/local storage is not those production gates.
6. iPhone review, then publish the reviewed local build. Earlier private Artifact links remain historical; nothing auto-republishes.

## Manual prompt: other LLM, step 03

The founder manually pastes this; do not auto-spawn agents.

```text
Claim step 03 only. Use a separate checkout/worktree on feat/miniapp-bridge from redesign; never switch the main directory branch or include its uncommitted changes. Read CLAUDE.md, PLAN.md §2 and ARCHITECTURE.md §§4,6. Write only demo/lab/offers.js, demo/lab/miniapps/*.html, your bridge/catalog module/fixtures and bridge tests.

Keep initOffers/wireOffers/openOffers/closeOffers, SERVICE_GROUPS and data-open/data-visit hooks compatible. The main agent owns app/chat/page/workflow/API/account/memory/docs files. Current host wrappers provide uniform full-card Open and shared preparation; coordinate their later removal/migration when reviewing your diff.

Implement host-owned published prices for EVERY template, strict payload/action/source/session validation, duplicate approval protection and honest lifecycle transitions. Business scope remains order.request only, sandbox allow-scripts without allow-same-origin. No OAuth tokens/new auth business scopes.

No secrets/memory reads, live/paid calls, publication, merge or commits of the main agent's changes. Return branch/base, claimed files and bounded approach first, then progress, concrete diff/commits, offline validation and limitations. We decide merge/edit/cancel after review.
```

A test cleanup deletion was rejected by automatic approval review because it could remove saved data. It was not performed; final memory checks used an isolated browser context with mocked edits/deletions. Saved data was preserved.

The fixed app viewport now uses overflow clipping where supported so focus does not scroll the whole shell; sheets retain their own scroll area. Final 390 × 844 geometry check confirms root scroll zero and a visible sheet header.

## Stop handoff — 13 Oct 2026

Founder requested stop after step 03 review. No merge, cherry-pick or implementation edits were made to the delegated branch or its nine files in the primary workspace. Primary redesign changes remain uncommitted.

Reviewed candidate: feat/miniapp-bridge, commit 0a85715cde317542d9c2596d30b30a9138b0e0ae, base 77715514022b02b91a279cc9aceecb2fa2181e97; isolated worktree C:/Users/h.ibrahim/AppData/Local/Temp/opencode/dubaiio-bridge. Decision: edit before merge.

Next owner: founder manually sends output/playwright/bridge-followup.txt to the other LLM. It fixes its own branch and returns a new commit/report; main agent then re-reviews against current host and wires reset/shared-workflow integration. Do not merge the current candidate. Original real sandbox fails at bridge.js:256 (cross-origin WindowProxy property access); deeper approval findings were tested only after bypassing that one read in temporary HTTP responses, not by editing either branch. Existing 241 bridge and 92 profile checks pass despite those bugs.

Evidence: output/playwright/bridge-review-report.md, bridge-dismiss-retry.png, bridge-late-close.png. Local review server/browser are being closed at stop; main API on port 8000 is left running. No live/paid/provider/OAuth calls or saved-data deletions were performed in this review. OAuth credentials, live adapters, iPhone review and publication remain pending as listed above.
