# Native iOS + website plan — 23 Oct 2026 (current; the 21 Oct plan below is history)

**Two tracks, one backend.** The founder runs two agents in parallel:
- **Web/mobile redesign (this repo's `redesign-community` branch):** owns `apps/web`, `apps/api`, `supabase/` and the canon docs. It continues the community redesign (S3 news, S5 services, map entry points).
- **Native + website (`ios-swift` branch):** owns `apps/ios` (SwiftUI) and a new `apps/site` (Next.js on Vercel). It merges `redesign-community` in regularly and never edits `apps/web` or `apps/api`. If it needs a backend change, it writes the request in `docs/request-backlog.md` under "Native/site requests"; the web agent implements it.

## Architecture and hosting (recommended)
| Layer | Choice | Why |
|---|---|---|
| Database, auth, storage | **Supabase** (Postgres + pgvector, Auth, Storage) | Already the selected platform. Migrations live in `supabase/migrations`. RLS is enabled on every table; only the API reaches the DB with the backend role. |
| API | **Keep Python FastAPI + LangGraph**, deployed as a container (Fly.io, Railway, Render or Google Cloud Run) in the same region as Supabase | It holds the assistant graph, approval engine, outbox, SSE streams, recommender and ~200 tests. Rewriting it as Supabase Edge Functions (Deno/TypeScript) means rewriting all of it with no user-visible gain. Edge Functions host neither Python nor long SSE streams well. |
| Supabase Edge Functions | Only for small glue later | E.g. auth hooks or provider webhooks, if useful. |
| Website | **Next.js (App Router, TypeScript) on Vercel**, calling the same API | Apple.com-style marketing site plus a signed-in web view. The existing `apps/web` stays the reference/prototype until the site reaches parity. |
| iOS | **SwiftUI (iOS 26+)**, calling the same API | Uses `apps/ios/Core` (typed `APIClient`, models, contract tests). |
| Identity | Supabase Auth (Sign in with Apple + email) → bearer token verified by FastAPI → existing `owner` scoping | Today's anonymous cookie session migrates to accounts later. Google OAuth stays last. |
| Keys | All provider keys server-side; the browser and app only get `GOOGLE_MAPS_BROWSER_KEY` / an iOS-restricted Maps key | `/api/maps/config` already serves the browser key. |

## Navigation and screens (both clients)
Bottom bar: **Home | Chat | Services | Feed**, plus a separate **Ask** button. Profile (Me) sits top-right on each tab. Maps is a feature opened on demand, not a tab.
- **Home:** full photo/gradient card deck; compact Today card (one brief line, lane chips, top three one-line rows); task history; Google-app-style news (one large 16:9 image per story; community posts mixed in).
- **Chat:** segments All | Unread | Groups | Communities; "Dubai-io assistant" pinned and opening Ask; group/community threads; Contacts (contacts you add + log of calls started from the app; calls via the dialer: `tel:` on web, `openURL` on iOS; iOS cannot read the system call log).
- **Services:** 3-column tiles; flat widgets (prayer times, orders & receipts "No payment taken", "Explore near you" map card); provider mini-apps with the shared decision card.
- **Feed:** stories rail (Snapchat-style viewer), communities to join (Reddit-like), persona posts with comments; Demo labels on seeded data.
- **Ask:** chat with decision/result/brief cards and the small live map that expands into Maps.
- **Maps:** interactive Google map. On iOS use the Google Maps SDK for iOS for Places content (Places data must sit on a Google map); MapKit only for the separate illustrative 3D view.

## API contracts to reuse (all live on `redesign-community`)
- Today/tasks: `/api/today`, `/api/today/lanes/{lane}`, `/api/tasks`, `/api/tasks/{id}`, `/api/tasks/{id}/commands` (edit, pause, resume, cancel, complete, check_back, staged_next, collect; always `expected_revision` + `command_key`), `/api/tasks/from-action`, `/api/tasks/from-report`.
- Decisions/orders: `/api/actions/prepare`, `/api/actions/{id}`, `/api/actions/{id}/approve` (Idempotency-Key, `snapshot_hash`, `revision`), `/api/actions/{id}/cancel`, `/api/actions/{id}/stream` (SSE), `/api/actions/{id}/request-earlier`, `/api/reminders`.
- Assistant: `/api/luna/turn` (intents incl. `places_near` with `query`), `/api/messages` + `/api/messages/stream` (outbox), `/api/assist` (ask/auto/learn), `/api/routines/brief`.
- Places/maps: `/api/discovery/places` (category, subcategory, optional `query`), `/api/places/search`, `/api/places/photo`, `/api/maps/config`.
- News: `/api/reading`, `/api/reading/thumbnails/{id}`.
- Community: `/api/communities`, `/api/communities/{id}/join|leave|posts|stories`, `/api/feed`, `/api/posts/{id}/comments|hide`, `/api/chats`, `/api/chats/{id}/messages`, `/api/contacts`, `/api/calls`.
- The rules don't change in any client:
  - no status without an authoritative event;
  - approval before any send or share;
  - provenance and `Demo` labels;
  - no shadows;
  - community content is untrusted.

## iOS build order (each step: Previews + Simulator + device check, commit)
1. Merge `redesign-community` into `ios-swift`. Bring `apps/ios/Core` models and contract tests up to the endpoints above.
2. App shell: tab bar + Ask button, profile, onboarding gradient. Liquid Glass for navigation only; flat content.
3. Home: compact Today, decision card (Approve / Not now / Discard), result card, brief.
4. Feed + story viewer; Chat hub + threads; Contacts with in-app call log.
5. Services tiles + widgets; mini-app host (`WKWebView`, sandboxed, `order.request` bridge); order SSE.
6. Maps (Google Maps SDK) + in-chat mini map; place detail in-app.
7. Notifications: outbox → APNs later; local banner "Task done: …" now.
8. Physical iPhone 13 Pro Max pass: safe areas, Dynamic Type, VoiceOver, reduced motion/transparency.

## Website (Next.js on Vercel) build order
1. `apps/site`: Next.js App Router + TypeScript, no UI kit. Apple.com-like: large type, generous white space, product-photo bands, cyan accent, no shadows, light/dark, fast.
2. Marketing pages: Home (hero + feature bands: Tasks, Decisions, Communities, Services, Maps), Privacy ("what we never do"), Contest/demo page.
3. Signed-in app (`/app`) reusing the API (cookie session now, Supabase Auth later): Home, Chat, Services, Feed, Ask, with parity to `apps/web`.
4. Vercel project: env `NEXT_PUBLIC_API_BASE` + `NEXT_PUBLIC_MAPS_KEY` (referrer-restricted); the API on its container host with CORS allowlisting the Vercel domain.

---

# Native iOS plan — 21 Oct 2026

Founder explicitly authorized: detailed documentation/status → commit and push current work → create `ios-swift` → start iOS. This supersedes the earlier native hold and founder-review prerequisite. Web baseline remains on `redesign`; no other queued request disappears. Status of record: [handoff](../../handoff.md); full queue: [request backlog](../request-backlog.md).

## Product and visual contract

- Dubai personal assistant across places, services, products, plans and events. Maps is one surface, not the product definition.
- Preserve the Wi-Fi/arrival demonstration and slow cyan/purple gradient introduction. Simulated arrival/install/network steps remain labelled; never imply the app actually joined airport Wi-Fi or installed itself.
- Native browse categories resemble the smooth Apple TV style direction. Opening Ask transitions to a focused chat with one composer; browse controls collapse, and Back restores the selected tab, category and draft.
- iOS 26+ SwiftUI/Liquid Glass for navigation and real controls; readable flat content, cyan palette and no added shadows. Respect reduced motion/transparency, Dynamic Type and VoiceOver. Keep ShipSwift/Libraries.dev references without adding a framework solely for appearance.
- One category row drills into options; Back goes up a level. Live Google 2D stays separate from illustrative 3D, including errors and delayed responses.

## Toolchain and what “working” means

The current Windows workspace has Git/GitHub CLI but no Swift, Xcode or iOS Simulator. Swift source/project generation is possible here; an iOS build or runtime claim requires a Mac.

Use a checked-in Xcode project, Apple frameworks and a small local Swift package. The founder opens the project in Xcode on the Mac, chooses a signing team and runs on the iPhone 13 Pro Max. No Expo/React Native/runtime wrapper is required. A macOS GitHub Actions job should compile the package and the unsigned simulator app; report its actual result, including any unavailable runner/credential limitation. A CI compile is not a visual/device test.

Avoid unsolicited remote-Mac setup. If CI cannot run, keep the source work explicitly uncompiled and provide the exact Mac commands. Never call a scaffold a finished conversion.

## First slice

1. **Foundation:** local Swift package with Codable DTOs matching actual FastAPI responses, validated base URL, injected HTTP transport, typed HTTP errors and URLSession cookie handling. Establish `/api/session` before owner-scoped requests. Validate the contract with backend-shaped fixtures.
2. **Native shell/onboarding:** SwiftUI views for labelled arrival, animated intro and browse-to-chat navigation. Preserve draft and selected browse surface when chat closes.
3. **Chat:** real `/api/luna/turn` calls, user/assistant text, research sources and product links. Display failure honestly; no native fake LLM success. Current API does not yet accept selected-card/itinerary context; that remains a separately tracked backend change.
4. **Discovery:** published demo catalog from `/api/catalog`, live Google place search with provider attribution, full Google static-map image, explicit separate 3D preview, saved confirmed facts and connection metadata. No made-up live availability/prices.
5. **In-app browser:** ordinary third-party HTTP(S) links use a Safari sheet. Close returns to the same chat/place/catalog state. Display the provider domain and retain deliberate external-app/browser actions for maps, calls and flows that require them.
6. **Build proof:** package tests plus simulator compile on macOS. Then founder device review for keyboard, safe areas, motion, text size and browsing return behavior.

This is a real first client slice, not full order/demo parity. A published sandbox catalog does not make a merchant real. Order/approval UI must not offer a working-looking send until the mini-app/approval bridge slice is implemented.

## In-app browsing design

Default ordinary merchant, product, event and article links to `SFSafariViewController`. This supplies a browser surface inside the app without requiring a custom browser implementation. It does not expose a private browser DOM/session to the assistant. Track the originating app card and user-initiated open, not an assumed purchase or external browsing history. [Safari sheet](https://developer.apple.com/documentation/safariservices/sfsafariviewcontroller).

A custom WebKit surface is an optional later refinement for controlled partner experiences: visible domain, progress/loading/error, Back/Forward, reload, Close and Open in browser. Handle popups/downloads and unsupported schemes explicitly. Do not give arbitrary pages the provider mini-app bridge or inject user credentials. Review provider compatibility before promising checkout inside it. [WebKit](https://developer.apple.com/documentation/webkit/wkwebview).

Google/Apple/other provider sign-in uses `ASWebAuthenticationSession` with validated callback/state/PKCE as appropriate. The current web OAuth callback only signals its popup opener; native login needs a compatible callback/exchange contract or Supabase Auth setup. Do not present the existing web callback as completed native login. [Authentication session](https://developer.apple.com/documentation/authenticationservices/aswebauthenticationsession).

The current web/PWA cannot guarantee this for arbitrary websites because providers can prohibit iframe embedding. Keep its existing handoff fallback. Browser presentation changes UX, not provider API access or the app's authority to book/pay. Completion/status requires the existing engine and authoritative evidence.

## Backend and data boundaries

- Retain FastAPI/LangGraph, deterministic approvals, idempotency, outbox and provenance. Supabase is the selected database/Auth platform; migration is not part of the first native source slice.
- First client uses existing anonymous cookie sessions to exercise current read/chat endpoints. Document that this is not cross-device identity. Keep a dedicated API session; never send its cookies or tokens to unrelated websites.
- Configure the API base URL visibly. Simulator localhost refers to the Mac; iPhone localhost refers to the phone. A Windows-hosted API needs a reachable LAN/HTTPS address. Production requires HTTPS; development local-network access is explicitly configured and explained.
- Google Places content remains on a Google-provided map. The separate 3D preview may use MapKit with illustrative area context and no Google-derived pins. Preserve Google/photo attribution and permitted retention.
- Maintain browser-origin and selected-card state separately from confirmed profile facts. Interaction signals belong to the proposed recommender pipeline, not hidden permanent facts.

## Next slices and gates

| Slice | Work | Gate |
|---|---|---|
| Identity | Supabase Auth, bearer verification, anonymous-owner transfer, merchant/operator roles | Cross-user isolation and owner migration verified; callbacks tested on device |
| Merchant execution | Separate-origin mini-app host, restricted script bridge, host catalog reconciliation, native approval snapshot, order card and SSE reconnect | User-approved exact fields/recipient/amount; server/provider evidence; unknown stays unknown |
| Reminders | Existing outbox → APNs; Live Activity/Dynamic Island | Explicit consent, dedupe/quiet hours; provider-backed status only |
| Context/recommendations | Bounded focus/task context and moderate temporal recommender | See `assistant-context.md` and `recommender-plan.md`; no transcript-to-fact promotion |
| Expansion | Voice, App Intents, event/occasion suggestions and sponsorship | Separate source permissions/scope decisions and physical-device checks |

## Web contracts the native client must reuse (23 Oct, FIN-08)

The web app on `redesign` is the reference implementation. Native screens call the same endpoints and keep the same rules; nothing below is re-decided in Swift.

| Surface | Endpoint(s) | Contract |
|---|---|---|
| Today / Needs you | `GET /api/today` | `needs_you.tasks[].decision` = `{kind: approve\|check\|deadline, title, detail, action_id, revision, snapshot_hash?, amount_aed?, earlier_target?}`. Only crucial stops; each task appears in one lane. `counts` = `needs_you, running, on_list, paused`. `scheduled.tasks` carry `check_back_at`. |
| Decision card | `GET /api/actions/{id}`, `POST /api/actions/{id}/approve` (Idempotency-Key, `snapshot_hash`, `revision`), `POST /api/actions/{id}/cancel`, `POST /api/tasks/from-action` (Not now) | Anatomy: context chip, amount, title, Will be shared / Never shared, note, Approve, Not now, Discard. Approve sends the exact revision on screen; 409 means reload. |
| Result card | — (client) | Context, title, verdict first, `Updated hh:mm`, Keep on Today (`/api/tasks/from-action` or `/from-report`), open. |
| Brief | `GET /api/today`, `GET/PUT /api/routines/brief` | "N moving and N need you", one line per item led by a chip. Deterministic; never model text. Daily routine: opt-in, 07:00–22:59, 30-day expiry. |
| Task commands | `POST /api/tasks/{id}/commands` | Kinds: edit, pause, resume, cancel, complete, `check_back` (`at` or null), `staged_next`, `collect`. Always `expected_revision` + `command_key`. |
| Messages | `GET /api/messages`, `/api/messages/stream` | Outbox only (consented, deduped, quiet hours). `task_checkback` carries `task_id`. Native maps these to APNs later; no LLM decides timing. |
| Follow-up mode | `GET/PUT /api/assist` | `ask \| auto \| learn`; `offer_auto` drives Learn's one-time offer. No mode sends, shares or pays. |
| Lost item (TAXI-02) | task commands above | Receipt-first quick replies; trip confirmed before the report; staged replies labelled at every step; collection only, delivery shown unavailable. |

**Mac toolchain (23 Oct):** Xcode 26.3 with iPhone 17 Pro / Pro Max / Air simulators is installed on the founder's Mac, so SwiftUI Previews and Simulator runs are available locally. Resume from `origin/ios-swift` (`eba81b7`) after rebasing or merging `redesign`.

## Founder review before native parity

Web walkthrough is available before the full native client. Known gaps: original Postgres recovery unresolved; preview uses separate SQLite review data; production identity/roles and complete forgetting across checkpoints are unfinished; broad recommender/context features are planned; physical Safari/phone validation remains. Existing configured Google/search/product APIs were live checked. Native source, successful compilation, Simulator run and device acceptance must be recorded separately in the handoff.

## Handoff checkpoint

Native feature work is parked at the founder's request. `cfb65a4` passed seven package tests and the unsigned Simulator build in macOS CI run 39585052919; physical UI review is still pending. See root `handoff-ios.md` for Mac steps and remaining parity. Backend/recommender work resumes on `redesign`; Google OAuth is deferred until last for the single tester.
