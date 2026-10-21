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

## Founder review before native parity

Web walkthrough is available before the full native client. Known gaps: original Postgres recovery unresolved; preview uses separate SQLite review data; production identity/roles and complete forgetting across checkpoints are unfinished; broad recommender/context features are planned; physical Safari/phone validation remains. Existing configured Google/search/product APIs were live checked. Native source, successful compilation, Simulator run and device acceptance must be recorded separately in the handoff.
