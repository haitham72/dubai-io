# iOS handoff — 21 Oct 2026

Native work is parked at the founder's request while backend/recommender work resumes on `redesign`. Use branch **`ios-swift`**, build commit **`cfb65a4`**. The client is a first slice and still needs substantial work before web feature parity.

## Verified

- [macOS CI run 39585052919](https://github.com/haitham72/dubai-io/actions/runs/39585052919): seven Swift package tests passed; unsigned iOS Simulator build succeeded with Xcode 26.6 / Swift 6.3.3. The earlier failure was fixed in `cfb65a4`.
- No Simulator UI session or physical iPhone run has been verified. Compilation does not establish visual or interaction acceptance.
- Native onboarding/Wi-Fi concept and gradients, browse dock that collapses into chat, live Luna chat, published sandbox catalog, Google 2D discovery, separate illustrative MapKit 3D area preview, saved facts, API settings and Safari browsing sheets are implemented.
- Typed URLSession client, anonymous cookie session, URL restrictions and API contract tests live in `apps/ios/Core`. No external Swift dependencies or project generation step are required.

## Test on the Mac

1. Pull `ios-swift`; open `apps/ios/DubaiIO.xcodeproj` in Xcode with iOS 26 SDK support. Select the shared `DubaiIO` scheme and an iPhone Simulator, then Run.
2. Run the existing FastAPI backend. In **Me**, set its reachable API base URL. Simulator `localhost` is the Mac; iPhone `localhost` is the phone. For a Windows backend use its LAN address. Debug allows local HTTP; release requires HTTPS.
3. For iPhone 13 Pro Max, use iOS 26+, select a signing team and unique bundle identifier, trust the developer profile if requested, then Run.
4. Review gradients/reduced motion, keyboard and single chat composer, Back restoring browse state, category drill-down/cyan selection, explicit 2D/3D switching, Google attribution, unavailable API states and closing Safari back to the same screen.

Detailed setup: `apps/ios/README.md`. Do not install a Windows Swift toolchain to force device validation.

## Still required

1. Native approval/order cards, isolated merchant mini-app bridge, host price reconciliation and SSE reconnect. Never expose a fake Send or claim an order is confirmed from model text.
2. Full arrival-guide and lost-item flow parity, including official handoff and clear status.
3. Production identity/roles and anonymous-owner transfer. **Google OAuth is explicitly deferred until last: the single tester can use the existing cookie session.** No public `tester` identity bypass or embedded secrets.
4. New backend recommender, bounded selected-card/task context and draft-plan interfaces; connect the native client after those contracts stabilize.
5. Optional APNs/Live Activity, voice and App Intents, then measured accessibility/performance/device review.

## Backend continuity

Supabase is the selected target, retaining FastAPI/LangGraph and the deterministic action engine. The old Docker Postgres remains unrecovered; preserve its volume. The web review server uses separate SQLite data, not recovered records. Do not copy credentials or private data into the native repository.

The remaining request order and implementation status live in `docs/request-backlog.md`; `PLAN.md` and `ARCHITECTURE.md` remain authoritative for execution boundaries.
