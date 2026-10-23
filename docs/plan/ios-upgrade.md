# iOS upgrade plan — Liquid Glass rebuild of the native app (23 Oct 2026)

Status: founder un-parked native work on 23 Oct ("built by a low-quality LLM, needs substantial upgrade… should be Liquid Glass"). This plan replaces the look and structure of `apps/ios/DubaiIO/` (about 2,900 lines across 13 views). `apps/ios/Core` (typed API client, models, contract tests) stays and only grows. Backend contracts are unchanged; anything new goes through `docs/request-backlog.md`.

## 1. Quality bar

- Reads like an Apple first-party iOS 26 app (Messages, Weather, Maps, Music): system typography and Dynamic Type, native navigation, nothing that looks like a web page in a frame.
- **Liquid Glass on the navigation layer only:** tab bar, toolbars, floating controls, sheets and the composer. Content (lists, cards, text) stays flat and readable. No added shadows (root rule); the system's own glass rendering is fine.
- Accessibility is part of done: Reduce Transparency (glass falls back to solid materials), Reduce Motion (no shader animation), Increase Contrast, VoiceOver labels, Dynamic Type up to AX sizes without clipping.
- Root rules still bind: truth in status, provenance and `Demo data` pills, no official branding, approval cards before side effects.

## 2. Liquid Glass usage (iOS 26 SDK)

| Surface | API |
|---|---|
| Tab bar | `TabView` with `Tab`s; Ask as `Tab(role: .search)`; `.tabBarMinimizeBehavior(.onScrollDown)`; `.tabViewBottomAccessory` for the active-task chip |
| Toolbars / nav bars | Standard `.toolbar` items (glass by default); `ToolbarSpacer` to group |
| Floating controls (map buttons, composer actions) | `.glassEffect(.regular.interactive(), in: .capsule)` inside a `GlassEffectContainer`; `glassEffectID` + `@Namespace` for morphs |
| Buttons | `.buttonStyle(.glass)` secondary, `.buttonStyle(.glassProminent)` for the one primary action per screen, tinted cyan |
| Hero images (Home, service detail) | `.backgroundExtensionEffect()` so the image extends under the glass bars |
| Sheets | System sheets (glass at partial detents); full-height content uses navigation push, not sheets (calls/panels plan §3) |

Never stack glass on glass; never put glass on scrolling content rows.

## 3. Libraries

- **ShipSwift** (`github.com/signerlabs/ShipSwift`, MIT): added as a Swift package dependency, pinned to an exact tag or commit; licence notice kept in `apps/ios/README.md` and an in-app Acknowledgements row. Uses, one effect per screen at a time:
  - Intro and hero field: `SWAnimatedMeshGradient` / `SWGrainGradient` in the cyan palette.
  - Assistant orb (avatar plus thinking state): `SWGlassOrb` or `SWMetaballs`.
  - "Found it" sparkle: `SWGlitter`, only when a search finds a real result. Never for a booking or payment status without provider evidence.
- **Libraries.dev** (React-only): rebuilt natively, not imported. A border beam on the composer while Luna is thinking, a voice glow on the mic, thinking-orb states. Palette `ocean`/cyan only; one glow at a time; all off under Reduce Motion.
- **Other founder-supplied libraries:** pending. The founder said there are more; list them here with licence and intended use before S2 starts.

## 4. Slices (in order; each reviewed separately)

| Slice | Scope | Owner |
|---|---|---|
| S0 | Screenshot harness: a DEBUG-only launch argument (`-screen home\|chat\|chat.thread\|calls\|feed\|feed.post\|services\|ask\|me\|settings`) that opens that screen with a reachable API, plus `apps/ios/tools/screens.sh`, which builds, installs and saves `simctl` screenshots for iPhone 17 Pro and Pro Max in light, dark and reduced-motion. Fix the README build command (it fails on x86_64: `Unable to find module dependency: 'DubaiIOCore'`; pass `ARCHS=arm64`, or fix the package architecture). Baseline screenshot set committed under `design/ios-baseline/`. | Claude (main) |
| S1 | Design system + shell: `DesignSystem.swift` (colors as asset tokens, type scale, spacing, glass helpers, `DemoPill`, provenance chip), new iOS 26 `TabView` shell (Home, Chat, Services, Feed, Ask as search role), Me in the toolbar, ShipSwift dependency added, intro rebuilt on a mesh gradient. Every later slice must use the design system. | Claude (main) |
| S2 | Home / Today: hero with background extension, task lanes, briefing, news; real empty states. | Sonnet subagent |
| S3 | Chat hub + WhatsApp-style calls (calls plan §1: Call header, call/keypad/favorites carousel, search row, contacts fixed right, `tel:` handoff) + threads pushed on navigation (calls plan §3). | Sonnet subagent |
| S4 | Feed + post thread pushed on navigation; stories viewer; AI-persona replies labelled; reply status from the API's `generation` field. | Sonnet subagent |
| S5 | Services: 3.1 thumbnails per row with snap (calls plan §2), provider detail, mini-app host sheet unchanged in behavior. | Sonnet subagent |
| S6 | Ask (Luna chat): glass composer with beam, orb thinking states, sources/product links, draft preserved. | Claude (main) |
| S7 | New settings screen (founder decision 23 Oct) pushed from Me: server, notifications, data/forget, acknowledgements. Profile ("You told me" / "I noticed") stays per rule 9. | Sonnet subagent |
| S8 | Maps: glass floating controls, category row, honest pins (user-confirmed places only). | Sonnet subagent |

## 5. Gates (every slice)

1. `swift test --package-path apps/ios/Core` green, and the Simulator build green (S0 fixes the command).
2. `apps/ios/tools/screens.sh` screenshots for the slice's screens at both phone sizes in light, dark, reduced-motion and reduce-transparency, compared against the S0 baseline.
3. No new warnings; no `.shadow(`; no hard-coded colors outside `DesignSystem.swift`.
4. **Founder visual review** of the screenshot set; build-green is not design-accepted (same gate as the website).

## 6. Open questions

1. The founder's other libraries (§3): where are they?
2. Physical iPhone check (iPhone 13 Pro Max on iOS 26) after S1, or only at the end?
