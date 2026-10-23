# Dubai-io native iOS preview

Native SwiftUI, iOS 26+, Apple frameworks and one local Swift package. Open the checked-in project directly; no Expo, JavaScript runtime or project-generation tool is needed.

## On your Mac

1. Pull `ios-swift`, then open `apps/ios/DubaiIO.xcodeproj` in Xcode with the iOS 26 or newer SDK.
2. Choose the **DubaiIO** scheme and an iPhone Simulator. Run.
3. In **Me**, enter your FastAPI server address and connect. If the server runs on the Windows PC, use `http://<pc-ip>:8000` in this Debug build. Simulator `localhost` is the Mac; iPhone `localhost` is the phone. Accept the local-network permission if prompted. The API must be reachable on the same network.
4. For your iPhone 13 Pro Max, choose your signing team under Signing & Capabilities, set an available bundle identifier if required, select the connected iPhone and run. iOS 26+ is required.

Release builds require HTTPS and contain no local HTTP ATS exception. Provider and LLM keys stay on FastAPI. Changing server clears the in-memory chat/thread; drafts are preserved. Initial ownership is an anonymous API cookie session, not Supabase sign-in or a cross-device account.

## This slice

- Labelled Wi-Fi/arrival preview and animated gradient introduction.
- Native browse dock collapses to a single focused chat composer; Back restores browsing/draft.
- Real Luna chat, research sources/product links and typed API errors.
- Published sandbox service catalog, saved details and connection status.
- Live Google Places + Google static-map pins; one category row; explicit separate MapKit 3D area preview.
- Third-party HTTP(S) links open in a Safari browsing sheet and return to the current app state.

Native merchant approval/mini-app/SSE parity, production Auth, APNs/Live Activities and full itinerary/recommendation context are next slices. Native sign-in is intentionally unavailable until its callback and ownership contract exist. Viewing an external checkout does not establish that anything was booked or paid.

## Checks

```sh
swift test --package-path apps/ios/Core
xcodebuild -project apps/ios/DubaiIO.xcodeproj -scheme DubaiIO \
  -configuration Debug -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath output/ios-build CODE_SIGNING_ALLOWED=NO build
```

The macOS CI workflow runs these checks. A successful compile does not establish iPhone appearance/performance or a completed app conversion. See [native plan](../../docs/references/ios-swift-plan.md) and [handoff](../../handoff.md) for actual status.

`tools/generate_project.py` reproduces the checked-in project after adding/removing source files; this is a maintainer helper, not a build prerequisite.
